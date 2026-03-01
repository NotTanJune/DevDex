# DevDex

**Scan your codebase. Generate your launch kit. Gotta ship 'em all.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://python.org)
[![Mistral AI](https://img.shields.io/badge/Mistral-AI-orange.svg)](https://mistral.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

DevDex is a CLI tool that scans a project codebase, runs a short interactive interview, and generates a complete deployment-ready launch kit — privacy policy, terms of service, App Store description, landing page, and deployment checklist — in one shot.

## Features

- **Codebase scanning** — Auto-detects frameworks, SDKs, data collection patterns, auth methods, and color themes
- **Smart interview** — Platform-aware questionnaire that auto-fills answers from scan results
- **6 artifact types** — Privacy policy, terms of service, App Store description, landing page (HTML), deployment checklist, support page
- **Multi-provider** — Works with NVIDIA NIM (free), Mistral AI, OpenAI, or any OpenAI-compatible API
- **Self-improvement** — Rates artifacts, stores feedback, and injects improvement context into future generations
- **Fine-tuning** — Export training data and fine-tune with Unsloth, MLX, TRL/PEFT, or Mistral API
- **Full observability** — W&B Weave auto-traces every LLM call; wandb logs feedback metrics
- **Interactive deployment guide** — Step-by-step checklist walkthrough with progress saving

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- An API key (NVIDIA NIM is free and the default)

### Install

```bash
git clone https://github.com/your-username/devdex.git
cd devdex
uv pip install -e .
```

### Set your API key

```bash
# Option 1: NVIDIA NIM (free, default)
export NVIDIA_API_KEY=nvapi-...

# Option 2: Mistral AI
export MISTRAL_API_KEY=...

# Option 3: OpenAI
export OPENAI_API_KEY=sk-...
```

### Run

```bash
devdex scan ./my-project
```

## Commands

### `devdex scan <path>`

Scan a project and generate a complete deployment kit.

| Flag | Description |
|------|-------------|
| `--skip-interview` | Skip the interactive interview |
| `--no-branch` | Don't create a git branch with generated files |
| `--output`, `-o` | Custom output directory |
| `--branch`, `-b` | Custom branch name for generated files |
| `--json` | Output machine-readable JSON to stdout |
| `--no-telemetry` | Disable anonymous telemetry for this run |

### `devdex config set <key> <value>`

Set a configuration value (stored in `~/.devdex/config.json`).

### `devdex config show`

Show current configuration.

### `devdex review <path>`

Open generated artifacts for review in your default editor.

### `devdex feedback <path>`

Rate generated artifacts and log feedback.

## Providers

| Provider | Env Var | Default | Cost |
|----------|---------|---------|------|
| **NVIDIA NIM** | `NVIDIA_API_KEY` | Yes | Free |
| **Mistral AI** | `MISTRAL_API_KEY` | — | Paid |
| **OpenAI** | `OPENAI_API_KEY` | — | Paid |
| **Custom** | `DEVDEX_API_KEY` + `DEVDEX_BASE_URL` | — | Varies |

Switch providers:

```bash
export DEVDEX_PROVIDER=mistral   # or nvidia, openai, custom
```

## Generated Artifacts

| Artifact | Format | Description |
|----------|--------|-------------|
| Privacy Policy | Markdown | GDPR/CCPA-compliant privacy policy based on detected data collection |
| Terms of Service | Markdown | Legal terms tailored to your app's features and platform |
| App Store Description | Markdown | Optimized App Store listing (skipped for web projects) |
| Landing Page | HTML | Responsive landing page with your app's branding and colors |
| Support Page | HTML | Contact and FAQ page matching landing page style |
| Deployment Checklist | Markdown | Platform-specific deployment steps with interactive walkthrough |

All artifacts are saved to `<project>/devdex-output/` by default.

## Self-Improvement Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  devdex     │────▶│   W&B       │────▶│  Feedback    │
│  scan       │     │   Weave     │     │  Collection  │
│             │     │  (tracing)  │     │  (ratings)   │
└─────────────┘     └─────────────┘     └──────┬───────┘
       ▲                                        │
       │                                        ▼
┌──────┴───────┐                        ┌──────────────┐
│  Improvement │◀───────────────────────│  Supabase    │
│  Context     │                        │  + Embeddings│
│  (injected)  │                        │  (storage)   │
└──────────────┘                        └──────┬───────┘
                                               │
                                               ▼
                                       ┌──────────────┐
                                       │  Fine-Tuning │
                                       │  (Unsloth/   │
                                       │   MLX/TRL)   │
                                       └──────────────┘
```

1. **Generate** — `devdex scan` produces artifacts while W&B Weave auto-traces every LLM call
2. **Rate** — User rates each artifact (1-5) with optional edit descriptions
3. **Store** — Feedback is stored in Supabase with Mistral embeddings for semantic search
4. **Improve** — Next generation loads past feedback and injects improvement context into prompts
5. **Fine-tune** — High-rated artifacts become training data for model fine-tuning


## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NVIDIA_API_KEY` | NVIDIA NIM API key | — |
| `MISTRAL_API_KEY` | Mistral AI API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `DEVDEX_API_KEY` | Generic API key (any provider) | — |
| `DEVDEX_BASE_URL` | Custom API base URL | NVIDIA NIM |
| `DEVDEX_PROVIDER` | Provider name (`nvidia`, `mistral`, `openai`, `custom`) | `nvidia` |
| `DEVDEX_SUPABASE_URL` | Supabase project URL | — |
| `DEVDEX_SUPABASE_KEY` | Supabase service role key | — |
| `WANDB_API_KEY` | Weights & Biases API key | — |
| `DEVDEX_TELEMETRY` | Set to `false` to disable telemetry | `true` |
| `DEVDEX_TELEMETRY_URL` | Override telemetry endpoint | Central Supabase |

## Telemetry

DevDex collects anonymous telemetry to improve generation quality. Data sent:

- Artifact ratings and edit descriptions (no project paths or identifying info)
- Session hash (SHA-256 of hostname) for deduplication

Opt out:

```bash
export DEVDEX_TELEMETRY=false
# or per-run:
devdex scan . --no-telemetry
```

## Project Structure

```
devdex/
├── __init__.py
├── __main__.py
├── cli.py                          # Main CLI (scan, config, review, feedback, finetune)
├── config.py                       # Configuration + provider management
├── models.py                       # Pydantic models for pipeline state
├── prompts/
│   ├── privacy_policy.py           # Privacy policy prompt template
│   ├── terms_of_service.py         # ToS prompt template
│   ├── appstore.py                 # App Store prompt template
│   ├── checklist.py                # Deployment checklist prompt template
│   └── landing_page.py             # Landing page prompt template
├── functions/
│   ├── codebase_scanner.py         # Project scanning + SDK detection
│   ├── project_interviewer.py      # Interactive interview
│   ├── privacy_policy_gen.py       # Privacy policy generator
│   ├── tos_gen.py                  # Terms of service generator
│   ├── appstore_gen.py             # App Store description generator
│   ├── checklist_gen.py            # Deployment checklist generator
│   ├── landing_page_gen.py         # Landing page prompt generator
│   ├── landing_page_html_gen.py    # HTML landing page generator
│   ├── deployment_guide.py         # Interactive deployment walkthrough
│   ├── feedback_loop.py            # Feedback collection + improvement loop
│   ├── vector_store.py             # Supabase vector store client
│   ├── finetune_pipeline.py        # Fine-tuning pipeline (export + train)
│   ├── ios_scanner.py              # iOS-specific scanning helpers
│   ├── sdk_database.py             # SDK detection patterns
│   └── register.py                 # Function registration
templates/                          # HTML templates for landing pages
branding/                           # ASCII art logo variants
```

## License

[MIT](LICENSE)
