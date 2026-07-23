BEGIN;

SET search_path TO provider_assessment, public;

ALTER TABLE assessment_plans
    ADD COLUMN plan_group_id text;

UPDATE assessment_plans
SET plan_group_id = assessment_plan_id
WHERE plan_group_id IS NULL;

ALTER TABLE assessment_plans
    ALTER COLUMN plan_group_id SET NOT NULL,
    ADD CONSTRAINT assessment_plans_group_id_format
        CHECK (plan_group_id ~ '^PLANG-[A-Z0-9-]{8,50}$' OR plan_group_id = assessment_plan_id),
    ADD CONSTRAINT assessment_plans_group_version_key
        UNIQUE (institution_id, case_id, plan_group_id, version),
    ADD CONSTRAINT assessment_plans_version_chain_check
        CHECK (
            (version = 1 AND supersedes_plan_id IS NULL)
            OR (version > 1 AND supersedes_plan_id IS NOT NULL)
        );

CREATE TRIGGER assessment_plans_immutable
BEFORE UPDATE OR DELETE ON assessment_plans
FOR EACH ROW EXECUTE FUNCTION deny_immutable_mutation();

ALTER TABLE team_reviews
    ADD COLUMN review_group_id text,
    ADD COLUMN version integer NOT NULL DEFAULT 1,
    ADD COLUMN supersedes_team_review_id text,
    ADD COLUMN created_by_provider_id text;

-- The baseline intentionally makes team reviews append-only. The trigger is
-- disabled only inside this transaction while existing rows are backfilled,
-- then restored before commit. PostgreSQL transactional DDL restores the
-- original state automatically if any following statement fails.
ALTER TABLE team_reviews DISABLE TRIGGER team_reviews_immutable;

UPDATE team_reviews review
SET review_group_id = review.team_review_id,
    created_by_provider_id = COALESCE(
        review.approved_by_provider_id,
        pathway.started_by_provider_id
    )
FROM pathway_instances pathway
WHERE pathway.pathway_instance_id = review.pathway_instance_id
  AND pathway.institution_id = review.institution_id
  AND pathway.case_id = review.case_id
  AND (
      review.review_group_id IS NULL
      OR review.created_by_provider_id IS NULL
  );

ALTER TABLE team_reviews ENABLE TRIGGER team_reviews_immutable;

ALTER TABLE team_reviews
    ALTER COLUMN review_group_id SET NOT NULL,
    ALTER COLUMN created_by_provider_id SET NOT NULL,
    ADD CONSTRAINT team_reviews_version_positive CHECK (version >= 1),
    ADD CONSTRAINT team_reviews_group_id_format
        CHECK (review_group_id ~ '^TREVG-[A-Z0-9-]{8,50}$' OR review_group_id = team_review_id),
    ADD CONSTRAINT team_reviews_group_version_key
        UNIQUE (institution_id, case_id, review_group_id, version),
    ADD CONSTRAINT team_reviews_created_by_tenant_fkey
        FOREIGN KEY (created_by_provider_id, institution_id)
        REFERENCES providers(provider_id, institution_id),
    ADD CONSTRAINT team_reviews_supersedes_tenant_case_fkey
        FOREIGN KEY (supersedes_team_review_id, institution_id, case_id)
        REFERENCES team_reviews(team_review_id, institution_id, case_id),
    ADD CONSTRAINT team_reviews_version_chain_check
        CHECK (
            (version = 1 AND supersedes_team_review_id IS NULL)
            OR (version > 1 AND supersedes_team_review_id IS NOT NULL)
        ),
    ADD CONSTRAINT team_reviews_meaningful_text_check
        CHECK (
            length(trim(decision)) >= 10
            AND length(trim(limitations)) >= 10
        ),
    ADD CONSTRAINT team_reviews_approved_members_check
        CHECK (
            status <> 'approved'
            OR jsonb_array_length(member_provider_ids) >= 2
        );

CREATE OR REPLACE FUNCTION enforce_review_version_chain()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    previous_group_id text;
    previous_version integer;
    previous_status text;
