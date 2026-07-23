BEGIN;

SET search_path TO provider_assessment, public;

ALTER TABLE audit_events
    ADD CONSTRAINT audit_events_tenant_identity_unique
        UNIQUE (audit_event_id, institution_id);

CREATE TABLE idempotency_records (
    institution_id text NOT NULL,
    provider_id text NOT NULL,
    operation text NOT NULL CHECK (operation ~ '^[a-z][a-z0-9_.:-]{2,120}$'),
    idempotency_key text NOT NULL CHECK (
        idempotency_key ~ '^[A-Za-z0-9._:-]{16,128}$'
    ),
    request_fingerprint text NOT NULL CHECK (
        request_fingerprint ~ '^[a-f0-9]{64}$'
    ),
    state text NOT NULL CHECK (state IN ('in_progress', 'completed')),
    http_status integer CHECK (http_status BETWEEN 200 AND 299),
    response_headers jsonb CHECK (
        response_headers IS NULL OR jsonb_typeof(response_headers) = 'object'
    ),
    response_payload jsonb,
    response_payload_hash text CHECK (
        response_payload_hash IS NULL OR response_payload_hash ~ '^[a-f0-9]{64}$'
    ),
    result_object_type text,
    result_object_id text,
    result_version bigint CHECK (result_version IS NULL OR result_version >= 1),
    audit_event_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    expires_at timestamptz NOT NULL,
    PRIMARY KEY (
        institution_id,
        provider_id,
        operation,
        idempotency_key
    ),
    FOREIGN KEY (provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    FOREIGN KEY (audit_event_id, institution_id)
        REFERENCES audit_events(audit_event_id, institution_id),
    CHECK (expires_at > created_at),
    CHECK (
        (
            state = 'in_progress'
            AND http_status IS NULL
            AND response_headers IS NULL
            AND response_payload IS NULL
            AND response_payload_hash IS NULL
            AND result_object_type IS NULL
            AND result_object_id IS NULL
            AND result_version IS NULL
            AND audit_event_id IS NULL
            AND completed_at IS NULL
        )
        OR
        (
            state = 'completed'
            AND http_status IS NOT NULL
            AND response_headers IS NOT NULL
            AND response_payload IS NOT NULL
            AND response_payload_hash IS NOT NULL
            AND result_object_type IS NOT NULL
            AND result_object_id IS NOT NULL
            AND result_version IS NOT NULL
            AND audit_event_id IS NOT NULL
            AND completed_at IS NOT NULL
            AND completed_at >= created_at
        )
    ),
    CHECK (
        response_payload IS NULL
        OR pg_column_size(response_payload) <= 65536
    )
);

CREATE INDEX idempotency_records_expiry_idx
    ON idempotency_records (expires_at)
    WHERE state = 'completed';

CREATE OR REPLACE FUNCTION enforce_idempotency_record_transition()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.state = 'completed' THEN
        RAISE EXCEPTION 'completed idempotency records are immutable';
    END IF;

    IF NEW.institution_id IS DISTINCT FROM OLD.institution_id
       OR NEW.provider_id IS DISTINCT FROM OLD.provider_id
       OR NEW.operation IS DISTINCT FROM OLD.operation
       OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
       OR NEW.request_fingerprint IS DISTINCT FROM OLD.request_fingerprint
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR NEW.expires_at IS DISTINCT FROM OLD.expires_at THEN
        RAISE EXCEPTION 'idempotency identity and retention fields are immutable';
    END IF;

    IF OLD.state <> 'in_progress' OR NEW.state <> 'completed' THEN
        RAISE EXCEPTION 'only in_progress to completed transition is allowed';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER idempotency_records_transition_guard
BEFORE UPDATE ON idempotency_records
FOR EACH ROW EXECUTE FUNCTION enforce_idempotency_record_transition();

CREATE TRIGGER idempotency_records_no_delete
BEFORE DELETE ON idempotency_records
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

ALTER TABLE idempotency_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_records FORCE ROW LEVEL SECURITY;

CREATE POLICY idempotency_tenant_scope
ON idempotency_records
FOR ALL
USING (
    institution_id = nullif(current_setting('app.institution_id', true), '')
)
WITH CHECK (
    institution_id = nullif(current_setting('app.institution_id', true), '')
);

CREATE POLICY idempotency_provider_scope
ON idempotency_records
AS RESTRICTIVE
FOR ALL
USING (
    provider_id = nullif(current_setting('app.provider_id', true), '')
)
WITH CHECK (
    provider_id = nullif(current_setting('app.provider_id', true), '')
);

REVOKE ALL ON FUNCTION enforce_idempotency_record_transition() FROM PUBLIC;

COMMENT ON TABLE idempotency_records IS
'Short-retention command ledger. A reservation, governed write, exact audit receipt, and replayable response are committed or rolled back together. Payloads must never contain protected assessment items or direct identity data.';

COMMENT ON COLUMN idempotency_records.response_payload IS
'Exact API response snapshot retained only for bounded idempotent replay under RLS. Direct identity data and protected assessment content are prohibited.';

COMMIT;
