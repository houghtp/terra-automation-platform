-- Backfill missing CIS metadata for Section 5 checks
-- Run this when the database is up to update existing scan results

\echo 'Starting metadata backfill for Section 5 checks...'

-- Update 5.1.2.1
UPDATE cspm_compliance_results
SET
    title = 'Ensure ''Per-user MFA'' is disabled',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.1 Identity',
    recommendation_id = '5.1.2.1'
WHERE check_id LIKE '5.1.2.1_%' AND title IS NULL;

-- Update 5.1.2.3
UPDATE cspm_compliance_results
SET
    title = 'Ensure ''Restrict non-admin users from creating tenants'' is set to ''Yes''',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.1 Identity',
    recommendation_id = '5.1.2.3'
WHERE check_id LIKE '5.1.2.3_%' AND title IS NULL;

-- Update 5.1.2.4
UPDATE cspm_compliance_results
SET
    title = 'Ensure access to the Entra admin center is restricted',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.1 Identity',
    recommendation_id = '5.1.2.4'
WHERE check_id LIKE '5.1.2.4_%' AND title IS NULL;

-- Update 5.1.3.1
UPDATE cspm_compliance_results
SET
    title = 'Ensure a dynamic group for guest users is created',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.1 Identity',
    recommendation_id = '5.1.3.1'
WHERE check_id LIKE '5.1.3.1_%' AND title IS NULL;

-- Update 5.1.5.2
UPDATE cspm_compliance_results
SET
    title = 'Ensure the admin consent workflow is enabled',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.1 Identity',
    recommendation_id = '5.1.5.2'
WHERE check_id LIKE '5.1.5.2_%' AND title IS NULL;

-- Update 5.1.6.2
UPDATE cspm_compliance_results
SET
    title = 'Ensure that guest user access is restricted',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.1 Identity',
    recommendation_id = '5.1.6.2'
WHERE check_id LIKE '5.1.6.2_%' AND title IS NULL;

-- Update 5.1.8.1
UPDATE cspm_compliance_results
SET
    title = 'Ensure that password hash sync is enabled for hybrid deployments',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.1 Identity',
    recommendation_id = '5.1.8.1'
WHERE check_id LIKE '5.1.8.1_%' AND title IS NULL;

-- Update all 5.2.2.* checks (Conditional Access)
UPDATE cspm_compliance_results
SET
    title = 'Ensure multifactor authentication is enabled for all users',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.1'
WHERE check_id LIKE '5.2.2.1_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure multifactor authentication is enabled for all Azure Management',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.2'
WHERE check_id LIKE '5.2.2.2_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Enable conditional access policies to block legacy authentication',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.3'
WHERE check_id LIKE '5.2.2.3_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure sign-in frequency is enabled and browser sessions are not persistent',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.4'
WHERE check_id LIKE '5.2.2.4_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Enable Identity Protection user risk policies',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.6'
WHERE check_id LIKE '5.2.2.6_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Enable Identity Protection sign-in risk policies',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.7'
WHERE check_id LIKE '5.2.2.7_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure a managed device is required for administrator access',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.9'
WHERE check_id LIKE '5.2.2.9_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure a managed device is required to register or join devices',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.10'
WHERE check_id LIKE '5.2.2.10_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure sign-in frequency for Intune enrollment is set to eight hours',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.11'
WHERE check_id LIKE '5.2.2.11_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure the device code sign-in flow is blocked',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Conditional Access',
    recommendation_id = '5.2.2.12'
WHERE check_id LIKE '5.2.2.12_%' AND title IS NULL;

-- Update all 5.2.3.* checks (Authentication methods)
UPDATE cspm_compliance_results
SET
    title = 'Ensure Microsoft Authenticator is configured to protect against MFA fatigue',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Authentication methods',
    recommendation_id = '5.2.3.1'
WHERE check_id LIKE '5.2.3.1_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure custom banned passwords lists are used',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Authentication methods',
    recommendation_id = '5.2.3.2'
WHERE check_id LIKE '5.2.3.2_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure password protection is enabled for on-premises Active Directory',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Authentication methods',
    recommendation_id = '5.2.3.3'
WHERE check_id LIKE '5.2.3.3_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure all member users are ''MFA capable''',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Authentication methods',
    recommendation_id = '5.2.3.4'
WHERE check_id LIKE '5.2.3.4_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure weak authentication methods are disabled',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Authentication methods',
    recommendation_id = '5.2.3.5'
WHERE check_id LIKE '5.2.3.5_%' AND title IS NULL;

UPDATE cspm_compliance_results
SET
    title = 'Ensure system-preferred multifactor authentication is enabled',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Authentication methods',
    recommendation_id = '5.2.3.6'
WHERE check_id LIKE '5.2.3.6_%' AND title IS NULL;

-- Update 5.2.4.1
UPDATE cspm_compliance_results
SET
    title = 'Ensure ''Self service password reset enabled'' is set to ''All''',
    level = 'L1',
    section = '5 Microsoft Entra admin center',
    subsection = '5.2 Password Protection',
    recommendation_id = '5.2.4.1'
WHERE check_id LIKE '5.2.4.1_%' AND title IS NULL;

\echo 'Metadata backfill completed!'

-- Show summary
SELECT
    COUNT(*) as total_section5_results,
    COUNT(title) as with_metadata,
    COUNT(*) - COUNT(title) as still_missing
FROM cspm_compliance_results
WHERE check_id LIKE '5.%';
