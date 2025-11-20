"""AI Prompt Service for managing and rendering prompt templates."""

from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from jinja2 import Environment, Template, meta, TemplateSyntaxError
import logging

from app.features.administration.ai_prompts.models import AIPrompt

logger = logging.getLogger(__name__)


class AIPromptService:
    """
    Service for managing AI prompt templates with Jinja2 rendering.

    Handles:
    - Retrieving prompts with tenant override logic
    - Rendering templates with variable substitution
    - Variable validation and extraction
    - Usage tracking
    """

    def __init__(self, db: AsyncSession):
        """Initialize service with database session."""
        self.db = db
        self.jinja_env = Environment(autoescape=False)

    async def ensure_system_prompt(self, prompt_key: str, defaults: Dict[str, Any]) -> None:
        """Ensure a system-level prompt exists, seeding it if missing."""
        try:
            existing = await self.get_prompt_template(prompt_key, tenant_id=None)
            if existing:
                return

            prompt = AIPrompt(
                prompt_key=prompt_key,
                name=defaults.get("name", prompt_key.replace("_", " ").title()),
                description=defaults.get("description"),
                category=defaults.get("category"),
                prompt_template=defaults.get("prompt_template", ""),
                required_variables=defaults.get("required_variables") or {},
                optional_variables=defaults.get("optional_variables") or {},
                ai_model=defaults.get("ai_model"),
                temperature=defaults.get("temperature", 0.7),
                max_tokens=defaults.get("max_tokens"),
                top_p=defaults.get("top_p"),
                frequency_penalty=defaults.get("frequency_penalty"),
                presence_penalty=defaults.get("presence_penalty"),
                is_active=True,
                is_system=True,
                tenant_id=None,
            )
            self.db.add(prompt)
            await self.db.commit()
            await self.db.refresh(prompt)
            logger.info(
                "Seeded system prompt prompt_key=%s prompt_id=%s",
                prompt_key,
                prompt.id
            )
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to ensure system prompt for key %s", prompt_key)

    async def get_prompt_by_id(self, prompt_id: int) -> Optional[AIPrompt]:
        """Get prompt by ID."""
        result = await self.db.execute(
            select(AIPrompt).where(AIPrompt.id == prompt_id)
        )
        return result.scalar_one_or_none()

    async def get_prompt_template(
        self,
        prompt_key: str,
        tenant_id: Optional[str] = None
    ) -> Optional[AIPrompt]:
        """
        Get prompt template, checking tenant override first, then system default.

        Priority:
        1. Active tenant-specific override
        2. Active system default
        3. None if not found

        Args:
            prompt_key: Unique prompt identifier
            tenant_id: Tenant ID for tenant-specific overrides

        Returns:
            AIPrompt instance or None
        """
        try:
            # Check tenant override first
            if tenant_id:
                result = await self.db.execute(
                    select(AIPrompt).where(
                        and_(
                            AIPrompt.prompt_key == prompt_key,
                            AIPrompt.tenant_id == tenant_id,
                            AIPrompt.is_active == True
                        )
                    )
                )
                tenant_prompt = result.scalar_one_or_none()
                if tenant_prompt:
                    logger.debug(f"Found tenant override for prompt '{prompt_key}' (tenant: {tenant_id})")
                    return tenant_prompt

            # Fallback to system prompt
            result = await self.db.execute(
                select(AIPrompt).where(
                    and_(
                        AIPrompt.prompt_key == prompt_key,
                        AIPrompt.is_system == True,
                        AIPrompt.is_active == True,
                        AIPrompt.tenant_id.is_(None)
                    )
                )
            )
            system_prompt = result.scalar_one_or_none()

            if system_prompt:
                logger.debug(f"Using system default for prompt '{prompt_key}'")
            else:
                logger.warning(f"Prompt '{prompt_key}' not found (system or tenant)")

            return system_prompt

        except Exception as e:
            logger.exception(f"Error retrieving prompt '{prompt_key}': {e}")
            return None

    async def render_prompt(
        self,
        prompt_key: str,
        variables: Dict[str, Any],
        tenant_id: Optional[str] = None,
        track_usage: bool = True
    ) -> Optional[str]:
        """
        Render prompt template with provided variables using Jinja2.

        Args:
            prompt_key: Unique prompt identifier
            variables: Dictionary of variables to substitute
            tenant_id: Tenant ID for tenant-specific overrides
            track_usage: Whether to increment usage counter

        Returns:
            Rendered prompt string or None if prompt not found

        Raises:
            ValueError: If required variables are missing
            TemplateSyntaxError: If template has syntax errors
        """
        try:
            # Get prompt template
            prompt = await self.get_prompt_template(prompt_key, tenant_id)
            if not prompt:
                raise ValueError(f"Prompt '{prompt_key}' not found")

            # Validate required variables
            required_vars = set((prompt.required_variables or {}).keys())
            provided_vars = set(variables.keys())
            missing_vars = required_vars - provided_vars

            if missing_vars:
                raise ValueError(f"Missing required variables for prompt '{prompt_key}': {missing_vars}")

            # Add default values for optional variables
            optional_vars = prompt.optional_variables or {}
            for var_name, var_config in optional_vars.items():
                if var_name not in variables and "default" in var_config:
                    variables[var_name] = var_config["default"]

            # Render template with Jinja2
            template = Template(prompt.prompt_template)
            rendered = template.render(**variables)

            # Track usage
            if track_usage:
                await self._track_usage(prompt, success=True)

            logger.info(f"Successfully rendered prompt '{prompt_key}' (length: {len(rendered)} chars)")
            return rendered

        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error in prompt '{prompt_key}': {e}")
            if track_usage and prompt:
                await self._track_usage(prompt, success=False)
            raise
        except ValueError as e:
            logger.error(f"Variable validation error for prompt '{prompt_key}': {e}")
            raise
        except Exception as e:
            logger.exception(f"Error rendering prompt '{prompt_key}': {e}")
            if track_usage and prompt:
                await self._track_usage(prompt, success=False)
            raise

    async def track_usage(
        self,
        prompt_key: str,
        tenant_id: Optional[str] = None,
        success: bool = True
    ) -> None:
        """
        Public helper to track prompt usage for system or tenant prompts.

        Args:
            prompt_key: Unique prompt identifier
            tenant_id: Tenant scope (None for system)
            success: Whether the usage succeeded
        """
        prompt = await self.get_prompt_template(prompt_key, tenant_id)
        if not prompt:
            logger.warning(
                "Attempted to track usage for missing prompt '%s' (tenant: %s)",
                prompt_key,
                tenant_id or "system"
            )
            return

        await self._track_usage(prompt, success=success)

    async def _track_usage(self, prompt: AIPrompt, success: bool = True) -> None:
        """Update usage statistics for a prompt."""
        try:
            prompt.usage_count += 1
            prompt.last_used_at = datetime.now(timezone.utc)

            if success:
                prompt.success_count += 1
            else:
                prompt.failure_count += 1

            await self.db.commit()
        except Exception as e:
            logger.error(f"Error tracking usage for prompt {prompt.id}: {e}")
            # Don't fail the main operation if tracking fails

    def validate_template(self, template_str: str) -> Dict[str, Any]:
        """
        Validate Jinja2 template syntax and extract variables.

        Args:
            template_str: Template string to validate

        Returns:
            Dictionary with validation results:
            {
                "valid": bool,
                "variables": List[str],
                "syntax_errors": List[str]
            }
        """
        result = {
            "valid": True,
            "variables": [],
            "syntax_errors": []
        }

        try:
            # Parse template to extract variables
            ast = self.jinja_env.parse(template_str)
            variables = meta.find_undeclared_variables(ast)
            result["variables"] = sorted(list(variables))

            # Try to compile template to check for syntax errors
            self.jinja_env.from_string(template_str)

        except TemplateSyntaxError as e:
            result["valid"] = False
            result["syntax_errors"].append(f"Line {e.lineno}: {e.message}")
        except Exception as e:
            result["valid"] = False
            result["syntax_errors"].append(str(e))

        return result

    async def list_prompts(
        self,
        tenant_id: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        include_system: bool = True
    ) -> List[AIPrompt]:
        """
        List prompts with optional filters.

        Args:
            tenant_id: Filter by tenant (None for system prompts)
            category: Filter by category
            is_active: Filter by active status
            include_system: Include system prompts in results

        Returns:
            List of AIPrompt instances
        """
        try:
            conditions = []

            # Tenant filter: include tenant-specific AND system prompts
            if tenant_id and include_system:
                conditions.append(
                    or_(
                        AIPrompt.tenant_id == tenant_id,
                        and_(AIPrompt.is_system == True, AIPrompt.tenant_id.is_(None))
                    )
                )
            elif tenant_id:
                conditions.append(AIPrompt.tenant_id == tenant_id)
            else:
                # Only system prompts
                conditions.append(AIPrompt.is_system == True)
                conditions.append(AIPrompt.tenant_id.is_(None))

            if category:
                conditions.append(AIPrompt.category == category)

            if is_active is not None:
                conditions.append(AIPrompt.is_active == is_active)

            query = select(AIPrompt)
            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(AIPrompt.category, AIPrompt.name)

            result = await self.db.execute(query)
            prompts = result.scalars().all()

            logger.debug(f"Listed {len(prompts)} prompts (tenant: {tenant_id}, category: {category})")
            return list(prompts)

        except Exception as e:
            logger.exception(f"Error listing prompts: {e}")
            return []

    async def create_prompt(self, prompt_data: Dict[str, Any]) -> AIPrompt:
        """
        Create a new prompt.

        Args:
            prompt_data: Dictionary with prompt fields

        Returns:
            Created AIPrompt instance
        """
        try:
            # Validate template before creating
            validation = self.validate_template(prompt_data["prompt_template"])
            if not validation["valid"]:
                raise ValueError(f"Invalid template: {validation['syntax_errors']}")

            prompt = AIPrompt(**prompt_data)
            self.db.add(prompt)
            await self.db.commit()
            await self.db.refresh(prompt)

            logger.info(f"Created prompt '{prompt.prompt_key}' (id: {prompt.id})")
            return prompt

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating prompt: {e}")
            raise

    async def update_prompt(self, prompt_id: int, prompt_data: Dict[str, Any]) -> Optional[AIPrompt]:
        """
        Update an existing prompt.

        Args:
            prompt_id: ID of prompt to update
            prompt_data: Dictionary with fields to update

        Returns:
            Updated AIPrompt instance or None if not found
        """
        try:
            prompt = await self.get_prompt_by_id(prompt_id)
            if not prompt:
                logger.warning(f"Prompt {prompt_id} not found for update")
                return None

            # Validate template if it's being updated
            if "prompt_template" in prompt_data:
                validation = self.validate_template(prompt_data["prompt_template"])
                if not validation["valid"]:
                    raise ValueError(f"Invalid template: {validation['syntax_errors']}")

            # Update fields
            for key, value in prompt_data.items():
                if hasattr(prompt, key):
                    setattr(prompt, key, value)

            await self.db.commit()
            await self.db.refresh(prompt)

            logger.info(f"Updated prompt {prompt_id} (key: {prompt.prompt_key})")
            return prompt

        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error updating prompt {prompt_id}: {e}")
            raise

    async def get_categories(self, tenant_id: Optional[str] = None) -> List[str]:
        """Get list of unique categories for available prompts."""
        try:
            query = select(AIPrompt.category).distinct()

            if tenant_id:
                query = query.where(
                    or_(
                        AIPrompt.tenant_id == tenant_id,
                        and_(AIPrompt.is_system == True, AIPrompt.tenant_id.is_(None))
                    )
                )
            else:
                query = query.where(AIPrompt.is_system == True)

            query = query.where(AIPrompt.is_active == True)

            result = await self.db.execute(query)
            categories = [row[0] for row in result.all() if row[0]]

            return sorted(categories)

        except Exception as e:
            logger.exception(f"Error getting categories: {e}")
            return []
