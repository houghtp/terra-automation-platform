# 🗂 Radium Community Platform — Project Plan

### Overview
Sprint-level rollout plan for the Radium Financial Advisor Community Platform (multi-tenant FastAPI stack).

| **Sprint** | **Goal** | **Key Deliverables** | **Dependencies** |
|-------------|-----------|----------------------|------------------|
| Sprint 1 | Foundation & Authentication | Tenant-aware onboarding, member directory skeleton, partner scaffolding, dashboard. | `auth/`, `tenants/`, `users/` |
| Sprint 2 | Profiles & Partner Directory | Member CRUD, search/filter directory, partner profiles, role-based access. | Sprint 1 |
| Sprint 3 | Community & Events | Groups/forums, messaging, event calendar, polls/surveys. | Sprint 2 |
| Sprint 4 | Content & Learning Hub | Articles, podcasts, guides, news feed, engagement metrics. | Sprint 3 |
| Sprint 5 | Careers & Opportunities | Job board, succession marketplace, advisor spotlight. | Sprint 4 |
| Sprint 6 | Tools & Resources | Valuation calculator, transition checklist, reviews, compliance links. | Sprint 5 |
| Sprint 7 | Engagement & Gamification | Badges, notifications, feedback dashboard. | Sprint 6 |
| Sprint 8 | Premium Expansion | Mastermind groups, marketplace, AMA sessions. | Sprint 7 |
