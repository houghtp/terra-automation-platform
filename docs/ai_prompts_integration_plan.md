# AI Prompts Integration Plan

## Current State

### ✅ Completed
- **Database**: `ai_prompts` table with tenant override support
- **Service**: `AIPromptService` with Jinja2 rendering and variable injection
- **Seeded Prompts**: 4 default prompts from existing hardcoded strings
- **UI**: Management interface for editing prompts

### ❌ Not Yet Integrated
The content generation services still use **hardcoded prompt strings** instead of fetching from the database.

---

## Where Prompts Are Hardcoded

### 1. Blog Post Generation
**File**: `app/features/business_automations/content_broadcaster/services/ai_generation_service.py`
**Method**: `generate_blog_post()` (lines 72-197)
**Prompt Key**: `seo_blog_generation`

**Current Code**:
```python
blog_prompt = f"""
Title: {title}

You are an **expert SEO blog writer**...
{context_section}
...
"""
```

**Variables Used**:
- `title` (required)
- `description` (optional)
- `target_audience` (optional)
- `keywords` (optional)
- `seo_analysis` (optional)
- `previous_content` (optional)
- `validation_feedback` (optional)
- `tone` (optional, default: "professional")

---

### 2. Channel Variant Generation
**File**: `app/features/business_automations/content_broadcaster/services/ai_generation_service.py`
**Method**: `generate_variants_per_channel()` (lines 200-300)
**Prompt Keys**:
- `channel_variant_twitter`
- `channel_variant_linkedin`
- `channel_variant_wordpress`

**Current Code**:
```python
variant_prompt = f"""
You are a content adaptation specialist...
Original Content: {title}
{content[:2000]}
Channel: {channel.upper()}
...
"""
```

**Variables Used**:
- `title` (required)
- `content` (required, truncated to 2000 chars)
- `channel` (required)
- `max_chars` (from constraints)
- `format` (from constraints)
- `tone` (from constraints)
- `instructions` (from constraints)

---

