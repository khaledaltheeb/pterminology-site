BEGIN;

SET search_path TO provider_assessment, public;

DROP POLICY assigned_case_access ON cases;

CREATE POLICY assigned_case_select
ON cases
AS RESTRICTIVE
FOR SELECT
USING (
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
);

CREATE POLICY assigned_case_update
ON cases
AS RESTRICTIVE
FOR UPDATE
USING (
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
WITH CHECK (
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
);

CREATE POLICY assigned_case_delete
ON cases
AS RESTRICTIVE
FOR DELETE
USING (
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
);

CREATE POLICY case_insert_by_authenticated_creator
ON cases
AS RESTRICTIVE
FOR INSERT
WITH CHECK (
    created_by_provider_id = nullif(current_setting('app.provider_id', true), '')
    AND safety_screened_by_provider_id = nullif(current_setting('app.provider_id', true), '')
    AND version = 1
    AND status IN ('intake', 'safety_hold')
    AND current_pathway_id IS NULL
    AND current_pathway_version IS NULL
);

COMMENT ON POLICY case_insert_by_authenticated_creator ON cases IS
'Allows an authenticated institutional provider to create only a new intake or safety-hold case attributed to that same provider. Subsequent visibility still requires lead assignment, active case assignment, or institutional audit scope.';

COMMENT ON POLICY assigned_case_select ON cases IS
'Case visibility is assignment-based and is intentionally separate from the one-time creation policy.';

COMMIT;
