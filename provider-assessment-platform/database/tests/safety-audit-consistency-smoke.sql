\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_consistency NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_consistency;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA provider_assessment TO pa_consistency;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA provider_assessment TO pa_consistency;

SET ROLE pa_consistency;
SELECT set_config('app.institution_id', 'INST-ALIGN01', false);
SELECT set_config('app.provider_id', 'PROV-ALIGN01', false);
SELECT set_config('app.audit_scope', '', false);

UPDATE cases
SET safety_level = 'urgent',
    status = 'safety_hold'
WHERE case_id = 'CASE-CREATE0001'
  AND institution_id = 'INST-ALIGN01';

DO $$
DECLARE
    version_before_event bigint;
    version_after_event bigint;
BEGIN
    SELECT version INTO version_before_event
    FROM cases
    WHERE case_id = 'CASE-CREATE0001'
      AND institution_id = 'INST-ALIGN01';

    INSERT INTO safety_events (
        safety_event_id,
        institution_id,
        case_id,
        level,
        domains,
        observations,
        immediate_actions,
        handoff_target,
        handoff_confirmed_at,
        routine_pathway_blocked,
        created_by_provider_id
    ) VALUES (
        'SAFE-CONSIST0001',
        'INST-ALIGN01',
        'CASE-CREATE0001',
        'urgent',
        '["medical"]'::jsonb,
        'Synthetic urgent event after the service already applied the hold.',
        '["pause_routine_pathway", "handoff_to_clinical_lead"]'::jsonb,
        'SYNTHETIC-CLINICAL-LEAD',
        now(),
        true,
        'PROV-ALIGN01'
    );

    SELECT version INTO version_after_event
    FROM cases
    WHERE case_id = 'CASE-CREATE0001'
      AND institution_id = 'INST-ALIGN01';

    IF version_after_event <> version_before_event THEN
        RAISE EXCEPTION 'Idempotent safety trigger raised case version twice: % -> %', version_before_event, version_after_event;
    END IF;
END;
$$;

DO $$
DECLARE
    version_before_monitor bigint;
    version_after_monitor bigint;
    observed_level text;
    observed_status text;
BEGIN
    SELECT version INTO version_before_monitor
    FROM cases
    WHERE case_id = 'CASE-CREATE0001'
      AND institution_id = 'INST-ALIGN01';

    INSERT INTO safety_events (
        safety_event_id,
        institution_id,
        case_id,
        level,
        domains,
        observations,
        immediate_actions,
        routine_pathway_blocked,
        created_by_provider_id
    ) VALUES (
        'SAFE-CONSIST0002',
        'INST-ALIGN01',
        'CASE-CREATE0001',
        'monitor',
        '["follow_up"]'::jsonb,
        'Synthetic lower-severity observation that must not clear an urgent hold.',
        '["continue_urgent_hold_review"]'::jsonb,
        false,
        'PROV-ALIGN01'
    );

    SELECT version, safety_level, status
    INTO version_after_monitor, observed_level, observed_status
    FROM cases
    WHERE case_id = 'CASE-CREATE0001'
      AND institution_id = 'INST-ALIGN01';

    IF version_after_monitor <> version_before_monitor THEN
        RAISE EXCEPTION 'Monitor event unexpectedly changed an urgent case version: % -> %', version_before_monitor, version_after_monitor;
    END IF;
    IF observed_level <> 'urgent' OR observed_status <> 'safety_hold' THEN
        RAISE EXCEPTION 'Monitor event downgraded urgent safety state: %, %', observed_level, observed_status;
    END IF;
END;
$$;

DO $$
DECLARE
    previous_hash text;
BEGIN
    previous_hash := current_institution_last_audit_hash();

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
        'AUD-CONSIST0001',
        'INST-ALIGN01',
        'CASE-CREATE0001',
        'PROV-ALIGN01',
        TIMESTAMPTZ '2026-07-23 21:00:00+00',
        'synthetic.audit.first',
        'synthetic_record',
        'SYNTHETIC-AUDIT-OBJECT-01',
        'First synthetic audit event for chain enforcement testing.',
        'CORR-CONSIST-AUDIT-01',
        previous_hash,
        repeat('a', 64),
        '{}'::jsonb
    );
END;
$$;

DO $$
DECLARE
    conflict_blocked boolean := false;
BEGIN
    BEGIN
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
            'AUD-CONSIST0002',
            'INST-ALIGN01',
            'CASE-CREATE0001',
            'PROV-ALIGN01',
            TIMESTAMPTZ '2026-07-23 21:01:00+00',
            'synthetic.audit.conflict',
            'synthetic_record',
            'SYNTHETIC-AUDIT-OBJECT-02',
            'Synthetic audit event with an intentionally stale predecessor.',
            'CORR-CONSIST-AUDIT-02',
            NULL,
            repeat('b', 64),
            '{}'::jsonb
        );
    EXCEPTION
        WHEN raise_exception THEN
            conflict_blocked := true;
    END;

    IF NOT conflict_blocked THEN
        RAISE EXCEPTION 'Stale audit predecessor was not rejected';
    END IF;
END;
$$;

DO $$
DECLARE
    previous_hash text;
    observed_hash text;
BEGIN
    previous_hash := current_institution_last_audit_hash();
    IF previous_hash <> repeat('a', 64) THEN
        RAISE EXCEPTION 'Unexpected terminal audit hash before second valid event: %', previous_hash;
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
        'AUD-CONSIST0003',
        'INST-ALIGN01',
        'CASE-CREATE0001',
        'PROV-ALIGN01',
        TIMESTAMPTZ '2026-07-23 21:02:00+00',
        'synthetic.audit.second',
        'synthetic_record',
        'SYNTHETIC-AUDIT-OBJECT-03',
        'Second valid synthetic audit event for chain enforcement testing.',
        'CORR-CONSIST-AUDIT-03',
        previous_hash,
        repeat('c', 64),
        '{}'::jsonb
    );

    observed_hash := current_institution_last_audit_hash();
    IF observed_hash <> repeat('c', 64) THEN
        RAISE EXCEPTION 'Terminal audit hash did not advance to the second valid event: %', observed_hash;
    END IF;
END;
$$;

RESET ROLE;
DROP OWNED BY pa_consistency;
DROP ROLE pa_consistency;

SELECT 'safety trigger idempotence, non-downgrade, and audit chain enforcement passed' AS result;