### 3. SEO Content Generator (Duplicate)
**File**: `app/features/core/connectors/seo_content_generator.py`
**Method**: `_generate_initial_content()` (lines 425-490)
**Prompt Key**: `seo_blog_generation` (same as #1)

This is a **duplicate** of the blog generation prompt in `ai_generation_service.py`.

---

## Integration Strategy

### Phase 1: Inject AIPromptService (Recommended First Step)

**Goal**: Make services use database prompts instead of hardcoded strings

**Changes Needed**:

#### 1.1 Update `AIGenerationService.__init__()`
```python
class AIGenerationService:
    def __init__(self, db_session: AsyncSession, tenant_id: str):
        self.db = db_session
        self.tenant_id = tenant_id
        self.prompt_service = AIPromptService(db_session)
```

#### 1.2 Update `generate_blog_post()`
```python
async def generate_blog_post(
    self,
    title: str,
    openai_api_key: str,
    description: Optional[str] = None,
    ...
) -> str:
    # Fetch prompt from database with tenant override support
    prompt_template = await self.prompt_service.get_prompt_template(
        prompt_key="seo_blog_generation",
        tenant_id=self.tenant_id
    )

    # Prepare variables for Jinja2 rendering
    variables = {
        "title": title,
        "description": description or "",
        "target_audience": target_audience or "general readers",
        "keywords": ", ".join(keywords) if keywords else "",
        "seo_analysis": seo_analysis or "",
        "previous_content": previous_content or "No previous version",
        "validation_feedback": validation_feedback or "No feedback yet",
        "tone": tone
    }

    # Render prompt with variables
    blog_prompt = await self.prompt_service.render_prompt(
        prompt_key="seo_blog_generation",
        variables=variables,
        tenant_id=self.tenant_id
    )

    # Rest of AI call remains the same
    client = AsyncOpenAI(api_key=openai_api_key)
    response = await client.chat.completions.create(...)
```

#### 1.3 Update `generate_variants_per_channel()`
```python
async def generate_variants_per_channel(
    self,
    content: str,
    title: str,
    channels: List[str],
    openai_api_key: str
) -> List[Dict[str, Any]]:
    variants = []

    for channel in channels:
        # Fetch channel-specific prompt template
        prompt_key = f"channel_variant_{channel}"

        try:
            prompt_template = await self.prompt_service.get_prompt_template(
                prompt_key=prompt_key,
                tenant_id=self.tenant_id
            )
        except Exception:
            # Fallback to generic if channel-specific not found
            logger.warning(f"No prompt found for {channel}, using default")
            prompt_template = await self.prompt_service.get_prompt_template(
                prompt_key="channel_variant_generic",
                tenant_id=self.tenant_id
            )

        # Get channel constraints (can move these to prompt metadata later)
        constraints = self._get_channel_constraints(channel)

        # Render prompt
        variables = {
            "title": title,
            "content": content[:2000],
            "channel": channel.upper(),
            "max_chars": constraints["max_chars"] or "No limit",
            "format": constraints["format"],
            "tone": constraints["tone"],
            "instructions": constraints["instructions"]
        }

        variant_prompt = await self.prompt_service.render_prompt(
            prompt_key=prompt_key,
            variables=variables,
            tenant_id=self.tenant_id
        )

        # AI call remains the same
        ...
```

---

### Phase 2: Track Usage & Success

**Goal**: Automatically update usage statistics when prompts are used

**Implementation**:

Add tracking to `AIPromptService.render_prompt()`:
```python
async def render_prompt(
    self,
    prompt_key: str,
    variables: Dict[str, Any],
    tenant_id: Optional[str] = None,
    track_usage: bool = True
) -> str:
    # Existing rendering logic
    rendered = self.template.render(**variables)

    # Track usage automatically
    if track_usage:
        await self.track_usage(
            prompt_key=prompt_key,
            tenant_id=tenant_id,
            success=True  # We'll update this based on AI response
        )

    return rendered
```

Add success/failure tracking after AI calls:
```python
# In AIGenerationService
try:
    response = await client.chat.completions.create(...)

    # Track success
    await self.prompt_service.track_usage(
        prompt_key="seo_blog_generation",
        tenant_id=self.tenant_id,
        success=True
    )

    return response.choices[0].message.content

except Exception as e:
    # Track failure
    await self.prompt_service.track_usage(
        prompt_key="seo_blog_generation",
        tenant_id=self.tenant_id,
        success=False
    )
    raise
```

---

### Phase 3: UI Enhancements (Future)

**Goal**: Allow users to test prompts before deploying

**Features**:
- **Prompt Preview**: Show rendered prompt with sample variables
- **Test Generation**: Generate sample content using the prompt
- **A/B Testing**: Compare multiple prompt versions
- **Version History**: Track changes to prompts over time

---

## Migration Path

### Step 1: Inject Service (No Behavior Change)
1. Add `db_session` and `tenant_id` to service constructors
2. Instantiate `AIPromptService` in `__init__`
3. **Don't change prompt logic yet** - just make service available

### Step 2: Replace One Prompt at a Time
1. Start with `seo_blog_generation` (most used)
2. Update method to fetch from database
3. Test thoroughly with existing seeded prompt
4. Verify output quality matches hardcoded version

### Step 3: Replace Remaining Prompts
1. Channel variants (twitter, linkedin, wordpress)
2. Any other prompt types discovered

### Step 4: Add Usage Tracking
1. Track usage count on every render
2. Track success/failure after AI response
3. Monitor statistics in UI

### Step 5: Enable Tenant Customization
1. Global admins can create tenant-specific overrides
2. Tenants see system prompts + their custom ones
3. Tenant overrides take precedence

---

## Benefits After Integration

### For Users
- ✅ **Customize prompts** without code changes
- ✅ **Test different prompt styles** for better output
- ✅ **See usage statistics** and success rates
- ✅ **Tenant-specific prompts** for brand voice

### For Developers
- ✅ **No more hardcoded strings** scattered in code
- ✅ **Easy prompt versioning** and rollback
- ✅ **Track what works** through usage data
- ✅ **A/B test prompts** without deployment

### For System
- ✅ **Centralized prompt management**
- ✅ **Audit trail** of prompt changes
- ✅ **Variable validation** prevents errors
- ✅ **Performance metrics** per prompt

---

## Variable Injection - How It Works

### Example: Blog Generation Prompt

**Database Prompt Template** (uses Jinja2 syntax):
```jinja2
Title: {{ title }}

You are an **expert SEO blog writer**. Your task is to produce a complete blog post about "{{ title }}".

{% if description %}
Context: {{ description }}
{% endif %}

{% if target_audience %}
Target Audience: {{ target_audience }}
{% endif %}

{% if keywords %}
Focus Keywords: {{ keywords }}
{% endif %}

{% if seo_analysis %}
### SEO Analysis (Competitor Research):
{{ seo_analysis }}
{% endif %}

{% if previous_content %}
### Previous Blog Post:
{{ previous_content }}
{% else %}
This is the first draft.
{% endif %}

{% if validation_feedback %}
### Validation Feedback:
{{ validation_feedback }}
{% else %}
No feedback yet. Optimize based on SEO best practices.
{% endif %}

Use a {{ tone }} tone.
```

**Variables Passed from Code**:
```python
variables = {
    "title": "The Future of AI in Software Development",
    "description": "Explore how AI is transforming...",
    "target_audience": "Software developers",
    "keywords": "AI, software development, automation",
    "seo_analysis": "Competitor analysis shows...",
    "previous_content": None,  # First iteration
    "validation_feedback": None,  # No feedback yet
    "tone": "professional"
}
```

**Rendered Output** (sent to AI):
```
Title: The Future of AI in Software Development

You are an **expert SEO blog writer**. Your task is to produce a complete blog post about "The Future of AI in Software Development".

Context: Explore how AI is transforming...

Target Audience: Software developers

Focus Keywords: AI, software development, automation

### SEO Analysis (Competitor Research):
Competitor analysis shows...

This is the first draft.

No feedback yet. Optimize based on SEO best practices.

Use a professional tone.
```

---

## Testing the Integration

### Unit Tests
```python
async def test_blog_generation_uses_database_prompt():
    service = AIGenerationService(db, tenant_id="test-tenant")

    # Mock the AI response
    with patch.object(service, '_call_openai') as mock_ai:
        mock_ai.return_value = "Generated blog content..."

        result = await service.generate_blog_post(
            title="Test Title",
            openai_api_key="test-key"
        )

        # Verify prompt was fetched from database
        assert mock_ai.called
        prompt_used = mock_ai.call_args[0][0]
        assert "Test Title" in prompt_used
        assert "expert SEO blog writer" in prompt_used
```

### Integration Tests
```python
async def test_prompt_override_per_tenant():
    # Create tenant-specific override
    await prompt_service.create_prompt(
        prompt_key="seo_blog_generation",
        name="Custom Blog Prompt",
        template_content="Custom prompt for {{title}}",
        tenant_id="tenant-123"
    )

    # Generate content for that tenant
    service = AIGenerationService(db, tenant_id="tenant-123")
    result = await service.generate_blog_post(
        title="Test",
        openai_api_key="key"
    )

    # Should use tenant override, not system default
    # Verify by checking the rendered prompt
```

---

## Rollout Checklist

- [ ] Update service constructors to accept `db_session` and `tenant_id`
- [ ] Add `AIPromptService` initialization in services
- [ ] Replace hardcoded blog generation prompt
- [ ] Replace channel variant prompts
- [ ] Add usage tracking
- [ ] Test with existing seeded prompts
- [ ] Verify output quality unchanged
- [ ] Document variable requirements for each prompt
- [ ] Create admin documentation for prompt editing
- [ ] Enable tenant override functionality
- [ ] Monitor usage statistics in UI

---

## Summary

**Current**: Prompts are hardcoded strings with `f"{variable}"` interpolation
**After Integration**: Prompts are Jinja2 templates stored in database with tenant override support

**Key Changes**:
1. Services fetch prompts from database instead of hardcoding
2. Variables passed to Jinja2 renderer instead of f-strings
3. Usage tracked automatically
4. Tenants can customize prompts without code changes

**Next Step**: Start with Phase 1 - inject `AIPromptService` into `AIGenerationService`
