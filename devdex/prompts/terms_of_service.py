from __future__ import annotations

from devdex.models import ProjectUnderstanding

SYSTEM_PROMPT = """You are a legal document generator specializing in Terms of Service for mobile and web apps.
Generate comprehensive Terms of Service covering:
- Acceptable use policy
- Intellectual property rights
- Limitation of liability and disclaimers
- Payment terms (if applicable)
- Account termination
- Governing law and dispute resolution
- Modifications to terms

Output the Terms of Service in Markdown format. Use proper headings, numbered sections, and clear language.
Keep sections concise — prioritize substance over length. Avoid repetitive boilerplate.
Do NOT include any preamble or explanation — output ONLY the Terms of Service document.
Do NOT wrap the output in markdown code fences (``` or ```markdown)."""


def build_prompt(pu: ProjectUnderstanding) -> str:
    payment_info = ""
    if pu.has_in_app_purchases or pu.monetization.value in ("paid", "freemium", "subscription"):
        payment_info = f"""
Payment model: {pu.monetization.value}
Has in-app purchases: {pu.has_in_app_purchases}
Include detailed payment terms, refund policy, and subscription cancellation sections."""

    return f"""Generate Terms of Service for the following app:

App name: {pu.display_name}
Platform: {pu.platform.value}
Purpose: {pu.app_purpose or 'Not specified'}
Target audience: {pu.target_audience or 'General consumers'}
Developer: {pu.developer_name or 'Not specified'}
Contact email: {pu.developer_email or 'Not specified'}
Country/Jurisdiction: {pu.developer_country or 'Not specified'}
{payment_info}

Include sections appropriate for a {pu.platform.value} application distributed via {pu.deployment_target.value}.
"""
