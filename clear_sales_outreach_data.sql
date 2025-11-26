-- Clear all Sales Outreach Prep data (cascades will handle related records)
-- Run this to start fresh for testing

-- Disable foreign key checks temporarily (PostgreSQL)
BEGIN;

-- Delete all prospects (this will cascade delete related records)
DELETE FROM prospects WHERE tenant_id = 'global';

-- Delete all campaign_companies associations
DELETE FROM campaign_companies WHERE tenant_id = 'global';

-- Delete all companies (optional - only if you want to clear companies too)
-- DELETE FROM companies WHERE tenant_id = 'global';

-- Delete all campaigns (this will cascade delete prospects via campaign_id FK)
DELETE FROM campaigns WHERE tenant_id = 'global';

-- Re-enable foreign key checks
COMMIT;

-- Verify cleanup
SELECT 'Campaigns remaining:' as check_type, COUNT(*) as count FROM campaigns WHERE tenant_id = 'global'
UNION ALL
SELECT 'Prospects remaining:', COUNT(*) FROM prospects WHERE tenant_id = 'global'
UNION ALL
SELECT 'Companies remaining:', COUNT(*) FROM companies WHERE tenant_id = 'global';
