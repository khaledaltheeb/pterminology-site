BEGIN;

SET search_path TO provider_assessment, public;

DROP POLICY IF EXISTS assigned_case_read ON cases;

CREATE POLICY assigned_case_access
AS RESTRICTIVE
ON cases
FOR ALL
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
)
WITH CHECK (
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

CREATE POLICY assignment_scope_access
AS RESTRICTIVE
ON case_assignments
FOR ALL
USING (
    provider_id = nullif(current_setting('app.provider_id', true), '')
    OR assigned_by_provider_id = nullif(current_setting('app.provider_id', true), '')
    OR current_setting('app.audit_scope', true) = 'institution'
)
WITH CHECK (
    assigned_by_provider_id = nullif(current_setting('app.provider_id', true), '')
    OR current_setting('app.audit_scope', true) = 'institution'
);

DO $$
DECLARE
    table_name text;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
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
        'report_versions'
    ]
    LOOP
        EXECUTE format(
            'CREATE POLICY assigned_case_access_%1$I AS RESTRICTIVE ON %1$I FOR ALL USING (
                EXISTS (
                    SELECT 1
                    FROM cases accessible_case
                    WHERE accessible_case.institution_id = %1$I.institution_id
                      AND accessible_case.case_id = %1$I.case_id
                )
            ) WITH CHECK (
                EXISTS (
                    SELECT 1
                    FROM cases accessible_case
                    WHERE accessible_case.institution_id = %1$I.institution_id
                      AND accessible_case.case_id = %1$I.case_id
                )
            )',
            table_name
        );
    END LOOP;
END;
$$;

CREATE POLICY audit_case_or_institution_access
AS RESTRICTIVE
ON audit_events
FOR SELECT
USING (
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
);

CREATE POLICY audit_event_insert_scope
AS RESTRICTIVE
ON audit_events
FOR INSERT
WITH CHECK (
    actor_provider_id = nullif(current_setting('app.provider_id', true), '')
    OR current_setting('app.audit_scope', true) = 'institution'
);

ALTER VIEW current_consents SET (security_invoker = true);
ALTER VIEW current_reports SET (security_invoker = true);

COMMENT ON POLICY assigned_case_access ON cases IS
'Institution isolation is necessary but insufficient. Access additionally requires active assignment, case leadership, or explicit institution audit scope.';

COMMENT ON POLICY audit_case_or_institution_access ON audit_events IS
'Case audit events follow case assignment. Institution-wide events require institution audit scope.';

COMMIT;
