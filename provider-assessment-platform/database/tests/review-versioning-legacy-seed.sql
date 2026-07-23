\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_legacy_seed NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_legacy_seed;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA provider_assessment TO pa_legacy_seed;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA provider_assessment TO pa_legacy_seed;

SET ROLE pa_legacy_seed;

SELECT set_config('app.institution_id', 'INST-B001', false);
SELECT set_config('app.provider_id', 'PROV-B001', false);
SELECT set_config('app.audit_scope', '', false);

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
    'PTH-BLEGACY01',
    'INST-B001',
    'CASE-B0000001',
    'developmental-intake',
    '0.1.0',
    repeat('4', 64),
    'multidisciplinary-review',
    'active',
    'PROV-B001'
);

INSERT INTO assessment_plans (
    assessment_plan_id,
    institution_id,
    case_id,
    pathway_instance_id,
    version,
    domains,
    assessment_ids,
    rationale,
    status,
    approved_by_provider_id,
    approved_at,
    created_by_provider_id
) VALUES (
    'PLAN-BLEGACY01',
    'INST-B001',
    'CASE-B0000001',
    'PTH-BLEGACY01',
    1,
    '["development", "participation"]'::jsonb,
    '["developmental-history-interview"]'::jsonb,
    'Synthetic legacy assessment plan created before stable plan-group identifiers.',
    'approved',
    'PROV-B001',
    now(),
    'PROV-B001'
);

INSERT INTO team_reviews (
    team_review_id,
    institution_id,
    case_id,
    pathway_instance_id,
    status,
    member_provider_ids,
    decision,
    supporting_evidence_ids,
    contrary_evidence_ids,
    limitations,
    support_needs,
    approved_by_provider_id,
    approved_at
) VALUES (
    'TREV-BLEGACY01',
    'INST-B001',
    'CASE-B0000001',
    'PTH-BLEGACY01',
    'approved',
    '["PROV-B001", "PROV-BLEGACY02"]'::jsonb,
    'Synthetic legacy team decision approved before explicit review versioning.',
    '["PLAN-BLEGACY01"]'::jsonb,
    '[]'::jsonb,
    'Synthetic limitations are long enough for the corrected migration constraints.',
    '["continue documented support"]'::jsonb,
    'PROV-B001',
    now()
);

RESET ROLE;

DROP OWNED BY pa_legacy_seed;
DROP ROLE pa_legacy_seed;

SELECT 'legacy review-versioning fixture inserted' AS result;
