from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.url, settings.anon_key)


def create_authenticated_supabase_client(access_token: str) -> Client:
    settings = get_settings()
    client = create_client(settings.url, settings.anon_key)
    client.postgrest.auth(access_token)
    return client
