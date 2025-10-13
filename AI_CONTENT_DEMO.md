# AI Content Generation Demo Guide

## 🎯 Overview

This demo showcases the **AI-driven content generation workflow** in the Content Broadcaster feature:

1. **Create Content Plan** - Submit a content idea/topic
2. **AI Processing** - Automated research and content generation
3. **Draft Review** - Review AI-generated draft content
4. **Approval & Publishing** - Standard content workflow

---

## 🚀 Quick Start

### Prerequisites

1. **OpenAI API Key** configured in Secrets Management:
   - Go to: `http://localhost:8000/features/administration/secrets`
   - Add key: `openai_api_key`
   - Value: Your OpenAI API key

2. **Server running**:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```

3. **Database initialized** with latest migrations

### Option 1: Run Demo Script (Automated)

```bash
# Make script executable
chmod +x demo_content_generation.py

# Run the demo
python demo_content_generation.py
```

The script will:
- ✅ Login automatically
- ✅ Create a sample content plan
- ✅ Process it with AI
- ✅ Display the generated draft

### Option 2: Manual Testing (API)

Use the API endpoints directly with Postman, curl, or httpx.

---

## 📋 Step-by-Step Workflow

### Step 1: Create a Content Plan

**Endpoint:** `POST /features/content-broadcaster/planning/create`

**Request Body:**
```json
{
  "title": "The Future of AI in Software Development",
  "description": "Explore how AI is transforming software development practices",
  "target_channels": ["wordpress", "linkedin"],
  "target_audience": "Software developers and tech leaders",
  "tone": "professional",
  "seo_keywords": ["AI", "software development", "automation"],
  "competitor_urls": [],
  "min_seo_score": 90,
  "max_iterations": 2
}
```

**Response:**
```json
{
  "success": true,
  "plan_id": "abc123...",
  "title": "The Future of AI in Software Development",
  "status": "planned",
  "message": "Content plan created successfully..."
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/features/content-broadcaster/planning/create \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "title": "The Future of AI in Software Development",
    "tone": "professional",
    "target_channels": ["wordpress"]
  }'
```

---

### Step 2: Process Content Plan with AI

**Endpoint:** `POST /features/content-broadcaster/planning/{plan_id}/process`

**Request Body:**
```json
{
  "use_research": false
}
```

**Note:** Set `use_research: true` if you have a web scraping API key (ScrapingBee) configured in Secrets.

**Response:**
```json
{
  "success": true,
  "plan_id": "abc123...",
  "content_item_id": "content_abc123...",
  "status": "draft_ready",
  "title": "The Future of AI in Software Development",
  "content_length": 3500,
  "research_sources": 0,
  "message": "Content generated successfully and saved as draft"
}
```

**What Happens:**
1. Plan status → `researching` (if research enabled)
2. AI analyzes competitor content (if URLs provided)
3. Plan status → `generating`
4. OpenAI generates SEO-optimized blog post
5. Plan status → `draft_ready`
6. ContentItem created with draft content
7. Plan linked to ContentItem

**Processing Time:** 30-60 seconds (depending on content complexity)

---

### Step 3: View Generated Content

**Endpoint:** `GET /features/content-broadcaster/api/{content_item_id}`

**Response:**
```json
{
  "id": "content_abc123...",
  "tenant_id": "tenant_xyz",
  "title": "The Future of AI in Software Development",
  "body": "# Introduction\n\nArtificial Intelligence (AI) is...",
  "state": "draft",
  "content_metadata": {
    "generated_from_plan": "abc123...",
    "research_sources": 0,
    "tone": "professional"
  },
  "tags": ["AI", "software development", "automation"],
  "created_at": "2025-10-11T10:30:00",
  "created_by": "user123"
}
```

---

### Step 4: Standard Content Workflow

Once you have the generated draft, follow the standard content workflow:

1. **Review Draft** - Edit if needed using ContentItem update endpoint
2. **Submit for Review** - `POST /api/{content_id}/submit`
3. **Approve Content** - `POST /api/{content_id}/approve`
4. **Schedule Publishing** - `POST /api/{content_id}/schedule`

---

## 🔧 API Endpoints Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/planning/create` | Create new content plan |
| GET | `/planning/list` | List all content plans |
| GET | `/planning/{id}` | Get plan details |
| POST | `/planning/{id}/process` | **Process with AI** |
| POST | `/planning/{id}/retry` | Retry failed plan |
| DELETE | `/planning/{id}` | Archive plan |

