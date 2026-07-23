\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_backfill_check NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_backfill_check;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA provider_assessment TO pa_backfill_check;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA provider_assessment TO pa_backfill_check;

SET ROLE pa_backfill_check;

SELECT set_config('app.institution_id', 'INST-B001', false);
SELECT set_config('app.provider_id', 'PROV-B001', false);
SELECT set_config('app.audit_scope', '', false);

DO $$
DECLARE
    observed_plan_group text;
    observed_plan_version integer;
    observed_review_group text;
    observed_review_version integer;
    observed_created_by text;
BEGIN
    SELECT plan_group_id, version
    INTO observed_plan_group, observed_plan_version
    FROM assessment_plans
    WHERE assessment_plan_id = 'PLAN-BLEGACY01';

    SELECT review_group_id, version, created_by_provider_id
    INTO observed_review_group, observed_review_version, observed_created_by
    FROM team_reviews
    WHERE team_review_id = 'TREV-BLEGACY01';

    IF observed_plan_group <> 'PLAN-BLEGACY01' OR observed_plan_version <> 1 THEN
        RAISE EXCEPTION 'Legacy assessment plan was not backfilled correctly: %, %', observed_plan_group, observed_plan_version;
    END IF;

    IF observed_review_group <> 'TREV-BLEGACY01' OR observed_review_version <> 1 THEN
        RAISE EXCEPTION 'Legacy team review was not backfilled correctly: %, %', observed_review_group, observed_review_version;
    END IF;

    IF observed_created_by <> 'PROV-B001' THEN
        RAISE EXCEPTION 'Legacy team review creator was not derived correctly: %', observed_created_by;
    END IF;
END;
$$;

DO $$
DECLARE
    immutable_restored boolean := false;
BEGIN
    BEGIN
        UPDATE team_reviews
        SET limitations = 'This post-migration update must be rejected.'
        WHERE team_review_id = 'TREV-BLEGACY01';
    EXCEPTION
        WHEN raise_exception THEN
            immutable_restored := true;
    END;

    IF NOT immutable_restored THEN
        RAISE EXCEPTION 'Team-review immutability trigger was not restored after legacy backfill';
    END IF;
END;
$$;

INSERT INTO report_versions (
    report_version_id,
    report_id,
    institution_id,
    case_id,
    team_review_id,
    version,
    status,
    template_version,
    content_reference,
    content_hash,
    created_by_provider_id
) VALUES (
    'RPTV-BLEGACY01',
    'RPT-BLEGACY01',
    'INST-B001',
    'CASE-B0000001',
    'TREV-BLEGACY01',
    1,
    'draft',
    '0.1.0',
    'SYNTHETIC-LEGACY-BACKFILL-REPORT',
    repeat('5', 64),
    'PROV-B001'
);

DO $$
DECLARE
    report_count integer;
BEGIN
    SELECT count(*)
    INTO report_count
    FROM report_versions
    WHERE report_id = 'RPT-BLEGACY01';

    IF report_count <> 1 THEN
        RAISE EXCEPTION 'Expected one report from the backfilled approved review, found %', report_count;
    END IF;
END;
$$;

RESET ROLE;

DROP OWNED BY pa_backfill_check;
DROP ROLE pa_backfill_check;

SELECT '0.2.2 legacy backfill and trigger-restoration checks passed' AS result;
