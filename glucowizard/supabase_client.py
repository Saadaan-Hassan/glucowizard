import os
from supabase import create_client, Client

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_KEY not set")
    
    # Ensure NO trailing slash here; the client library adds them
    if url.endswith("/"):
        url = url[:-1]
        
    return create_client(url, key)
