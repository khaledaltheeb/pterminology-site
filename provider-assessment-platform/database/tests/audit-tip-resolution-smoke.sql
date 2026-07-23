\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_audit_tip NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_audit_tip;
GRANT SELECT, INSERT ON audit_events TO pa_audit_tip;
GRANT EXECUTE ON FUNCTION current_institution_last_audit_hash() TO pa_audit_tip;
GRANT EXECUTE ON FUNCTION institution_audit_chain_tip(text) TO pa_audit_tip;

SET ROLE pa_audit_tip;
SELECT set_config('app.institution_id', 'INST-ALIGN01', false);
SELECT set_config('app.provider_id', 'PROV-ALIGN01', false);
SELECT set_config('app.audit_scope', '', false);

DO $$
DECLARE
    previous_hash text;
    observed_tip text;
BEGIN
    previous_hash := current_institution_last_audit_hash();
    IF previous_hash <> repeat('c', 64) THEN
        RAISE EXCEPTION 'Unexpected pre-test audit tip: %', previous_hash;
    END IF;

    INSERT INTO audit_events (
        audit_event_id,
        institution_id,
        case_id,
        actor_provider_id,
        occurred_at,
        action,
        object_type,
        object_id,
        reason,
        correlation_id,
        previous_event_hash,
        event_hash,
        metadata
    ) VALUES (
        'AUD-TIPTEST0001',
        'INST-ALIGN01',
        'CASE-CREATE0001',
        'PROV-ALIGN01',
        TIMESTAMPTZ '2001-01-01 00:00:00+00',
        'synthetic.audit.out_of_order_time',
        'synthetic_record',
        'SYNTHETIC-AUDIT-TIP-01',
        'Synthetic event uses an older timestamp but is the next cryptographic link.',
        'CORR-AUDIT-TIP-0001',
        previous_hash,
        repeat('9', 64),
        '{}'::jsonb
    );

    observed_tip := current_institution_last_audit_hash();
    IF observed_tip <> repeat('9', 64) THEN
        RAISE EXCEPTION 'Audit tip was resolved by timestamp instead of hash links: %', observed_tip;
    END IF;
END;
$$;

RESET ROLE;

INSERT INTO institutions (
    institution_id,
    legal_name,
    country_code,
    active,
    authorization_expires_at,
    data_processing_agreement_active,
    clinical_governance_active,
    emergency_configuration_active
) VALUES (
    'INST-FORK01',
    'Synthetic Fork Detection Institution',
    'JO',
    true,
    DATE '2099-12-31',
    true,
    true,
    true
);

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
    'PROV-FORK01',
    'INST-FORK01',
    true,
    '["quality_auditor"]'::jsonb,
    'SYNTHETIC-LICENSE-FORK01',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar"]'::jsonb
);

ALTER TABLE audit_events DISABLE TRIGGER audit_events_chain_guard;

INSERT INTO audit_events (
    audit_event_id,
    institution_id,
    case_id,
    actor_provider_id,
    occurred_at,
    action,
    object_type,
    object_id,
    reason,
    correlation_id,
    previous_event_hash,
    event_hash,
    metadata
) VALUES
(
    'AUD-FORK00000001',
    'INST-FORK01',
    NULL,
    'PROV-FORK01',
    TIMESTAMPTZ '2026-07-23 22:00:00+00',
    'synthetic.audit.root',
    'synthetic_record',
    'SYNTHETIC-FORK-ROOT',
    'Synthetic root for deliberate historical fork detection.',
    'CORR-FORK-ROOT-0001',
    NULL,
    repeat('1', 64),
    '{}'::jsonb
),
(
    'AUD-FORK00000002',
    'INST-FORK01',
    NULL,
    'PROV-FORK01',
    TIMESTAMPTZ '2026-07-23 22:01:00+00',
    'synthetic.audit.branch_a',
    'synthetic_record',
    'SYNTHETIC-FORK-A',
    'Synthetic first branch for deliberate historical fork detection.',
    'CORR-FORK-A-0001',
    repeat('1', 64),
    repeat('2', 64),
    '{}'::jsonb
),
(
    'AUD-FORK00000003',
    'INST-FORK01',
    NULL,
    'PROV-FORK01',
    TIMESTAMPTZ '2026-07-23 22:02:00+00',
    'synthetic.audit.branch_b',
    'synthetic_record',
    'SYNTHETIC-FORK-B',
    'Synthetic second branch for deliberate historical fork detection.',
    'CORR-FORK-B-0001',
    repeat('1', 64),
    repeat('3', 64),
    '{}'::jsonb
);

ALTER TABLE audit_events ENABLE TRIGGER audit_events_chain_guard;

DO $$
DECLARE
    fork_detected boolean := false;
BEGIN
    BEGIN
        PERFORM institution_audit_chain_tip('INST-FORK01');
    EXCEPTION
        WHEN raise_exception THEN
            fork_detected := true;
    END;

    IF NOT fork_detected THEN
        RAISE EXCEPTION 'A pre-existing audit-chain fork was not detected';
    END IF;
END;
$$;

DROP OWNED BY pa_audit_tip;
DROP ROLE pa_audit_tip;

SELECT 'link-derived audit tip, out-of-order timestamp handling, and fork detection passed' AS result;
