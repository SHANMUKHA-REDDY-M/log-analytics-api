# Enterprise Log Analytics

Enterprise-oriented log ingestion, asynchronous processing, search, archival, and
real-time dashboard application.

The backend is built with FastAPI, SQLAlchemy 2, PostgreSQL, Redis, Celery, and
RabbitMQ. The frontend is a React/Vite dashboard. Local development uses Docker
Compose, while the production deployment target is AWS EKS with Terraform,
Amazon ECR, External Secrets Operator, and GitHub Actions.

## What is implemented

### Application

- FastAPI API with asynchronous database access.
- PostgreSQL log persistence using SQLAlchemy 2 typed models and Alembic migrations.
- Pydantic request and response validation.
- API-key authentication through the `X-API-Key` header.
- Atomic Redis sliding-window rate limiting with HTTP 429 responses.
- Log ingestion, search, statistics, and WebSocket statistics streaming.
- Redis-backed cross-process publish/subscribe for real-time updates.
- Celery worker and beat configuration for asynchronous archival and cleanup.
- RabbitMQ broker and Redis result backend support.
- S3-compatible archival support. Local Compose uses Adobe S3Mock because the
previously referenced MinIO images are no longer available from the configured
registries.
- OpenTelemetry integration for FastAPI, SQLAlchemy, Redis, and Celery.
- Liveness, readiness, and database health endpoints.
- Configurable CORS, service URLs, rate limits, and telemetry settings.

### Frontend and local platform

- React/Vite dashboard in [`log-dashboard/`](./log-dashboard/).
- Docker Compose services for PostgreSQL, PgBouncer, Redis, RabbitMQ, S3Mock,
  Jaeger, Prometheus, Grafana, API, Celery, and the frontend.
- [`stream_simulator.py`](./stream_simulator.py) for bounded or continuous local
  ingestion traffic.

### Kubernetes and AWS

- Terraform baseline for a multi-AZ VPC, private EKS endpoint, managed node
  groups, S3 gateway endpoint, and secure archive bucket.
- On-Demand node group for API workloads.
- Spot node group for Celery workers.
- Kubernetes API, worker, and frontend Deployments with resource limits,
  security contexts, probes, rolling updates, and disruption budgets.
- Dedicated Alembic migration Job instead of running migrations concurrently
  inside every API replica.
- Default-deny and service-specific NetworkPolicies.
- External Secrets Operator manifests for AWS Secrets Manager.
- API HorizontalPodAutoscaler.
- GitHub Actions workflow with formatting, linting, migrations, tests, frontend
  build, immutable image publishing, manifest validation, migration Job execution,
  and rollout checks.
- Git repository initialized on `main` and published to:
  <https://github.com/SHANMUKHA-REDDY-M/log-analytics-api>

## What is not completed yet

These items are prepared for deployment but are not complete until they are
configured and verified in your AWS/GitHub account:

- Terraform has not been applied to an AWS account.
- The Terraform remote state S3 bucket and DynamoDB lock table must be created
  before `terraform init`.
- AWS IAM roles for GitHub OIDC, External Secrets Operator, and application
  access still need to be created and attached.
- ECR repositories and the EKS cluster must exist before the build/deploy jobs
  can succeed.
- The EKS endpoint is private-only in Terraform; GitHub-hosted runners cannot
  reach it without private network connectivity or a self-hosted runner.
- Kubernetes manifests still contain deployment placeholders such as
  `REPLACE_ACCOUNT_ID`, `REPLACE_ECR_REGISTRY`, and `REPLACE_IMAGE_TAG`.
  The workflow renders image placeholders, but the AWS account and IAM values
  must be configured.
- The AWS Secrets Manager secret `prod/log-analytics/env` must exist with all
  environment keys consumed by the application.
- External Secrets Operator and metrics-server must be installed in the cluster.
- A successful production EKS rollout has not yet been verified.
- The latest GitHub Actions run should be treated as the source of truth for
  CI status; inspect it before enabling required branch checks.
- GitHub branch protection has not been configured automatically.

## Deployment decision and current state

The application is currently deployed locally with Docker Compose, not on AWS.
An AWS EKS environment was provisioned temporarily during the deployment
investigation, but it was intentionally destroyed before leaving it running.
This was a cost-control decision: EKS worker nodes, NAT gateways, load
balancers, public IPv4 addresses, and related storage can continue generating
charges even when the application is not actively being used. The Terraform
state bucket and lock table were also deleted after the teardown.

