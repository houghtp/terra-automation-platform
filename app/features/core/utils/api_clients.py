# --- Centralized API Key Retrieval (Linux/WSL2 compatible) ---
def get_api_keys() -> dict:
    """
    Retrieve all relevant API keys from environment variables (Linux/WSL2 compatible).
    """
    keys = {
        "openai": os.getenv("OPENAI_API_KEY"),
        "serpapi": os.getenv("SERPAPI_KEY"),
        "scrapingdog": os.getenv("SCRAPINGDOG_API_KEY"),
        "scrapingbee": os.getenv("SCRAPINGBEE_API_KEY"),
        "hunter": os.getenv("HUNTER_API_KEY"),
        "zerobounce": os.getenv("ZEROBOUNCE_API_KEY"),
        "firecrawl": os.getenv("FIRECRAWL_API_KEY"),
        # Microsoft Graph API
        "microsoft_tenant_id": os.getenv("MICROSOFT_TENANT_ID"),
        "microsoft_client_id": os.getenv("MICROSOFT_CLIENT_ID"),
        "microsoft_client_secret": os.getenv("MICROSOFT_CLIENT_SECRET")
    }
    return keys
# --- API Key Verification Utility ---
def verify_api_keys() -> dict:
    """
    Verify required API keys are available and not placeholders.
    """
    missing_keys = []
    placeholder_keys = []
    keys_to_check = {
        "OPENAI_API_KEY": "OpenAI",
        "FIRECRAWL_API_KEY": "Firecrawl",
        "HUNTER_API_KEY": "Hunter"
    }
    placeholders = [
        "your_openai_api_key_here",
        "your_firecrawl_api_key_here",
        "your_hunter_api_key_here",
        "sk-placeholder"
    ]
    for env_key, display_name in keys_to_check.items():
        api_key = os.environ.get(env_key)
        if not api_key:
            missing_keys.append(display_name)
        elif any(placeholder in api_key.lower() for placeholder in placeholders):
            placeholder_keys.append(display_name)
    if missing_keys:
        return {
            "status": "error",
            "error": f"Missing required API keys: {', '.join(missing_keys)}. Please add them to your .env file.",
            "missing_keys": missing_keys
        }
    if placeholder_keys:
        return {
            "status": "error",
            "error": f"Found placeholder API keys for: {', '.join(placeholder_keys)}. Please replace them with actual API keys in your .env file.",
            "placeholder_keys": placeholder_keys
        }
    return {"status": "success"}
"""
Shared API clients for OpenAI, Firecrawl, and Hunter.io/email lookup.
All functions are async and return parsed results.
"""
import os
import httpx
from typing import List, Dict, Any

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY", "")


# --- Generic OpenAI Chat Completion ---
async def openai_chat_completion(messages: list, model: str = "gpt-4", temperature: float = 0.7) -> str:
    """
    Generic OpenAI chat completion call. Returns the response text.
    """
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]




# --- Firecrawl Executive Search (Generic) ---
async def firecrawl_search(query: str, limit: int = 10, extract_profiles: bool = True) -> Any:
    """
    Generic Firecrawl search API call. Returns raw JSON response.
    """
    if not FIRECRAWL_API_KEY:
        return None
    url = "https://api.firecrawl.dev/v1/search"
    payload = {
        "query": query,
        "limit": limit,
        "extract_profiles": extract_profiles
    }
    headers = {"Authorization": f"Bearer {FIRECRAWL_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


# --- Hunter.io Email Lookup (Generic) ---
async def hunter_email_finder(full_name: str, domain: str) -> str:
    """
    Call Hunter.io API to find a verified email for the given name and domain.
    """
    if not HUNTER_API_KEY or not full_name or not domain:
        return "N/A"
    url = "https://api.hunter.io/v2/email-finder"
    params = {
        "domain": domain,
        "full_name": full_name,
        "api_key": HUNTER_API_KEY
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return "N/A"
        data = resp.json()
    email = data.get("data", {}).get("email")
    return email or "N/A"
