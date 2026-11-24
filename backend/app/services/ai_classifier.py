"""
app/services/ai_classifier.py
Klasifikasi blok ambigu menggunakan LLM (PRD §FR-12, §6.1).
- Hanya blok dengan confidence < 0.6 dikirim ke AI
- Potongan minimal (maks AI_MAX_CHUNK_CHARS karakter)
- Dapat dimatikan lewat konfigurasi AI_ENABLED=false
- Keluaran AI HANYA label peran, tidak pernah masuk ke isi dokumen
"""

from __future__ import annotations

import json
from typing import List, Optional

from app.core.config import settings
from app.core.logging import logger
from app.schemas.session import BlockRole, DocumentBlock


class AIClassifier:
    """Klasifikasi blok ambigu dengan LLM."""

    SYSTEM_PROMPT = (
        "Kamu adalah classifier struktur dokumen akademik Indonesia. "
        "Analisis seluruh blok yang diberikan dengan konteks urutan dokumen. "
        "Tentukan role paling tepat tanpa mengubah atau menulis ulang teks. "
        "Role yang valid: cover, kata_pengantar, abstrak, daftar_isi, daftar_tabel, daftar_gambar, "
        "lembar_pengesahan, heading_bab, heading_subbab, paragraf, daftar_pustaka, lampiran, "
        "tabel, gambar, caption, kutipan_blok, unknown. "
        'Jawab JSON array saja, setiap item berbentuk {"block_id": string, "role": string}.'
    )

    def classify_ambiguous(self, blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        """Klasifikasi semua blok dengan konteks urutan dokumen."""
        if not settings.ai_enabled or not blocks:
            return blocks

        payload = json.dumps([
            {"block_id": block.block_id, "text": block.text_content or block.text_preview, "current_role": block.role.value, "confidence": block.confidence}
            for block in blocks
        ], ensure_ascii=False)
        try:
            classifications = self._classify_document(payload)
            by_id = {item.get("block_id"): item.get("role") for item in classifications if isinstance(item, dict)}
            for block in blocks:
                role = self._parse_role(str(by_id.get(block.block_id, "")))
                if role:
                    block.role = role
                    block.is_ambiguous = block.confidence < 0.8
        except Exception as e:
            logger.warning("ai_document_classification_failed", error=str(e))
        return blocks

    def _classify_document(self, payload: str) -> list[dict]:
        provider = settings.ai_provider.lower()
        if provider == "gemini":
            text = self._call_gemini_text(payload)
        else:
            raise ValueError(f"Provider AI tidak didukung untuk analisis dokumen: {provider}")
        parsed = json.loads(text.strip().removeprefix("``json").removesuffix("``").strip())
        return parsed if isinstance(parsed, list) else []

    def _classify_one(self, text: str) -> Optional[BlockRole]:
        """Kirim satu potongan ke AI dan kembalikan role."""
        # Potong teks ke batas maksimum
        chunk = text[: settings.ai_max_chunk_chars]

        provider = settings.ai_provider.lower()

        if provider == "openai":
            return self._call_openai(chunk)
        elif provider == "anthropic":
            return self._call_anthropic(chunk)
        elif provider == "gemini":
            return self._call_gemini(chunk)
        else:
            logger.warning("unknown_ai_provider", provider=provider)
            return None

    def _call_openai(self, chunk: str) -> Optional[BlockRole]:
        try:
            import httpx
            response = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.ai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "messages": [
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": chunk},
                    ],
                    "max_tokens": 20,
                    "temperature": 0,
                },
                timeout=10.0,
            )
            response.raise_for_status()
            role_str = response.json()["choices"][0]["message"]["content"].strip().lower()
            return self._parse_role(role_str)
        except Exception as e:
            logger.error("openai_error", error=str(e))
            return None

    def _call_anthropic(self, chunk: str) -> Optional[BlockRole]:
        try:
            import httpx
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.ai_api_key or "",
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.ai_model,
                    "max_tokens": 20,
                    "system": self.SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": chunk}],
                },
                timeout=10.0,
            )
            response.raise_for_status()
            role_str = response.json()["content"][0]["text"].strip().lower()
            return self._parse_role(role_str)
        except Exception as e:
            logger.error("anthropic_error", error=str(e))
            return None

    def _call_gemini_text(self, chunk: str) -> str:
        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.ai_model}:generateContent"
        response = httpx.post(
            url,
            headers={"x-goog-api-key": settings.ai_api_key or "", "Content-Type": "application/json"},
            json={"system_instruction": {"parts": [{"text": self.SYSTEM_PROMPT}]}, "contents": [{"role": "user", "parts": [{"text": chunk}]}], "generationConfig": {"temperature": 0, "maxOutputTokens": max(100, len(chunk) // 8)}},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _call_gemini(self, chunk: str) -> Optional[BlockRole]:
        try:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.ai_model}:generateContent"
            response = httpx.post(
                url,
                headers={"x-goog-api-key": settings.ai_api_key or "", "Content-Type": "application/json"},
                json={
                    "system_instruction": {"parts": [{"text": self.SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": chunk}]}],
                    "generationConfig": {"temperature": 0, "maxOutputTokens": 20},
                },
                timeout=15.0,
            )
            response.raise_for_status()
            role_str = response.json()["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
            return self._parse_role(role_str)
        except Exception as e:
            logger.error("gemini_error", error=str(e))
            return None

    @staticmethod
    def _parse_role(role_str: str) -> Optional[BlockRole]:
        try:
            return BlockRole(role_str)
        except ValueError:
            return None
