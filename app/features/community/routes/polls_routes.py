"""API routes for community polls."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User

from ..dependencies import get_poll_service, get_poll_vote_service
from ..schemas import (
    PollCreate,
    PollResponse,
    PollUpdate,
    PollVoteCreate,
    PollVoteResponse,
)
from ..services import PollService, PollVoteService

router = APIRouter(prefix="/polls", tags=["community-polls"])


@router.get("/api")
async def list_polls_api(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: PollService = Depends(get_poll_service),
):
    polls, total = await service.list_polls(status=status, limit=limit, offset=offset)
    data = []
    for poll in polls:
        payload = poll.to_dict()
        payload["options"] = [option.to_dict() for option in poll.options] if hasattr(poll, "options") else []
        data.append(payload)
    return {
        "data": data,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api", response_model=PollResponse, status_code=201)
async def create_poll_api(
    payload: PollCreate,
    current_user: User = Depends(get_current_user),
    service: PollService = Depends(get_poll_service),
):
    poll = await service.create_poll(payload.model_dump(), current_user)
    if not poll:
        raise HTTPException(status_code=500, detail="Failed to create poll")
    poll_dict = poll.to_dict()
    poll_dict["options"] = [option.to_dict() for option in poll.options]
    return PollResponse.model_validate(poll_dict)


@router.put("/api/{poll_id}", response_model=PollResponse)
async def update_poll_api(
    poll_id: str,
    payload: PollUpdate,
    current_user: User = Depends(get_current_user),
    service: PollService = Depends(get_poll_service),
):
    poll = await service.update_poll(poll_id, payload.model_dump(exclude_unset=True), current_user)
    if not poll:
        raise HTTPException(status_code=404, detail="Poll not found")
    poll_dict = poll.to_dict()
    poll_dict["options"] = [option.to_dict() for option in poll.options]
    return PollResponse.model_validate(poll_dict)


@router.delete("/api/{poll_id}", status_code=204)
async def delete_poll_api(
    poll_id: str,
    service: PollService = Depends(get_poll_service),
):
    deleted = await service.delete_poll(poll_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Poll not found")
    return Response(status_code=204)


@router.post("/api/{poll_id}/vote", response_model=PollVoteResponse, status_code=201)
async def cast_vote_api(
    poll_id: str,
    payload: PollVoteCreate,
    current_user: User = Depends(get_current_user),
    vote_service: PollVoteService = Depends(get_poll_vote_service),
):
    data = payload.model_dump()
    vote = await vote_service.cast_vote(
        poll_id=poll_id,
        option_id=data["option_id"],
        member_id=current_user.id if current_user else None,
    )
    return PollVoteResponse.model_validate(vote, from_attributes=True)


@router.get("/api/{poll_id}/summary")
async def poll_summary_api(
    poll_id: str,
    vote_service: PollVoteService = Depends(get_poll_vote_service),
):
    return {"data": await vote_service.vote_summary(poll_id)}
