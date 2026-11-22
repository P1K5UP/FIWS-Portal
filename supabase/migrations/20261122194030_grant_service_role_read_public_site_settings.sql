-- Allow the server-side Edge Function to read published site configuration.
-- Browser clients retain SELECT access only through the existing public read policy.
GRANT SELECT ON TABLE public.site_settings TO service_role;
