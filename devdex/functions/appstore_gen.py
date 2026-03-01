from __future__ import annotations

from devdex.models import DevDexPipelineState, GeneratedArtifact
from devdex.prompts import appstore


async def generate_appstore(
    state: DevDexPipelineState,
    client,
    model: str,
    improvement_context: str = "",
) -> GeneratedArtifact:
    pu = state.understanding
    artifact = GeneratedArtifact(
        artifact_type="appstore_description",
        file_path="appstore/description.md",
        format="markdown",
        model_used=model,
    )

    system_prompt = appstore.SYSTEM_PROMPT
    if improvement_context:
        system_prompt += f"\n\nIMPROVEMENT NOTES FROM PAST USER FEEDBACK:\n{improvement_context}"

    user_prompt = appstore.build_prompt(pu)
    artifact.system_prompt = system_prompt
    artifact.user_prompt = user_prompt

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=2048,
            temperature=0.5,
        )
        content = response.choices[0].message.content or ""
        if content.startswith("```markdown"):
            content = content[len("```markdown"):]
        elif content.startswith("```md"):
            content = content[len("```md"):]
        elif content.startswith("```"):
            content = content[3:]
        if content.rstrip().endswith("```"):
            content = content.rstrip()[:-3]
        artifact.content = content.strip()
    except Exception as e:
        artifact.error = str(e)

    return artifact
