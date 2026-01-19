import os
from supabase import create_client, Client

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set")
    
    # Ensure a trailing slash; the storage client sometimes expects it
    if not url.endswith("/"):
        url += "/"
        
    return create_client(url, key)
