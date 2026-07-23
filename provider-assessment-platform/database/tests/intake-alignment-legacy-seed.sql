\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

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
    'INST-ALIGN01',
    'Synthetic Intake Alignment Institution',
    'JO',
    true,
    DATE '2099-12-31',
    true,
    true,
    true
);

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
    'PROV-ALIGN01',
    'INST-ALIGN01',
    true,
    '["intake_coordinator", "case_lead"]'::jsonb,
    'SYNTHETIC-LICENSE-ALIGN01',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar", "en"]'::jsonb
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
    created_by_provider_id,
    created_at,
    updated_at
) VALUES (
    'CASE-ALIGN0001',
    'INST-ALIGN01',
    'IDENTITY-VAULT-SYNTHETIC-ALIGN01',
    'intake',
    DATE '2016-07-23',
    120,
    'ar',
    '["ar"]'::jsonb,
    '["ar", "en"]'::jsonb,
    '["speech", "writing"]'::jsonb,
    'JO',
    'none_identified',
    'PROV-ALIGN01',
    'PROV-ALIGN01',
    TIMESTAMPTZ '2026-07-23 18:00:00+00',
    TIMESTAMPTZ '2026-07-23 18:00:00+00'
);

SELECT 'legacy intake alignment seed inserted' AS result;
