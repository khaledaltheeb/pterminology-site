\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

DO $$
DECLARE
    screened_at_value timestamptz;
    screened_by_value text;
    actions_value jsonb;
BEGIN
    SELECT safety_screened_at,
           safety_screened_by_provider_id,
           intake_safety_actions
    INTO screened_at_value,
         screened_by_value,
         actions_value
    FROM cases
    WHERE institution_id = 'INST-ALIGN01'
      AND case_id = 'CASE-ALIGN0001';

    IF screened_at_value <> TIMESTAMPTZ '2026-07-23 18:00:00+00' THEN
        RAISE EXCEPTION 'Legacy safety screened timestamp was not backfilled from case creation time: %', screened_at_value;
    END IF;

    IF screened_by_value <> 'PROV-ALIGN01' THEN
        RAISE EXCEPTION 'Legacy safety screener was not backfilled from case creator: %', screened_by_value;
    END IF;

    IF actions_value <> '["legacy_record_requires_safety_action_review"]'::jsonb THEN
        RAISE EXCEPTION 'Legacy record must carry an explicit review marker, found %', actions_value;
    END IF;
END;
$$;

INSERT INTO cases (
    case_id,
    institution_id,
    identity_vault_reference,
    status,
    date_of_birth,
    age_months_at_intake,
    preferred_language,
    home_languages,
    education_languages,
    communication_modes,
    country_of_service,
    safety_level,
    safety_screened_at,
    safety_screened_by_provider_id,
    intake_safety_actions,
    assigned_case_lead_provider_id,
    created_by_provider_id
) VALUES (
    'CASE-ALIGN0002',
    'INST-ALIGN01',
    'IDENTITY-VAULT-SYNTHETIC-ALIGN02',
    'intake',
    DATE '2016-07-23',
    120,
    'ar',
    '["ar"]'::jsonb,
    '["ar", "en"]'::jsonb,
    '["speech"]'::jsonb,
    'JO',
    'none_identified',
    TIMESTAMPTZ '2026-07-23 19:00:00+00',
    'PROV-ALIGN01',
    '["no_immediate_action_required"]'::jsonb,
    'PROV-ALIGN01',
    'PROV-ALIGN01'
);

DO $$
BEGIN
    BEGIN
        INSERT INTO cases (
            case_id,
            institution_id,
            identity_vault_reference,
            status,
            date_of_birth,
            age_months_at_intake,
            preferred_language,
            home_languages,
            education_languages,
            communication_modes,
            country_of_service,
            safety_level,
            safety_screened_at,
            safety_screened_by_provider_id,
            intake_safety_actions,
            assigned_case_lead_provider_id,
            created_by_provider_id
        ) VALUES (
            'CASE-ALIGN0003',
            'INST-ALIGN01',
            'IDENTITY-VAULT-SYNTHETIC-ALIGN03',
            'intake',
            DATE '2016-07-23',
            120,
            'ar',
            '["ar"]'::jsonb,
            '["ar"]'::jsonb,
            '["speech"]'::jsonb,
            'JO',
            'none_identified',
            TIMESTAMPTZ '2026-07-23 19:00:00+00',
            'PROV-ALIGN01',
            '[]'::jsonb,
            'PROV-ALIGN01',
            'PROV-ALIGN01'
        );
        RAISE EXCEPTION 'Empty intake safety actions were not rejected';
    EXCEPTION
        WHEN check_violation THEN
            NULL;
    END;
END;
$$;

SELECT 'intake alignment migration and conservative backfill passed' AS result;
