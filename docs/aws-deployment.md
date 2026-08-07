# AWS application deployment and recovery

This runbook implements ADR-0022 without changing ChangeOps product boundaries. Terraform owns
the AWS environment; the protected `Deploy production` workflow owns immutable application
releases. No workflow creates infrastructure, changes database roles, reads the RDS administrator
secret, or silently runs migrations during application startup.

## Release controls

- The `production` GitHub Environment must require a human reviewer, prevent unreviewed branches,
  and allow only `main`.
- GitHub Actions uses the Terraform-created OIDC role. Do not configure AWS access-key secrets.
- ECR image tags are the full Git commit SHA in immutable repositories.
- Alembic runs as a separate Fargate task with the migration-only database secret. The service is
  updated only after migration and a separate runtime-authority fictional-data setup task both
  exit successfully.
- The first release is prepared while ECS desired count is zero. This prevents an empty ECR
  repository and placeholder task revision from creating a first-deployment deadlock.
- ECS health checks, ALB target health, the deployment circuit breaker, and the post-deployment
  smoke check gate success. A failed rollout is returned to the previous task definition.
- A second protected workflow accepts only a non-seeded run ID and checks the persisted identities
  and artifacts from a human-performed deployed journey. Fixture records are never accepted as
  live journey evidence.
- The long-running task receives only the restricted runtime database secret and configured
  provider secrets. It never receives the migration or RDS administrator credential.

## One-time environment and database bootstrap

Complete the safe off-state provisioning in
[`infra/terraform/README.md`](../infra/terraform/README.md) first. Applying a saved Terraform plan
still requires explicit human review of the exact account, domain, resources, and cost impact.

The private RDS database needs two non-administrative logins before the first release. Keep the
RDS-managed administrator credential out of ECS:

1. Create an AWS CloudShell VPC environment in one Terraform output `public_subnet_ids` subnet and
   attach the Terraform output `task_security_group_id`. Delete that CloudShell VPC environment
   after bootstrap. This gives the short-lived operator shell the same database network path as
   the application without making RDS public. After entering that VPC environment, use the
   CloudShell **Actions → Upload file** control to upload the reviewed
   `scripts/bootstrap_database_roles.sql`; do not depend on internet access or persistent storage.
   Compare `sha256sum scripts/bootstrap_database_roles.sql` there with the checksum from the
   reviewed `main` checkout before executing it.
2. In CloudShell, confirm the account and retrieve the non-secret outputs:

   ```bash
   aws sts get-caller-identity
   aws rds describe-db-instances \
     --db-instance-identifier changeops-demo-postgres \
     --query 'DBInstances[0].{host:Endpoint.Address,port:Endpoint.Port,public:PubliclyAccessible}'
   ```

   Stop unless `public` is `false` and the account is the reviewed portfolio account.
3. Install the PostgreSQL 17 client if the CloudShell image does not already provide `psql`.
   Retrieve the AWS-managed administrator secret into shell variables without printing it:

   ```bash
   admin_secret_arn="PASTE_TERRAFORM_OUTPUT_database_admin_secret_arn"
   admin_secret="$(aws secretsmanager get-secret-value \
     --secret-id "${admin_secret_arn}" \
     --query SecretString --output text)"
   export PGUSER="$(jq -r .username <<<"${admin_secret}")"
   export PGPASSWORD="$(jq -r .password <<<"${admin_secret}")"
   export PGHOST="PASTE_PRIVATE_DATABASE_ENDPOINT"
   export PGPORT=5432
   export PGDATABASE=changeops
   export PGSSLMODE=require
   ```
4. Generate two distinct high-entropy passwords and store them temporarily in mode-`0600` JSON
   files. Run the reviewed role script and paste the matching value at each masked `\password`
   prompt:

   ```bash
   psql --file scripts/bootstrap_database_roles.sql
   ```

   The script creates fixed `changeops_schema_owner` and `changeops_runtime` roles, transfers
   schema ownership to the migration role, removes runtime DDL authority, and establishes only
   the required DML/default privileges.
5. Put `{"username":"changeops_schema_owner","password":"..."}` in the migration secret and
   `{"username":"changeops_runtime","password":"..."}` in the runtime secret. Populate the model
   provider secret and optional dedicated Jira/Confluence secrets using the shapes in the
   infrastructure runbook. Never use customer or production-enterprise credentials.
6. Test both non-administrative credentials over TLS, unset `PGPASSWORD`, clear the administrator
   JSON variable, securely remove temporary files, close CloudShell, and delete its VPC
   environment.

## Configure protected deployment

Create the repository environment named `production` with required reviewers and a `main`-only
deployment branch rule. Add these non-secret environment variables:

| Variable | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | Terraform output `github_deploy_role_arn` |
| `AWS_REGION` | `us-east-1` |
| `APPLICATION_URL` | Terraform output `application_url` while the demo window is enabled |

The Terraform OIDC trust policy expects
`repo:jaydreyer/ChangeOps:environment:production`. The workflow declares
`id-token: write` and obtains short-lived credentials; no long-lived AWS key is stored by GitHub.

## Prepare and deploy

