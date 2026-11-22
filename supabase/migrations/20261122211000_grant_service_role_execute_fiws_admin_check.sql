-- The legacy applications audit trigger evaluates this helper on every UPDATE.
-- The custom-session admin API uses service_role, so it needs EXECUTE; the helper
-- still returns false for service_role JWTs and does not grant admin status.
GRANT EXECUTE ON FUNCTION private.is_fiws_admin() TO service_role;