This means:

- The local application is available for development and demonstration.
- No AWS EKS cluster, VPC, NAT gateway, or Terraform state backend from this
  setup is currently active.
- AWS deployment remains prepared in Terraform, Kubernetes, and GitHub Actions,
  but it has not received a final production rollout verification.
- Re-deploying to AWS requires a deliberate budget decision and should be
  treated as a new provisioning operation.

The local stack uses S3Mock at `http://localhost:9000` as an S3-compatible
test service. It is not a replacement for production AWS S3 and should not be
used to evaluate production durability, availability, or security.

## Repository layout

```text
app/                         FastAPI application, models, services, worker
alembic/                     Database migration environment and revisions
tests/                       Unit and integration tests
log-dashboard/               React/Vite frontend
k8s/                         Kubernetes manifests
terraform/                   AWS VPC, EKS, and S3 infrastructure
.github/workflows/ci-cd.yml  CI, image build, and EKS deployment workflow
docker-compose.yml           Local enterprise stack
stream_simulator.py          Local ingestion traffic generator
```

## Prerequisites

### Local development

- Python 3.11+
- Docker Desktop with the Docker daemon running
- Node.js and npm
- Git

### AWS deployment

- AWS CLI configured for the target account
- Terraform 1.6+ and AWS credentials
- `kubectl`
- An S3 bucket and DynamoDB table for Terraform state locking
- Permission to create VPC, EKS, IAM, S3, and related resources
- An EKS access path from the deployment runner
- An ECR registry and repositories, if they are not created separately
- External Secrets Operator and metrics-server installed in EKS

## Local quick start

1. Copy the example environment file and replace development values:

   ```bash
   cp .env.example .env
   ```

   Never commit `.env`. Use separate credentials for anything beyond local
   development.

2. Start the stack:

   ```bash
   docker compose up --build -d
   ```

3. Check the API:

   ```bash
   curl http://localhost:8000/health/live
   curl http://localhost:8000/health/ready
   ```

4. Open local tools:

   - API: <http://localhost:8000/docs>
   - Frontend: <http://localhost:3001>
   - RabbitMQ: <http://localhost:15672>
   - Flower: <http://localhost:5555>
   - S3Mock endpoint: <http://localhost:9000>
   - Jaeger: <http://localhost:16686>
   - Grafana: <http://localhost:3000>

5. Send a test log using a configured API key:

   ```bash
   curl -X POST http://localhost:8000/api/v1/logs/ \
     -H 'Content-Type: application/json' \
     -H 'X-API-Key: service-auth-xyz' \
     -d '{
       "service": "auth-service",
       "severity": "ERROR",
       "message": "Local deployment verification"
     }'
   ```

6. Generate bounded traffic:

   ```bash
   python stream_simulator.py --count 25 --interval 0.2
   ```

   Run continuously only when desired:

   ```bash
   python stream_simulator.py
   ```

7. Stop the stack:

   ```bash
   docker compose down
   ```

      Add `-v` only when you intentionally want to delete local database and
      S3Mock volumes.

## Validation

Run the focused Python checks:

```bash
python -m black --check app/ tests/
python -m flake8 app/ tests/ --max-line-length=88
pytest tests/ -v --disable-warnings
```

The API integration tests require PostgreSQL and Redis. Start the Compose stack
first, or provide equivalent services and environment variables.

At the time of this documentation update, the local runtime checks pass and
the focused tests pass. The full local test run reports 6 passed and 1
environment-sensitive failure in
`tests/api/test_logs.py::test_search_logs_by_severity`. The failing run occurs
when the async Redis client is cleaned up after its event loop has already
closed (`RuntimeError: Event loop is closed`); the same test passes when run
individually. This is a test-fixture/client lifecycle issue, not an API
readiness failure, but it should be fixed before claiming a clean CI baseline.

Build the frontend independently:

```bash
npm ci --prefix log-dashboard
npm run build --prefix log-dashboard
```

Generate coverage:

```bash
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
```

The HTML report is written to `htmlcov/`, which is ignored by Git.

## Production deployment runbook

