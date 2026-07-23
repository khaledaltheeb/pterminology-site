\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

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
    'INST-CYCLE01',
    'Synthetic Cycle Detection Institution',
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
    'PROV-CYCLE01',
    'INST-CYCLE01',
    true,
    '["quality_auditor"]'::jsonb,
    'SYNTHETIC-LICENSE-CYCLE01',
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
    'AUD-CYCLE0000001',
    'INST-CYCLE01',
    NULL,
    'PROV-CYCLE01',
    TIMESTAMPTZ '2026-07-23 23:00:00+00',
    'synthetic.audit.cycle_a',
    'synthetic_record',
    'SYNTHETIC-CYCLE-A',
    'Synthetic first event in a deliberate closed audit cycle.',
    'CORR-CYCLE-A-0001',
    repeat('5', 64),
    repeat('4', 64),
    '{}'::jsonb
),
(
    'AUD-CYCLE0000002',
    'INST-CYCLE01',
    NULL,
    'PROV-CYCLE01',
    TIMESTAMPTZ '2026-07-23 23:01:00+00',
    'synthetic.audit.cycle_b',
    'synthetic_record',
    'SYNTHETIC-CYCLE-B',
    'Synthetic second event closing a deliberate audit cycle.',
    'CORR-CYCLE-B-0001',
    repeat('4', 64),
    repeat('5', 64),
    '{}'::jsonb
);

ALTER TABLE audit_events ENABLE TRIGGER audit_events_chain_guard;

DO $$
DECLARE
    cycle_detected boolean := false;
BEGIN
    BEGIN
        PERFORM institution_audit_chain_tip('INST-CYCLE01');
    EXCEPTION
        WHEN raise_exception THEN
            cycle_detected := true;
    END;

    IF NOT cycle_detected THEN
        RAISE EXCEPTION 'A closed audit-chain cycle with zero terminal events was not detected';
    END IF;
END;
$$;

SELECT 'closed audit-chain cycle detection passed' AS result;
