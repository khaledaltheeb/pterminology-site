\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT USAGE ON SCHEMA provider_assessment TO pa_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA provider_assessment TO pa_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA provider_assessment TO pa_app;

SET ROLE pa_app;

SELECT set_config('app.institution_id', 'INST-A001', false);
SELECT set_config('app.provider_id', 'PROV-A001', false);
SELECT set_config('app.audit_scope', '', false);

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
    'INST-A001',
    'Synthetic Institution A',
    'JO',
    true,
    DATE '2099-12-31',
    true,
    true,
    true
);

SELECT set_config('app.institution_id', 'INST-B001', false);
SELECT set_config('app.provider_id', 'PROV-B001', false);

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
    'INST-B001',
    'Synthetic Institution B',
    'JO',
    true,
    DATE '2099-12-31',
    true,
    true,
    true
);

SELECT set_config('app.institution_id', 'INST-A001', false);
SELECT set_config('app.provider_id', 'PROV-A001', false);

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
) VALUES
(
    'PROV-A001',
    'INST-A001',
    true,
    '["case_lead", "clinical_reviewer"]'::jsonb,
    'SYNTHETIC-LICENSE-A1',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar", "en"]'::jsonb
),
(
    'PROV-A002',
    'INST-A001',
    true,
    '["provider"]'::jsonb,
    'SYNTHETIC-LICENSE-A2',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar"]'::jsonb
);

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
    assigned_case_lead_provider_id,
    created_by_provider_id
) VALUES (
    'CASE-A0000001',
    'INST-A001',
    'IDENTITY-VAULT-SYNTHETIC-A1',
    'intake',
    DATE '2017-01-01',
    114,
    'ar',
    '["ar"]'::jsonb,
    '["ar", "en"]'::jsonb,
    '["speech", "writing"]'::jsonb,
    'JO',
    'none_identified',
    'PROV-A001',
    'PROV-A001'
);

INSERT INTO case_assignments (
    case_assignment_id,
    institution_id,
    case_id,
    provider_id,
    assignment_role,
    assigned_by_provider_id
) VALUES (
    'CASG-A0000001',
    'INST-A001',
    'CASE-A0000001',
    'PROV-A001',
    'case_lead',
    'PROV-A001'
);

DO $$
DECLARE
    visible_cases integer;
BEGIN
    SELECT count(*) INTO visible_cases FROM cases;
    IF visible_cases <> 1 THEN
        RAISE EXCEPTION 'Assigned provider expected one visible case, found %', visible_cases;
    END IF;
END;
$$;

SELECT set_config('app.provider_id', 'PROV-A002', false);

DO $$
DECLARE
    visible_cases integer;
BEGIN
    SELECT count(*) INTO visible_cases FROM cases;
    IF visible_cases <> 0 THEN
        RAISE EXCEPTION 'Unassigned provider expected zero visible cases, found %', visible_cases;
    END IF;
END;
$$;

SELECT set_config('app.audit_scope', 'institution', false);

DO $$
DECLARE
    visible_cases integer;
BEGIN
    SELECT count(*) INTO visible_cases FROM cases;
    IF visible_cases <> 1 THEN
        RAISE EXCEPTION 'Institution auditor expected one visible case, found %', visible_cases;
    END IF;
END;
$$;

SELECT set_config('app.audit_scope', '', false);
SELECT set_config('app.provider_id', 'PROV-A001', false);

INSERT INTO consent_versions (
    consent_version_id,
    institution_id,
    case_id,
    version,
    legal_basis,
    scope,
    obtained_at,
    withdrawal_explained,
    document_reference,
    created_by_provider_id
) VALUES (
    'CONS-A0000001',
    'INST-A001',
    'CASE-A0000001',
    1,
    'guardian_consent',
    '["assessment", "record_review"]'::jsonb,
    now(),
    true,
    'SYNTHETIC-CONSENT-A1',
    'PROV-A001'
);

SELECT set_config('app.provider_id', 'PROV-A002', false);

DO $$
DECLARE
    visible_consents integer;
