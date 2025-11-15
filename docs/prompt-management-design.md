# AI Prompt Management UI - Design Document

## 🎯 Overview

Create a UI to surface, edit, and manage AI prompts with dynamic variable placeholder support.

## 📊 Current State

AI prompts are currently hardcoded in Python services with f-string variables:

```python
blog_prompt = f"""
You are a senior SEO content writer. Generate a high-quality blog post.

**Title:** {title}
**SEO Analysis:** {seo_analysis}
**Previous Content:** {previous_content if previous_content else "No previous version"}
**Tone:** professional and engaging
"""
```

**Variables used:**
- `{title}` - Content title
- `{seo_analysis}` - SEO research data
- `{previous_content}` - Previous version for refinement
- `{validation_feedback}` - SEO validation feedback
- `{tone}` - Writing tone
- `{topic}` - Content topic
- `{channel}` - Target channel (twitter, linkedin, etc.)
- `{constraints}` - Channel-specific constraints

## 🎨 Proposed Solution

### 1. Database Schema - `ai_prompts` Table

```python
class AIPrompt(Base):
    """Configurable AI prompts with variable placeholders."""
    __tablename__ = "ai_prompts"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(String, index=True)  # Tenant-specific overrides

    # Prompt identification
    prompt_key = Column(String, unique=True, nullable=False, index=True)
    # e.g., "seo_blog_generation", "channel_variant_twitter", "content_refinement"

    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # "content_generation", "channel_adaptation", "refinement"

    # Prompt content
    prompt_template = Column(Text, nullable=False)
    # Template with {{variable}} placeholders (using Jinja2 syntax)

    # Variable definitions
    required_variables = Column(JSONB)
    # {"title": {"type": "string", "description": "Content title"},
    #  "tone": {"type": "string", "default": "professional", "options": ["casual", "professional", "technical"]}}

    optional_variables = Column(JSONB)
    # {"previous_content": {"type": "string", "description": "Previous version for refinement"}}

    # Metadata
    ai_model = Column(String)  # "gpt-4-turbo", "gpt-4o-mini", "claude-3-opus"
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer)

    # Usage tracking
    usage_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True))

    # Status
    is_active = Column(Boolean, default=True)
    is_system = Column(Boolean, default=False)  # System prompts can't be deleted, only overridden

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String)
```

### 2. Prompt Template Syntax

Use **Jinja2** template syntax (consistent with existing HTML templates):

```jinja
You are a senior SEO content writer. Generate a high-quality blog post.

**Title:** {{ title }}

{% if seo_analysis %}
**SEO Analysis:**
{{ seo_analysis }}
{% endif %}

**Previous Content:**
{{ previous_content | default("No previous version, this is the first draft.") }}

{% if validation_feedback %}
**Validation Feedback:**
{{ validation_feedback }}
{% else %}
**Validation Feedback:** No feedback yet. Optimize based on SEO best practices.
{% endif %}

**Tone:** {{ tone | default("professional") }}
```

**Benefits:**
- ✅ Consistent with existing Jinja2 templates
- ✅ Supports conditionals (`{% if %}`)
- ✅ Supports defaults (`{{ var | default("fallback") }}`)
- ✅ Rich formatting options
- ✅ Easy to render: `jinja2.Template(prompt_template).render(**variables)`

### 3. UI Features

#### A. Prompt Library Page

**Route:** `/features/administration/ai-prompts`

