\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_idempotency_test NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_idempotency_test;
GRANT SELECT, INSERT, UPDATE ON idempotency_records TO pa_idempotency_test;

SET ROLE pa_idempotency_test;
SELECT set_config('app.institution_id', 'INST-ALIGN01', false);
SELECT set_config('app.provider_id', 'PROV-ALIGN01', false);
SELECT set_config('app.audit_scope', '', false);

INSERT INTO idempotency_records (
    institution_id,
    provider_id,
    operation,
    idempotency_key,
    request_fingerprint,
    state,
    created_at,
    expires_at
) VALUES (
    'INST-ALIGN01',
    'PROV-ALIGN01',
    'case.create',
    'IDEMPOTENCY-TEST-0001',
    repeat('a', 64),
    'in_progress',
    TIMESTAMPTZ '2026-07-23 22:00:00+00',
    TIMESTAMPTZ '2026-07-24 22:00:00+00'
);

DO $$
DECLARE
    duplicate_mismatch_blocked boolean := false;
BEGIN
    BEGIN
        INSERT INTO idempotency_records (
            institution_id,
            provider_id,
            operation,
            idempotency_key,
            request_fingerprint,
            state,
            created_at,
            expires_at
        ) VALUES (
            'INST-ALIGN01',
            'PROV-ALIGN01',
            'case.create',
            'IDEMPOTENCY-TEST-0001',
            repeat('b', 64),
            'in_progress',
            TIMESTAMPTZ '2026-07-23 22:00:01+00',
            TIMESTAMPTZ '2026-07-24 22:00:01+00'
        );
    EXCEPTION
        WHEN unique_violation THEN
            duplicate_mismatch_blocked := true;
    END;

    IF NOT duplicate_mismatch_blocked THEN
        RAISE EXCEPTION 'Same scoped idempotency key accepted a different request fingerprint';
    END IF;
END;
$$;

SELECT set_config('app.provider_id', 'PROV-ALIGN02', false);

DO $$
DECLARE
    visible_records integer;
BEGIN
    SELECT count(*) INTO visible_records FROM idempotency_records;
    IF visible_records <> 0 THEN
        RAISE EXCEPTION 'A different provider could see another provider idempotency record: %', visible_records;
    END IF;
END;
$$;

SELECT set_config('app.provider_id', 'PROV-ALIGN01', false);

UPDATE idempotency_records
SET state = 'completed',
    http_status = 201,
    response_headers = '{"ETag":"W/\"case-version-1\"","X-Audit-Event-Id":"AUD-TIPTEST0001"}'::jsonb,
    response_payload = '{"case_id":"CASE-CREATE0001","version":1,"status":"intake"}'::jsonb,
    response_payload_hash = repeat('d', 64),
    result_object_type = 'case',
    result_object_id = 'CASE-CREATE0001',
    result_version = 1,
    audit_event_id = 'AUD-TIPTEST0001',
    completed_at = TIMESTAMPTZ '2026-07-23 22:00:02+00'
WHERE institution_id = 'INST-ALIGN01'
  AND provider_id = 'PROV-ALIGN01'
  AND operation = 'case.create'
  AND idempotency_key = 'IDEMPOTENCY-TEST-0001';

DO $$
DECLARE
    mutation_blocked boolean := false;
BEGIN
    BEGIN
        UPDATE idempotency_records
        SET response_payload = '{"case_id":"MUTATED"}'::jsonb
        WHERE institution_id = 'INST-ALIGN01'
          AND provider_id = 'PROV-ALIGN01'
          AND operation = 'case.create'
          AND idempotency_key = 'IDEMPOTENCY-TEST-0001';
    EXCEPTION
        WHEN raise_exception THEN
            mutation_blocked := true;
    END;

    IF NOT mutation_blocked THEN
        RAISE EXCEPTION 'A completed idempotency record remained mutable';
    END IF;
END;
$$;

DO $$
DECLARE
    direct_delete_blocked boolean := false;
BEGIN
    BEGIN
        DELETE FROM idempotency_records
        WHERE institution_id = 'INST-ALIGN01'
          AND provider_id = 'PROV-ALIGN01'
          AND operation = 'case.create'
          AND idempotency_key = 'IDEMPOTENCY-TEST-0001';
    EXCEPTION
        WHEN insufficient_privilege THEN
            direct_delete_blocked := true;
    END;

    IF NOT direct_delete_blocked THEN
        RAISE EXCEPTION 'The service-like role could delete an idempotency record directly';
    END IF;
END;
$$;

RESET ROLE;

INSERT INTO idempotency_records (
    institution_id,
    provider_id,
    operation,
    idempotency_key,
    request_fingerprint,
    state,
    http_status,
    response_headers,
    response_payload,
    response_payload_hash,
    result_object_type,
    result_object_id,
    result_version,
    audit_event_id,
    created_at,
    completed_at,
    expires_at
) VALUES (
    'INST-ALIGN01',
    'PROV-ALIGN01',
    'case.create',
    'IDEMPOTENCY-EXPIRED-0001',
    repeat('e', 64),
    'completed',
    201,
    '{"ETag":"W/\"case-version-1\"","X-Audit-Event-Id":"AUD-TIPTEST0001"}'::jsonb,
    '{"case_id":"CASE-CREATE0001","version":1,"status":"intake"}'::jsonb,
    repeat('f', 64),
    'case',
    'CASE-CREATE0001',
    1,
    'AUD-TIPTEST0001',
    TIMESTAMPTZ '2020-01-01 00:00:00+00',
    TIMESTAMPTZ '2020-01-01 00:00:01+00',
    TIMESTAMPTZ '2020-01-02 00:00:00+00'
);

CREATE ROLE pa_idempotency_maintenance NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT EXECUTE ON FUNCTION purge_expired_idempotency_records(integer) TO pa_idempotency_maintenance;

SET ROLE pa_idempotency_maintenance;

DO $$
DECLARE
    deleted_count integer;
BEGIN
    deleted_count := purge_expired_idempotency_records(100);
    IF deleted_count <> 1 THEN
        RAISE EXCEPTION 'Expected one expired idempotency record to be purged, found %', deleted_count;
    END IF;
END;
$$;

RESET ROLE;

DO $$
DECLARE
    expired_remaining integer;
    active_remaining integer;
BEGIN
    SELECT count(*) INTO expired_remaining
    FROM idempotency_records
    WHERE idempotency_key = 'IDEMPOTENCY-EXPIRED-0001';

    SELECT count(*) INTO active_remaining
    FROM idempotency_records
    WHERE idempotency_key = 'IDEMPOTENCY-TEST-0001';

    IF expired_remaining <> 0 THEN
        RAISE EXCEPTION 'Expired idempotency record remained after governed purge';
    END IF;
    IF active_remaining <> 1 THEN
        RAISE EXCEPTION 'Non-expired completed idempotency record was incorrectly purged';
    END IF;
END;
$$;

DROP OWNED BY pa_idempotency_maintenance;
DROP ROLE pa_idempotency_maintenance;
DROP OWNED BY pa_idempotency_test;
DROP ROLE pa_idempotency_test;

SELECT 'transactional idempotency isolation, immutability, replay snapshot, and governed retention purge passed' AS result;
