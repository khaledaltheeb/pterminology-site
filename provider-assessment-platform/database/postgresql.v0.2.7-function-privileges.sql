BEGIN;

SET search_path TO provider_assessment, public;

REVOKE ALL ON FUNCTION deny_immutable_mutation() FROM PUBLIC;
REVOKE ALL ON FUNCTION set_case_update_metadata() FROM PUBLIC;
REVOKE ALL ON FUNCTION enforce_case_safety_hold() FROM PUBLIC;
REVOKE ALL ON FUNCTION enforce_review_version_chain() FROM PUBLIC;
REVOKE ALL ON FUNCTION enforce_assessment_plan_version_chain() FROM PUBLIC;
REVOKE ALL ON FUNCTION enforce_approved_team_review_for_report() FROM PUBLIC;
REVOKE ALL ON FUNCTION enforce_audit_event_chain() FROM PUBLIC;
REVOKE ALL ON FUNCTION institution_audit_chain_tip(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION current_institution_last_audit_hash() FROM PUBLIC;

COMMENT ON FUNCTION institution_audit_chain_tip(text) IS
'Internal SECURITY DEFINER helper. PUBLIC execution is revoked because the institution argument must never be caller-controlled.';

COMMENT ON FUNCTION current_institution_last_audit_hash() IS
'Application-facing SECURITY DEFINER function. PUBLIC execution is revoked; deployment grants it only to the non-bypass service role.';

COMMIT;
