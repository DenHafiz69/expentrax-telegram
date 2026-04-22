# Managing the ExpenTrax Telegram Bot

This document outlines the architecture, management, and deployment process for the ExpenTrax Telegram Bot running on Google Cloud Functions.

## 1. Serverless Architecture Overview

The bot operates using two separate, serverless Google Cloud Functions for efficiency and scalability:

1.  **Webhook Function (`expentrax-telegram-webhook`)**:
    *   **Source Code**: `main.py` (entry point: `webhook`)
    *   **Trigger**: HTTP Request
    *   **Purpose**: This function receives real-time updates from Telegram whenever a user interacts with the bot. It processes commands, messages, and callbacks. This replaces the old polling method.

2.  **Scheduler Function (`expentrax-telegram-scheduler`)**:
    *   **Source Code**: `recurring_check.py` (entry point: `check_transactions_cron`)
    *   **Trigger**: Google Cloud Scheduler (cron job)
    *   **Purpose**: This function runs on a schedule (daily at midnight) to check for and create recurring transactions. This replaces the old background thread scheduler.

## 2. How to Manage the Bot

### Viewing Logs

Logs are essential for debugging and monitoring your bot's activity.

1.  Go to the **Google Cloud Console**.
2.  Navigate to **Logging > Logs Explorer**.
3.  In the query builder, filter by your Cloud Functions:
    *   For the webhook: `resource.type="cloud_function" resource.labels.function_name="expentrax-telegram-webhook"`
    *   For the scheduler: `resource.type="cloud_function" resource.labels.function_name="expentrax-telegram-scheduler"`
4.  You can view `print` statements, `logger` outputs, and any errors or exceptions.

### Checking Function Status

1.  Go to the **Google Cloud Console**.
2.  Navigate to **Cloud Functions**.
3.  You will see a list of your functions (`expentrax-telegram-webhook` and `expentrax-telegram-scheduler`).
4.  Here you can check their status, region, trigger URL, and other configuration details.

### Managing the Scheduler

1.  Go to the **Google Cloud Console**.
2.  Navigate to **Cloud Scheduler**.
3.  You will see your job (`expentrax-daily-check`).
4.  From here, you can manually trigger a run ("Force run"), pause the job, or edit its schedule.

### Environment Variables & Secrets

*   **Local Development**: The `BOT_TOKEN` is loaded from a `.env` file. **Never commit this file to Git.**
*   **Production (Google Cloud)**: Secrets should be set as environment variables during deployment. The `gcloud` commands I provided can be modified to include them:

    ```bash
    gcloud functions deploy expentrax-telegram-webhook \
      ... # other flags
      --set-env-vars BOT_TOKEN="your_actual_token_here"
    ```
    For better security, use **Google Secret Manager** to store your bot token and grant your Cloud Function access to it.

## 3. CI/CD Process with GitHub Actions

Automating your deployment process (CI/CD) is crucial for releasing new features safely and quickly. Here’s a sample workflow using GitHub Actions.

### Step 1: Create a Service Account

First, you need a Google Cloud Service Account so GitHub Actions can securely authenticate with your GCP project.

1.  In the Google Cloud Console, go to **IAM & Admin > Service Accounts**.
2.  Click **Create Service Account**.
3.  Give it a name (e.g., `github-actions-deployer`).
4.  Grant it the following roles:
    *   `Cloud Functions Admin`
    *   `Service Account User`
    *   `Cloud Build Editor` (required for deployments)
5.  Create the account, and then create a **JSON key** for it. Download and save this key file.

### Step 2: Configure GitHub Secrets

In your GitHub repository, go to **Settings > Secrets and variables > Actions** and add the following secrets:

*   `GCP_PROJECT_ID`: Your Google Cloud project ID (`expentrax-telegram`).
*   `GCP_SA_KEY`: The entire content of the JSON key file you downloaded.
*   `BOT_TOKEN`: Your Telegram bot token.

### Step 3: Create the GitHub Actions Workflow File

Create a new file in your repository at `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Google Cloud Functions

on:
  push:
    branches:
      - main  # Trigger deployment on push to the main branch

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: 'google-github-actions/auth@v2'
        with:
          credentials_json: '${{ secrets.GCP_SA_KEY }}'

      - name: Set up Cloud SDK
        uses: 'google-github-actions/setup-gcloud@v2'

      - name: Deploy Webhook Function
        run: |
          gcloud functions deploy expentrax-telegram-webhook \
            --gen2 \
            --runtime=python313 \
            --region=asia-southeast1 \
            --source=. \
            --entry-point=webhook \
            --trigger-http \
            --allow-unauthenticated \
            --project=${{ secrets.GCP_PROJECT_ID }} \
            --set-env-vars=BOT_TOKEN=${{ secrets.BOT_TOKEN }}

      - name: Deploy Scheduler Function
        run: |
          gcloud functions deploy expentrax-telegram-scheduler \
            --gen2 \
            --runtime=python313 \
            --region=asia-southeast1 \
            --source=. \
            --entry-point=check_transactions_cron \
            --trigger-http \
            --allow-unauthenticated \
            --project=${{ secrets.GCP_PROJECT_ID }}
```

### How This CI/CD Workflow Works

1.  **Trigger**: Whenever you push a new commit to your `main` branch, this workflow will automatically start.
2.  **Authentication**: It securely logs into your Google Cloud project using the service account key you stored in GitHub Secrets.
3.  **Deployment**: It runs the `gcloud functions deploy` commands for both your webhook and scheduler functions, updating them with the latest code from your repository. It also securely injects the `BOT_TOKEN` as an environment variable.

This setup ensures that your production bot is always in sync with your `main` branch, providing a seamless process for releasing updates.
