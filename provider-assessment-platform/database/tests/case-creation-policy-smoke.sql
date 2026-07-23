\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

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
    'PROV-ALIGN02',
    'INST-ALIGN01',
    true,
    '["provider"]'::jsonb,
    'SYNTHETIC-LICENSE-ALIGN02',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar"]'::jsonb
);

CREATE ROLE pa_intake NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_intake;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA provider_assessment TO pa_intake;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA provider_assessment TO pa_intake;

SET ROLE pa_intake;
SELECT set_config('app.institution_id', 'INST-ALIGN01', false);
SELECT set_config('app.provider_id', 'PROV-ALIGN01', false);
SELECT set_config('app.audit_scope', '', false);

DO $$
DECLARE
    cross_creator_blocked boolean := false;
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
            'CASE-CREATE0000',
            'INST-ALIGN01',
            'IDENTITY-VAULT-SYNTHETIC-CREATE00',
            'intake',
            DATE '2016-07-23',
            120,
            'ar',
            '["ar"]'::jsonb,
            '["ar"]'::jsonb,
            '["speech"]'::jsonb,
            'JO',
            'none_identified',
            TIMESTAMPTZ '2026-07-23 20:00:00+00',
            'PROV-ALIGN01',
            '["no_immediate_action_required"]'::jsonb,
            NULL,
            'PROV-ALIGN02'
        );
    EXCEPTION
        WHEN insufficient_privilege THEN
            cross_creator_blocked := true;
    END;

    IF NOT cross_creator_blocked THEN
        RAISE EXCEPTION 'A provider was allowed to create a case attributed to another provider';
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
    'CASE-CREATE0001',
    'INST-ALIGN01',
    'IDENTITY-VAULT-SYNTHETIC-CREATE01',
    'intake',
    DATE '2016-07-23',
    120,
    'ar',
    '["ar"]'::jsonb,
    '["ar", "en"]'::jsonb,
    '["speech", "writing"]'::jsonb,
    'JO',
    'none_identified',
    TIMESTAMPTZ '2026-07-23 20:00:00+00',
    'PROV-ALIGN01',
    '["no_immediate_action_required"]'::jsonb,
    NULL,
    'PROV-ALIGN01'
);

DO $$
DECLARE
    visible_cases integer;
BEGIN
    SELECT count(*) INTO visible_cases
    FROM cases
    WHERE case_id = 'CASE-CREATE0001';

    IF visible_cases <> 0 THEN
        RAISE EXCEPTION 'A newly created unassigned case became visible before assignment: %', visible_cases;
    END IF;
END;
$$;

INSERT INTO case_assignments (
    case_assignment_id,
    institution_id,
    case_id,
    provider_id,
    assignment_role,
    assigned_by_provider_id
) VALUES (
    'CASG-CREATE0001',
    'INST-ALIGN01',
    'CASE-CREATE0001',
    'PROV-ALIGN01',
    'intake_coordinator',
    'PROV-ALIGN01'
);

DO $$
DECLARE
    visible_cases integer;
BEGIN
    SELECT count(*) INTO visible_cases
    FROM cases
    WHERE case_id = 'CASE-CREATE0001';

    IF visible_cases <> 1 THEN
        RAISE EXCEPTION 'Assigned case did not become visible after governed assignment: %', visible_cases;
    END IF;
END;
$$;

RESET ROLE;
DROP OWNED BY pa_intake;
DROP ROLE pa_intake;

SELECT 'case creation and post-creation assignment RLS boundary passed' AS result;
