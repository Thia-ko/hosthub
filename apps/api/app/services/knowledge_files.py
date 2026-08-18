import base64
import logging
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.models.instance_knowledge_file import InstanceKnowledgeFile, KnowledgeFileKind, KnowledgeFileStatus
from app.services.ai_assist_provider import AiAssistProvider

logger = logging.getLogger(__name__)

# Relative to the FastAPI process cwd (`/app` inside the container, bind-mounted from
# `apps/api/`), so uploads land on the host at `apps/api/uploads/knowledge/` and persist across
# container restarts without any docker-compose changes.
KNOWLEDGE_UPLOAD_ROOT = Path("uploads/knowledge")

_KIND_LABEL = {
    KnowledgeFileKind.TEXT: "texto",
    KnowledgeFileKind.IMAGE: "imagem",
    KnowledgeFileKind.AUDIO: "audio",
    KnowledgeFileKind.VIDEO: "video",
}

_TEXT_CONTENT_TYPES = {"text/plain", "text/markdown", "text/csv"}


def _kind_for_content_type(content_type: str) -> KnowledgeFileKind:
    if content_type in _TEXT_CONTENT_TYPES:
        return KnowledgeFileKind.TEXT
    if content_type.startswith("image/"):
        return KnowledgeFileKind.IMAGE
    if content_type.startswith("audio/"):
        return KnowledgeFileKind.AUDIO
    if content_type.startswith("video/"):
        return KnowledgeFileKind.VIDEO
    raise ValueError("Tipo de arquivo nao suportado")


async def save_knowledge_file(
    db, instance_id: uuid.UUID, upload: UploadFile, provider: AiAssistProvider
) -> InstanceKnowledgeFile:
    content = await upload.read()
    content_type = upload.content_type or "application/octet-stream"
    kind = _kind_for_content_type(content_type)

    dest_dir = KNOWLEDGE_UPLOAD_ROOT / str(instance_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    storage_path = dest_dir / f"{uuid.uuid4()}-{upload.filename}"
    storage_path.write_bytes(content)

    content_text: str | None = None
    status = KnowledgeFileStatus.READY

    try:
        if kind == KnowledgeFileKind.TEXT:
            content_text = content.decode("utf-8", errors="replace")
        elif kind == KnowledgeFileKind.IMAGE:
            if provider.is_configured:
                data_uri = f"data:{content_type};base64,{base64.b64encode(content).decode()}"
                content_text, _prompt_tokens, _completion_tokens = await provider.describe_image(data_uri)
        elif kind == KnowledgeFileKind.AUDIO:
            if provider.is_configured:
                content_text = await provider.transcribe_bytes(content, upload.filename or "audio", content_type)
        # VIDEO: no automatic processing - content_text stays None until an admin fills it in
        # manually via PATCH.
    except Exception:
        logger.exception(
            "Falha ao processar arquivo de conhecimento (%s) da instancia %s", _KIND_LABEL[kind], instance_id
        )
        content_text = None
        status = KnowledgeFileStatus.PROCESSING_FAILED

    item = InstanceKnowledgeFile(
        instance_id=instance_id,
        filename=upload.filename or "arquivo",
        content_type=content_type,
        kind=kind,
        status=status,
        storage_path=str(storage_path),
        size_bytes=len(content),
        content_text=content_text,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


def build_knowledge_section(files: list[InstanceKnowledgeFile]) -> str:
    """Formats the already-filtered set of knowledge files (eligible usage_mode, non-null
    content_text) into a prompt-ready block. Empty string when there's nothing to include."""
    lines = [
        f"- {item.filename} ({_KIND_LABEL[item.kind]}): {item.content_text}"
        for item in files
        if item.content_text
    ]
    if not lines:
        return ""
    return "## Arquivos de Conhecimento\n" + "\n".join(lines)
