from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import PromptInfo, PromptListResponse
from app.prompts.manager import get_prompt_manager

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=PromptListResponse)
async def list_prompts() -> PromptListResponse:
    """Introspection endpoint over the externalized prompt library
    (app/prompts/library/*.yaml) -- lets an operator confirm which prompt
    versions are live without reading source code."""
    pm = get_prompt_manager()
    prompts = [PromptInfo(name=name, **info) for name, info in pm.list_prompts().items()]
    return PromptListResponse(prompts=prompts)


@router.post("/reload", response_model=PromptListResponse)
async def reload_prompts() -> PromptListResponse:
    """Hot-reloads prompt YAML files from disk without restarting the
    service -- so a prompt-only change can be deployed independently of an
    application code release."""
    pm = get_prompt_manager()
    pm.reload()
    prompts = [PromptInfo(name=name, **info) for name, info in pm.list_prompts().items()]
    return PromptListResponse(prompts=prompts)
