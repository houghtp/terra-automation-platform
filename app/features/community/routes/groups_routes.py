"""API routes for community groups and forum posts."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.features.auth.dependencies import get_current_user
from app.features.auth.models import User

from ..dependencies import (
    get_group_service,
    get_group_post_service,
    get_group_comment_service,
)
from ..schemas import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    GroupPostCreate,
    GroupPostResponse,
    GroupPostUpdate,
    GroupCommentCreate,
    GroupCommentResponse,
)
from ..services import (
    GroupService,
    GroupPostService,
    GroupCommentService,
)

router = APIRouter(prefix="/groups", tags=["community-groups"])


@router.get("/api")
async def list_groups_api(
    search: Optional[str] = Query(default=None),
    privacy: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: GroupService = Depends(get_group_service),
):
    """Return paginated group data."""
    groups, total = await service.list_groups(search=search, privacy=privacy, limit=limit, offset=offset)
    return {
        "data": [group.to_dict() for group in groups],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api", response_model=GroupResponse, status_code=201)
async def create_group_api(
    payload: GroupCreate,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(get_current_user),
):
    group = await service.create_group(payload.model_dump(), current_user)
    if not group:
        raise HTTPException(status_code=500, detail="Failed to create group")
    return GroupResponse.model_validate(group, from_attributes=True)


@router.put("/api/{group_id}", response_model=GroupResponse)
async def update_group_api(
    group_id: str,
    payload: GroupUpdate,
    service: GroupService = Depends(get_group_service),
    current_user: User = Depends(get_current_user),
):
    group = await service.update_group(group_id, payload.model_dump(exclude_unset=True), current_user)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return GroupResponse.model_validate(group, from_attributes=True)


@router.delete("/api/{group_id}", status_code=204)
async def delete_group_api(
    group_id: str,
    service: GroupService = Depends(get_group_service),
):
    deleted = await service.delete_group(group_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Group not found")
    return Response(status_code=204)


@router.get("/api/{group_id}/posts")
async def list_posts_api(
    group_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: GroupPostService = Depends(get_group_post_service),
):
    posts, total = await service.list_posts(group_id=group_id, limit=limit, offset=offset)
    return {
        "data": [post.to_dict() for post in posts],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/{group_id}/posts", response_model=GroupPostResponse, status_code=201)
async def create_post_api(
    group_id: str,
    payload: GroupPostCreate,
    service: GroupPostService = Depends(get_group_post_service),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    data["group_id"] = group_id
    post = await service.create_post(data, current_user)
    if not post:
        raise HTTPException(status_code=500, detail="Failed to create post")
    return GroupPostResponse.model_validate(post, from_attributes=True)


@router.put("/api/posts/{post_id}", response_model=GroupPostResponse)
async def update_post_api(
    post_id: str,
    payload: GroupPostUpdate,
    service: GroupPostService = Depends(get_group_post_service),
    current_user: User = Depends(get_current_user),
):
    post = await service.update_post(post_id, payload.model_dump(exclude_unset=True), current_user)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return GroupPostResponse.model_validate(post, from_attributes=True)


@router.delete("/api/posts/{post_id}", status_code=204)
async def delete_post_api(
    post_id: str,
    service: GroupPostService = Depends(get_group_post_service),
):
    deleted = await service.delete_by_id(post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
    return Response(status_code=204)


@router.get("/api/posts/{post_id}/comments")
async def list_comments_api(
    post_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: GroupCommentService = Depends(get_group_comment_service),
):
    comments, total = await service.list_comments(post_id=post_id, limit=limit, offset=offset)
    return {
        "data": [comment.to_dict() for comment in comments],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/api/posts/{post_id}/comments", response_model=GroupCommentResponse, status_code=201)
async def create_comment_api(
    post_id: str,
    payload: GroupCommentCreate,
    service: GroupCommentService = Depends(get_group_comment_service),
    current_user: User = Depends(get_current_user),
):
    data = payload.model_dump()
    data["post_id"] = post_id
    comment = await service.create_comment(data, current_user)
    if not comment:
        raise HTTPException(status_code=500, detail="Failed to create comment")
    return GroupCommentResponse.model_validate(comment, from_attributes=True)


@router.delete("/api/comments/{comment_id}", status_code=204)
async def delete_comment_api(
    comment_id: str,
    service: GroupCommentService = Depends(get_group_comment_service),
):
    deleted = await service.delete_by_id(comment_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found")
    return Response(status_code=204)
