# ChangeOps AWS infrastructure

This directory implements GitHub issue #44 and the fixed deployment architecture in ADR-0022.
Terraform is the source of truth for managed AWS resources. It does not deploy application
releases, run Alembic, create database roles, seed data, or implement the later demo-lifecycle
workflows.

## Application deployment gate

Issue #45 implements and tests ADR-0022's application prerequisites:

1. Next.js verifies ALB and Cognito claims and fails closed.
2. The proxy replaces, rather than forwards, browser actor and role headers.
3. Backend and migration processes assemble a TLS-required database URL from separate endpoint
   and injected credential fields.
4. Request IDs and secret-safe structured JSON logs are implemented.
5. Next.js exposes the configured health endpoint.
6. Production container sizing and the bounded synchronous path are verified.

The protected two-phase release workflow, initial database-role bootstrap, live human-journey
evidence gate, and recovery steps are in
[`docs/aws-deployment.md`](../../docs/aws-deployment.md). This does not authorize an
unreviewed Terraform apply: the exact saved plan, account, domain, and cost impact still require
human approval. The safe default is `demo_enabled = false`: no ALB or application DNS alias and
ECS desired count zero.

## Root layout and provisioned controls

- `bootstrap/` creates the private, encrypted, versioned S3 state bucket. It is separate because a
  backend cannot create its own bucket before initialization.
- `environments/demo/` creates the single approved environment. Files are separated by concern,
  with no generic modules because no actual reuse exists.

The demo root provisions:

- one two-AZ VPC with public runtime and isolated database subnets;
- security groups allowing only ALB-to-Next.js on 3000 and task-to-RDS on 5432, with no public
  FastAPI or RDS ingress;
- immutable scan-on-push ECR repositories;
- one two-container Fargate application task, separate migration and fictional-bootstrap task
  definitions with distinct DB authority, and one ECS service;
- encrypted private Single-AZ PostgreSQL 17 RDS, 20 GiB gp3 storage, 50 GiB autoscaling cap,
  seven-day backups, TLS enforcement, log exports, deletion protection, and an AWS-managed
  break-glass master password;
- separate empty Secrets Manager containers for runtime DB, migration DB, model-provider, Jira,
  and Confluence credentials—never secret values in Terraform source;
- a closed Cognito pool with required TOTP MFA and `reviewer` and `admin` groups;
- ACM and Route 53, plus Cognito-authenticated ALB ingress only when a demo is enabled;
- separate least-privilege application/migration execution roles, permissionless task roles, and
  GitHub OIDC deploy/lifecycle roles restricted to the protected production environment;
- 30-day logs, a dashboard, alarms, event notifications, SNS, and a tag-filtered USD 20 budget.

## Local verification

From the repository root:

```bash
terraform fmt -check -recursive infra/terraform
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap validate
terraform -chdir=infra/terraform/bootstrap test
terraform -chdir=infra/terraform/environments/demo init -backend=false
terraform -chdir=infra/terraform/environments/demo validate
terraform -chdir=infra/terraform/environments/demo test
```

The native tests prove the default off state, declared one-task demo state, private Single-AZ
database controls, fixed task size and ALB timeout, Region guard, and exact destructive
confirmation guard.

## Initial provisioning checklist

Complete this only after the hard deployment gate is satisfied.

### 1. Confirm the AWS account and operator session

Use a dedicated portfolio AWS account or one where the USD 20 budget is appropriate. Do not
provide or commit long-lived access keys.

1. Install AWS CLI v2 and Terraform 1.15.8 (or a compatible `versions.tf` version).
2. Configure an AWS IAM Identity Center session:

   ```bash
   aws configure sso --profile changeops-admin
   aws sso login --profile changeops-admin
   export AWS_PROFILE=changeops-admin
   export AWS_REGION=us-east-1
   ```

3. Verify the exact account:

   ```bash
   aws sts get-caller-identity
   ```

