# 🧱 Radium Community Platform — Product Requirements Plan (PRP)

## Architecture Alignment
- Backend: FastAPI (async, multi-tenant, JWT auth)
- DB: PostgreSQL (JSONB, temporal tables)
- Frontend: HTMX + Alpine.js + Tabulator + ECharts
- Infra: Dockerized Ubuntu appliance

## Phases (Sprints)
1. **Foundation & Membership**
   - Slices: `members/`, `partners/`, `dashboard/`, `auth/`
   - Deliverables: member registration, profiles, partner directory, dashboard metrics.
2. **Community & Networking**
   - Slices: `groups/`, `messages/`, `events/`, `polls/`
   - Deliverables: private groups, chat, event calendar, surveys.
3. **Content & Learning**
   - Slices: `content/`, `podcasts/`, `videos/`, `news/`
   - Deliverables: content hub with analytics.
4. **Opportunities & Careers**
   - Slices: `jobs/`, `succession/`, `spotlight/`
   - Deliverables: job board, succession planning, spotlight features.
5. **Tools & Resources**
   - Slices: `tools/`, `resources/`
   - Deliverables: calculators, checklists, reviews, compliance links.
6. **Engagement & Growth**
   - Slices: `badges/`, `notifications/`, `feedback/`
   - Deliverables: gamification, alerts, analytics.
7. **Premium Expansion**
   - Slices: `mastermind/`, `marketplace/`
   - Deliverables: premium groups, service marketplace, AMA sessions.

## Shared Components
- Multi-tenant isolation via BaseService
- Role-based access: global_admin / member / partner
- SMTP + Celery for async email & background jobs
- Dashboard charts via ECharts
