BEGIN;

SET search_path TO provider_assessment, public;

ALTER TABLE safety_events
    ADD CONSTRAINT safety_events_tenant_case_key
    UNIQUE (safety_event_id, institution_id, case_id);

ALTER TABLE pathway_instances
    ADD CONSTRAINT pathway_instances_tenant_case_key
    UNIQUE (pathway_instance_id, institution_id, case_id);

ALTER TABLE assessment_plans
    ADD CONSTRAINT assessment_plans_tenant_case_key
    UNIQUE (assessment_plan_id, institution_id, case_id);

ALTER TABLE assessment_sessions
    ADD CONSTRAINT assessment_sessions_tenant_case_key
    UNIQUE (session_id, institution_id, case_id);

ALTER TABLE team_reviews
    ADD CONSTRAINT team_reviews_tenant_case_key
    UNIQUE (team_review_id, institution_id, case_id);

ALTER TABLE consent_versions
    ADD CONSTRAINT consent_versions_tenant_case_key
    UNIQUE (consent_version_id, institution_id, case_id);

ALTER TABLE report_versions
    ADD CONSTRAINT report_versions_tenant_case_key
    UNIQUE (report_version_id, institution_id, case_id);

ALTER TABLE safety_event_reviews
    DROP CONSTRAINT safety_event_reviews_safety_event_id_fkey,
    ADD CONSTRAINT safety_event_reviews_tenant_case_fkey
        FOREIGN KEY (safety_event_id, institution_id, case_id)
        REFERENCES safety_events(safety_event_id, institution_id, case_id);

ALTER TABLE pathway_events
    DROP CONSTRAINT pathway_events_pathway_instance_id_fkey,
    ADD CONSTRAINT pathway_events_tenant_case_fkey
        FOREIGN KEY (pathway_instance_id, institution_id, case_id)
        REFERENCES pathway_instances(pathway_instance_id, institution_id, case_id);

ALTER TABLE assessment_plans
    DROP CONSTRAINT assessment_plans_pathway_instance_id_fkey,
    ADD CONSTRAINT assessment_plans_pathway_tenant_case_fkey
        FOREIGN KEY (pathway_instance_id, institution_id, case_id)
        REFERENCES pathway_instances(pathway_instance_id, institution_id, case_id);

ALTER TABLE assessment_sessions
    DROP CONSTRAINT assessment_sessions_assessment_plan_id_fkey,
    ADD CONSTRAINT assessment_sessions_plan_tenant_case_fkey
        FOREIGN KEY (assessment_plan_id, institution_id, case_id)
        REFERENCES assessment_plans(assessment_plan_id, institution_id, case_id);

ALTER TABLE assessment_session_deviations
    DROP CONSTRAINT assessment_session_deviations_session_id_fkey,
    ADD CONSTRAINT session_deviations_tenant_case_fkey
        FOREIGN KEY (session_id, institution_id, case_id)
        REFERENCES assessment_sessions(session_id, institution_id, case_id);

ALTER TABLE team_reviews
    DROP CONSTRAINT team_reviews_pathway_instance_id_fkey,
    ADD CONSTRAINT team_reviews_pathway_tenant_case_fkey
        FOREIGN KEY (pathway_instance_id, institution_id, case_id)
        REFERENCES pathway_instances(pathway_instance_id, institution_id, case_id);

ALTER TABLE report_versions
    DROP CONSTRAINT report_versions_team_review_id_fkey,
    ADD CONSTRAINT report_versions_review_tenant_case_fkey
        FOREIGN KEY (team_review_id, institution_id, case_id)
        REFERENCES team_reviews(team_review_id, institution_id, case_id);

ALTER TABLE consent_versions
    DROP CONSTRAINT consent_versions_supersedes_consent_version_id_fkey,
    ADD CONSTRAINT consent_versions_supersedes_tenant_case_fkey
        FOREIGN KEY (supersedes_consent_version_id, institution_id, case_id)
        REFERENCES consent_versions(consent_version_id, institution_id, case_id);

ALTER TABLE assessment_plans
    DROP CONSTRAINT assessment_plans_supersedes_plan_id_fkey,
    ADD CONSTRAINT assessment_plans_supersedes_tenant_case_fkey
        FOREIGN KEY (supersedes_plan_id, institution_id, case_id)
        REFERENCES assessment_plans(assessment_plan_id, institution_id, case_id);

ALTER TABLE report_versions
    DROP CONSTRAINT report_versions_supersedes_report_version_id_fkey,
    ADD CONSTRAINT report_versions_supersedes_tenant_case_fkey
        FOREIGN KEY (supersedes_report_version_id, institution_id, case_id)
        REFERENCES report_versions(report_version_id, institution_id, case_id);

DROP POLICY IF EXISTS audit_event_insert_scope ON audit_events;

CREATE POLICY audit_event_insert_scope
AS RESTRICTIVE
ON audit_events
FOR INSERT
WITH CHECK (
    (
        actor_provider_id = nullif(current_setting('app.provider_id', true), '')
        OR current_setting('app.audit_scope', true) = 'institution'
    )
    AND (
        (
            case_id IS NOT NULL
            AND EXISTS (
                SELECT 1
                FROM cases accessible_case
                WHERE accessible_case.institution_id = audit_events.institution_id
                  AND accessible_case.case_id = audit_events.case_id
            )
        )
        OR (
            case_id IS NULL
            AND current_setting('app.audit_scope', true) = 'institution'
        )
    )
);

COMMENT ON CONSTRAINT safety_event_reviews_tenant_case_fkey ON safety_event_reviews IS
'Prevents a safety review from referencing an event in another institution or case.';

COMMENT ON CONSTRAINT report_versions_review_tenant_case_fkey ON report_versions IS
'Prevents report versions from referencing a team review in another institution or case.';

COMMIT;