4. Stop if the returned 12-digit `Account` is not the intended account.
5. The initial provisioning identity needs permission for S3 state, VPC/EC2 networking, ECR, ECS,
   ELBv2, RDS, Secrets Manager, Cognito, ACM, Route 53, IAM/OIDC, CloudWatch, EventBridge, SNS, and
   AWS Budgets. If temporary administrator access is used for the reviewed bootstrap, remove it
   immediately afterward.

### 2. Bootstrap secure Terraform state

The first bootstrap apply uses Terraform's implicit local backend because the bucket does not yet
exist. The committed S3 backend is deliberately an inactive `.example` file during this phase;
`terraform init -backend=false` is not a substitute for a usable local backend.

1. Initialize the implicit local backend and create a saved plan:

   ```bash
   terraform -chdir=infra/terraform/bootstrap init
   terraform -chdir=infra/terraform/bootstrap plan -out=bootstrap.tfplan
   terraform -chdir=infra/terraform/bootstrap show bootstrap.tfplan
   ```

2. Confirm the plan creates only the account-scoped state bucket, versioning, AES-256
   server-side encryption, all four public-access blocks, and the TLS-only bucket policy. After
   explicit human approval of that exact saved plan, apply it and print the bucket name:

   ```bash
   terraform -chdir=infra/terraform/bootstrap apply bootstrap.tfplan
   terraform -chdir=infra/terraform/bootstrap output -raw state_bucket_name
   ```

3. Keep the local `terraform.tfstate` until migration is verified. Activate the reviewed partial
   S3 backend configuration in the ignored override file, then migrate the state to the bucket:

   ```bash
   cp infra/terraform/bootstrap/backend.s3.tf.example \
     infra/terraform/bootstrap/backend_override.tf
   terraform -chdir=infra/terraform/bootstrap init -migrate-state \
     -backend-config="bucket=PASTE_BUCKET_NAME" \
     -backend-config="region=us-east-1"
   ```

4. Answer `yes` only when Terraform asks to copy the existing local state into that exact bucket.
   Do not use `-reconfigure`, which changes backend configuration without migrating state.
5. Verify remote state:

   ```bash
   terraform -chdir=infra/terraform/bootstrap state list
   ```

6. Continue only when the state list includes the state bucket and every protection resource. If
   a local state copy remains, move it to encrypted storage and securely remove the working copy.
   Keep the ignored `backend_override.tf` for commands from this checkout. The bucket is
   versioned, encrypted, public-access-blocked, TLS-only, lock-enabled, and protected from
   Terraform destruction.

For a later clean checkout, recreate `backend_override.tf` from the committed example and run
`terraform init -reconfigure` with the exact bucket and Region backend arguments. Use
`-migrate-state` only when a local state file actually needs to be copied. Run `terraform state
list` and confirm the expected protected bucket resources before any plan or apply from that
checkout.

### 3. Prepare the environment configuration

1. Create the ignored variable file:

   ```bash
   cp infra/terraform/environments/demo/terraform.tfvars.example \
     infra/terraform/environments/demo/terraform.tfvars
   ```

2. Set the registered `hosted_zone_name`, the `application_hostname` subdomain, `alert_email`,
   `github_repository = "jaydreyer/ChangeOps"`, `github_environment = "production"`, and
   `demo_enabled = false`.
3. After independently verifying every hard-gate prerequisite at the top of this document, set
   `infrastructure_prerequisites_confirmed = true`. Terraform rejects every environment plan while
   it remains false.
4. If the public Route 53 zone already exists, find its ID:

   ```bash
   aws route53 list-hosted-zones-by-name --dns-name example.com
   ```

   Set `existing_hosted_zone_id` to the exact ID. Do not create a duplicate zone.
5. Check for an existing GitHub OIDC provider:

   ```bash
   ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
   aws iam get-open-id-connect-provider \
     --open-id-connect-provider-arn \
     "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
   ```

   If it exists, set `existing_github_oidc_provider_arn` to that ARN. If AWS returns
   `NoSuchEntity`, leave it unset. AWS validates GitHub with trusted root CAs; no pinned
   thumbprint is stored.

### 4. Initialize the demo root

