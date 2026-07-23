\set ON_ERROR_STOP on

SET search_path TO provider_assessment, public;

CREATE ROLE pa_service_app
LOGIN
PASSWORD 'provider_assessment_test_password'
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOINHERIT
NOBYPASSRLS;

GRANT USAGE ON SCHEMA provider_assessment TO pa_service_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA provider_assessment TO pa_service_app;
GRANT EXECUTE ON FUNCTION current_institution_last_audit_hash() TO pa_service_app;

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
    'INST-SVC001',
    'Synthetic Service Integration Institution',
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
) VALUES
(
    'PROV-SVC001',
    'INST-SVC001',
    true,
    '["provider", "intake_coordinator", "case_lead", "clinical_reviewer", "report_author"]'::jsonb,
    'SYNTHETIC-LICENSE-SVC001',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar", "en"]'::jsonb
),
(
    'PROV-SVC002',
    'INST-SVC001',
    true,
    '["provider", "clinical_reviewer"]'::jsonb,
    'SYNTHETIC-LICENSE-SVC002',
    DATE '2099-12-31',
    'verified',
    true,
    '["ar"]'::jsonb
);

SELECT 'service integration role and synthetic institution prepared with least-function privilege' AS result;