BEGIN
    SELECT count(*) INTO visible_consents FROM consent_versions;
    IF visible_consents <> 0 THEN
        RAISE EXCEPTION 'Unassigned provider expected zero visible consents, found %', visible_consents;
    END IF;
END;
$$;

SELECT set_config('app.provider_id', 'PROV-A001', false);

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
    'SAFE-A0000001',
    'INST-A001',
    'CASE-A0000001',
    'urgent',
    '["medical"]'::jsonb,
    'Synthetic urgent safety observation for migration testing only.',
    '["pause_routine_pathway", "contact_clinical_lead"]'::jsonb,
    'SYNTHETIC-CLINICAL-LEAD',
    now(),
    true,
    'PROV-A001'
);

DO $$
DECLARE
    observed_status text;
    observed_level text;
BEGIN
    SELECT status, safety_level
    INTO observed_status, observed_level
    FROM cases
    WHERE case_id = 'CASE-A0000001';

    IF observed_status <> 'safety_hold' OR observed_level <> 'urgent' THEN
        RAISE EXCEPTION 'Urgent safety event did not place case on hold: %, %', observed_status, observed_level;
    END IF;
END;
$$;

DO $$
DECLARE
    mutation_blocked boolean := false;
BEGIN
    BEGIN
        UPDATE safety_events
        SET observations = 'This update must be blocked.'
        WHERE safety_event_id = 'SAFE-A0000001';
    EXCEPTION
        WHEN raise_exception THEN
            mutation_blocked := true;
    END;

    IF NOT mutation_blocked THEN
        RAISE EXCEPTION 'Immutable safety event update was not blocked';
    END IF;
END;
$$;

SELECT set_config('app.institution_id', 'INST-B001', false);
SELECT set_config('app.provider_id', 'PROV-B001', false);
SELECT set_config('app.audit_scope', '', false);

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
    'PROV-B001',
    'INST-B001',
    true,
    '["case_lead", "clinical_reviewer"]'::jsonb,
    'SYNTHETIC-LICENSE-B1',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar"]'::jsonb
);

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
    assigned_case_lead_provider_id,
    created_by_provider_id
) VALUES (
    'CASE-B0000001',
    'INST-B001',
    'IDENTITY-VAULT-SYNTHETIC-B1',
    'intake',
    DATE '2018-01-01',
    102,
    'ar',
    '["ar"]'::jsonb,
    '["ar"]'::jsonb,
    '["speech"]'::jsonb,
    'JO',
    'none_identified',
    'PROV-B001',
    'PROV-B001'
);

INSERT INTO case_assignments (
    case_assignment_id,
    institution_id,
    case_id,
    provider_id,
    assignment_role,
    assigned_by_provider_id
) VALUES (
    'CASG-B0000001',
    'INST-B001',
    'CASE-B0000001',
    'PROV-B001',
    'case_lead',
    'PROV-B001'
);

DO $$
DECLARE
    cross_tenant_blocked boolean := false;
BEGIN
    BEGIN
        INSERT INTO safety_event_reviews (
            safety_review_id,
            institution_id,
            safety_event_id,
            case_id,
            decision,
            rationale,
            reviewed_by_provider_id,
            reviewed_at
        ) VALUES (
            'SREV-B0000001',
            'INST-B001',
            'SAFE-A0000001',
            'CASE-B0000001',
            'continue_hold',
            'Synthetic cross-tenant reference attempt that must be rejected.',
            'PROV-B001',
            now()
        );
    EXCEPTION
        WHEN foreign_key_violation OR insufficient_privilege THEN
            cross_tenant_blocked := true;
    END;

    IF NOT cross_tenant_blocked THEN
        RAISE EXCEPTION 'Cross-tenant safety-event reference was not blocked';
    END IF;
END;
$$;

DO $$
DECLARE
    visible_cases integer;
BEGIN
    SELECT count(*) INTO visible_cases FROM cases;
    IF visible_cases <> 1 THEN
        RAISE EXCEPTION 'Institution B provider expected one own case, found %', visible_cases;
    END IF;
END;
$$;

RESET ROLE;

DROP OWNED BY pa_app;
DROP ROLE pa_app;

SELECT 'provider_assessment RLS smoke tests passed' AS result;