---

## 🎨 What Gets Generated

### Content Structure

The AI generates a complete blog post with:

- **SEO-Optimized Title** (from your plan)
- **Introduction** - Engaging opening paragraph
- **Body Sections** - Well-structured content with headings
- **Key Points** - Bullet lists and emphasis
- **Conclusion** - Strong closing with call-to-action
- **Metadata** - SEO keywords, tags, and formatting

### Content Quality

- ✅ Professional tone (or custom tone you specify)
- ✅ SEO-optimized keywords
- ✅ Proper Markdown formatting
- ✅ Engaging and readable
- ✅ 1500-3000+ words (depending on topic)

---

## 🔍 Monitoring & Debugging

### Check Plan Status

```bash
GET /planning/{plan_id}
```

Status flow:
- `planned` → Ready for processing
- `researching` → Analyzing competitors
- `generating` → Creating content
- `draft_ready` → ✅ Content generated successfully
- `failed` → ❌ Check `error_log` field

### Common Issues

**1. "OpenAI API key not configured"**
- Solution: Add `openai_api_key` in Secrets Management
- Go to: `/features/administration/secrets`

**2. Processing times out**
- Increase timeout in client (120+ seconds)
- Check OpenAI API rate limits

**3. Plan stuck in 'generating' state**
- Check server logs for errors
- Verify OpenAI API key is valid
- Retry with `/planning/{id}/retry`

---

## 📊 Database State

### Tables Involved

1. **content_plans** - Stores content ideas and AI metadata
2. **content_items** - Stores generated drafts and published content
3. **secrets** - Stores API keys securely

### Check Data

```sql
-- View content plans
SELECT id, title, status, created_at FROM content_plans ORDER BY created_at DESC;

-- View generated content
SELECT id, title, state, length(body) as content_length
FROM content_items WHERE id LIKE 'content_%';

-- Check plan-content linkage
SELECT
  cp.title as plan_title,
  cp.status as plan_status,
  ci.state as content_state,
  length(ci.body) as content_length
FROM content_plans cp
LEFT JOIN content_items ci ON cp.generated_content_item_id = ci.id;
```

---

## 🎯 Demo Scenarios

### Scenario 1: Simple Blog Post

```json
{
  "title": "10 Tips for Better Code Reviews",
  "tone": "casual",
  "target_audience": "Junior developers"
}
```

### Scenario 2: Technical Deep-Dive

```json
{
  "title": "Understanding Kubernetes Pod Networking",
  "tone": "technical",
  "seo_keywords": ["kubernetes", "networking", "pods", "containers"],
  "target_audience": "DevOps engineers"
}
```

### Scenario 3: Marketing Content

```json
{
  "title": "Why Your Startup Needs CI/CD in 2025",
  "tone": "persuasive",
  "target_channels": ["linkedin", "medium"],
  "target_audience": "Startup founders and CTOs"
}
```

---

## 🚀 Next Steps

### For Demo

1. ✅ Run the demo script
2. ✅ Show generated content to colleague
3. ✅ Demonstrate edit → approve → schedule workflow

### For Production

1. ⏳ Implement Celery worker for background processing
2. ⏳ Add web scraping for competitor research
3. ⏳ Implement SEO validation and scoring
4. ⏳ Add iterative refinement loop
5. ⏳ Build UI for content planning

---

## 📝 Notes

- **Synchronous Processing:** Currently processes synchronously (blocks until complete). In production, this should be a background Celery task.
- **Research Phase:** Disabled by default. Enable with `use_research: true` if you have a scraping API key.
- **Cost:** Each generation uses OpenAI API (GPT-4). Estimated cost: $0.10-0.30 per blog post.
- **Multi-Tenant:** All content is properly isolated by tenant_id.

---

## 🤝 Support

Issues or questions? Check:
- Server logs: Look for "Content generation workflow" messages
- Plan status: Use `GET /planning/{id}` to see current state
- Error logs: Check `content_plans.error_log` field for failures

---

**Happy Content Creating! 🎉**
