BEGIN;

SET search_path TO provider_assessment, public;

ALTER TABLE cases
    ADD COLUMN safety_screened_at timestamptz,
    ADD COLUMN safety_screened_by_provider_id text,
    ADD COLUMN intake_safety_actions jsonb;

UPDATE cases case_record
SET safety_screened_at = case_record.created_at,
    safety_screened_by_provider_id = case_record.created_by_provider_id,
    intake_safety_actions = COALESCE(
        (
            SELECT safety_event.immediate_actions
            FROM safety_events safety_event
            WHERE safety_event.institution_id = case_record.institution_id
              AND safety_event.case_id = case_record.case_id
            ORDER BY safety_event.created_at ASC, safety_event.safety_event_id ASC
            LIMIT 1
        ),
        '["legacy_record_requires_safety_action_review"]'::jsonb
    )
WHERE safety_screened_at IS NULL
   OR safety_screened_by_provider_id IS NULL
   OR intake_safety_actions IS NULL;

ALTER TABLE cases
    ALTER COLUMN safety_screened_at SET NOT NULL,
    ALTER COLUMN safety_screened_by_provider_id SET NOT NULL,
    ALTER COLUMN intake_safety_actions SET NOT NULL,
    ADD CONSTRAINT cases_intake_safety_actions_array_check
        CHECK (
            jsonb_typeof(intake_safety_actions) = 'array'
            AND jsonb_array_length(intake_safety_actions) >= 1
        ),
    ADD CONSTRAINT cases_safety_screened_by_tenant_fkey
        FOREIGN KEY (safety_screened_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id);

COMMENT ON COLUMN cases.safety_screened_at IS
'When the intake safety snapshot was completed. Legacy records use the original case creation timestamp and require explicit review.';

COMMENT ON COLUMN cases.safety_screened_by_provider_id IS
'Provider responsible for the intake safety snapshot, constrained to the same institution.';

COMMENT ON COLUMN cases.intake_safety_actions IS
'Actions or documented no-action decision from intake safety screening. The legacy review marker is not a clinical action.';

COMMIT;
