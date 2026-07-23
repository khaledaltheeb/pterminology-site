BEGIN;

SET search_path TO provider_assessment, public;

CREATE OR REPLACE FUNCTION institution_audit_chain_tip(target_institution text)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = provider_assessment, pg_temp
AS $$
DECLARE
    event_count integer;
    tip_count integer;
    tip_hash text;
BEGIN
    IF target_institution IS NULL OR target_institution = '' THEN
        RAISE EXCEPTION 'institution is required for audit-chain resolution';
    END IF;

    SELECT count(*)
    INTO event_count
    FROM audit_events
    WHERE institution_id = target_institution;

    SELECT count(*), min(parent.event_hash)
    INTO tip_count, tip_hash
    FROM audit_events parent
    WHERE parent.institution_id = target_institution
      AND NOT EXISTS (
          SELECT 1
          FROM audit_events child
          WHERE child.institution_id = parent.institution_id
            AND child.previous_event_hash = parent.event_hash
      );

    IF event_count = 0 THEN
        RETURN NULL;
    END IF;

    IF tip_count <> 1 THEN
        RAISE EXCEPTION 'audit chain must have exactly one terminal event for institution %, found %', target_institution, tip_count;
    END IF;

    RETURN tip_hash;
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
BEGIN
    current_institution := nullif(current_setting('app.institution_id', true), '');
    IF current_institution IS NULL THEN
        RAISE EXCEPTION 'institution context is required for the audit chain';
    END IF;

    PERFORM pg_advisory_xact_lock(hashtextextended(current_institution, 0));
    RETURN institution_audit_chain_tip(current_institution);
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
    expected_previous_hash := institution_audit_chain_tip(NEW.institution_id);

    IF NEW.previous_event_hash IS DISTINCT FROM expected_previous_hash THEN
        RAISE EXCEPTION 'audit chain conflict for institution %', NEW.institution_id;
    END IF;

    RETURN NEW;
END;
$$;

COMMENT ON FUNCTION institution_audit_chain_tip(text) IS
'Resolves exactly one terminal hash from predecessor links, independent of event timestamps or identifier ordering, and rejects forks or closed cycles.';

COMMENT ON FUNCTION current_institution_last_audit_hash() IS
'Returns the unique link-derived terminal hash for app.institution_id while holding the institution transaction advisory lock.';

COMMENT ON FUNCTION enforce_audit_event_chain() IS
'Appends only to the unique link-derived audit-chain terminal under an institution-scoped transaction lock.';

COMMIT;
