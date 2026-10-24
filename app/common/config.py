import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class SupabaseSettings:
    url: str
    anon_key: str


@lru_cache(maxsize=1)
def get_settings() -> SupabaseSettings:
    load_dotenv(Path(__file__).parent.parent / ".env")

    url = os.getenv("SUPABASE_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", url),
            ("SUPABASE_ANON_KEY", anon_key),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required Supabase environment variable(s): {', '.join(missing)}"
        )

    return SupabaseSettings(url=url, anon_key=anon_key)
