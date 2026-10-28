alter table public.tydesk_connection_settings
  add column if not exists calculator_config text
  check (calculator_config is null or calculator_config ~ '^[a-f0-9]{96}$');
