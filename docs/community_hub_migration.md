# Community Hub Migration Guide

This guide outlines the steps to deploy the Community Content & Learning Hub (Phase 3) database changes across environments.

## 1. Prerequisites

- Confirm the `alembic` CLI is available (`pip install alembic` if missing).
- Ensure the application has been built with commit containing migration `9b3c1d0f3b5a_add_community_content_tables`.
- Verify database credentials in `alembic.ini` or environment variables for each target environment.

## 2. Migration Overview

The migration adds the following tables (all tenant-scoped):

- `community_content` – long-form articles/guides (markdown body).
- `community_podcasts` – podcast episode metadata.
- `community_videos` – embedded training videos.
- `community_news` – curated news links.
- `community_content_engagement` – tracks member interactions with published content.

Each table includes audit columns and indexes to support dashboard queries.

## 3. Execution Steps

### Local / Development

```bash
alembic upgrade head
```

- Validate tables exist: `\dt community_%` (PostgreSQL).
- Run the seeding script (see `seed_community_content.py`) to populate starter data.
- Smoke-test `/features/community/content` to confirm modals and tables load.

### Staging

1. Put the application into maintenance mode (if required by ops).
2. Deploy the build containing the migration.
3. Run:
   ```bash
   alembic upgrade head
   ```
4. Audit the schema:
   ```sql
   SELECT table_name FROM information_schema.tables
     WHERE table_name LIKE 'community_%';
   ```
5. Seed sample content for demo tenant (optional) using the management script.
6. Execute the Community Hub regression suite (service + API tests).

### Production

1. Communicate downtime window (migration is non-blocking but best done off-peak).
2. Backup the production database snapshot.
3. Run `alembic upgrade head`.
4. Monitor migration logs for errors; rollback using snapshot if necessary.
5. Post-deploy checks:
   - Visit `/features/community/content`.
   - Verify navigation, article creation, and engagement logging.
   - Tail logs for any SQL errors.

## 4. Rollback Plan

If rollback is required:

1. Restore database snapshot taken pre-migration.
2. Redeploy previous application version (without Content Hub features).
3. Communicate status to stakeholders.

> Note: Downgrade migration is available but dropping tables will remove content. Prefer snapshot restore in production.

## 5. Post-Deployment Tasks

- Run the seed script to populate tenant-specific learning materials.
- Update `docs/community_hub_progress.md` to reflect deployment status.
- Notify product leads that Community Hub V1 is ready for content entry.