**Features:**
- Table with all prompts (name, category, model, usage count, last used)
- Search/filter by category, active/inactive
- "Create Prompt" button
- View/Edit/Duplicate/Deactivate actions
- System prompts marked with badge (can't delete, only override)

#### B. Prompt Editor

**Features:**

1. **Basic Info Section:**
   - Name
   - Description
   - Category (dropdown: content_generation, channel_adaptation, refinement, etc.)
   - Active toggle

2. **Template Editor:**
   - Large textarea with syntax highlighting
   - Live variable detection (scan for `{{ variable }}` patterns)
   - Variable reference panel on right side

3. **Variable Definition Panel:**
   ```
   Detected Variables:
   - {{title}} [Required] ✓ Configured
   - {{tone}} [Optional] ✓ Configured
   - {{seo_analysis}} [Unconfirmed] ⚠️ Configure

   [+ Add Variable Definition]
   ```

4. **Variable Configuration Modal:**
   - Variable name
   - Type: string, int, boolean, array
   - Required/Optional
   - Default value
   - Description
   - Options (for enums: ["casual", "professional", "technical"])

5. **AI Model Settings:**
   - Model dropdown (gpt-4-turbo, gpt-4o-mini, claude-3-opus, etc.)
   - Temperature slider (0.0 - 1.0)
   - Max tokens input

6. **Preview Section:**
   - "Test with Sample Data" button
   - Input sample values for each variable
   - Preview rendered prompt
   - "Run AI Test" - actually call AI with the prompt and show output

7. **Usage History:**
   - Show recent uses
   - Success rate
   - Average tokens used

#### C. Tenant Override System

**Global Admin:**
- Can create system prompts (visible to all tenants)
- Can edit system prompts

**Tenant Admin:**
- Can override system prompts for their tenant
- Overridden prompts shown with "Custom" badge
- "Reset to System Default" button

### 4. Service Integration

#### Prompt Service

```python
class AIPromptService:
    """Manage and render AI prompts."""

    async def get_prompt_template(
        self,
        prompt_key: str,
        tenant_id: str
    ) -> AIPrompt:
        """Get prompt, checking tenant override first, then system default."""
        # Check tenant override
        tenant_prompt = await self.db.execute(
            select(AIPrompt).where(
                AIPrompt.prompt_key == prompt_key,
                AIPrompt.tenant_id == tenant_id,
                AIPrompt.is_active == True
            )
        )
        if tenant_prompt:
            return tenant_prompt

        # Fallback to system prompt
        system_prompt = await self.db.execute(
            select(AIPrompt).where(
                AIPrompt.prompt_key == prompt_key,
                AIPrompt.is_system == True,
                AIPrompt.is_active == True
            )
        )
        return system_prompt

    async def render_prompt(
        self,
        prompt_key: str,
        tenant_id: str,
        variables: Dict[str, Any]
    ) -> str:
        """Render prompt template with provided variables."""
        prompt = await self.get_prompt_template(prompt_key, tenant_id)

        # Validate required variables
        missing = set(prompt.required_variables.keys()) - set(variables.keys())
        if missing:
            raise ValueError(f"Missing required variables: {missing}")

        # Render with Jinja2
        from jinja2 import Template
        template = Template(prompt.prompt_template)
        rendered = template.render(**variables)

        # Update usage tracking
        prompt.usage_count += 1
        prompt.last_used_at = datetime.now(timezone.utc)
        await self.db.commit()

        return rendered

    async def validate_template(self, template: str) -> Dict[str, Any]:
        """Validate template syntax and extract variables."""
        from jinja2 import Environment, meta

        env = Environment()
        ast = env.parse(template)
        variables = meta.find_undeclared_variables(ast)

        return {
            "valid": True,
            "variables": list(variables),
            "syntax_errors": []
        }
```

#### Update Existing Services

**Before:**
```python
blog_prompt = f"""
You are a senior SEO content writer. Generate a high-quality blog post.
**Title:** {title}
"""
```

**After:**
```python
prompt_service = AIPromptService(db)
blog_prompt = await prompt_service.render_prompt(
    prompt_key="seo_blog_generation",
    tenant_id=tenant_id,
    variables={
        "title": title,
        "seo_analysis": seo_analysis,
        "tone": tone,
        "previous_content": previous_content,
        "validation_feedback": validation_feedback
    }
)
```

### 5. System Prompt Seeds

Create migration/seed to populate default prompts:

```python
DEFAULT_PROMPTS = [
    {
        "prompt_key": "seo_blog_generation",
        "name": "SEO Blog Post Generation",
        "category": "content_generation",
        "description": "Generate SEO-optimized long-form blog content",
        "prompt_template": """...""",  # Copy from existing service
        "required_variables": {
            "title": {"type": "string", "description": "Content title"},
            "seo_analysis": {"type": "string", "description": "SEO research analysis"}
        },
        "optional_variables": {
            "tone": {"type": "string", "default": "professional"},
            "previous_content": {"type": "string"},
            "validation_feedback": {"type": "string"}
        },
        "ai_model": "gpt-4-turbo",
        "temperature": 0.7,
        "is_system": True
    },
    {
        "prompt_key": "channel_variant_twitter",
        "name": "Twitter Content Adaptation",
        "category": "channel_adaptation",
        "prompt_template": """...""",
        "required_variables": {
            "content": {"type": "string"},
            "title": {"type": "string"}
        },
        "ai_model": "gpt-4o-mini",  # Use mini for variants
        "temperature": 0.7,
        "is_system": True
    }
    # ... more prompts
]
```

## 🎯 Benefits

1. **Flexibility:** Business users can tweak prompts without code changes
2. **Experimentation:** A/B test different prompt approaches
3. **Tenant Customization:** Each tenant can customize prompts for their brand voice
4. **Version Control:** Track prompt changes and performance
5. **Transparency:** Users see exactly what the AI is being asked
6. **Debugging:** Easier to identify prompt issues
7. **Reusability:** Share successful prompts across tenants

## 📋 Implementation Plan

### Phase 1: Core Infrastructure
- [ ] Create `ai_prompts` table and model
- [ ] Build `AIPromptService` with render/validate methods
- [ ] Seed default system prompts from existing code
- [ ] Write tests for template rendering

### Phase 2: Basic UI
- [ ] Create prompt library page (read-only view)
- [ ] List all prompts with categories
- [ ] View prompt details modal
- [ ] Search and filter

### Phase 3: Editing & Management
- [ ] Create/edit prompt form
- [ ] Variable detection and configuration
- [ ] Template validation
- [ ] Tenant override system

### Phase 4: Advanced Features
- [ ] Prompt preview with sample data
- [ ] Live AI testing
- [ ] Usage analytics
- [ ] Version history
- [ ] Import/export prompts

### Phase 5: Service Integration
- [ ] Update SEOContentGenerator to use prompt service
- [ ] Update AIGenerationService to use prompt service
- [ ] Migrate all hardcoded prompts
- [ ] Remove old prompt code

## 🔒 Security Considerations

- Only global admin and tenant admin can edit prompts
- System prompts can't be deleted (only overridden per-tenant)
- Audit all prompt changes
- Validate template syntax before saving
- Prevent prompt injection attacks (sanitize variable inputs)

## 📊 Analytics to Track

- Most used prompts
- Success rate (content generated vs. failed)
- Average tokens per prompt
- Cost per prompt (based on model and tokens)
- Tenant customization rate

---

**Next Steps:** Review this design and decide which phase to implement first!
