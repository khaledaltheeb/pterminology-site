\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_function_test NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_function_test;
GRANT SELECT, UPDATE ON cases TO pa_function_test;
GRANT INSERT ON safety_events TO pa_function_test;
GRANT EXECUTE ON FUNCTION current_institution_last_audit_hash() TO pa_function_test;

DO $$
BEGIN
    IF NOT has_function_privilege(
        'pa_function_test',
        'provider_assessment.current_institution_last_audit_hash()',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'Service-facing current audit hash function was not granted explicitly';
    END IF;

    IF has_function_privilege(
        'pa_function_test',
        'provider_assessment.institution_audit_chain_tip(text)',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'Internal institution-argument audit helper remained executable';
    END IF;

    IF has_function_privilege(
        'pa_function_test',
        'provider_assessment.enforce_audit_event_chain()',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'Internal audit trigger function remained executable';
    END IF;

    IF has_function_privilege(
        'pa_function_test',
        'provider_assessment.enforce_case_safety_hold()',
        'EXECUTE'
    ) THEN
        RAISE EXCEPTION 'Internal safety trigger function remained executable';
    END IF;
END;
$$;

SET ROLE pa_function_test;
SELECT set_config('app.institution_id', 'INST-ALIGN01', false);
SELECT set_config('app.provider_id', 'PROV-ALIGN01', false);
SELECT set_config('app.audit_scope', '', false);

DO $$
DECLARE
    direct_helper_blocked boolean := false;
    current_hash text;
BEGIN
    current_hash := current_institution_last_audit_hash();
    IF current_hash <> repeat('9', 64) THEN
        RAISE EXCEPTION 'Explicitly granted current audit hash returned an unexpected value: %', current_hash;
    END IF;

    BEGIN
        PERFORM institution_audit_chain_tip('INST-ALIGN01');
    EXCEPTION
        WHEN insufficient_privilege THEN
            direct_helper_blocked := true;
    END;

    IF NOT direct_helper_blocked THEN
        RAISE EXCEPTION 'Internal institution-argument audit helper was callable by the service-like role';
    END IF;
END;
$$;

UPDATE cases
SET safety_level = 'none_identified',
    status = 'intake'
WHERE institution_id = 'INST-ALIGN01'
  AND case_id = 'CASE-CREATE0001';

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
    'SAFE-PRIVTEST0001',
    'INST-ALIGN01',
    'CASE-CREATE0001',
    'urgent',
    '["medical"]'::jsonb,
    'Synthetic event verifies triggers continue to run without direct function execution privilege.',
    '["pause_routine_pathway", "handoff_to_clinical_lead"]'::jsonb,
    'SYNTHETIC-CLINICAL-LEAD',
    now(),
    true,
    'PROV-ALIGN01'
);

DO $$
DECLARE
    observed_level text;
    observed_status text;
BEGIN
    SELECT safety_level, status
    INTO observed_level, observed_status
    FROM cases
    WHERE institution_id = 'INST-ALIGN01'
      AND case_id = 'CASE-CREATE0001';

    IF observed_level <> 'urgent' OR observed_status <> 'safety_hold' THEN
        RAISE EXCEPTION 'Revoked direct trigger execution prevented governed trigger behavior: %, %', observed_level, observed_status;
    END IF;
END;
$$;

RESET ROLE;
DROP OWNED BY pa_function_test;
DROP ROLE pa_function_test;

SELECT 'least-function privilege and trigger execution behavior passed' AS result;
