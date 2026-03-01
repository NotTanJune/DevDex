from __future__ import annotations

from devdex.models import DevDexPipelineState, GeneratedArtifact
from devdex.prompts import landing_page


async def generate_landing_page(
    state: DevDexPipelineState,
    client,
    model: str,
    improvement_context: str = "",
) -> GeneratedArtifact:
    pu = state.understanding
    prompt_content = landing_page.build_prompt(pu)

    full_content = f"""# Landing Page Prompt for {pu.display_name}

> Paste this prompt into **Mistral Le Chat** (le.chat.mistral.ai — vibe coding mode),
> **v0.dev**, **Bolt.new**, **Lovable**, or any AI website builder to generate
> a polished, production-ready landing page.

---

## System Instructions

{landing_page.SYSTEM_PROMPT}

---

## Prompt

{prompt_content}
"""

    return GeneratedArtifact(
        artifact_type="landing_page",
        content=full_content,
        file_path="landing-page/LANDING_PAGE_PROMPT.md",
        format="markdown",
        model_used="n/a (prompt template)",
        system_prompt=landing_page.SYSTEM_PROMPT,
        user_prompt=prompt_content,
    )
