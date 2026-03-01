from __future__ import annotations

from devdex.models import ProjectUnderstanding

SYSTEM_PROMPT = """You are a web designer who creates beautiful, modern landing pages.
Generate a COMPLETE, single-file HTML landing page with:
- Embedded CSS (no external dependencies)
- Responsive design (mobile-first)
- Modern, clean aesthetic with gradients and subtle animations
- Sections: Hero (with app name + tagline), Features (3-4 cards), How It Works, CTA, Footer
- Accessibility: semantic HTML, proper heading hierarchy, alt text
- Use the exact brand colors provided — they MUST be the dominant colors throughout the page
- Footer links to privacy-policy.html, terms-of-service.html, and support.html (same directory)

Output ONLY the complete HTML file, starting with <!DOCTYPE html>.
Do NOT include any explanation or markdown wrapping — output raw HTML only."""

SUPPORTING_PAGE_SYSTEM_PROMPT = """You are a web designer generating a supporting HTML page
that MUST visually match the landing page style provided.

Requirements:
- Use the SAME CSS custom properties, fonts, and color scheme as the landing page
- Include a simple nav bar with the app name linking back to index.html
- Include a footer with links to privacy-policy.html, terms-of-service.html, and support.html
- Content should be well-structured with proper headings, paragraphs, and lists
- Responsive design matching the landing page
- Output ONLY complete HTML starting with <!DOCTYPE html>
- Do NOT include any explanation or markdown wrapping — output raw HTML only."""


def build_prompt(
    pu: ProjectUnderstanding, template_html: str = ""
) -> str:
    features = []
    for sdk in pu.sdks:
        if sdk.category in ("auth", "payments", "analytics"):
            features.append(sdk.name)

    color_section = ""
    if pu.color_theme:
        colors = []
        for name, value in pu.color_theme.items():
            colors.append(f"  - {name}: {value}")
        color_section = (
            "\n\nBrand colors (USE THESE EXACTLY):\n"
            + "\n".join(colors)
            + "\nUse the primary color for hero backgrounds, buttons, and CTAs. "
            "Use the secondary color for accents, hover states, and supporting elements. "
            "Derive gradients and lighter/darker shades from these base colors."
        )
    else:
        color_section = (
            "\n\nNo specific brand colors provided — use a clean black and white color scheme. "
            "Use #000000 for primary text and headings, #FFFFFF for backgrounds, "
            "and grayscale tones (#333333, #666666, #999999, #E5E5E5, #F5F5F5) "
            "for hierarchy and subtle differentiation. No colored gradients."
        )

    template_context = ""
    if template_html:
        template_context = (
            "\n\nHere is a reference HTML template for structure and style inspiration. "
            "Use it as a starting point but customize the content, colors, and copy "
            "to match the app described above:\n\n"
            f"```html\n{template_html}\n```"
        )

    return f"""Create a landing page for:

App name: {pu.display_name}
Tagline/Purpose: {pu.app_purpose or 'A modern mobile application'}
Target audience: {pu.target_audience or 'General consumers'}
Platform: {pu.platform.value}
Developer: {pu.developer_name or 'Independent Developer'}
Contact: {pu.developer_email or ''}
Support URL: {pu.support_url or ''}

Key integrations: {', '.join(features) if features else 'Standard features'}
{color_section}

Make the landing page feel premium and trustworthy. Include:
- App Store download badge placeholder (link to #)
- Privacy policy link (privacy-policy.html), Terms of Service link (terms-of-service.html), Support link (support.html)
- Contact information in footer
{template_context}"""


def build_supporting_page_prompt(
    page_type: str,
    pu: ProjectUnderstanding,
    landing_html: str,
    page_content: str = "",
) -> str:
    page_descriptions = {
        "privacy-policy": (
            "Generate a Privacy Policy HTML page. Include sections for: "
            "what data is collected, how it's used, third-party services, "
            "user rights, data retention, contact information, and update policy."
        ),
        "terms-of-service": (
            "Generate a Terms of Service HTML page. Include sections for: "
            "acceptance of terms, description of service, user obligations, "
            "intellectual property, limitation of liability, termination, "
            "governing law, and contact information."
        ),
        "support": (
            "Generate a Support / Help Center HTML page. Include: "
            "a FAQ section with 4-6 common questions, contact information, "
            "how to report issues, and links to privacy policy and terms."
        ),
    }

    description = page_descriptions.get(page_type, "Generate a supporting page.")

    content_section = ""
    if page_content:
        content_section = (
            f"\n\nUse the following content as the basis for this page "
            f"(convert from markdown to HTML, match the visual style):\n\n{page_content}"
        )

    return f"""{description}

App name: {pu.display_name}
Developer: {pu.developer_name or 'Independent Developer'}
Contact email: {pu.developer_email or ''}
Country/Jurisdiction: {pu.developer_country or 'United States'}

The page file will be named {page_type}.html and lives in the same directory as index.html.
Links to other pages should use relative paths: privacy-policy.html, terms-of-service.html, support.html, index.html.

Here is the landing page HTML — match its visual style (colors, fonts, layout patterns):

```html
{landing_html[:3000]}
```
{content_section}"""
