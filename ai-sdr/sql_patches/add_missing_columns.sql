-- One-time SQL patch to add missing columns to live Railway PostgreSQL DB
-- Run this in Railway's PostgreSQL console if init_db migrations are stuck
-- Safe to run multiple times (uses IF NOT EXISTS where supported)

-- sdr_profiles: Vapi + channel toggles
ALTER TABLE sdr_profiles ADD COLUMN IF NOT EXISTS vapi_credentials_encrypted TEXT;
ALTER TABLE sdr_profiles ADD COLUMN IF NOT EXISTS email_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE sdr_profiles ADD COLUMN IF NOT EXISTS linkedin_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE sdr_profiles ADD COLUMN IF NOT EXISTS vapi_enabled BOOLEAN DEFAULT FALSE;

-- vp_sales_profiles: outreach toggle + data source
ALTER TABLE vp_sales_profiles ADD COLUMN IF NOT EXISTS outreach_active BOOLEAN DEFAULT FALSE;
ALTER TABLE vp_sales_profiles ADD COLUMN IF NOT EXISTS target_titles TEXT;
ALTER TABLE vp_sales_profiles ADD COLUMN IF NOT EXISTS target_business_types TEXT;
ALTER TABLE vp_sales_profiles ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'web_scraping';
ALTER TABLE vp_sales_profiles ADD COLUMN IF NOT EXISTS data_source_config JSON;
ALTER TABLE vp_sales_profiles ADD COLUMN IF NOT EXISTS manual_upload_done BOOLEAN DEFAULT FALSE;

-- email_messages: direction column
ALTER TABLE email_messages ADD COLUMN IF NOT EXISTS direction VARCHAR(20) DEFAULT 'outbound';
