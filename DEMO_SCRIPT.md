<![CDATA[# DevDex Video Demo Script

**Target length:** 3–4 minutes
**Format:** Screen recording with voiceover (terminal + browser)

---

## Pre-Recording Setup

1. Have a sample project ready (e.g., a simple web app or iOS app with a few dependencies)
2. API key set in environment (`NVIDIA_API_KEY` or `MISTRAL_API_KEY`)
3. Terminal at ~120 columns, dark theme, large font (16–18pt)
4. Browser ready for landing page preview
5. Clear any previous `devdex-output/` directory

---

## Script

### 0:00–0:15 — Intro

**Show:** Terminal with DevDex Pokeball logo (run `devdex --version` or just show the logo)

**Say:**
> "DevDex is a CLI tool that scans your codebase and generates everything you need to ship — privacy policy, terms of service, App Store description, a full landing page, and a deployment checklist. All in one command."

---

### 0:15–0:30 — Install

**Show:** Terminal

```bash
uv pip install -e .
export NVIDIA_API_KEY=nvapi-...
```

**Say:**
> "Install with uv, set your API key — NVIDIA NIM is free and the default provider — and you're ready to go."

---

### 0:30–1:00 — Scan

**Run:**
```bash
devdex scan ./my-app
```

**Show:** The Pokeball logo appearing, then the codebase scan output

**Say:**
> "DevDex starts by scanning your project. It auto-detects your frameworks, SDKs, data collection patterns, authentication methods, and even your color theme from CSS or SwiftUI."

---

### 1:00–1:30 — Interview

**Show:** The interactive questionnaire with step bar

**Say:**
> "Next is a short interview to fill in what the scanner can't detect — your app name, company, target audience. Notice the step bar at the top and how questions auto-fill from the scan results. Web projects automatically skip irrelevant steps like App Store and age rating."

**Action:** Answer 3–4 questions, show the auto-fill working, then confirm at the summary screen.

---

### 1:30–2:00 — Generation

**Show:** Live progress spinners for each artifact being generated in parallel

**Say:**
> "Now DevDex generates all your artifacts in parallel. Each one uses a specialized prompt with the context from your scan and interview. Every LLM call is automatically traced by W&B Weave — input, output, latency, token counts — with zero extra code."

---

### 2:00–2:30 — Artifacts

**Show:** Open the generated files in quick succession

```bash
ls devdex-output/
cat devdex-output/privacy_policy.md | head -30
cat devdex-output/terms_of_service.md | head -20
cat devdex-output/deployment_checklist.md | head -20
```

**Say:**
> "Here's what we got — a full privacy policy with GDPR and CCPA sections based on the actual SDKs detected in your code. Terms of service tailored to your platform. And a deployment checklist with every step you need."

---

### 2:30–2:45 — Landing Page

**Show:** Open `devdex-output/landing_page.html` in browser

**Say:**
> "The landing page is a fully responsive HTML page using your app's actual color theme. It includes all the sections you need — hero, features, pricing, footer — plus a matching support page."

---

### 2:45–3:00 — Deployment Guide

**Show:** The interactive checklist UI in terminal

**Say:**
> "The deployment guide turns your checklist into an interactive walkthrough. Check off items as you go, save progress, and resume later. Each step includes context, gotchas, and code snippets."

**Action:** Check off 2–3 items to show the interaction.

---

### 3:00–3:15 — Feedback & Self-Improvement

**Show:** The feedback rating flow

**Say:**
> "After generation, you rate each artifact. These ratings feed back into the system — stored in Supabase with semantic embeddings. Next time you run DevDex, it loads your past feedback and improves the prompts automatically."

**Action:** Rate one artifact to show the flow.

---

### 3:15–3:30 — Fine-Tuning

**Show:** Terminal or W&B dashboard screenshot

```bash
devdex finetune --unsloth --dev
```

**Say:**
> "And to close the loop — export your highest-rated artifacts as training data and fine-tune with Unsloth, MLX, or TRL. The fine-tuned model gets registered in W&B and used for future generations. A complete self-improving pipeline."

---

### 3:30–3:45 — Close

**Show:** Terminal with DevDex logo

**Say:**
> "DevDex — scan your codebase, generate your launch kit, and keep getting better. Built with Mistral AI for the Mistral Worldwide Hackathon. Try it out — link in the description."

---

## Key Points to Emphasize

1. **One command** — `devdex scan .` does everything
2. **Auto-detection** — frameworks, SDKs, colors, auth methods
3. **Platform-aware** — web vs mobile, auto-skips irrelevant steps
4. **Real artifacts** — not templates, generated from actual project context
5. **Self-improving** — feedback loop + fine-tuning closes the loop
6. **Full observability** — W&B Weave traces every LLM call automatically
7. **Multi-provider** — NVIDIA NIM (free), Mistral, OpenAI, or custom

## Recording Tips

- Use a clean terminal with no sensitive info visible
- Increase font size for readability
- Pause briefly on key screens (logo, generated artifacts, landing page)
- Keep mouse movements minimal and deliberate
- Record audio separately if possible for cleaner results
]]>