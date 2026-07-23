\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_version_test NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_version_test;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA provider_assessment TO pa_version_test;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA provider_assessment TO pa_version_test;

SET ROLE pa_version_test;

SELECT set_config('app.institution_id', 'INST-B001', false);
SELECT set_config('app.provider_id', 'PROV-B001', false);
SELECT set_config('app.audit_scope', '', false);

INSERT INTO providers (
    provider_id,
    institution_id,
    active,
    roles,
    professional_license_reference,
    professional_license_expires_at,
    professional_license_status,
    mfa_enabled,
    languages
) VALUES (
    'PROV-B002',
    'INST-B001',
    true,
    '["clinical_reviewer"]'::jsonb,
    'SYNTHETIC-LICENSE-B2',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar"]'::jsonb
);

INSERT INTO pathway_instances (
    pathway_instance_id,
    institution_id,
    case_id,
    pathway_id,
    pathway_version,
    pathway_definition_hash,
    current_node_id,
    status,
    started_by_provider_id
) VALUES (
    'PTH-B0000001',
    'INST-B001',
    'CASE-B0000001',
    'developmental-intake',
    '0.1.0',
    repeat('1', 64),
    'battery-planning',
    'active',
    'PROV-B001'
);

INSERT INTO assessment_plans (
    assessment_plan_id,
    institution_id,
    case_id,
    pathway_instance_id,
    plan_group_id,
    version,
    domains,
    assessment_ids,
    rationale,
    status,
    created_by_provider_id
) VALUES (
    'PLAN-B0000001',
    'INST-B001',
    'CASE-B0000001',
    'PTH-B0000001',
    'PLANG-B0000001',
    1,
    '["development", "participation"]'::jsonb,
    '["developmental-history-interview"]'::jsonb,
    'Synthetic initial assessment plan draft for version-chain testing.',
    'draft',
    'PROV-B001'
);

INSERT INTO assessment_plans (
    assessment_plan_id,
    institution_id,
    case_id,
    pathway_instance_id,
    plan_group_id,
    version,
    domains,
    assessment_ids,
    rationale,
    status,
    approved_by_provider_id,
    approved_at,
    created_by_provider_id,
    supersedes_plan_id
) VALUES (
    'PLAN-B0000002',
    'INST-B001',
    'CASE-B0000001',
    'PTH-B0000001',
    'PLANG-B0000001',
    2,
    '["development", "participation"]'::jsonb,
    '["developmental-history-interview", "functional-observation"]'::jsonb,
    'Synthetic approved assessment plan with a documented second evidence source.',
    'approved',
    'PROV-B001',
    now(),
    'PROV-B001',
    'PLAN-B0000001'
);

DO $$
DECLARE
    invalid_version_blocked boolean := false;
BEGIN
    BEGIN
        INSERT INTO assessment_plans (
            assessment_plan_id,
            institution_id,
            case_id,
            pathway_instance_id,
            plan_group_id,
            version,
            domains,
            assessment_ids,
            rationale,
            status,
            approved_by_provider_id,
            approved_at,
            created_by_provider_id,
            supersedes_plan_id
        ) VALUES (
            'PLAN-B0000003',
            'INST-B001',
            'CASE-B0000001',
            'PTH-B0000001',
            'PLANG-B0000001',
            4,
            '["development"]'::jsonb,
            '[]'::jsonb,
            'This version intentionally skips the required next version number.',
            'approved',
            'PROV-B001',
            now(),
            'PROV-B001',
            'PLAN-B0000002'
        );
    EXCEPTION
        WHEN raise_exception THEN
            invalid_version_blocked := true;
    END;

    IF NOT invalid_version_blocked THEN
        RAISE EXCEPTION 'Assessment plan version skip was not blocked';
    END IF;
END;
$$;

DO $$
DECLARE
    update_blocked boolean := false;
BEGIN
    BEGIN
        UPDATE assessment_plans
        SET rationale = 'This update must be blocked.'
        WHERE assessment_plan_id = 'PLAN-B0000002';
    EXCEPTION
        WHEN raise_exception THEN
            update_blocked := true;
    END;

    IF NOT update_blocked THEN
        RAISE EXCEPTION 'Append-only assessment plan update was not blocked';
    END IF;
END;
$$;

