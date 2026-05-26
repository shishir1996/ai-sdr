-- AI SDR Platform - Supabase Initial Migration
-- This migration creates all tables with RLS policies for multi-tenant isolation

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ORGANIZATIONS
-- ============================================================
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    google_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_org_id ON users(org_id);

-- ============================================================
-- LEADS
-- ============================================================
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    title VARCHAR(255),
    company VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    linkedin_url VARCHAR(500),
    website VARCHAR(500),
    industry VARCHAR(255),
    location VARCHAR(255),
    city VARCHAR(255),
    state VARCHAR(255),
    country VARCHAR(100),
    postal_code VARCHAR(20),
    company_size VARCHAR(50),
    revenue VARCHAR(50),
    products_services TEXT,
    score INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'new',
    source VARCHAR(50),
    notes TEXT,
    custom_fields TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_leads_org_id ON leads(org_id);
CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_source ON leads(source);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_created_at ON leads(created_at);
CREATE INDEX idx_leads_org_score ON leads(org_id, score DESC);
CREATE INDEX idx_leads_org_status ON leads(org_id, status);

-- ============================================================
-- CAMPAIGNS
-- ============================================================
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    sdr_profile_id VARCHAR,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    ai_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_campaigns_org_id ON campaigns(org_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
CREATE INDEX idx_campaigns_sdr_profile ON campaigns(sdr_profile_id);

-- ============================================================
-- CAMPAIGN STEPS
-- ============================================================
CREATE TABLE campaign_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    step_order INTEGER NOT NULL,
    channel VARCHAR(50) NOT NULL,
    template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    call_script_id UUID REFERENCES call_scripts(id) ON DELETE SET NULL,
    delay_days INTEGER DEFAULT 0,
    conditions JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_campaign_steps_campaign ON campaign_steps(campaign_id);

-- ============================================================
-- EMAIL TEMPLATES
-- ============================================================
CREATE TABLE email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    variables JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_email_templates_org ON email_templates(org_id);

-- ============================================================
-- EMAIL MESSAGES
-- ============================================================
CREATE TABLE email_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    template_id UUID REFERENCES email_templates(id) ON DELETE SET NULL,
    from_email VARCHAR(255) NOT NULL,
    to_email VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    bounced_at TIMESTAMPTZ,
    message_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_email_messages_org ON email_messages(org_id);
CREATE INDEX idx_email_messages_lead ON email_messages(lead_id);
CREATE INDEX idx_email_messages_status ON email_messages(status);
CREATE INDEX idx_email_messages_sent ON email_messages(sent_at);

-- ============================================================
-- CALL SCRIPTS
-- ============================================================
CREATE TABLE call_scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_call_scripts_org ON call_scripts(org_id);

-- ============================================================
-- CALL LOGS
-- ============================================================
CREATE TABLE call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    script_id UUID REFERENCES call_scripts(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'scheduled',
    duration_seconds INTEGER,
    recording_url VARCHAR(500),
    transcript TEXT,
    outcome VARCHAR(50),
    called_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_call_logs_org ON call_logs(org_id);
CREATE INDEX idx_call_logs_lead ON call_logs(lead_id);

-- ============================================================
-- PIPELINES
-- ============================================================
CREATE TABLE pipelines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_pipelines_org ON pipelines(org_id);

-- ============================================================
-- DEAL STAGES
-- ============================================================
CREATE TABLE deal_stages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    stage_order INTEGER NOT NULL,
    probability INTEGER DEFAULT 0,
    color VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_deal_stages_pipeline ON deal_stages(pipeline_id);

-- ============================================================
-- DEALS
-- ============================================================
CREATE TABLE deals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    campaign_id UUID REFERENCES campaigns(id) ON DELETE SET NULL,
    stage_id UUID NOT NULL REFERENCES deal_stages(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    value DOUBLE PRECISION DEFAULT 0.0,
    currency VARCHAR(10) DEFAULT 'USD',
    status VARCHAR(50) DEFAULT 'open',
    source VARCHAR(50),
    notes TEXT,
    closed_at TIMESTAMPTZ,
    won_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_deals_org_id ON deals(org_id);
CREATE INDEX idx_deals_stage ON deals(stage_id);
CREATE INDEX idx_deals_status ON deals(status);
CREATE INDEX idx_deals_org_status ON deals(org_id, status);

-- ============================================================
-- FEATURE FLAGS
-- ============================================================
CREATE TABLE feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_feature_flags_key ON feature_flags(key);

-- ============================================================
-- ORG FEATURE FLAGS
-- ============================================================
CREATE TABLE org_feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    flag_key VARCHAR(100) NOT NULL,
    enabled BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_org_flags_org ON org_feature_flags(org_id);

-- ============================================================
-- INTEGRATIONS
-- ============================================================
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL,
    label VARCHAR(255),
    api_key_encrypted TEXT,
    api_secret_encrypted TEXT,
    refresh_token_encrypted TEXT,
    extra_config TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_integrations_org ON integrations(org_id);
CREATE INDEX idx_integrations_provider ON integrations(provider);

-- ============================================================
-- SDR PROFILES
-- ============================================================
CREATE TABLE sdr_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL DEFAULT 'AI SDR',
    region VARCHAR(255),
    sell_type VARCHAR(50) NOT NULL,
    product_name VARCHAR(255),
    product_description TEXT,
    payment_link VARCHAR(500),
    service_description TEXT,
    calendar_link VARCHAR(500),
    target_titles TEXT,
    target_industries TEXT,
    target_locations TEXT,
    target_company_size_min INTEGER,
    target_company_size_max INTEGER,
    lead_sources TEXT,
    sdr_personality TEXT,
    outreach_tone VARCHAR(50) DEFAULT 'professional',
    max_daily_emails INTEGER DEFAULT 20,
    max_daily_calls INTEGER DEFAULT 10,
    max_daily_linkedin INTEGER DEFAULT 15,
    max_daily_likes INTEGER DEFAULT 20,
    max_daily_comments INTEGER DEFAULT 10,
    linkedin_connect_enabled BOOLEAN DEFAULT TRUE,
    linkedin_dm_enabled BOOLEAN DEFAULT TRUE,
    linkedin_like_enabled BOOLEAN DEFAULT FALSE,
    linkedin_comment_enabled BOOLEAN DEFAULT FALSE,
    linkedin_engagement_feed TEXT,
    web_scrape_targets TEXT,
    auto_scrape_enabled BOOLEAN DEFAULT FALSE,
    scrape_business_category VARCHAR(255),
    scrape_country VARCHAR(100),
    scrape_directory_urls TEXT,
    campaign_sequence TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    leads_target INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_sdr_profiles_org ON sdr_profiles(org_id);

-- ============================================================
-- LEAD STATES
-- ============================================================
CREATE TABLE lead_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    sdr_profile_id VARCHAR,
    state VARCHAR(50) DEFAULT 'new',
    is_paused BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 50,
    last_contacted_at TIMESTAMPTZ,
    contact_count INTEGER DEFAULT 0,
    channels_used JSONB DEFAULT '[]',
    engagement_score INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_lead_states_org ON lead_states(org_id);
CREATE INDEX idx_lead_states_lead ON lead_states(lead_id);
CREATE INDEX idx_lead_states_sdr ON lead_states(sdr_profile_id);

-- ============================================================
-- AGENT LOGS
-- ============================================================
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
    sdr_profile_id VARCHAR,
    action VARCHAR(100) NOT NULL,
    channel VARCHAR(50),
    reasoning TEXT,
    result TEXT,
    status VARCHAR(50) DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_agent_logs_org ON agent_logs(org_id);
CREATE INDEX idx_agent_logs_lead ON agent_logs(lead_id);
CREATE INDEX idx_agent_logs_action ON agent_logs(action);
CREATE INDEX idx_agent_logs_created ON agent_logs(created_at);

-- ============================================================
-- ORG SETTINGS
-- ============================================================
CREATE TABLE org_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID UNIQUE NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    sell_type VARCHAR(50) DEFAULT 'product',
    product_name VARCHAR(255),
    product_description TEXT,
    payment_link VARCHAR(500),
    service_description TEXT,
    calendar_link VARCHAR(500),
    knowledge_base TEXT,
    scraping_enabled BOOLEAN DEFAULT FALSE,
    approved_countries TEXT,
    approved_categories TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SCRAPE PROFILES
-- ============================================================
CREATE TABLE scrape_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id VARCHAR NOT NULL,
    name VARCHAR(255) NOT NULL,
    persona_description TEXT NOT NULL DEFAULT '',
    business_category VARCHAR(255) NOT NULL DEFAULT '',
    country VARCHAR(100) NOT NULL DEFAULT '',
    directory_urls TEXT NOT NULL DEFAULT '',
    selected_fields TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_scrape_profiles_org ON scrape_profiles(org_id);

-- ============================================================
-- SMTP CONFIGURATIONS (NEW)
-- ============================================================
CREATE TABLE smtp_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider VARCHAR(50) DEFAULT 'custom',
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 587,
    use_tls BOOLEAN DEFAULT TRUE,
    use_ssl BOOLEAN DEFAULT FALSE,
    username VARCHAR(255) NOT NULL,
    password_encrypted TEXT NOT NULL,
    sender_name VARCHAR(255),
    sender_email VARCHAR(255) NOT NULL,
    reply_to VARCHAR(255),
    daily_limit INTEGER DEFAULT 300,
    hourly_limit INTEGER DEFAULT 30,
    warmup_enabled BOOLEAN DEFAULT FALSE,
    warmup_daily_increment INTEGER DEFAULT 5,
    warmup_current_daily INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_smtp_configs_org ON smtp_configs(org_id);

-- ============================================================
-- AUDIT LOGS (NEW)
-- ============================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(100),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_org ON audit_logs(org_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);

-- ============================================================
-- AI USAGE LOGS (NEW)
-- ============================================================
CREATE TABLE ai_usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    cost DOUBLE PRECISION DEFAULT 0.0,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ai_usage_org ON ai_usage_logs(org_id);
CREATE INDEX idx_ai_usage_provider ON ai_usage_logs(provider);
CREATE INDEX idx_ai_usage_created ON ai_usage_logs(created_at);

-- ============================================================
-- NOTIFICATIONS (NEW)
-- ============================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_org ON notifications(org_id);

-- ============================================================
-- ROW LEVEL SECURITY POLICIES
-- ============================================================

-- Helper function to get current user's org_id from JWT
CREATE OR REPLACE FUNCTION auth.get_org_id()
RETURNS UUID
LANGUAGE SQL
STABLE
AS $$
    SELECT COALESCE(
        current_setting('request.jwt.claims', true)::jsonb ->> 'org_id',
        ''
    )::UUID;
$$;

-- Helper function to get current user's role from JWT
CREATE OR REPLACE FUNCTION auth.get_user_role()
RETURNS VARCHAR
LANGUAGE SQL
STABLE
AS $$
    SELECT COALESCE(
        current_setting('request.jwt.claims', true)::jsonb ->> 'role',
        ''
    )::VARCHAR;
$$;

-- Helper function to get current user id from JWT
CREATE OR REPLACE FUNCTION auth.get_user_id()
RETURNS UUID
LANGUAGE SQL
STABLE
AS $$
    SELECT COALESCE(
        current_setting('request.jwt.claims', true)::jsonb ->> 'sub',
        ''
    )::UUID;
$$;

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_scripts ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE deal_stages ENABLE ROW LEVEL SECURITY;
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE sdr_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE lead_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE scrape_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE smtp_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Organizations: users can see only their own org
CREATE POLICY org_isolation ON organizations
    FOR ALL
    USING (id = auth.get_org_id());

-- Users: can see own org users, update only self
CREATE POLICY user_org_isolation ON users
    FOR ALL
    USING (org_id = auth.get_org_id());

CREATE POLICY user_self_update ON users
    FOR UPDATE
    USING (id = auth.get_user_id());

-- Generic org-scoped policy (applies to all org-tables)
CREATE POLICY org_scope ON leads FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON campaigns FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON campaign_steps FOR ALL USING (
    campaign_id IN (SELECT id FROM campaigns WHERE org_id = auth.get_org_id())
);
CREATE POLICY org_scope ON email_templates FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON email_messages FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON call_scripts FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON call_logs FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON pipelines FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON deal_stages FOR ALL USING (
    pipeline_id IN (SELECT id FROM pipelines WHERE org_id = auth.get_org_id())
);
CREATE POLICY org_scope ON deals FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON integrations FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON sdr_profiles FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON lead_states FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON agent_logs FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON org_settings FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON scrape_profiles FOR ALL USING (org_id = auth.get_org_id()::text = org_id);
CREATE POLICY org_scope ON smtp_configs FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON audit_logs FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON ai_usage_logs FOR ALL USING (org_id = auth.get_org_id());
CREATE POLICY org_scope ON notifications FOR ALL USING (org_id = auth.get_org_id());

-- Admin override: admins can see all org data within their org
CREATE POLICY admin_access ON organizations
    FOR ALL
    USING (auth.get_user_role() = 'admin');

-- Feature flags are global (no org scope)
ALTER TABLE feature_flags ENABLE ROW LEVEL SECURITY;
CREATE POLICY flag_global ON feature_flags FOR SELECT USING (true);
CREATE POLICY flag_admin ON feature_flags FOR ALL USING (auth.get_user_role() = 'admin');

ALTER TABLE org_feature_flags ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_flag_scope ON org_feature_flags FOR ALL USING (org_id = auth.get_org_id());

-- Seed default feature flags
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