```bash
terraform -chdir=infra/terraform/environments/demo init \
  -backend-config="bucket=PASTE_BUCKET_NAME" \
  -backend-config="region=us-east-1"
terraform -chdir=infra/terraform/environments/demo validate
terraform -chdir=infra/terraform/environments/demo test
```

### 5. Delegate DNS when Terraform creates the zone

Skip this when `existing_hosted_zone_id` is set.

1. Create only the hosted zone and print its four nameservers:

   ```bash
   terraform -chdir=infra/terraform/environments/demo apply \
     -target=aws_route53_zone.app
   terraform -chdir=infra/terraform/environments/demo output hosted_zone_name_servers
   ```

2. At the domain registrar, open the domain's DNS/nameserver settings, choose custom nameservers,
   replace the current set with all four Route 53 values, and save.
3. Wait for delegation, then verify:

   ```bash
   dig NS example.com +short
   ```

   Continue only when the returned set matches Terraform. Propagation can take from minutes to the
   registrar's published maximum.

### 6. Review and apply the safe off-state infrastructure

```bash
terraform -chdir=infra/terraform/environments/demo plan -out=demo-off.tfplan
terraform -chdir=infra/terraform/environments/demo apply demo-off.tfplan
terraform -chdir=infra/terraform/environments/demo output
```

Before applying, confirm the saved plan has no ALB or application A alias, ECS desired count
is zero, RDS is private/Single-AZ/deletion-protected, and no NAT Gateway, Kubernetes, queue, event
bus, API Gateway, or Lambda appears.

### 7. Finish notifications and cost visibility

1. Open the AWS SNS email for `changeops-demo-operations` and choose **Confirm subscription**.
2. In **Billing and Cost Management** → **Cost allocation tags** → **User-defined cost allocation
   tags**, select `Application` and choose **Activate**.
3. In **Budgets**, verify `changeops-demo-monthly`: USD 20, with 50%, 80%, and 100% actual-spend
   notifications. Activated tag data may take up to 24 hours to appear.

### 8. Configure the protected GitHub Environment

Terraform trusts only `repo:jaydreyer/ChangeOps:environment:production`. GitHub must enforce the
human and branch side:

1. Repository **Settings** → **Environments** → **New environment**.
2. Enter `production` exactly and choose **Configure environment**.
3. Enable **Required reviewers** and add the intended human approver.
4. Enable **Prevent self-review** when a different approver is available.
5. Under **Deployment branches and tags**, choose **Selected branches and tags** and add only the
   protected `main` branch.
6. Save. Later workflows must declare `environment: production` and
   `permissions: id-token: write, contents: read`, use the Terraform output role ARNs, and never
   use stored AWS access keys.

### 9. Populate secrets only during the later deployment bootstrap

Terraform creates secret containers but no values. After a separately reviewed database bootstrap
creates the schema-owner and restricted runtime users, create mode-`0600` JSON files outside the
repository and use `aws secretsmanager put-secret-value --secret-string file://...`.

Required shapes:

```json
{"username":"restricted_runtime_user","password":"generated-password"}
```

```json
{"username":"schema_owner_user","password":"different-generated-password"}
```

```json
{"api_key":"portfolio-model-provider-key"}
```

Optional Jira/Confluence shape:

```json
{"email":"dedicated-portfolio-user@example.com","api_token":"dedicated-token"}
```

Never use customer, Workday, Salesforce, or production-enterprise credentials. Never put values
in `.tfvars`, GitHub secrets, task definitions, shell history, or repository files. Securely
delete the local JSON files after AWS confirms the secret versions.

### 10. Invite closed Cognito users only for a demo

1. AWS Console → **Cognito** → **User pools** → `changeops-demo-users`.
2. **Users** → **Create user**; enter the invited email and send a temporary password.
3. Open the user → **Add user to group**; choose exactly one of `reviewer` or `admin`, never both.
4. At first sign-in the user changes the temporary password and enrolls an authenticator-app TOTP
   factor. MFA is required.
5. Disable or delete temporary users after the demo when access should not persist.

## Routine safe off state

1. Set `demo_enabled = false`.
2. Save and review the plan:

   ```bash
   terraform -chdir=infra/terraform/environments/demo plan -out=demo-off.tfplan
   ```

