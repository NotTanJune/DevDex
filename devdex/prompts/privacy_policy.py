from __future__ import annotations

from devdex.models import ProjectUnderstanding

SYSTEM_PROMPT = """You are a legal document generator specializing in mobile app privacy policies.
Generate a comprehensive, legally compliant privacy policy that covers:
- GDPR (EU), CCPA (California), PDPA (Singapore), and general international privacy requirements
- Specific data collection practices based on the SDKs and features detected
- Clear language that is accessible to non-lawyers
- All required sections: information collected, how it's used, sharing, retention, user rights, contact

Output the privacy policy in Markdown format. Use proper headings, bullet points, and sections.
Do NOT include any preamble or explanation — output ONLY the privacy policy document.
Do NOT wrap the output in markdown code fences (``` or ```markdown)."""


def build_prompt(pu: ProjectUnderstanding) -> str:
    sdk_section = ""
    if pu.sdks:
        sdk_lines = []
        for sdk in pu.sdks:
            data = ", ".join(sdk.data_collected) if sdk.data_collected else "none"
            sdk_lines.append(f"- {sdk.name} ({sdk.category}): collects {data}")
        sdk_section = "Detected SDKs and data collection:\n" + "\n".join(sdk_lines)

    data_section = ""
    if pu.data_collection:
        data_lines = [f"- {dc.pattern_type}: {dc.description}" for dc in pu.data_collection]
        data_section = "Additional data collection patterns:\n" + "\n".join(data_lines)

    auth_section = ""
    if pu.auth_methods:
        auth_lines = [f"- {a.method}" for a in pu.auth_methods]
        auth_section = "Authentication methods:\n" + "\n".join(auth_lines)

    return f"""Generate a privacy policy for the following app:

App name: {pu.display_name}
Platform: {pu.platform.value}
Purpose: {pu.app_purpose or 'Not specified'}
Developer: {pu.developer_name or 'Not specified'}
Contact email: {pu.developer_email or 'Not specified'}
Country/Jurisdiction: {pu.developer_country or 'Not specified'}
Monetization: {pu.monetization.value}
Has in-app purchases: {pu.has_in_app_purchases}

{sdk_section}

{data_section}

{auth_section}

All data types collected: {', '.join(pu.all_data_types) or 'None detected'}
"""
