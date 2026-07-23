BEGIN;

SET search_path TO provider_assessment, public;

CREATE OR REPLACE FUNCTION enforce_case_safety_hold()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.level IN ('urgent', 'emergency') THEN
        UPDATE cases
        SET safety_level = NEW.level,
            status = 'safety_hold'
        WHERE case_id = NEW.case_id
          AND institution_id = NEW.institution_id
          AND (
              safety_level IS DISTINCT FROM NEW.level
              OR status IS DISTINCT FROM 'safety_hold'
          );
    ELSIF NEW.level = 'monitor' THEN
        UPDATE cases
        SET safety_level = 'monitor'
        WHERE case_id = NEW.case_id
          AND institution_id = NEW.institution_id
          AND safety_level = 'none_identified';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION current_institution_last_audit_hash()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = provider_assessment, pg_temp
AS $$
DECLARE
    current_institution text;
    latest_hash text;
BEGIN
    current_institution := nullif(current_setting('app.institution_id', true), '');
    IF current_institution IS NULL THEN
        RAISE EXCEPTION 'institution context is required for the audit chain';
    END IF;

    PERFORM pg_advisory_xact_lock(hashtextextended(current_institution, 0));

    SELECT event_hash
    INTO latest_hash
    FROM audit_events
    WHERE institution_id = current_institution
    ORDER BY occurred_at DESC, audit_event_id DESC
    LIMIT 1;

    RETURN latest_hash;
END;
$$;

CREATE OR REPLACE FUNCTION enforce_audit_event_chain()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = provider_assessment, pg_temp
AS $$
DECLARE
    expected_previous_hash text;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(NEW.institution_id, 0));

    SELECT event_hash
    INTO expected_previous_hash
    FROM audit_events
    WHERE institution_id = NEW.institution_id
    ORDER BY occurred_at DESC, audit_event_id DESC
    LIMIT 1;

    IF NEW.previous_event_hash IS DISTINCT FROM expected_previous_hash THEN
        RAISE EXCEPTION 'audit chain conflict for institution %', NEW.institution_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER audit_events_chain_guard
BEFORE INSERT ON audit_events
FOR EACH ROW EXECUTE FUNCTION enforce_audit_event_chain();

COMMENT ON FUNCTION current_institution_last_audit_hash() IS
'Returns only the opaque terminal audit hash for the current app.institution_id and holds the institution advisory lock for the surrounding transaction.';

COMMENT ON FUNCTION enforce_audit_event_chain() IS
'Prevents audit forks by validating previous_event_hash against the institution terminal hash under a transaction-scoped advisory lock.';

COMMENT ON FUNCTION enforce_case_safety_hold() IS
'Defense-in-depth safety routing. It becomes a no-op when the application service already applied the same urgent state and never downgrades an urgent or emergency state from a monitor event.';

COMMIT;
