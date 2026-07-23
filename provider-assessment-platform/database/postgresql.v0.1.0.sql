BEGIN;

CREATE SCHEMA IF NOT EXISTS provider_assessment;
SET search_path TO provider_assessment, public;

CREATE TABLE institutions (
    institution_id text PRIMARY KEY CHECK (institution_id ~ '^INST-[A-Z0-9-]{4,40}$'),
    legal_name text NOT NULL CHECK (length(trim(legal_name)) >= 3),
    country_code text NOT NULL CHECK (country_code ~ '^[A-Z]{2}$'),
    active boolean NOT NULL DEFAULT false,
    authorization_expires_at date NOT NULL,
    data_processing_agreement_active boolean NOT NULL DEFAULT false,
    clinical_governance_active boolean NOT NULL DEFAULT false,
    emergency_configuration_active boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (NOT active OR (
        data_processing_agreement_active
        AND clinical_governance_active
        AND emergency_configuration_active
    ))
);

CREATE TABLE providers (
    provider_id text PRIMARY KEY CHECK (provider_id ~ '^PROV-[A-Z0-9-]{4,40}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    active boolean NOT NULL DEFAULT false,
    roles jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(roles) = 'array'),
    professional_license_reference text NOT NULL,
    professional_license_expires_at date NOT NULL,
    professional_license_status text NOT NULL CHECK (
        professional_license_status IN ('pending', 'verified', 'rejected', 'expired', 'suspended')
    ),
    mfa_enabled boolean NOT NULL DEFAULT false,
    languages jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(languages) = 'array'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider_id, institution_id),
    CHECK (NOT active OR (professional_license_status = 'verified' AND mfa_enabled))
);