This runbook provisions billable AWS resources. Do not start it unless the
account has an approved budget and someone is responsible for monitoring and
tearing down the environment. For a low-cost evaluation, use the local
Compose quick start instead.

The recommended order is:

1. Prepare AWS prerequisites.
2. Provision Terraform infrastructure.
3. Create IAM roles, ECR repositories, and cluster add-ons.
4. Create the Secrets Manager secret.
5. Configure GitHub Actions.
6. Run validation on a pull request.
7. Push to `main` to build and deploy.
8. Verify the migration Job and workload rollouts.

### 1. Prepare Terraform remote state

Create an S3 state bucket and DynamoDB lock table in the target AWS account.
The names must match [`terraform/backend.hcl.example`](./terraform/backend.hcl.example).
Enable bucket versioning and restrict access to the deployment operators.

Copy and edit the backend configuration:

```bash
cp terraform/backend.hcl.example terraform/backend.hcl
```

Do not commit `terraform/backend.hcl` if it contains account-specific values.

### 2. Provision VPC, EKS, and S3

```bash
cd terraform
terraform init -backend-config=backend.hcl
terraform validate
terraform plan \
  -var='state_bucket=YOUR_STATE_BUCKET' \
  -out=tfplan.binary
terraform show tfplan.binary
terraform apply tfplan.binary
```

The baseline creates a private-only EKS API endpoint. Run `kubectl` and the
deployment workflow from a network location that can reach the VPC, such as a
self-hosted GitHub Actions runner in the VPC, or change the endpoint strategy
after reviewing the security implications.

Record the outputs:

```bash
terraform output cluster_name
terraform output archive_bucket_name
terraform output vpc_id
```

### 3. Configure IAM and cluster add-ons

Create and verify:

- GitHub Actions OIDC provider and role.
- `GitHubActionsEKSRole` with only the ECR and EKS permissions required by the
  workflow.
- IAM role `log-analytics-external-secrets` trusted by the EKS service account
  `log-analytics-eso`.
- Application role permissions for the archive bucket and required AWS APIs.
- External Secrets Operator.
- Kubernetes metrics-server.
- EKS access entries or `aws-auth` permissions for the deployment identity.

The External Secrets manifest is
[`k8s/1-external-secrets.yaml`](./k8s/1-external-secrets.yaml). Replace the
account ID and role ARN before applying it.

### 4. Create ECR repositories

```bash
aws ecr create-repository \
  --repository-name log-analytics-api \
  --region ap-south-1

aws ecr create-repository \
  --repository-name log-frontend \
  --region ap-south-1
```

If the repositories already exist, continue without recreating them.

### 5. Create the application secret

Create the Secrets Manager secret referenced by the ExternalSecret:

```text
prod/log-analytics/env
```

Its JSON keys must match the environment variables consumed by the API and
workers, including database, Redis, Celery, API-key, CORS, telemetry, and S3
settings. Use production endpoints and credentials; do not copy local MinIO
credentials into AWS.

### 6. Configure the GitHub workflow

Update the environment values in
[`.github/workflows/ci-cd.yml`](./.github/workflows/ci-cd.yml):

- `AWS_REGION`
- `EKS_CLUSTER_NAME`
- `IAM_ROLE_ARN`
- ECR repository names, if different

The workflow:

- Runs `validate` on pushes and pull requests.
- Runs `build` only after a successful `validate` on `main`.
- Tags both images with the immutable commit SHA.
- Runs `deploy` only after a successful image build.
- Uses the `production` GitHub environment.
- Runs the migration Job before applying application workloads.

Configure the `production` environment with approval rules and any required
variables. For private EKS access, use a self-hosted runner or an equivalent
private connectivity design.

### 7. Deploy through GitHub Actions

Commit infrastructure and workflow configuration only after reviewing all
placeholders:

```bash
git add .
git commit -m "chore: configure production deployment"
git push origin main
```

Monitor the workflow at:

<https://github.com/SHANMUKHA-REDDY-M/log-analytics-api/actions>

The deployment order is:

1. `validate`
2. `build`
3. `deploy`
4. ExternalSecret application and secret readiness
5. Alembic migration Job
6. API, worker, frontend, and NetworkPolicy rollout

### 8. Verify the deployment

From a machine with cluster access:

