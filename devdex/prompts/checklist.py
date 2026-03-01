from __future__ import annotations

from devdex.models import ProjectUnderstanding

SYSTEM_PROMPT = """You are a mobile app deployment expert.
Generate a comprehensive deployment checklist in Markdown format with:
- Grouped sections (Pre-submission, App Store Connect, Legal, Technical, Post-launch)
- Each item as a checkbox: - [ ] Item description
- Difficulty rating per section (Easy / Medium / Hard)
- Platform-specific steps based on the detected platform
- Tips or gotchas as blockquotes where relevant

When a checklist item can be completed using a generated artifact, reference the exact file path and section name so the user can copy-paste directly.
For example: "Copy your short description from appstore/description.md (Short Description section) into App Store Connect > App Information > Subtitle"

Output ONLY the checklist in Markdown format.
Do NOT include any preamble — start directly with the checklist.
Do NOT wrap the output in markdown code fences (``` or ```markdown)."""


def build_prompt(
    pu: ProjectUnderstanding,
    generated_artifacts: list[dict] | None = None,
) -> str:
    sdk_names = ", ".join(pu.sdk_names) if pu.sdk_names else "None detected"

    prompt = f"""Generate a deployment checklist for:

App name: {pu.display_name}
Platform: {pu.platform.value}
Deployment target: {pu.deployment_target.value}
Monetization: {pu.monetization.value}
Age rating: {pu.age_rating.value}
Has in-app purchases: {pu.has_in_app_purchases}
SDKs used: {sdk_names}
Languages: {', '.join(pu.languages) or 'Not detected'}
Bundle ID: {pu.bundle_id or 'Not set'}
Minimum OS version: {pu.min_ios_version or 'Not set'}

Data types collected: {', '.join(pu.all_data_types) or 'None detected'}
Auth methods: {', '.join(a.method for a in pu.auth_methods) or 'None detected'}

Include platform-specific steps for {pu.deployment_target.value} deployment.
If in-app purchases are present, include StoreKit/payment testing steps.
"""

    if generated_artifacts:
        lines = [
            "",
            "The following artifacts have already been generated and are available in the output directory:",
        ]
        for art in generated_artifacts:
            desc = art.get("description", "")
            suffix = f" — {desc}" if desc else ""
            lines.append(f"- {art['file_path']}{suffix}")
        lines.append("")
        lines.append(
            "For checklist items that relate to these artifacts, reference the specific file and section. "
            'Example: "Copy your short description from appstore/description.md (Short Description section) '
            'into App Store Connect > App Information > Subtitle"'
        )
        prompt += "\n".join(lines) + "\n"

    return prompt
