from functools import lru_cache

from app.common.db.supabase_client import get_supabase_client
from app.Authentication.services.supabase_auth_service import SupabaseAuthService


@lru_cache(maxsize=1)
def get_supabase_auth_service() -> SupabaseAuthService:
    return SupabaseAuthService(get_supabase_client())