INSERT INTO team_reviews (
    team_review_id,
    institution_id,
    case_id,
    pathway_instance_id,
    review_group_id,
    version,
    status,
    member_provider_ids,
    decision,
    supporting_evidence_ids,
    contrary_evidence_ids,
    limitations,
    support_needs,
    created_by_provider_id
) VALUES (
    'TREV-B0000001',
    'INST-B001',
    'CASE-B0000001',
    'PTH-B0000001',
    'TREVG-B0000001',
    1,
    'draft',
    '["PROV-B001"]'::jsonb,
    'Synthetic draft review awaiting a second reviewer and additional evidence.',
    '["PLAN-B0000002"]'::jsonb,
    '[]'::jsonb,
    'The review is not approved and cannot support report creation.',
    '["continue evidence review"]'::jsonb,
    'PROV-B001'
);

DO $$
DECLARE
    report_from_draft_blocked boolean := false;
BEGIN
    BEGIN
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
            'RPTV-B0000001',
            'RPT-B0000001',
            'INST-B001',
            'CASE-B0000001',
            'TREV-B0000001',
            1,
            'draft',
            '0.1.0',
            'SYNTHETIC-REPORT-DRAFT-INVALID',
            repeat('2', 64),
            'PROV-B001'
        );
    EXCEPTION
        WHEN raise_exception THEN
            report_from_draft_blocked := true;
    END;

    IF NOT report_from_draft_blocked THEN
        RAISE EXCEPTION 'Report creation from an unapproved team review was not blocked';
    END IF;
END;
$$;

INSERT INTO team_reviews (
    team_review_id,
    institution_id,
    case_id,
    pathway_instance_id,
    review_group_id,
    version,
    status,
    member_provider_ids,
    decision,
    supporting_evidence_ids,
    contrary_evidence_ids,
    limitations,
    support_needs,
    approved_by_provider_id,
    approved_at,
    created_by_provider_id,
    supersedes_team_review_id
) VALUES (
    'TREV-B0000002',
    'INST-B001',
    'CASE-B0000001',
    'PTH-B0000001',
    'TREVG-B0000001',
    2,
    'approved',
    '["PROV-B001", "PROV-B002"]'::jsonb,
    'Synthetic multidisciplinary decision approved after independent review.',
    '["PLAN-B0000002", "SRC-SYNTHETIC-B1"]'::jsonb,
    '["SRC-SYNTHETIC-B2"]'::jsonb,
    'Synthetic limitations remain explicit and prevent unsupported generalization.',
    '["documented follow-up", "functional support"]'::jsonb,
    'PROV-B002',
    now(),
    'PROV-B001',
    'TREV-B0000001'
);

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
    'RPTV-B0000002',
    'RPT-B0000002',
    'INST-B001',
    'CASE-B0000001',
    'TREV-B0000002',
    1,
    'draft',
    '0.1.0',
    'SYNTHETIC-REPORT-DRAFT-VALID',
    repeat('3', 64),
    'PROV-B001'
);

DO $$
DECLARE
    current_plan_version integer;
    current_review_version integer;
    report_count integer;
BEGIN
    SELECT version
    INTO current_plan_version
    FROM current_assessment_plans
    WHERE case_id = 'CASE-B0000001'
      AND plan_group_id = 'PLANG-B0000001';

    SELECT version
    INTO current_review_version
    FROM current_team_reviews
    WHERE case_id = 'CASE-B0000001'
      AND review_group_id = 'TREVG-B0000001';

    SELECT count(*)
    INTO report_count
    FROM report_versions
    WHERE report_id = 'RPT-B0000002';

    IF current_plan_version <> 2 THEN
        RAISE EXCEPTION 'Expected current plan version 2, found %', current_plan_version;
    END IF;

    IF current_review_version <> 2 THEN
        RAISE EXCEPTION 'Expected current review version 2, found %', current_review_version;
    END IF;

    IF report_count <> 1 THEN
        RAISE EXCEPTION 'Expected one report from the approved review, found %', report_count;
    END IF;
END;
$$;

DO $$
DECLARE
    update_blocked boolean := false;
BEGIN
    BEGIN
        UPDATE team_reviews
        SET limitations = 'This update must be blocked.'
        WHERE team_review_id = 'TREV-B0000002';
    EXCEPTION
        WHEN raise_exception THEN
            update_blocked := true;
    END;

    IF NOT update_blocked THEN
        RAISE EXCEPTION 'Append-only team review update was not blocked';
    END IF;
END;
$$;

RESET ROLE;

DROP OWNED BY pa_version_test;
DROP ROLE pa_version_test;

SELECT 'review and assessment-plan versioning smoke tests passed' AS result;
