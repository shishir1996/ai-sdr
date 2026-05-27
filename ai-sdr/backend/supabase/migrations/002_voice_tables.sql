-- Voice / Vapi / Twilio tables
-- Run this in Supabase SQL Editor

-- Voice Agents (mapped to Vapi assistants)
CREATE TABLE IF NOT EXISTS voice_agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  sdr_profile_id UUID REFERENCES sdr_profiles(id) ON DELETE SET NULL,
  name VARCHAR(255) NOT NULL,
  vapi_assistant_id VARCHAR(255) UNIQUE,
  ai_model VARCHAR(100) DEFAULT 'gpt-4o-mini',
  voice_provider VARCHAR(100) DEFAULT '11labs',
  voice_id VARCHAR(100) DEFAULT 'default',
  transcriber_provider VARCHAR(100) DEFAULT 'deepgram',
  system_prompt TEXT,
  first_message VARCHAR(500),
  temperature FLOAT DEFAULT 0.7,
  max_duration_seconds INTEGER DEFAULT 300,
  is_active BOOLEAN DEFAULT false,
  is_default BOOLEAN DEFAULT false,
  config JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE voice_agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON voice_agents USING (org_id = auth.get_org_id());

CREATE INDEX idx_voice_agents_org ON voice_agents(org_id);
CREATE INDEX idx_voice_agents_vapi ON voice_agents(vapi_assistant_id);

-- Call Campaigns
CREATE TABLE IF NOT EXISTS call_campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  sdr_profile_id UUID REFERENCES sdr_profiles(id) ON DELETE SET NULL,
  voice_agent_id UUID REFERENCES voice_agents(id) ON DELETE SET NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(50) DEFAULT 'draft',
  schedule_start TIMESTAMPTZ,
  schedule_end TIMESTAMPTZ,
  timezone_restrictions JSONB,
  business_hours_start VARCHAR(10) DEFAULT '09:00',
  business_hours_end VARCHAR(10) DEFAULT '18:00',
  business_days JSONB DEFAULT '[]',
  max_concurrent_calls INTEGER DEFAULT 3,
  max_calls_per_day INTEGER DEFAULT 50,
  retry_on_no_answer BOOLEAN DEFAULT true,
  max_retries INTEGER DEFAULT 2,
  retry_delay_minutes INTEGER DEFAULT 30,
  voicemail_detection BOOLEAN DEFAULT true,
  voicemail_action VARCHAR(50) DEFAULT 'leave_message',
  call_timeout_seconds INTEGER DEFAULT 60,
  lead_filter_criteria JSONB,
  total_calls INTEGER DEFAULT 0,
  total_connected INTEGER DEFAULT 0,
  total_positive INTEGER DEFAULT 0,
  last_run_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE call_campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON call_campaigns USING (org_id = auth.get_org_id());

CREATE INDEX idx_call_campaigns_org ON call_campaigns(org_id);
CREATE INDEX idx_call_campaigns_status ON call_campaigns(status);

-- Call Records (detailed call log from Vapi)
CREATE TABLE IF NOT EXISTS call_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  campaign_id UUID REFERENCES call_campaigns(id) ON DELETE SET NULL,
  voice_agent_id UUID REFERENCES voice_agents(id) ON DELETE SET NULL,
  sdr_profile_id UUID,
  vapi_call_id VARCHAR(255) UNIQUE,
  phone_number VARCHAR(50) NOT NULL,
  direction VARCHAR(20) DEFAULT 'outbound',
  status VARCHAR(50) DEFAULT 'queued',
  duration_seconds INTEGER,
  cost FLOAT,
  outcome VARCHAR(50),
  sentiment VARCHAR(50),
  lead_qualified BOOLEAN,
  lead_intent VARCHAR(100),
  ai_summary TEXT,
  transcript TEXT,
  transcript_url VARCHAR(500),
  recording_url VARCHAR(500),
  recording_duration INTEGER,
  voicemail_detected BOOLEAN,
  answered_by VARCHAR(50),
  next_action VARCHAR(100),
  followup_scheduled BOOLEAN DEFAULT false,
  followup_at TIMESTAMPTZ,
  error_message TEXT,
  retry_count INTEGER DEFAULT 0,
  called_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE call_records ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON call_records USING (org_id = auth.get_org_id());

