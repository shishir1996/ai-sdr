-- AI SDR Platform - PostgreSQL Schema for Railway
-- Run this via Railway Dashboard → PostgreSQL service → Query tab
-- Safe to re-run (uses IF NOT EXISTS / ON CONFLICT DO NOTHING)

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ORGANIZATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- USERS (includes migration 003 auth fields)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'member',
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    google_id VARCHAR(255),
    phone VARCHAR(50),
    country_code VARCHAR(10),
    email_verified BOOLEAN DEFAULT false,
    supabase_uid VARCHAR(255) UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_org_id ON users(org_id);
CREATE INDEX IF NOT EXISTS ix_users_supabase_uid ON users(supabase_uid);

-- ============================================================
-- LEADS
-- ============================================================
CREATE TABLE IF NOT EXISTS leads (
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
CREATE INDEX IF NOT EXISTS idx_leads_org_id ON leads(org_id);
CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);
CREATE INDEX IF NOT EXISTS idx_leads_org_score ON leads(org_id, score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_org_status ON leads(org_id, status);

-- ============================================================
-- CAMPAIGNS
-- ============================================================
CREATE TABLE IF NOT EXISTS campaigns (
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
CREATE INDEX IF NOT EXISTS idx_campaigns_org_id ON campaigns(org_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_sdr_profile ON campaigns(sdr_profile_id);

-- ============================================================
-- CAMPAIGN STEPS
-- ============================================================
CREATE TABLE IF NOT EXISTS campaign_steps (
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
CREATE INDEX IF NOT EXISTS idx_campaign_steps_campaign ON campaign_steps(campaign_id);

-- ============================================================
-- EMAIL TEMPLATES
-- ============================================================
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    variables JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_email_templates_org ON email_templates(org_id);

-- ============================================================
-- EMAIL MESSAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS email_messages (
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
    direction VARCHAR(20) DEFAULT 'outbound',
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    bounced_at TIMESTAMPTZ,
    message_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_email_messages_org ON email_messages(org_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_lead ON email_messages(lead_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_status ON email_messages(status);
CREATE INDEX IF NOT EXISTS idx_email_messages_sent ON email_messages(sent_at);

-- ============================================================
-- CALL SCRIPTS
-- ============================================================
CREATE TABLE IF NOT EXISTS call_scripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_call_scripts_org ON call_scripts(org_id);

-- ============================================================
-- CALL LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS call_logs (
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
CREATE INDEX IF NOT EXISTS idx_call_logs_org ON call_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_lead ON call_logs(lead_id);

-- ============================================================
-- PIPELINES
-- ============================================================
CREATE TABLE IF NOT EXISTS pipelines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pipelines_org ON pipelines(org_id);

-- ============================================================
-- DEAL STAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS deal_stages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    stage_order INTEGER NOT NULL,
    probability INTEGER DEFAULT 0,
    color VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_deal_stages_pipeline ON deal_stages(pipeline_id);

-- ============================================================
-- DEALS
-- ============================================================
CREATE TABLE IF NOT EXISTS deals (
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
CREATE INDEX IF NOT EXISTS idx_deals_org_id ON deals(org_id);
CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage_id);
CREATE INDEX IF NOT EXISTS idx_deals_status ON deals(status);
CREATE INDEX IF NOT EXISTS idx_deals_org_status ON deals(org_id, status);

-- ============================================================
-- FEATURE FLAGS
-- ============================================================
CREATE TABLE IF NOT EXISTS feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_feature_flags_key ON feature_flags(key);

-- ============================================================
-- ORG FEATURE FLAGS
-- ============================================================
CREATE TABLE IF NOT EXISTS org_feature_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    flag_key VARCHAR(100) NOT NULL,
    enabled BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_org_flags_org ON org_feature_flags(org_id);

-- ============================================================
-- INTEGRATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS integrations (
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
CREATE INDEX IF NOT EXISTS idx_integrations_org ON integrations(org_id);
CREATE INDEX IF NOT EXISTS idx_integrations_provider ON integrations(provider);

-- ============================================================
-- SDR PROFILES
-- ============================================================
CREATE TABLE IF NOT EXISTS sdr_profiles (
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
    email_credentials_encrypted TEXT,
    linkedin_credentials_encrypted TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    leads_target INTEGER DEFAULT 100,
    deleted_at TIMESTAMPTZ,
    deleted_by VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sdr_profiles_org ON sdr_profiles(org_id);

-- ============================================================
-- LEAD STATES
-- ============================================================
CREATE TABLE IF NOT EXISTS lead_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    sdr_profile_id VARCHAR,
    state VARCHAR(50) DEFAULT 'new',
    is_paused BOOLEAN DEFAULT FALSE,
    priority INTEGER DEFAULT 50,
    last_contacted_at TIMESTAMPTZ,
    contact_count INTEGER DEFAULT 0,
    channels_used JSON DEFAULT '[]',
    engagement_score INTEGER DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lead_states_org ON lead_states(org_id);
CREATE INDEX IF NOT EXISTS idx_lead_states_lead ON lead_states(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_states_sdr ON lead_states(sdr_profile_id);

-- ============================================================
-- AGENT LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_logs (
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
CREATE INDEX IF NOT EXISTS idx_agent_logs_org ON agent_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_lead ON agent_logs(lead_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_action ON agent_logs(action);
CREATE INDEX IF NOT EXISTS idx_agent_logs_created ON agent_logs(created_at);

-- ============================================================
-- ORG SETTINGS
-- ============================================================
CREATE TABLE IF NOT EXISTS org_settings (
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
CREATE TABLE IF NOT EXISTS scrape_profiles (
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
CREATE INDEX IF NOT EXISTS idx_scrape_profiles_org ON scrape_profiles(org_id);

-- ============================================================
-- SMTP CONFIGURATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS smtp_configs (
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
CREATE INDEX IF NOT EXISTS idx_smtp_configs_org ON smtp_configs(org_id);

-- ============================================================
-- AUDIT LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
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
CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at);

-- ============================================================
-- AI USAGE LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_usage_logs (
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
CREATE INDEX IF NOT EXISTS idx_ai_usage_org ON ai_usage_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_ai_usage_provider ON ai_usage_logs(provider);
CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON ai_usage_logs(created_at);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_org ON notifications(org_id);

-- ============================================================
-- AGENT ACTIVITIES
-- ============================================================
CREATE TABLE IF NOT EXISTS agent_activities (
    id VARCHAR PRIMARY KEY,
    org_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    sdr_profile_id VARCHAR,
    lead_id VARCHAR REFERENCES leads(id) ON DELETE SET NULL,
    campaign_id VARCHAR,
    stage VARCHAR(100) NOT NULL,
    status VARCHAR(50) DEFAULT 'completed',
    summary TEXT,
    reasoning TEXT,
    details JSON,
    channel VARCHAR(50),
    next_planned_action TEXT,
    confidence_score INTEGER,
    is_expandable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_activities_org ON agent_activities(org_id);
CREATE INDEX IF NOT EXISTS idx_agent_activities_lead ON agent_activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_agent_activities_sdr ON agent_activities(sdr_profile_id);
CREATE INDEX IF NOT EXISTS idx_agent_activities_stage ON agent_activities(stage);

-- ============================================================
-- SDR REASONING LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS sdr_reasoning_logs (
    id VARCHAR PRIMARY KEY,
    org_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    sdr_profile_id VARCHAR,
    lead_id VARCHAR REFERENCES leads(id) ON DELETE SET NULL,
    decision_type VARCHAR(100) NOT NULL,
    human_readable_reasoning TEXT,
    detailed_reasoning JSON,
    ai_confidence_score INTEGER,
    alternatives_considered JSON,
    context_summary TEXT,
    channel_selected VARCHAR(50),
    timing_explanation TEXT,
    personalization_strategy TEXT,
    industry_context TEXT,
    country_context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sdr_reasoning_org ON sdr_reasoning_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_sdr_reasoning_lead ON sdr_reasoning_logs(lead_id);

-- ============================================================
-- CAMPAIGN EVENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS campaign_events (
    id VARCHAR PRIMARY KEY,
    org_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    campaign_id VARCHAR NOT NULL,
    sdr_profile_id VARCHAR,
    event_type VARCHAR(100) NOT NULL,
    summary TEXT,
    reasoning TEXT,
    details JSON,
    progress_before INTEGER,
    progress_after INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_campaign_events_org ON campaign_events(org_id);
CREATE INDEX IF NOT EXISTS idx_campaign_events_campaign ON campaign_events(campaign_id);

-- ============================================================
-- LEAD TIMELINE
-- ============================================================
CREATE TABLE IF NOT EXISTS lead_timeline (
    id VARCHAR PRIMARY KEY,
    org_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lead_id VARCHAR NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    sdr_profile_id VARCHAR,
    event_type VARCHAR(100) NOT NULL,
    summary TEXT,
    reasoning TEXT,
    message_preview TEXT,
    channel VARCHAR(50),
    response_received TEXT,
    sdr_status_before VARCHAR(50),
    sdr_status_after VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lead_timeline_org ON lead_timeline(org_id);
CREATE INDEX IF NOT EXISTS idx_lead_timeline_lead ON lead_timeline(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_timeline_created ON lead_timeline(created_at);

-- ============================================================
-- SEQUENCE EXECUTION LOGS
-- ============================================================
CREATE TABLE IF NOT EXISTS sequence_execution_logs (
    id VARCHAR PRIMARY KEY,
    org_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    campaign_id VARCHAR NOT NULL,
    lead_id VARCHAR REFERENCES leads(id) ON DELETE SET NULL,
    sdr_profile_id VARCHAR,
    step_order INTEGER NOT NULL,
    channel VARCHAR(50),
    delay_days INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    executed_at TIMESTAMPTZ,
    result TEXT,
    reasoning TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_seq_exec_org ON sequence_execution_logs(org_id);
CREATE INDEX IF NOT EXISTS idx_seq_exec_lead ON sequence_execution_logs(lead_id);

-- ============================================================
-- SDR STATUS
-- ============================================================
CREATE TABLE IF NOT EXISTS sdr_status (
    id VARCHAR PRIMARY KEY,
    org_id VARCHAR NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    sdr_profile_id VARCHAR NOT NULL,
    current_status VARCHAR(50) DEFAULT 'idle',
    current_action VARCHAR(200),
    current_lead_id VARCHAR,
    current_campaign_id VARCHAR,
    reasoning_summary TEXT,
    next_planned_action TEXT,
    heartbeat_at TIMESTAMPTZ DEFAULT NOW(),
    last_active_at TIMESTAMPTZ DEFAULT NOW(),
    leads_processed INTEGER DEFAULT 0,
    campaigns_created INTEGER DEFAULT 0,
    emails_drafted INTEGER DEFAULT 0,
    linkedin_invites_sent INTEGER DEFAULT 0,
    replies_detected INTEGER DEFAULT 0,
    meetings_booked INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sdr_status_profile ON sdr_status(sdr_profile_id);
CREATE INDEX IF NOT EXISTS idx_sdr_status_org ON sdr_status(org_id);

-- ============================================================
-- CALL RECORDS
-- ============================================================
CREATE TABLE IF NOT EXISTS call_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lead_id UUID,
    campaign_id UUID,
    voice_agent_id VARCHAR,
    status VARCHAR(50) DEFAULT 'pending',
    duration_seconds INTEGER,
    recording_url VARCHAR(500),
    transcript TEXT,
    summary TEXT,
    outcome VARCHAR(50),
    call_time TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_call_records_org ON call_records(org_id);

-- ============================================================
-- CALL CAMPAIGNS
-- ============================================================
CREATE TABLE IF NOT EXISTS call_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    script TEXT,
    status VARCHAR(50) DEFAULT 'draft',
    max_calls_per_day INTEGER DEFAULT 50,
    timezone VARCHAR(50) DEFAULT 'UTC',
    start_time TIME DEFAULT '09:00',
    end_time TIME DEFAULT '17:00',
    days_of_week VARCHAR(50) DEFAULT '1,2,3,4,5',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_call_campaigns_org ON call_campaigns(org_id);

-- ============================================================
-- VOICE AGENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS voice_agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(50) DEFAULT 'vapi',
    provider_agent_id VARCHAR(255),
    config JSONB,
    is_active BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_voice_agents_org ON voice_agents(org_id);

-- ============================================================
-- CALL QUEUE
-- ============================================================
CREATE TABLE IF NOT EXISTS call_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    call_campaign_id UUID REFERENCES call_campaigns(id) ON DELETE SET NULL,
    voice_agent_id VARCHAR,
    status VARCHAR(50) DEFAULT 'queued',
    priority INTEGER DEFAULT 50,
    scheduled_at TIMESTAMPTZ,
    called_at TIMESTAMPTZ,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_call_queue_org ON call_queue(org_id);
CREATE INDEX IF NOT EXISTS idx_call_queue_status ON call_queue(status);

-- ============================================================
-- CALL ANALYTICS
-- ============================================================
CREATE TABLE IF NOT EXISTS call_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    total_calls INTEGER DEFAULT 0,
    completed_calls INTEGER DEFAULT 0,
    answered_calls INTEGER DEFAULT 0,
    voicemail_calls INTEGER DEFAULT 0,
    failed_calls INTEGER DEFAULT 0,
    avg_duration_seconds INTEGER DEFAULT 0,
    total_cost DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_call_analytics_org ON call_analytics(org_id);
CREATE INDEX IF NOT EXISTS idx_call_analytics_date ON call_analytics(date);

-- ============================================================
-- AI SUMMARIES
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    call_record_id UUID,
    summary_text TEXT NOT NULL,
    key_points JSONB,
    action_items JSONB,
    sentiment VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SEED DEFAULT FEATURE FLAGS
-- ============================================================
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