BEGIN
    IF NEW.version = 1 THEN
        RETURN NEW;
    END IF;

    SELECT review_group_id, version, status
    INTO previous_group_id, previous_version, previous_status
    FROM team_reviews
    WHERE team_review_id = NEW.supersedes_team_review_id
      AND institution_id = NEW.institution_id
      AND case_id = NEW.case_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'superseded team review was not found in the same institution and case';
    END IF;

    IF previous_group_id <> NEW.review_group_id THEN
        RAISE EXCEPTION 'team review version must remain in the same review group';
    END IF;

    IF previous_version + 1 <> NEW.version THEN
        RAISE EXCEPTION 'team review version must increment by exactly one';
    END IF;

    IF previous_status = 'approved' AND NEW.status = 'draft' THEN
        RAISE EXCEPTION 'an approved team review cannot be superseded by an unapproved draft';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER team_review_version_chain
BEFORE INSERT ON team_reviews
FOR EACH ROW EXECUTE FUNCTION enforce_review_version_chain();

CREATE OR REPLACE FUNCTION enforce_assessment_plan_version_chain()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    previous_group_id text;
    previous_version integer;
    previous_status text;
BEGIN
    IF NEW.version = 1 THEN
        RETURN NEW;
    END IF;

    SELECT plan_group_id, version, status
    INTO previous_group_id, previous_version, previous_status
    FROM assessment_plans
    WHERE assessment_plan_id = NEW.supersedes_plan_id
      AND institution_id = NEW.institution_id
      AND case_id = NEW.case_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'superseded assessment plan was not found in the same institution and case';
    END IF;

    IF previous_group_id <> NEW.plan_group_id THEN
        RAISE EXCEPTION 'assessment plan version must remain in the same plan group';
    END IF;

    IF previous_version + 1 <> NEW.version THEN
        RAISE EXCEPTION 'assessment plan version must increment by exactly one';
    END IF;

    IF previous_status = 'approved' AND NEW.status = 'draft' THEN
        RAISE EXCEPTION 'an approved assessment plan cannot be superseded by an unapproved draft';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER assessment_plan_version_chain
BEFORE INSERT ON assessment_plans
FOR EACH ROW EXECUTE FUNCTION enforce_assessment_plan_version_chain();

CREATE OR REPLACE FUNCTION enforce_approved_team_review_for_report()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    review_status text;
    review_approved_at timestamptz;
BEGIN
    SELECT status, approved_at
    INTO review_status, review_approved_at
    FROM team_reviews
    WHERE team_review_id = NEW.team_review_id
      AND institution_id = NEW.institution_id
      AND case_id = NEW.case_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'team review was not found for the report institution and case';
    END IF;

    IF review_status <> 'approved' OR review_approved_at IS NULL THEN
        RAISE EXCEPTION 'report creation requires an approved team review';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER report_requires_approved_team_review
BEFORE INSERT ON report_versions
FOR EACH ROW EXECUTE FUNCTION enforce_approved_team_review_for_report();

CREATE VIEW current_assessment_plans
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (institution_id, case_id, plan_group_id)
    assessment_plan_id,
    institution_id,
    case_id,
    pathway_instance_id,
    plan_group_id,
    version,
    domains,
    assessment_ids,
    rationale,
    status,
    approved_by_provider_id,
    approved_at,
    created_by_provider_id,
    created_at,
    supersedes_plan_id
FROM assessment_plans
ORDER BY institution_id, case_id, plan_group_id, version DESC;

CREATE VIEW current_team_reviews
WITH (security_invoker = true)
AS
SELECT DISTINCT ON (institution_id, case_id, review_group_id)
    team_review_id,
    institution_id,
    case_id,
    pathway_instance_id,
    review_group_id,
    version,
    status,
    member_provider_ids,
    decision,
    supporting_evidence_ids,
    contrary_evidence_ids,
    limitations,
    support_needs,
    approved_by_provider_id,
    approved_at,
    created_by_provider_id,
    created_at,
    supersedes_team_review_id
FROM team_reviews
ORDER BY institution_id, case_id, review_group_id, version DESC;

COMMENT ON COLUMN assessment_plans.plan_group_id IS
'Stable identifier shared by all append-only versions of one assessment plan.';

COMMENT ON COLUMN team_reviews.review_group_id IS
'Stable identifier shared by all append-only versions of one multidisciplinary review.';

COMMENT ON TRIGGER report_requires_approved_team_review ON report_versions IS
'Prevents report drafts or signed reports from referencing an unapproved team review.';

COMMIT;
