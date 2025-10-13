# 📄 Radium Community Platform — Product Requirements Document (PRD)

## Phase 1: Foundation & Membership
### Members
- Table: `members` (id, tenant_id, name, email, firm, bio, aum_range, location, specialties, tags, created_at, updated_at)
- Routes: CRUD + profile view (`/members/{id}`)
- Templates: member list, profile detail, edit modal
- Logic: tenant-scoped, uses JWT for identity

### Partners
- Table: `partners` (id, tenant_id, name, logo_url, description, offer, website, category, created_at)
- Routes: list, detail, admin CRUD
- Templates: partner grid + offer modal

### Dashboard
- Charts: total members, active partners, recent logins
- Sources: audit logs, users, members, partners

---

## Phase 2: Community & Networking
### Groups / Forums
- Tables: `groups`, `group_posts`, `group_comments`
- Fields: title, description, privacy, owner_id, tenant_id
- Templates: list view, post thread (HTMX partials)
- Access: members of same tenant

### Messaging
- Table: `messages` (id, sender_id, recipient_id, content, created_at, thread_id)
- Refresh: polling via HTMX (no websockets MVP)

### Events
- Table: `events` (id, title, start_date, location, url, category, description)
- Views: calendar, upcoming list

### Polls
- Tables: `polls`, `poll_options`, `poll_votes`
- Chart: results via ECharts bar chart

---

## Phase 3: Content & Learning
- `content` table: title, body_md, tags, category, author_id, published_at
- `podcasts` table: title, link, description, duration
- `videos` table: title, embed_url, description, category
- `news` table: headline, url, source, publish_date
- Engagement tracking: `content_engagement` (member_id, content_id, action)

---

## Phase 4: Opportunities & Careers
- `jobs`: title, firm, location, salary, visibility, contact_id
- `succession`: advisor_id, firm, aum, desired_outcome
- `spotlight`: member_id, title, feature_text, image_url

---

## Phase 5: Tools & Resources
- `valuation_inputs`: JSON field with calculator params
- `resources`: title, url, category, type
- `reviews`: rating, text, category, advisor_id

---

## Phase 6: Engagement & Gamification
- `badges`: name, description, icon
- `member_badges`: m2m link table
- `notifications`: title, message, type, read_status, member_id
- `feedback`: context, rating, comment, member_id

---

## Phase 7: Premium Features
- `mastermind_groups`: name, description, access_type, member_limit
- `marketplace`: service_name, provider_name, price, url, rating
- `ama_sessions`: title, guest_name, schedule_time, recording_url

---

## Cross-Cutting
- Every model inherits `AuditMixin`
- `tenant_id` enforced in all queries via `BaseService`
- JWT roles enforce access control
- Async Celery tasks for email + notifications
- ECharts used for all visual summaries
