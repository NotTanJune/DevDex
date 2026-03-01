from __future__ import annotations

import hashlib
import json
import logging
import platform
from collections import defaultdict
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console(stderr=True)

FEEDBACK_HISTORY_PATH = Path.home() / ".devdex" / "feedback_history.json"


def load_past_feedback(wandb_api_key: str = "") -> list[dict]:
    feedback: list[dict] = []

    if wandb_api_key:
        try:
            import wandb

            api = wandb.Api(api_key=wandb_api_key, timeout=5)
            runs = api.runs("devdex-feedback")
            for run in runs:
                for row in run.history(pandas=False):
                    row_dict = dict(row)
                    if "artifact_type" in row_dict and "user_rating" in row_dict:
                        feedback.append(row_dict)
        except Exception as e:
            logger.debug("W&B feedback load failed: %s", e)

    if FEEDBACK_HISTORY_PATH.exists():
        try:
            local = json.loads(FEEDBACK_HISTORY_PATH.read_text())
            if isinstance(local, list):
                feedback.extend(local)
        except Exception as e:
            logger.debug("Local feedback load failed: %s", e)

    return feedback


def build_improvement_context(feedback: list[dict]) -> str:
    if not feedback:
        return ""

    by_type: dict[str, list[dict]] = defaultdict(list)
    for entry in feedback:
        atype = entry.get("artifact_type", "unknown")
        by_type[atype].append(entry)

    lines: list[str] = []
    for atype, entries in sorted(by_type.items()):
        ratings = [e.get("user_rating", 0) for e in entries if e.get("user_rating")]
        if not ratings:
            continue
        avg = sum(ratings) / len(ratings)

        edits = [
            e["edit_description"]
            for e in entries
            if e.get("had_edits") and e.get("edit_description")
        ]

        parts = [f"- {atype}: avg rating {avg:.1f}/5 ({len(ratings)} reviews)."]
        if edits:
            recent = edits[-3:]
            parts.append(f"  Common edits: {'; '.join(recent)}.")

        lines.append(" ".join(parts))

    if not lines:
        return ""

    return (
        "Based on past user feedback, please improve the generated output. "
        "Here is the summary:\n" + "\n".join(lines)
    )


def save_feedback_to_history(ratings: list[dict]) -> None:
    existing: list[dict] = []
    if FEEDBACK_HISTORY_PATH.exists():
        try:
            existing = json.loads(FEEDBACK_HISTORY_PATH.read_text())
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    existing.extend(ratings)

    FEEDBACK_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEEDBACK_HISTORY_PATH.write_text(json.dumps(existing, indent=2))


def display_feedback_summary(feedback: list[dict], theme: dict) -> None:
    if not feedback:
        return

    by_type: dict[str, list[dict]] = defaultdict(list)
    for entry in feedback:
        atype = entry.get("artifact_type", "unknown")
        by_type[atype].append(entry)

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
    table.add_column("Artifact")
    table.add_column("Reviews", justify="right")
    table.add_column("Avg Rating", justify="right")
    table.add_column("Edits", justify="right")

    total_reviews = 0
    for atype, entries in sorted(by_type.items()):
        ratings = [e.get("user_rating", 0) for e in entries if e.get("user_rating")]
        if not ratings:
            continue
        avg = sum(ratings) / len(ratings)
        edit_count = sum(1 for e in entries if e.get("had_edits"))
        total_reviews += len(ratings)

        if avg >= 4.0:
            rating_style = "green"
        elif avg >= 3.0:
            rating_style = "yellow"
        else:
            rating_style = "red"

        name = atype.replace("_", " ").title()
        table.add_row(
            name,
            str(len(ratings)),
            f"[{rating_style}]{avg:.1f}/5[/]",
            str(edit_count),
        )

    if total_reviews == 0:
        return

    console.print(Panel(
        table,
        title=f"[{theme['accent']}]Using feedback from {total_reviews} past reviews[/]",
        border_style=theme["border"],
        padding=(1, 2),
    ))


