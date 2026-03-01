from __future__ import annotations

from devdex.models import DevDexPipelineState, GeneratedArtifact
from devdex.prompts import terms_of_service


async def generate_tos(
    state: DevDexPipelineState,
    client,
    model: str,
    improvement_context: str = "",
) -> GeneratedArtifact:
    pu = state.understanding
    artifact = GeneratedArtifact(
        artifact_type="terms_of_service",
        file_path="legal/terms-of-service.md",
        format="markdown",
        model_used=model,
    )

    system_prompt = terms_of_service.SYSTEM_PROMPT
    if improvement_context:
        system_prompt += f"\n\nIMPROVEMENT NOTES FROM PAST USER FEEDBACK:\n{improvement_context}"

    user_prompt = terms_of_service.build_prompt(pu)
    artifact.system_prompt = system_prompt
    artifact.user_prompt = user_prompt

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=3000,
            temperature=0.3,
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
