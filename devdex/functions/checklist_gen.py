from __future__ import annotations

from devdex.models import DevDexPipelineState, GeneratedArtifact
from devdex.prompts import checklist


KNOWN_ARTIFACTS: list[dict] = [
    {
        "file_path": "appstore/description.md",
        "description": "Contains: Short Description, Long Description, Keywords, Category, What's New",
    },
    {
        "file_path": "legal/privacy-policy.md",
        "description": "Complete privacy policy",
    },
    {
        "file_path": "legal/terms-of-service.md",
        "description": "Complete terms of service",
    },
    {
        "file_path": "deployment-checklist.md",
        "description": "The deployment checklist itself",
    },
]


async def generate_checklist(
    state: DevDexPipelineState,
    client,
    model: str,
    improvement_context: str = "",
    generated_artifacts: list[dict] | None = None,
) -> GeneratedArtifact:
    pu = state.understanding
    artifact = GeneratedArtifact(
        artifact_type="deployment_checklist",
        file_path="deployment-checklist.md",
        format="markdown",
        model_used=model,
    )

    system_prompt = checklist.SYSTEM_PROMPT
    if improvement_context:
        system_prompt += f"\n\nIMPROVEMENT NOTES FROM PAST USER FEEDBACK:\n{improvement_context}"

    user_prompt = checklist.build_prompt(
        pu,
        generated_artifacts=generated_artifacts or KNOWN_ARTIFACTS,
    )
    artifact.system_prompt = system_prompt
    artifact.user_prompt = user_prompt

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
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
