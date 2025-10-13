# Content Broadcaster - Quick Demo Setup

## ✅ What's Ready

You now have a **working demo** of AI-powered content generation! Here's what's been implemented:

### New Components

1. **ContentOrchestratorService** - Coordinates the AI workflow
2. **Planning Routes** - API endpoints for content plan management
3. **Demo Script** - Automated demonstration script
4. **Demo Guide** - Comprehensive documentation

### Workflow

```
Content Idea → AI Processing → Draft Content → Review → Publish
     ↓              ↓              ↓             ↓         ↓
  Create Plan   Research &     ContentItem   Approve   Schedule
               Generate        (Draft)
```

---

## 🚀 Run the Demo

### 1. Prerequisites

**Add OpenAI API Key:**
```bash
# Login to the app
http://localhost:8000

# Go to: Administration → Secrets Management
# Add new secret:
#   Key: openai_api_key
#   Value: sk-...your-key...
```

### 2. Start Server

```bash
# Start database
docker start terra_automation_platform_dev_db

# Run migrations (if needed)
python manage_db.py upgrade

# Start server
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Run Demo Script

```bash
python demo_content_generation.py
```

**The script will:**
- ✅ Create a content plan for "The Future of AI in Software Development"
- ✅ Process it with AI (takes 30-60 seconds)
- ✅ Display the generated blog post draft
- ✅ Show you the content item ID for further workflow

---

## 📋 API Endpoints

### Create Content Plan
```bash
POST /features/content-broadcaster/planning/create

{
  "title": "Your Content Idea Here",
  "tone": "professional",
  "target_channels": ["wordpress", "linkedin"]
}
```

### Process with AI
```bash
POST /features/content-broadcaster/planning/{plan_id}/process

{
  "use_research": false
}
```

### View Generated Content
```bash
GET /features/content-broadcaster/api/{content_item_id}
```

---

## 🎯 What to Show Your Colleague

1. **Show the API workflow:**
   - Create a plan with an interesting topic
   - Process it and watch the AI generate content
   - Display the full blog post

2. **Demonstrate the quality:**
   - SEO-optimized structure
   - Professional writing style
   - Proper Markdown formatting
   - 1500-3000 word articles

3. **Explain the flow:**
   - Content idea → AI generation → Draft
   - Then: Review → Approve → Schedule → Publish
   - Multi-tenant isolation
   - Audit trail

4. **Show what's coming:**
   - Competitor research integration
   - SEO scoring and validation
   - Iterative refinement
   - Background worker (Celery)
   - Full UI for content planning

---

## 📖 Full Documentation

See **AI_CONTENT_DEMO.md** for:
- Complete API reference
- Step-by-step workflow
- Troubleshooting guide
- Demo scenarios
- Database queries

---

## 🔧 Current Status

### ✅ Implemented
- Content planning service (CRUD)
- AI research service (ready)
- AI generation service (working)
- Content orchestrator (coordinates workflow)
- Planning API routes
- ContentPlan ↔ ContentItem integration
- Demo script and documentation

### ⏳ Coming Next
- Celery background worker
- Web scraping for research
- SEO validation service
- Iterative refinement loop
- Planning UI (HTMX + Tabulator)

---

## 💡 Quick Tips

**API Testing:**
```bash
# Login first
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin@example.com&password=admin123" \
  -c cookies.txt

# Then use cookies.txt for authenticated requests
curl -X POST http://localhost:8000/features/content-broadcaster/planning/create \
  -b cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"title": "AI in 2025", "tone": "professional"}'
```

**Check Status:**
```bash
# View plan status
GET /features/content-broadcaster/planning/{plan_id}

# View all plans
GET /features/content-broadcaster/planning/list
```

**Retry Failed Plans:**
```bash
POST /features/content-broadcaster/planning/{plan_id}/retry
```

---

## 🎉 Success Criteria

After running the demo, you should see:

✅ Content plan created with status "planned"
✅ AI processing completes in 30-60 seconds
✅ Status changes to "draft_ready"
✅ ContentItem created with full blog post
✅ Content is 1500+ words, well-formatted
✅ Metadata shows generation details

---

**Ready to impress your colleague! 🚀**