1. Review and merge the release to `main`.
2. Keep `demo_enabled = false`, make the private RDS instance available, and confirm the ECS
   service desired count is zero. In GitHub Actions, run **Deploy production** from `main` with
   `release_mode=prepare` and approve the protected environment gate. `APPLICATION_URL` is not
   needed in this phase.
3. The prepare phase:
   - builds reproducible Linux/AMD64 backend and frontend images from locked dependencies and
     digest-pinned base images;
   - publishes both images under the full commit SHA;
   - registers application, migration, and restricted fixture task-definition revisions without
     changing reviewed environment or secret wiring;
   - runs `alembic upgrade head` as an explicit one-off task;
   - initializes and validates the idempotent fictional catalog and demo timeline with restricted
     runtime DB authority; and
   - points the zero-count ECS service at the prepared application revision.
4. Create and review the exact Terraform plan that changes `demo_enabled` to `true`. Apply only
   that saved, human-approved plan. Confirm desired task count is one, the ALB and application
   alias exist, and the protected `APPLICATION_URL` matches the Terraform output.
5. Run **Deploy production** again with `release_mode=deploy`. This idempotently repeats migration
   and fixture setup, rolls the two-container service, waits for ECS/ALB health, and:
   - verifies public HTTPS Next.js-to-FastAPI readiness, Cognito enforcement on product routes,
     required security headers, and the same request ID in CloudWatch API logs.

## Verify the deployed flagship journey

The fictional fixture makes the international-travel story immediately inspectable, including a
deterministic Jira receipt and prevented replay. It is data setup, not proof that authentication,
human approval, and execution work in the deployed application.

After a successful deploy:

1. Sign in through Cognito as an invited `reviewer`. Create and complete a new international-travel
   policy analysis, decide every proposed action, and save the new policy-analysis run ID. Do not
   use the pre-seeded run.
2. Sign in as an invited `admin`. Open that completed approval, prepare the immutable commands,
   explicitly execute at least one simulated learning assignment, inspect its result and the
   Unified Audit Timeline.
3. Confirm the seeded Jira item is clearly labeled fictional/deterministic and its timeline
   contains the Jira receipt and replay prevention.
4. From the deployed commit on `main`, run **Verify production flagship**. Supply the full deployed
   commit SHA, new policy-analysis run ID, and the exact confirmation
   `verified-live-human-journey`. Approve the protected environment gate. Actor subjects remain
   only in the immutable business audit trail and are not copied into workflow or CloudWatch logs.
5. Preserve the successful workflow URL as acceptance evidence. The workflow fails unless the
   named SHA is running, the run was created after the currently running task started, the run is
   not the deterministic seed, review decisions have one authenticated reviewer identity and role,
   immutable preparation and explicit successful execution have one authenticated admin identity
   and role, the simulated side effect and provenance exist, the deterministic Jira fixture exists,
   and the public HTTPS/authentication boundary remains healthy.

Do not report the flagship deployment verified until this protected workflow succeeds.

## Failure and rollback

- A migration or fixture-setup failure stops the workflow before the service changes. Inspect
  `/changeops/demo/migration`; fix forward and rerun. Never represent a failed task as successful.
- An unhealthy task triggers the ECS circuit breaker and automatic rollback. A failure in the
  post-deployment smoke check explicitly restores the prior task-definition revision.
- Database migrations are forward-only during automated rollback. Do not automatically downgrade.
  If a reviewed migration is incompatible with the previous application, ship a compatible
  forward fix or use the documented RDS snapshot recovery procedure.
- For database corruption or loss, restore the latest verified snapshot as described in
  ADR-0022, reapply private networking, TLS, backup, deletion-protection, and log-export controls,
  then repeat migration, fixture setup, deployment, and protected flagship verification. Retain
  the predecessor snapshot until the restored audit timeline passes.
- Between demos, follow the safe off-state procedure in the Terraform runbook. Confirm ECS counts
  are zero, the ALB is absent, and RDS is stopped for at most seven days or replaced by a verified
  retained snapshot. An unavailable URL alone is not proof that billing has stopped.

## Acceptance evidence

| Requirement | Evidence |
|---|---|
| Reproducible production containers | Digest-pinned base images, `requirements.lock` hashes, `package-lock.json`, non-root runtime stages, CI image builds |
| Runtime configuration and secrets | ECS non-secret environment fields plus separately scoped Secrets Manager injections |
| Controlled migration | Protected one-off migration task completes before service update |
| Health and HTTPS architecture | ECS container checks, ALB target check, public `/readyz` through Next.js to task-local FastAPI, and tested HSTS/security headers |
| Authentication boundary | ES256 ALB claim verification, Cognito access-token verification, exact one-group mapping, proxy header replacement tests |
| Observability | Structured JSON stdout, CloudWatch log groups, response/request correlation check |
| Keyless CI/CD | GitHub Environment approval plus AWS OIDC role |
| Fictional demo setup | Restricted, idempotent setup validates the deterministic Jira receipt, replay prevention, and immediately inspectable Unified Audit Timeline without claiming live proof |
| Flagship journey | Protected post-deployment evidence task rejects the seed and checks a human-performed analysis, reviewer identity, approval, immutable preparation, admin identity, explicit successful execution, simulated side effect, and audit provenance |
| Recovery | ECS automatic/manual application rollback and reviewed forward-only database recovery above |
