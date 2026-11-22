-- Allow the authenticated admin Edge Function's service role to publish settings.
GRANT INSERT, UPDATE ON TABLE public.site_settings TO service_role;