_ARTIFACT_KEYWORDS: dict[str, list[str]] = {
    "privacy_policy": [
        "privacy", "policy", "data collection", "gdpr", "ccpa", "data usage",
        "personal data", "tracking", "cookies",
    ],
    "terms_of_service": [
        "terms", "tos", "service", "legal", "liability", "disclaimer",
        "agreement", "conditions",
    ],
    "landing_page": [
        "landing", "page", "website", "site", "html", "css", "hero",
        "design", "layout", "homepage", "web",
    ],
    "deployment_checklist": [
        "checklist", "deployment", "deploy", "release", "submit",
        "app store", "testflight", "provisioning", "certificate",
    ],
    "appstore_description": [
        "app store", "appstore", "description", "listing", "metadata",
        "keywords", "screenshots", "subtitle",
    ],
}


def store_feedback_to_vector_store(
    ratings: list[dict],
    supabase_url: str = "",
    supabase_key: str = "",
    mistral_api_key: str = "",
    project_path: str = "",
    run_id: str = "",
) -> None:
    if not supabase_url or not supabase_key:
        return

    try:
        from devdex.functions.vector_store import VectorStore

        vs = VectorStore(supabase_url, supabase_key, mistral_api_key)
        for entry in ratings:
            entry_with_path = {**entry, "project_path": project_path, "run_id": run_id}
            vs.store_feedback(entry_with_path)
    except Exception as e:
        logger.debug("Vector store feedback failed: %s", e)


def build_improvement_context_with_search(
    query: str,
    artifact_type: str = "",
    supabase_url: str = "",
    supabase_key: str = "",
    mistral_api_key: str = "",
    fallback_feedback: list[dict] | None = None,
) -> str:
    if supabase_url and supabase_key and mistral_api_key:
        try:
            from devdex.functions.vector_store import VectorStore

            vs = VectorStore(supabase_url, supabase_key, mistral_api_key)
            results = vs.search_similar_feedback(query, artifact_type, limit=5)
            if results:
                lines = []
                for r in results:
                    lines.append(
                        f"- {r.get('artifact_type', 'unknown')}: "
                        f"\"{r.get('edit_text', '')}\""
                    )
                return (
                    "Based on semantically similar past feedback, "
                    "please address these common issues:\n" + "\n".join(lines)
                )
        except Exception as e:
            logger.debug("Semantic search fallback: %s", e)

    if fallback_feedback:
        return build_improvement_context(fallback_feedback)
    return ""


def _get_session_id() -> str:
    raw = platform.node() + ":" + platform.system()
    return hashlib.sha256(raw.encode()).hexdigest()


def send_central_telemetry(
    ratings: list[dict],
    telemetry_url: str,
    devdex_version: str,
    run_id: str = "",
) -> bool:
    if not telemetry_url or not ratings:
        return False

    ALLOWED_FIELDS = {"artifact_type", "user_rating", "had_edits", "edit_description"}
    sanitized = [
        {k: v for k, v in r.items() if k in ALLOWED_FIELDS}
        for r in ratings
    ]

    payload = {
        "session_id": _get_session_id(),
        "run_id": run_id,
        "devdex_version": devdex_version,
        "ratings": sanitized,
    }

    try:
        import httpx

        resp = httpx.post(telemetry_url, json=payload, timeout=10.0)
        return resp.status_code == 200
    except Exception:
        return False


def send_central_artifacts(
    artifacts: list[dict],
    telemetry_url: str,
    devdex_version: str,
    run_id: str = "",
) -> bool:
    if not telemetry_url or not artifacts:
        return False

    artifact_url = telemetry_url.replace("feedback-ingest", "artifact-ingest")

    ALLOWED_FIELDS = {"artifact_type", "system_prompt", "user_prompt", "generated_content", "model_used"}
    sanitized = [
        {k: v for k, v in a.items() if k in ALLOWED_FIELDS}
        for a in artifacts
    ]

    payload = {
        "session_id": _get_session_id(),
        "run_id": run_id,
        "devdex_version": devdex_version,
        "artifacts": sanitized,
    }

    try:
        import httpx

        resp = httpx.post(artifact_url, json=payload, timeout=10.0)
        return resp.status_code == 200
    except Exception:
        return False


def classify_feedback_to_artifacts(
    text: str, rated_artifacts: list[str]
) -> list[str]:
    text_lower = text.lower()
    matched: list[str] = []

    for artifact_type, keywords in _ARTIFACT_KEYWORDS.items():
        if artifact_type not in rated_artifacts:
            continue
        for kw in keywords:
            if kw in text_lower:
                matched.append(artifact_type)
                break

    if not matched:
        matched = list(rated_artifacts)

    return matched
