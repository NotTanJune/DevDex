from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class VectorStore:

    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        mistral_api_key: str = "",
    ) -> None:
        self._supabase_url = supabase_url
        self._supabase_key = supabase_key
        self._mistral_api_key = mistral_api_key
        self._supabase = None
        self._mistral = None

    def _get_supabase(self):
        if self._supabase is None:
            from supabase import create_client

            self._supabase = create_client(self._supabase_url, self._supabase_key)
        return self._supabase

    def _get_mistral(self):
        if self._mistral is None:
            from mistralai import Mistral

            self._mistral = Mistral(api_key=self._mistral_api_key)
        return self._mistral

    def _get_embedding(self, text: str) -> list[float]:
        client = self._get_mistral()
        response = client.embeddings.create(
            model="mistral-embed",
            inputs=[text],
        )
        return response.data[0].embedding

    def store_feedback(self, entry: dict[str, Any]) -> dict | None:
        try:
            sb = self._get_supabase()

            row = {
                "project_path": entry.get("project_path", ""),
                "artifact_type": entry.get("artifact_type", ""),
                "user_rating": entry.get("user_rating", 0),
                "had_edits": entry.get("had_edits", False),
                "edit_description": entry.get("edit_description", ""),
                "run_id": entry.get("run_id"),
                "created_at": datetime.now().isoformat(),
            }

            result = sb.table("feedback_entries").insert(row).execute()
            feedback_id = result.data[0]["id"] if result.data else None

            if feedback_id and entry.get("had_edits") and entry.get("edit_description"):
                self._embed_feedback(
                    feedback_id,
                    entry["edit_description"],
                    entry.get("artifact_type", ""),
                )

            return result.data[0] if result.data else None
        except Exception as e:
            logger.debug("Failed to store feedback: %s", e)
            return None

    def _embed_feedback(
        self, feedback_id: int, edit_text: str, artifact_type: str
    ) -> None:
        try:
            embedding = self._get_embedding(edit_text)
            sb = self._get_supabase()
            sb.table("feedback_embeddings").insert({
                "feedback_id": feedback_id,
                "embedding": embedding,
                "edit_text": edit_text,
                "artifact_type": artifact_type,
                "created_at": datetime.now().isoformat(),
            }).execute()
        except Exception as e:
            logger.debug("Failed to embed feedback: %s", e)

    def store_artifact(self, record: dict[str, Any]) -> dict | None:
        try:
            sb = self._get_supabase()
            row = {
                "feedback_id": record.get("feedback_id"),
                "artifact_type": record.get("artifact_type", ""),
                "system_prompt": record.get("system_prompt", ""),
                "user_prompt": record.get("user_prompt", ""),
                "generated_content": record.get("generated_content", ""),
                "model_used": record.get("model_used", ""),
                "project_context": json.dumps(record.get("project_context", {})),
                "run_id": record.get("run_id"),
                "created_at": datetime.now().isoformat(),
            }
            result = sb.table("generated_artifacts").insert(row).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.debug("Failed to store artifact: %s", e)
            return None

    def search_similar_feedback(
        self,
        query: str,
        artifact_type: str = "",
        limit: int = 5,
    ) -> list[dict]:
        try:
            embedding = self._get_embedding(query)
            sb = self._get_supabase()
            result = sb.rpc(
                "match_feedback_embeddings",
                {
                    "query_embedding": embedding,
                    "match_threshold": 0.5,
                    "match_count": limit,
                    "filter_artifact_type": artifact_type or None,
                },
            ).execute()
            return result.data or []
        except Exception as e:
            logger.debug("Semantic search failed: %s", e)
            return []

    def get_training_data(
        self,
        min_rating: int = 4,
        limit: int = 1000,
    ) -> list[dict]:
        sb = self._get_supabase()
        result = sb.rpc(
            "get_training_data",
            {
                "p_min_rating": min_rating,
                "p_limit": limit,
            },
        ).execute()
        return result.data or []
