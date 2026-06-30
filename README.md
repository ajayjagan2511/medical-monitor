# 🏥 Medical Image Dataset Monitor

An automated Python agent that scans **Kaggle**, **Hugging Face**, **Zenodo**, and **PubMed** daily for newly published medical image datasets and sends consolidated alerts to Slack.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Multi-platform scanning** — queries 4 major data repositories in a single run
- **17 medical imaging keywords** — covers MRI, CT, X-ray, histopathology, DICOM, mammography, and more
- **Deduplication** — SQLite-backed memory prevents repeat alerts across runs
- **Batched Slack alerts** — one clean message per run, grouped by platform
- **Resilient** — if one platform is down, the others still run
- **Zero-maintenance deployment** — GitHub Actions cron with auto-commit of state

## Architecture

```
main.py                     ← Orchestrator
├── config.py               ← Keywords, env vars, constants
├── database.py             ← SQLite state manager (seen_datasets + run_log)
├── alerting.py             ← Slack Block Kit notifications
└── scrapers/
    ├── base.py             ← BaseScraper ABC + DatasetResult dataclass
    ├── kaggle_scraper.py   ← Official Kaggle API
    ├── huggingface_scraper.py ← HF REST API
    ├── zenodo_scraper.py   ← Zenodo REST API
    └── pubmed_scraper.py   ← NCBI E-Utilities
```

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/medical-monitor.git
cd medical-monitor
pip install -r requirements.txt
```

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your actual keys (see Setup Guide below)
```

### 3. Run locally

```bash
python main.py
```

On the first run, it scans the last **60 days**. Subsequent runs only look for datasets newer than the previous run.

---

## Setup Guide

### Kaggle API Token

1. Go to [kaggle.com/settings](https://www.kaggle.com/settings)
2. Scroll to the **API** section
3. Click **"Generate New Token"** under the token settings (or generate an API token).
4. Copy the API token and add it to your `.env`:

```
KAGGLE_API_TOKEN=your_kaggle_api_token
```

### Slack Webhook

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app (or use an existing one)
2. Under **Features → Incoming Webhooks**, toggle it **On**
3. Click **"Add New Webhook to Workspace"** and select your target channel
4. Copy the webhook URL into your `.env`:

```
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00.../B00.../xxxx
```

### GitHub Actions Deployment

1. Push this repo to GitHub
2. Go to **Settings → Secrets and variables → Actions**
3. Add these **Repository Secrets**:

| Secret Name | Value |
|---|---|
| `KAGGLE_API_TOKEN` | Your Kaggle API token |
| `SLACK_WEBHOOK_URL` | Your Slack webhook URL |

4. Configure Workflow Permissions (Crucial for database persistence):
   - Go to **Settings → Actions → General**.
   - Under **Workflow permissions**, check **Read and write permissions**.
   - Click **Save**.

5. The workflow runs automatically at **06:00 UTC daily** and can also be triggered manually from the **Actions** tab.

> **Important:** The workflow commits the updated `datasets_state.db` back to the repo after each run. This requires the "Read and write permissions" enabled above so the agent doesn't suffer from memory loss across runs.

---

## How It Works

```
┌─────────────┐
│  GitHub     │  Cron: 0 6 * * * (daily at 06:00 UTC)
│  Actions    │──────────────────────────────────────┐
└─────────────┘                                       │
                                                      ▼
                                              ┌───────────────┐
                                              │   main.py     │
                                              └───────┬───────┘
                                                      │
                        ┌──────────┬──────────┬───────┴────────┐
                        ▼          ▼          ▼                ▼
                    Kaggle    Hugging Face  Zenodo          PubMed
                        │          │          │                │
                        └──────────┴──────────┴────────────────┘
                                              │
                                              ▼
                                     ┌─────────────────┐
                                     │  SQLite Dedup   │
                                     │  (seen_datasets)│
                                     └────────┬────────┘
                                              │ new only
                                              ▼
                                     ┌─────────────────┐
                                     │  Slack Alert    │
                                     │  (batched)      │
                                     └─────────────────┘
```

## License

MIT
