"""
Group services for Sprint 3 collaboration features.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.features.core.sqlalchemy_imports import (
    AsyncSession,
    func,
    or_,
    select,
)
from app.features.core.audit_mixin import AuditContext
from app.features.core.base_service import TenantScopedCRUDService

from ..models import Group, GroupPost, GroupComment


class GroupService(TenantScopedCRUDService[Group]):
    """Service for managing community groups."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, Group)

    async def list_groups(
        self,
        search: Optional[str] = None,
        privacy: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Group], int]:
        """Return paginated group records."""
        try:
            stmt = select(Group)
            count_stmt = select(func.count(Group.id))

            filters = []
            if self.tenant_id is not None:
                filters.append(Group.tenant_id == self.tenant_id)

            if search:
                like = f"%{search.lower()}%"
                filters.append(or_(func.lower(Group.name).like(like), func.lower(Group.description).like(like)))

            if privacy:
                filters.append(func.lower(Group.privacy) == privacy.lower())

            if filters:
                stmt = stmt.where(*filters)
                count_stmt = count_stmt.where(*filters)

            stmt = stmt.order_by(func.lower(Group.name)).offset(offset).limit(limit)

            result = await self.db.execute(stmt)
            groups = list(result.scalars().all())

            total = (await self.db.execute(count_stmt)).scalar_one()
            return groups, int(total or 0)
        except Exception as exc:
            await self.handle_service_error("list_groups", exc)

    async def create_group(self, payload: Dict[str, Any], user) -> Group:
        """Create a new group."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for groups.")

            audit_ctx = AuditContext.from_user(user)
            group = Group(
                id=str(uuid4()),
                tenant_id=tenant_id,
                name=payload["name"],
                description=payload.get("description"),
                privacy=payload.get("privacy", "private"),
                owner_id=payload.get("owner_id"),
            )
            group.set_created_by(audit_ctx.user_email, audit_ctx.user_name)

            self.db.add(group)
            await self.db.flush()
            await self.db.refresh(group)
            return group
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Group with that name already exists.") from exc
        except Exception as exc:
            await self.handle_service_error("create_group", exc)

    async def update_group(self, group_id: str, payload: Dict[str, Any], user) -> Optional[Group]:
        """Update existing group."""
        group = await self.get_by_id(group_id)
        if not group:
            return None

        try:
            for key, value in payload.items():
                if value is not None and hasattr(group, key):
                    setattr(group, key, value)

            audit_ctx = AuditContext.from_user(user)
            group.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)

            await self.db.flush()
            await self.db.refresh(group)
            return group
        except IntegrityError as exc:
            await self.db.rollback()
            raise ValueError("Group with that name already exists.") from exc
        except Exception as exc:
            await self.handle_service_error("update_group", exc, group_id)

    async def delete_group(self, group_id: str) -> bool:
        """Remove a group."""
        return await self.delete_by_id(group_id)


class GroupPostService(TenantScopedCRUDService[GroupPost]):
    """Service for managing group posts."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, GroupPost)

    async def list_posts(
        self,
        group_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[GroupPost], int]:
        """Return posts optionally filtered by group."""
        try:
            stmt = select(GroupPost)
            count_stmt = select(func.count(GroupPost.id))
            filters = []

            if self.tenant_id is not None:
                filters.append(GroupPost.tenant_id == self.tenant_id)

            if group_id:
                filters.append(GroupPost.group_id == group_id)

            if filters:
                stmt = stmt.where(*filters)
                count_stmt = count_stmt.where(*filters)

            stmt = stmt.order_by(GroupPost.created_at.desc()).offset(offset).limit(limit)

            result = await self.db.execute(stmt)
            posts = list(result.scalars().all())
            total = (await self.db.execute(count_stmt)).scalar_one()
            return posts, int(total or 0)
        except Exception as exc:
            await self.handle_service_error("list_posts", exc, group_id=group_id)

    async def create_post(self, payload: Dict[str, Any], user) -> GroupPost:
        """Create a group post."""
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for posts.")

            audit_ctx = AuditContext.from_user(user)
            post = GroupPost(
                id=str(uuid4()),
                tenant_id=tenant_id,
                group_id=payload["group_id"],
                author_id=payload.get("author_id"),
                title=payload.get("title"),
                content=payload["content"],
            )
            post.set_created_by(audit_ctx.user_email, audit_ctx.user_name)

            self.db.add(post)
            await self.db.flush()
            await self.db.refresh(post)
            return post
        except Exception as exc:
            await self.handle_service_error("create_post", exc)

    async def update_post(self, post_id: str, payload: Dict[str, Any], user) -> Optional[GroupPost]:
        """Update a post."""
        post = await self.get_by_id(post_id)
        if not post:
            return None

        try:
            for key, value in payload.items():
                if value is not None and hasattr(post, key):
                    setattr(post, key, value)

            audit_ctx = AuditContext.from_user(user)
            post.set_updated_by(audit_ctx.user_email, audit_ctx.user_name)
            await self.db.flush()
            await self.db.refresh(post)
            return post
        except Exception as exc:
            await self.handle_service_error("update_post", exc, post_id)


class GroupCommentService(TenantScopedCRUDService[GroupComment]):
    """Service for managing comments."""

    def __init__(self, db_session: AsyncSession, tenant_id: Optional[str]):
        super().__init__(db_session, tenant_id, GroupComment)

    async def list_comments(
        self,
        post_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[GroupComment], int]:
        try:
            stmt = select(GroupComment).where(GroupComment.post_id == post_id)
            count_stmt = select(func.count(GroupComment.id)).where(GroupComment.post_id == post_id)

            if self.tenant_id is not None:
                stmt = stmt.where(GroupComment.tenant_id == self.tenant_id)
                count_stmt = count_stmt.where(GroupComment.tenant_id == self.tenant_id)

            stmt = stmt.order_by(GroupComment.created_at.asc()).offset(offset).limit(limit)
            result = await self.db.execute(stmt)
            comments = list(result.scalars().all())

            total = (await self.db.execute(count_stmt)).scalar_one()
            return comments, int(total or 0)
        except Exception as exc:
            await self.handle_service_error("list_comments", exc, post_id=post_id)

    async def create_comment(self, payload: Dict[str, Any], user) -> GroupComment:
        try:
            tenant_id = self.tenant_id
            if tenant_id in (None, "global"):
                raise ValueError("Tenant context is required for comments.")

            audit_ctx = AuditContext.from_user(user)
            comment = GroupComment(
                id=str(uuid4()),
                tenant_id=tenant_id,
                post_id=payload["post_id"],
                author_id=payload.get("author_id"),
                content=payload["content"],
            )
            comment.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            self.db.add(comment)
            await self.db.flush()
            await self.db.refresh(comment)
            return comment
        except Exception as exc:
            await self.handle_service_error("create_comment", exc)