```bash
kubectl get nodes
kubectl get pods
kubectl get jobs
kubectl get externalsecret,secretstore
kubectl get hpa

kubectl rollout status deployment/log-analytics-api
kubectl rollout status deployment/log-analytics-worker
kubectl rollout status deployment/log-analytics-frontend
```

Inspect failures with:

```bash
kubectl describe job/log-analytics-migrate-IMAGE_TAG
kubectl logs job/log-analytics-migrate-IMAGE_TAG
kubectl logs deployment/log-analytics-api
kubectl logs deployment/log-analytics-worker
kubectl get events --sort-by=.lastTimestamp
```

Replace `IMAGE_TAG` with the commit SHA used by the workflow.

Before exposing public traffic, also verify:

- API readiness and liveness probes.
- API-key rejection and rate-limit behavior.
- WebSocket updates.
- Celery queue consumption and archival.
- S3 archive object creation.
- Prometheus targets, Grafana dashboards, and Jaeger traces.
- NetworkPolicy behavior from frontend, API, and worker pods.
- Spot-node drain and graceful worker shutdown.

### 9. Cost monitoring and teardown

Before provisioning, create an AWS budget alert and enable cost notifications.
During the evaluation, monitor:

- EKS control-plane and worker-node charges.
- NAT gateway hourly and data-processing charges.
- Application load balancer and public IPv4 charges.
- ECR storage, S3 storage/requests, CloudWatch logs, and data transfer.

When the evaluation is finished, delete the application workloads first and
then destroy the Terraform-managed infrastructure:

```bash
cd terraform
terraform plan -destroy \
  -var='state_bucket=YOUR_STATE_BUCKET' \
  -out=destroy.plan
terraform show destroy.plan
terraform apply destroy.plan
```

After Terraform completes, verify that no EKS clusters, NAT gateways, load
balancers, or public IPv4 addresses remain. Keep the versioned Terraform state
bucket and DynamoDB lock table only if the environment will be recreated; if
they are no longer needed, remove all object versions and delete both backend
resources according to the organization's retention policy. Never delete
shared resources that are not owned by this project.

If the private EKS endpoint is used, retain a private runner or bastion only
for the deployment window and remove it immediately afterward. Do not leave a
bastion, NAT gateway, or load balancer running just to keep the environment
available.

## GitHub branch protection

Protect `main` after the workflow has a successful run:

1. Open repository **Settings → Branches**.
2. Add a rule or ruleset for `main`.
3. Require pull requests before merging.
4. Require at least one approval.
5. Dismiss stale approvals after new commits.
6. Require branches to be up to date.
7. Require the `validate` status check.
8. Block force pushes and branch deletion.

Only require `build` or `deploy` for pull requests after changing the workflow
to run those jobs on pull requests. In the current workflow those jobs are
`main`-push deployment jobs.

## Important security notes

- Never commit `.env`, cloud credentials, Terraform state, kubeconfig files, or
  production secrets.
- Replace all placeholder IAM account IDs and role ARNs.
- Do not use local MinIO credentials in production.
- Keep the EKS endpoint private unless a reviewed security decision requires
  public access.
- Restrict GitHub OIDC trust to this repository and the intended branch or
  environment.
- Review Terraform plans for destructive changes before applying.
- Treat the Kubernetes NetworkPolicies as one layer; enforce database and AWS
  security-group boundaries separately.
- Pin production image references to commit SHAs, not `latest`.

## Current status summary

| Area | Status |
|---|---|
| FastAPI ingestion/search/statistics API | Implemented |
| API-key authentication | Implemented |
| Atomic Redis rate limiting | Implemented |
| WebSocket statistics streaming | Implemented |
| Celery/RabbitMQ asynchronous processing | Implemented |
| OpenTelemetry integration | Implemented |
| React/Vite dashboard | Implemented |
| Local Docker Compose stack | Implemented and verified |
| Stream simulator and focused tests | Implemented |
| Kubernetes manifests | Implemented |
| Terraform baseline | Implemented, not applied |
| GitHub Actions workflow | Implemented, requires account configuration |
| GitHub repository publication | Complete |
| AWS infrastructure deployment | Not active; intentionally deferred for cost control |
| EKS production rollout | Pending verification |
| Branch protection | Pending configuration |

## License

Add the project license and copyright policy before distributing this repository
outside your organization.
