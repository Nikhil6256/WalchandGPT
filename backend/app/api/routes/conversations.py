"""Conversation CRUD routes."""
import uuid

import structlog
from fastapi import APIRouter, HTTPException, status

from app.core.deps import CurrentUser, DBDep
from app.schemas.conversation import ConversationCreate, ConversationResponse, ConversationList
from app.services.conversation_service import ConversationService

log = structlog.get_logger(__name__)
router = APIRouter()


@router.get("", response_model=ConversationList)
async def list_conversations(current_user: CurrentUser, db: DBDep):
    """List all conversations for the current user."""
    service = ConversationService(db)
    convs = await service.list_by_user(current_user.id)
    return ConversationList(conversations=convs)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    current_user: CurrentUser,
    db: DBDep,
):
    """Create a new conversation."""
    service = ConversationService(db)
    conv = await service.create(user_id=current_user.id, title=payload.title)
    return ConversationResponse.model_validate(conv)


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBDep,
):
    """Get a specific conversation with its messages."""
    service = ConversationService(db)
    conv = await service.get_by_id(conversation_id, current_user.id)
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: CurrentUser,
    db: DBDep,
):
    """Delete a conversation and all its messages."""
    service = ConversationService(db)
    deleted = await service.delete(conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