CREATE TABLE provider_training_records (
    training_record_id text PRIMARY KEY CHECK (training_record_id ~ '^TRN-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    provider_id text NOT NULL,
    training_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('current', 'expired', 'revoked', 'pending_review')),
    completed_at timestamptz NOT NULL,
    expires_at date,
    evidence_reference text NOT NULL,
    reviewed_by_provider_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    FOREIGN KEY (reviewed_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    UNIQUE (institution_id, provider_id, training_id, completed_at)
);

CREATE TABLE assessment_catalog (
    assessment_id text PRIMARY KEY CHECK (assessment_id ~ '^[a-z0-9][a-z0-9-]{2,80}$'),
    active_definition_version text NOT NULL,
    enabled_globally boolean NOT NULL DEFAULT false,
    license_status text NOT NULL,
    digital_right_status text NOT NULL,
    owner_reference text NOT NULL,
    definition_hash text NOT NULL CHECK (definition_hash ~ '^[a-f0-9]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (NOT enabled_globally OR digital_right_status IN ('allowed', 'allowed_after_governance_approval'))
);

CREATE TABLE institution_assessment_authorizations (
    authorization_id text PRIMARY KEY CHECK (authorization_id ~ '^AUTH-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    assessment_id text NOT NULL REFERENCES assessment_catalog(assessment_id),
    status text NOT NULL CHECK (status IN ('pending', 'approved', 'restricted', 'suspended', 'expired', 'rejected')),
    authorized_operations jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(authorized_operations) = 'array'),
    license_document_reference text NOT NULL,
    effective_from date,
    expires_at date,
    reviewed_by_provider_id text,
    reviewed_at timestamptz,
    restrictions jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(restrictions) = 'array'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (reviewed_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    UNIQUE (institution_id, assessment_id, effective_from)
);

CREATE TABLE provider_assessment_authorizations (
    provider_authorization_id text PRIMARY KEY CHECK (provider_authorization_id ~ '^PAUTH-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    provider_id text NOT NULL,
    assessment_id text NOT NULL REFERENCES assessment_catalog(assessment_id),
    status text NOT NULL CHECK (status IN ('pending', 'approved', 'restricted', 'suspended', 'expired', 'rejected')),
    effective_from date,
    expires_at date,
    training_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(training_ids) = 'array'),
    reviewed_by_provider_id text,
    reviewed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    FOREIGN KEY (reviewed_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    UNIQUE (institution_id, provider_id, assessment_id, effective_from)
);

CREATE TABLE cases (
    case_id text PRIMARY KEY CHECK (case_id ~ '^CASE-[A-Z0-9-]{8,40}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    identity_vault_reference text NOT NULL,
    status text NOT NULL CHECK (
        status IN (
            'intake', 'safety_hold', 'assessment_planning', 'in_assessment',
            'multidisciplinary_review', 'report_draft', 'approved', 'closed', 'withdrawn'
        )
    ),
    version bigint NOT NULL DEFAULT 1 CHECK (version >= 1),
    date_of_birth date NOT NULL,
    age_months_at_intake integer NOT NULL CHECK (age_months_at_intake BETWEEN 0 AND 1440),
    preferred_language text NOT NULL,
    home_languages jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(home_languages) = 'array'),
    education_languages jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(education_languages) = 'array'),
    communication_modes jsonb NOT NULL CHECK (
        jsonb_typeof(communication_modes) = 'array'
        AND jsonb_array_length(communication_modes) >= 1
    ),
    country_of_service text NOT NULL CHECK (country_of_service ~ '^[A-Z]{2}$'),
    safety_level text NOT NULL DEFAULT 'none_identified' CHECK (
        safety_level IN ('none_identified', 'monitor', 'urgent', 'emergency')
    ),
    current_pathway_id text,
    current_pathway_version text,
    assigned_case_lead_provider_id text,
    created_by_provider_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (case_id, institution_id),
    FOREIGN KEY (assigned_case_lead_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    CHECK (
        (current_pathway_id IS NULL AND current_pathway_version IS NULL)
        OR (current_pathway_id IS NOT NULL AND current_pathway_version IS NOT NULL)
    ),
    CHECK (safety_level NOT IN ('urgent', 'emergency') OR status = 'safety_hold')
);

CREATE TABLE case_assignments (
    case_assignment_id text PRIMARY KEY CHECK (case_assignment_id ~ '^CASG-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    provider_id text NOT NULL,
    assignment_role text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    assigned_by_provider_id text NOT NULL,
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    FOREIGN KEY (assigned_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    CHECK ((active AND ended_at IS NULL) OR (NOT active AND ended_at IS NOT NULL))
);

CREATE UNIQUE INDEX case_assignments_one_active_role
    ON case_assignments (institution_id, case_id, provider_id, assignment_role)
    WHERE active;

CREATE TABLE consent_versions (
    consent_version_id text PRIMARY KEY CHECK (consent_version_id ~ '^CONS-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    version integer NOT NULL CHECK (version >= 1),
    legal_basis text NOT NULL CHECK (
        legal_basis IN ('guardian_consent', 'adult_consent', 'authorized_representative', 'other_documented_basis')
    ),
    scope jsonb NOT NULL CHECK (jsonb_typeof(scope) = 'array' AND jsonb_array_length(scope) >= 1),
    obtained_at timestamptz NOT NULL,
    withdrawal_explained boolean NOT NULL CHECK (withdrawal_explained),
    withdrawn_at timestamptz,
    document_reference text NOT NULL,
    created_by_provider_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    supersedes_consent_version_id text REFERENCES consent_versions(consent_version_id),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    UNIQUE (institution_id, case_id, version),
    CHECK (withdrawn_at IS NULL OR withdrawn_at >= obtained_at)
);

CREATE TABLE referrals (
    referral_id text PRIMARY KEY CHECK (referral_id ~ '^REF-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    reason text NOT NULL CHECK (length(trim(reason)) >= 10),
    questions jsonb NOT NULL CHECK (jsonb_typeof(questions) = 'array' AND jsonb_array_length(questions) >= 1),
    referrer_role text NOT NULL,
    urgency text NOT NULL CHECK (urgency IN ('routine', 'priority', 'urgent')),
    received_at timestamptz NOT NULL,
    created_by_provider_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id)
);

CREATE TABLE information_sources (
    source_id text PRIMARY KEY CHECK (source_id ~ '^SRC-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    source_type text NOT NULL,
    relationship text NOT NULL,
    language_used text NOT NULL,
    interpreter_used boolean NOT NULL DEFAULT false,
    collected_at timestamptz NOT NULL,
    reliability_notes text NOT NULL,
    record_reference text,
    created_by_provider_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id)
);

CREATE TABLE safety_events (
    safety_event_id text PRIMARY KEY CHECK (safety_event_id ~ '^SAFE-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    level text NOT NULL CHECK (level IN ('monitor', 'urgent', 'emergency')),
    domains jsonb NOT NULL CHECK (jsonb_typeof(domains) = 'array' AND jsonb_array_length(domains) >= 1),
    observations text NOT NULL CHECK (length(trim(observations)) >= 10),
    immediate_actions jsonb NOT NULL CHECK (
        jsonb_typeof(immediate_actions) = 'array'
        AND jsonb_array_length(immediate_actions) >= 1
    ),
    handoff_target text,
    handoff_confirmed_at timestamptz,
    routine_pathway_blocked boolean NOT NULL,
    created_by_provider_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    CHECK (level = 'monitor' OR routine_pathway_blocked),
    CHECK (handoff_confirmed_at IS NULL OR handoff_target IS NOT NULL)
);

CREATE TABLE safety_event_reviews (
    safety_review_id text PRIMARY KEY CHECK (safety_review_id ~ '^SREV-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    safety_event_id text NOT NULL REFERENCES safety_events(safety_event_id),
    case_id text NOT NULL,
    decision text NOT NULL CHECK (decision IN ('continue_hold', 'resume_pathway', 'close_case', 'escalate')),
    rationale text NOT NULL CHECK (length(trim(rationale)) >= 10),
    reviewed_by_provider_id text NOT NULL,
    reviewed_at timestamptz NOT NULL,
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (reviewed_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id)
);

CREATE TABLE pathway_instances (
    pathway_instance_id text PRIMARY KEY CHECK (pathway_instance_id ~ '^PTH-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    pathway_id text NOT NULL,
    pathway_version text NOT NULL,
    pathway_definition_hash text NOT NULL CHECK (pathway_definition_hash ~ '^[a-f0-9]{64}$'),
    current_node_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'safety_hold', 'completed', 'withdrawn', 'superseded')),
    started_by_provider_id text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (started_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    CHECK ((status = 'completed' AND completed_at IS NOT NULL) OR status <> 'completed')
);

CREATE TABLE pathway_events (
    pathway_event_id text PRIMARY KEY CHECK (pathway_event_id ~ '^PEVT-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    pathway_instance_id text NOT NULL REFERENCES pathway_instances(pathway_instance_id),
    from_node_id text NOT NULL,
    transition_id text,
    to_node_id text,
    truth_value text NOT NULL CHECK (truth_value IN ('true', 'false', 'unknown')),
    source_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(source_ids) = 'array'),
    missing_fields jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(missing_fields) = 'array'),
    explanation_ar text NOT NULL,
    explanation_en text NOT NULL,
    requires_human_confirmation boolean NOT NULL,
    human_confirmation_received boolean NOT NULL,
    automation_blocked boolean NOT NULL,
    evaluated_by_provider_id text NOT NULL,
    evaluated_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (evaluated_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    CHECK (NOT human_confirmation_received OR requires_human_confirmation),
    CHECK (NOT requires_human_confirmation OR automation_blocked)
);

CREATE TABLE assessment_plans (
    assessment_plan_id text PRIMARY KEY CHECK (assessment_plan_id ~ '^PLAN-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    pathway_instance_id text NOT NULL REFERENCES pathway_instances(pathway_instance_id),
    version integer NOT NULL CHECK (version >= 1),
    domains jsonb NOT NULL CHECK (jsonb_typeof(domains) = 'array' AND jsonb_array_length(domains) >= 1),
    assessment_ids jsonb NOT NULL CHECK (jsonb_typeof(assessment_ids) = 'array'),
    rationale text NOT NULL CHECK (length(trim(rationale)) >= 10),
    status text NOT NULL CHECK (status IN ('draft', 'approved', 'rejected', 'superseded')),
    approved_by_provider_id text,
    approved_at timestamptz,
    created_by_provider_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    supersedes_plan_id text REFERENCES assessment_plans(assessment_plan_id),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (approved_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    UNIQUE (institution_id, case_id, pathway_instance_id, version),
    CHECK (
        (status = 'approved' AND approved_by_provider_id IS NOT NULL AND approved_at IS NOT NULL)
        OR status <> 'approved'
    )
);

CREATE TABLE assessment_sessions (
    session_id text PRIMARY KEY CHECK (session_id ~ '^SES-[A-Z0-9-]{8,40}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    assessment_plan_id text NOT NULL REFERENCES assessment_plans(assessment_plan_id),
    assessment_id text NOT NULL REFERENCES assessment_catalog(assessment_id),
    assessment_version text NOT NULL,
    administrator_provider_id text NOT NULL,
    status text NOT NULL CHECK (status IN ('planned', 'in_progress', 'completed', 'stopped', 'invalidated')),
    validity text NOT NULL CHECK (validity IN ('not_yet_determined', 'valid', 'qualified', 'invalid')),
    started_at timestamptz,
    ended_at timestamptz,
    result_reference text,
    manual_review_required boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (administrator_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    CHECK (result_reference IS NULL OR length(trim(result_reference)) >= 3),
    CHECK (status <> 'completed' OR ended_at IS NOT NULL),
    CHECK (validity <> 'invalid' OR manual_review_required)
);

CREATE TABLE assessment_session_deviations (
    deviation_id text PRIMARY KEY CHECK (deviation_id ~ '^DEV-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    session_id text NOT NULL REFERENCES assessment_sessions(session_id),
    deviation_type text NOT NULL,
    description text NOT NULL CHECK (length(trim(description)) >= 5),
    affected_scope text NOT NULL,
    validity_impact text NOT NULL CHECK (validity_impact IN ('none', 'qualified', 'invalid')),
    recorded_by_provider_id text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (recorded_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id)
);

CREATE TABLE team_reviews (
    team_review_id text PRIMARY KEY CHECK (team_review_id ~ '^TREV-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    pathway_instance_id text NOT NULL REFERENCES pathway_instances(pathway_instance_id),
    status text NOT NULL CHECK (status IN ('draft', 'approved', 'insufficient_evidence', 'returned_for_data')),
    member_provider_ids jsonb NOT NULL CHECK (
        jsonb_typeof(member_provider_ids) = 'array'
        AND jsonb_array_length(member_provider_ids) >= 1
    ),
    decision text NOT NULL,
    supporting_evidence_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(supporting_evidence_ids) = 'array'),
    contrary_evidence_ids jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(contrary_evidence_ids) = 'array'),
    limitations text NOT NULL,
    support_needs jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(support_needs) = 'array'),
    approved_by_provider_id text,
    approved_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (approved_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    CHECK (
        (status = 'approved' AND approved_by_provider_id IS NOT NULL AND approved_at IS NOT NULL)
        OR status <> 'approved'
    )
);

CREATE TABLE report_versions (
    report_version_id text PRIMARY KEY CHECK (report_version_id ~ '^RPTV-[A-Z0-9-]{8,50}$'),
    report_id text NOT NULL CHECK (report_id ~ '^RPT-[A-Z0-9-]{8,40}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text NOT NULL,
    team_review_id text NOT NULL REFERENCES team_reviews(team_review_id),
    version integer NOT NULL CHECK (version >= 1),
    status text NOT NULL CHECK (status IN ('draft', 'signed', 'superseded', 'withdrawn')),
    template_version text NOT NULL,
    content_reference text NOT NULL,
    content_hash text NOT NULL CHECK (content_hash ~ '^[a-f0-9]{64}$'),
    human_review_required boolean NOT NULL DEFAULT true CHECK (human_review_required),
    professional_license_reference text,
    signed_by_provider_id text,
    signed_at timestamptz,
    created_by_provider_id text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    supersedes_report_version_id text REFERENCES report_versions(report_version_id),
    withdrawal_reason text,
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (signed_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    UNIQUE (institution_id, report_id, version),
    CHECK (
        (status = 'signed'
            AND signed_by_provider_id IS NOT NULL
            AND signed_at IS NOT NULL
            AND professional_license_reference IS NOT NULL)
        OR status <> 'signed'
    ),
    CHECK (status <> 'withdrawn' OR withdrawal_reason IS NOT NULL)
);

CREATE TABLE audit_events (
    audit_event_id text PRIMARY KEY CHECK (audit_event_id ~ '^AUD-[A-Z0-9-]{8,50}$'),
    institution_id text NOT NULL REFERENCES institutions(institution_id),
    case_id text,
    actor_provider_id text,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    action text NOT NULL,
    object_type text NOT NULL,
    object_id text NOT NULL,
    reason text NOT NULL,
    correlation_id text NOT NULL,
    request_id text,
    previous_event_hash text CHECK (previous_event_hash IS NULL OR previous_event_hash ~ '^[a-f0-9]{64}$'),
    event_hash text NOT NULL UNIQUE CHECK (event_hash ~ '^[a-f0-9]{64}$'),
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    FOREIGN KEY (case_id, institution_id)
        REFERENCES cases(case_id, institution_id),
    FOREIGN KEY (actor_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id)
);

CREATE INDEX providers_institution_idx ON providers (institution_id, active);
CREATE INDEX cases_institution_status_idx ON cases (institution_id, status, updated_at DESC);
CREATE INDEX assignments_provider_idx ON case_assignments (institution_id, provider_id, active);
CREATE INDEX consent_case_version_idx ON consent_versions (institution_id, case_id, version DESC);
CREATE INDEX sources_case_idx ON information_sources (institution_id, case_id, collected_at DESC);
CREATE INDEX safety_case_idx ON safety_events (institution_id, case_id, created_at DESC);
CREATE INDEX pathway_case_idx ON pathway_instances (institution_id, case_id, started_at DESC);
CREATE INDEX pathway_events_case_idx ON pathway_events (institution_id, case_id, evaluated_at DESC);
CREATE INDEX sessions_case_idx ON assessment_sessions (institution_id, case_id, created_at DESC);
CREATE INDEX reports_case_idx ON report_versions (institution_id, case_id, report_id, version DESC);
CREATE INDEX audit_case_idx ON audit_events (institution_id, case_id, occurred_at DESC);
CREATE INDEX audit_correlation_idx ON audit_events (institution_id, correlation_id, occurred_at);

CREATE OR REPLACE FUNCTION deny_immutable_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'immutable record: use a new version or correction event';
END;
$$;

CREATE TRIGGER consent_versions_immutable
BEFORE UPDATE OR DELETE ON consent_versions
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER referrals_immutable
BEFORE UPDATE OR DELETE ON referrals
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER information_sources_immutable
BEFORE UPDATE OR DELETE ON information_sources
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER safety_events_immutable
BEFORE UPDATE OR DELETE ON safety_events
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER safety_event_reviews_immutable
BEFORE UPDATE OR DELETE ON safety_event_reviews
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER pathway_events_immutable
BEFORE UPDATE OR DELETE ON pathway_events
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER assessment_session_deviations_immutable
BEFORE UPDATE OR DELETE ON assessment_session_deviations
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER team_reviews_immutable
BEFORE UPDATE OR DELETE ON team_reviews
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER report_versions_immutable
BEFORE UPDATE OR DELETE ON report_versions
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE TRIGGER audit_events_immutable
BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

CREATE OR REPLACE FUNCTION set_case_update_metadata()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.version := OLD.version + 1;
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER cases_version_on_update
BEFORE UPDATE ON cases
FOR EACH ROW EXECUTE FUNCTION set_case_update_metadata();

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
          AND institution_id = NEW.institution_id;
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

CREATE TRIGGER safety_event_blocks_case
AFTER INSERT ON safety_events
FOR EACH ROW EXECUTE FUNCTION enforce_case_safety_hold();

CREATE VIEW current_consents AS
SELECT DISTINCT ON (institution_id, case_id)
    consent_version_id,
    institution_id,
    case_id,
    version,
    legal_basis,
    scope,
    obtained_at,
    withdrawal_explained,
    withdrawn_at,
    document_reference,
    created_by_provider_id,
    created_at
FROM consent_versions
ORDER BY institution_id, case_id, version DESC;

CREATE VIEW current_reports AS
SELECT DISTINCT ON (institution_id, report_id)
    report_version_id,
    report_id,
    institution_id,
    case_id,
    team_review_id,
    version,
    status,
    template_version,
    content_reference,
    content_hash,
    human_review_required,
    professional_license_reference,
    signed_by_provider_id,
    signed_at,
    created_by_provider_id,
    created_at
FROM report_versions
ORDER BY institution_id, report_id, version DESC;

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'institutions',
        'providers',
        'provider_training_records',
        'institution_assessment_authorizations',
        'provider_assessment_authorizations',
        'cases',
        'case_assignments',
        'consent_versions',
        'referrals',
        'information_sources',
        'safety_events',
        'safety_event_reviews',
        'pathway_instances',
        'pathway_events',
        'assessment_plans',
        'assessment_sessions',
        'assessment_session_deviations',
        'team_reviews',
        'report_versions',
        'audit_events'
    ]
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format(
            'CREATE POLICY institution_isolation_%1$I ON %1$I USING (institution_id = nullif(current_setting(''app.institution_id'', true), '''')) WITH CHECK (institution_id = nullif(current_setting(''app.institution_id'', true), ''''))',
            table_name
        );
    END LOOP;
END;
$$;

CREATE POLICY assigned_case_read ON cases
FOR SELECT
USING (
    institution_id = nullif(current_setting('app.institution_id', true), '')
    AND (
        assigned_case_lead_provider_id = nullif(current_setting('app.provider_id', true), '')
        OR EXISTS (
            SELECT 1
            FROM case_assignments assignment
            WHERE assignment.institution_id = cases.institution_id
              AND assignment.case_id = cases.case_id
              AND assignment.provider_id = nullif(current_setting('app.provider_id', true), '')
              AND assignment.active
        )
        OR current_setting('app.audit_scope', true) = 'institution'
    )
);

COMMENT ON SCHEMA provider_assessment IS
'Provider assessment workflow only. Identity is referenced through an external vault; protected test content and norm tables must never be stored here.';

COMMENT ON COLUMN cases.identity_vault_reference IS
'Opaque reference to a separately secured identity vault. Do not store names, national identifiers, addresses, or contact details in this schema.';

COMMENT ON COLUMN assessment_sessions.result_reference IS
'Opaque reference to an approved scoring or publisher boundary. Protected test items, prompts, answer keys, and norm tables are prohibited.';

COMMENT ON COLUMN report_versions.content_reference IS
'Opaque reference to versioned report content. Signed content is immutable and identified by content_hash.';

COMMIT;
