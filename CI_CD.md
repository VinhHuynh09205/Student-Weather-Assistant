# CI/CD with GitHub Actions

This project uses `.github/workflows/ci-cd.yml`.

## What CI does

CI runs on every push and pull request to `main`:

- Backend: install Python dependencies, run `ruff check`, run Alembic migrations, then run `pytest`.
- Frontend: install Node dependencies, run `npm run lint`, then run `npm run build`.
- Docker: build backend and frontend Docker images to verify the Dockerfiles.

## What CD does

CD can deploy to AWS after CI passes:

- Backend image is built and pushed to Amazon ECR.
- ECS task definition is updated with the new image.
- Optional one-off ECS migration task runs if subnet and security group variables are configured.
- ECS service is updated and waited until stable.
- Frontend is built and synced to S3.
- Optional CloudFront invalidation runs if a distribution ID is configured.

CD is disabled by default. This prevents the workflow from failing before AWS is configured.

## Enable AWS deployment

In GitHub, open:

`Settings` -> `Secrets and variables` -> `Actions`

Add this repository secret:

| Secret | Required | Description |
| --- | --- | --- |
| `AWS_ROLE_TO_ASSUME` | Yes | IAM role ARN for GitHub Actions OIDC deployment. |

Add these repository variables:

| Variable | Required | Example |
| --- | --- | --- |
| `AWS_DEPLOY_ENABLED` | Yes | `true` |
| `AWS_REGION` | Yes | `ap-southeast-1` |
| `ECR_REPOSITORY` | Yes | `student-weather-backend` |
| `ECS_CLUSTER` | Yes | `student-weather-cluster` |
| `ECS_SERVICE` | Yes | `student-weather-backend-service` |
| `ECS_TASK_DEFINITION` | Yes | `student-weather-backend-td` |
| `ECS_CONTAINER_NAME` | Yes | `backend` |
| `S3_BUCKET` | Yes | `student-weather-frontend-prod` |
| `VITE_API_BASE_URL` | Yes | `https://api.yourdomain.com` |
| `VITE_GOOGLE_CLIENT_ID` | Optional | Google OAuth client ID |
| `CLOUDFRONT_DISTRIBUTION_ID` | Optional | `E1234567890ABC` |

Optional variables for running migrations through a one-off ECS Fargate task:

| Variable | Required for migrations | Example |
| --- | --- | --- |
| `ECS_SUBNETS` | Yes | `subnet-aaa,subnet-bbb` |
| `ECS_SECURITY_GROUPS` | Yes | `sg-aaa` |
| `ECS_ASSIGN_PUBLIC_IP` | No | `DISABLED` or `ENABLED` |

If `ECS_SUBNETS` and `ECS_SECURITY_GROUPS` are not set, the deploy workflow skips the migration task and only updates the ECS service.

## Deployment triggers

After `AWS_DEPLOY_ENABLED=true` is configured:

- Push to `main`: CI runs first, then deploy runs automatically.
- Manual run: open the workflow in GitHub Actions, choose `Run workflow`, and set `deploy=true`.

## Important notes

- Do not store `.env` values in the repository.
- Store production secrets in AWS Secrets Manager, AWS Systems Manager Parameter Store, or ECS task definition secrets.
- The GitHub workflow assumes the ECS task definition already exists and has a container name matching `ECS_CONTAINER_NAME`.
