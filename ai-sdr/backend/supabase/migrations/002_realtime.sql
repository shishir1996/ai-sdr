-- Enable Realtime for key tables
-- Run this in Supabase SQL Editor after the initial migration

-- Enable replication on tables for realtime subscriptions
ALTER TABLE leads REPLICA IDENTITY FULL;
ALTER TABLE campaigns REPLICA IDENTITY FULL;
ALTER TABLE email_messages REPLICA IDENTITY FULL;
ALTER TABLE agent_logs REPLICA IDENTITY FULL;
ALTER TABLE notifications REPLICA IDENTITY FULL;
ALTER TABLE deal_stages REPLICA IDENTITY FULL;
ALTER TABLE deals REPLICA IDENTITY FULL;

-- Create realtime publication
-- Use Supabase dashboard: Go to Database > Replication > Enable for these tables:
-- leads, campaigns, email_messages, agent_logs, notifications, deal_stages, deals

-- Or run:
-- BEGIN;
--   DROP PUBLICATION IF EXISTS supabase_realtime;
--   CREATE PUBLICATION supabase_realtime FOR TABLE
--     leads,
--     campaigns,
--     email_messages,
--     agent_logs,
--     notifications,
--     deal_stages,
--     deals;
-- COMMIT;