3. Confirm it sets ECS desired count to zero and destroys only the ALB, listeners, the A alias,
   and demo-only alarms. Apply the saved plan.
4. Verify:

   ```bash
   aws ecs describe-services \
     --cluster changeops-demo-cluster \
     --services changeops-demo-service \
     --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}'
   aws elbv2 describe-load-balancers --names changeops-demo-alb
   ```

   ECS counts must all be zero; ELB must return `LoadBalancerNotFound`.
5. For a known break of at most seven days:

   ```bash
   aws rds stop-db-instance --db-instance-identifier changeops-demo-postgres
   aws rds wait db-instance-stopped --db-instance-identifier changeops-demo-postgres
   ```

AWS automatically restarts RDS after seven stopped days. A stopped DB is not a durable long-term
off state. The later reviewed lifecycle workflow will automate these operations and billable
inventory verification; until then, never report a partial teardown as off.

## Full environment teardown

Full teardown is destructive, not the normal between-demo operation.

1. Complete the routine safe off state.
2. Choose a unique final snapshot ID, such as `changeops-demo-final-20260806t230000z`.
3. Plan and apply only the deletion-protection change:

   ```bash
   terraform -chdir=infra/terraform/environments/demo plan \
     -var='allow_database_destroy=true' \
     -var='database_destroy_confirmation=demo' \
     -var='database_final_snapshot_identifier=changeops-demo-final-20260806t230000z' \
     -out=disable-db-protection.tfplan
   terraform -chdir=infra/terraform/environments/demo apply disable-db-protection.tfplan
   ```

   Confirm the only DB change is `deletion_protection: true → false`.
4. Create and review the destroy plan with the same exact values:

   ```bash
   terraform -chdir=infra/terraform/environments/demo plan -destroy \
     -var='allow_database_destroy=true' \
     -var='database_destroy_confirmation=demo' \
     -var='database_final_snapshot_identifier=changeops-demo-final-20260806t230000z' \
     -out=destroy-demo.tfplan
   ```

5. Confirm account, environment, every target, retained state bucket, and final snapshot ID.
   Obtain human approval, then apply only the saved plan:

   ```bash
   terraform -chdir=infra/terraform/environments/demo apply destroy-demo.tfplan
   ```
6. Verify the final snapshot:

   ```bash
   aws rds wait db-snapshot-available \
     --db-snapshot-identifier changeops-demo-final-20260806t230000z
   aws rds describe-db-snapshots \
     --db-snapshot-identifier changeops-demo-final-20260806t230000z
   ```

7. Confirm Cost Explorer and resource inventory show no ALB, running Fargate task, public task
   address, or RDS instance. A failed destroy is not success.
8. Retain the verified snapshot and its verified predecessor. Deleting an older snapshot is a
   separate human-approved retention action.

The bootstrap state bucket is intentionally separate and protected. Archive its versioned state
before proposing any removal; never bypass `prevent_destroy` casually.

## What Codex can execute for the operator

Codex can run the bootstrap, plans, reviewed applies, read-only verification, and GitHub
Environment configuration in a later explicitly authorized task. To do that safely, provide:

1. the intended 12-digit AWS account ID;
2. the registered parent domain and desired ChangeOps hostname;
3. whether the Route 53 hosted zone already exists and, if so, its zone ID;
4. the operational alert email;
5. an active AWS IAM Identity Center session available as a named local AWS CLI profile with the
   provisioning permissions listed above—never send raw access keys in chat;
6. repository-admin authorization if Codex should configure the protected GitHub Environment; and
7. explicit authorization for the exact saved Terraform plan to be applied.

For a domain at an external registrar, either complete the four-nameserver delegation yourself or
explicitly authorize browser assistance while already signed in. Do not share the registrar
password. Secret values and Cognito users are not needed to provision the safe off-state
infrastructure, and Codex should not receive real secret values in chat.

Repository changes and CI perform validation only and create no cloud resources. Apply a saved
plan only through the reviewed operator procedure above, then use the protected application
deployment workflow and recovery runbook.