CREATE INDEX idx_call_records_org ON call_records(org_id);
CREATE INDEX idx_call_records_vapi ON call_records(vapi_call_id);
CREATE INDEX idx_call_records_lead ON call_records(lead_id);
CREATE INDEX idx_call_records_campaign ON call_records(campaign_id);
CREATE INDEX idx_call_records_status ON call_records(status);
CREATE INDEX idx_call_records_called_at ON call_records(called_at);

-- Call Queue
CREATE TABLE IF NOT EXISTS call_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  campaign_id UUID REFERENCES call_campaigns(id) ON DELETE SET NULL,
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  voice_agent_id UUID REFERENCES voice_agents(id) ON DELETE SET NULL,
  phone_number VARCHAR(50) NOT NULL,
  priority INTEGER DEFAULT 50,
  status VARCHAR(50) DEFAULT 'pending',
  scheduled_at TIMESTAMPTZ,
  retry_count INTEGER DEFAULT 0,
  max_retries INTEGER DEFAULT 2,
  last_error TEXT,
  idempotency_key VARCHAR(255) UNIQUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE call_queue ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON call_queue USING (org_id = auth.get_org_id());

CREATE INDEX idx_call_queue_org ON call_queue(org_id);
CREATE INDEX idx_call_queue_status ON call_queue(status);
CREATE INDEX idx_call_queue_lead ON call_queue(lead_id);
CREATE INDEX idx_call_queue_idempotency ON call_queue(idempotency_key);

-- Call Analytics (daily aggregated stats)
CREATE TABLE IF NOT EXISTS call_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  date VARCHAR(10) NOT NULL,
  total_calls INTEGER DEFAULT 0,
  connected_calls INTEGER DEFAULT 0,
  voicemail_calls INTEGER DEFAULT 0,
  failed_calls INTEGER DEFAULT 0,
  no_answer_calls INTEGER DEFAULT 0,
  total_duration_seconds INTEGER DEFAULT 0,
  total_cost FLOAT DEFAULT 0.0,
  positive_outcomes INTEGER DEFAULT 0,
  meetings_booked INTEGER DEFAULT 0,
  qualified_leads INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE call_analytics ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON call_analytics USING (org_id = auth.get_org_id());

CREATE INDEX idx_call_analytics_org_date ON call_analytics(org_id, date);

-- AI Summaries
CREATE TABLE IF NOT EXISTS ai_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  call_record_id UUID REFERENCES call_records(id) ON DELETE SET NULL,
  lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
  summary TEXT NOT NULL,
  transcript_summary TEXT,
  key_points JSONB,
  action_items JSONB,
  next_steps TEXT,
  sentiment_analysis JSONB,
  qualification_score INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE ai_summaries ENABLE ROW LEVEL SECURITY;
CREATE POLICY org_isolation ON ai_summaries USING (org_id = auth.get_org_id());

CREATE INDEX idx_ai_summaries_org ON ai_summaries(org_id);
CREATE INDEX idx_ai_summaries_call ON ai_summaries(call_record_id);
CREATE INDEX idx_ai_summaries_lead ON ai_summaries(lead_id);

-- Add 'twilio' to integration providers if table-driven
-- (already added to INTEGRATION_PROVIDERS list in Python code)

-- Seed default feature flag for calling if applicable
INSERT INTO feature_flags (key, name, description, default_enabled)
SELECT 'ai_calling', 'AI Calling', 'Vapi.ai + Twilio outbound calling', true
WHERE NOT EXISTS (SELECT 1 FROM feature_flags WHERE key = 'ai_calling');
