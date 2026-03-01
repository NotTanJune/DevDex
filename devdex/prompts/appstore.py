from __future__ import annotations

from devdex.models import ProjectUnderstanding

SYSTEM_PROMPT = """You are an ASO (App Store Optimization) expert who writes compelling App Store descriptions.
Generate a complete App Store listing with these exact sections, separated by the headers shown:

## Short Description
(Max 30 words, compelling one-liner)

## Long Description
(Detailed description with features, benefits, and social proof style. 150-300 words.)

## Keywords
(Comma-separated keywords for ASO, max 100 characters total)

## Category
(Primary App Store category recommendation)

## What's New
(Release notes for v1.0 launch)

Output in Markdown format with the exact section headers above.
Do NOT include any preamble — output ONLY the App Store listing.
Do NOT wrap the output in markdown code fences (``` or ```markdown)."""


def build_prompt(pu: ProjectUnderstanding) -> str:
    features = []
    if pu.auth_methods:
        methods = [a.method.replace("_", " ").title() for a in pu.auth_methods]
        features.append(f"Authentication: {', '.join(methods)}")
    if pu.has_in_app_purchases:
        features.append("In-app purchases available")
    if pu.sdks:
        categories = list({s.category for s in pu.sdks if s.category})
        if categories:
            features.append(f"Integrations: {', '.join(categories)}")

    feature_section = ""
    if features:
        feature_section = "Key features detected:\n" + "\n".join(f"- {f}" for f in features)

    return f"""Generate an App Store listing for:

App name: {pu.display_name}
Platform: {pu.platform.value}
Purpose: {pu.app_purpose or 'Not specified'}
Target audience: {pu.target_audience or 'General consumers'}
Age rating: {pu.age_rating.value}
Monetization: {pu.monetization.value}
Languages: {', '.join(pu.languages) or 'Not detected'}
Frameworks: {', '.join(pu.frameworks) or 'Not detected'}

{feature_section}

README excerpt:
{pu.readme_content[:1000] if pu.readme_content else 'No README found.'}
"""
