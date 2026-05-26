-- Seed data for development
-- Run this after migration

-- Create default feature flags
INSERT INTO feature_flags (key, enabled, description) VALUES
    ('email_outreach_enabled', true, 'Enable email outreach capabilities'),
    ('calls_enabled', false, 'Enable phone call capabilities'),
    ('lead_extraction_apollo_enabled', true, 'Enable Apollo.io lead extraction'),
    ('lead_extraction_web_enabled', true, 'Enable web scraping for leads'),
    ('lead_extraction_csv_enabled', true, 'Enable CSV import for leads'),
    ('ai_lead_scoring_enabled', true, 'Enable AI-powered lead scoring'),
    ('ai_email_drafting_enabled', true, 'Enable AI email drafting'),
    ('ai_call_script_enabled', true, 'Enable AI call script generation')
ON CONFLICT (key) DO NOTHING;
