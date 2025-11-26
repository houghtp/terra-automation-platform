"""
GA4 OAuth helpers (auth URL, token exchange, property listing).

Uses direct REST calls to keep control over token exchange flow and stay HTMX-friendly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException

from app.features.business_automations.marketing_intellegence_hub.ga4_credentials import load_ga4_credentials

OAUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
ACCOUNT_SUMMARIES_URL = "https://analyticsadmin.googleapis.com/v1alpha/accountSummaries"
SCOPE = "https://www.googleapis.com/auth/analytics.readonly"


def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{OAUTH_BASE}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str, redirect_uri: str, credentials: Dict[str, str]) -> Dict[str, str]:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": credentials["client_id"],
                    "client_secret": credentials["client_secret"],
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            # Normalize expiry timestamp to ISO string for storage
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 0))
            return {
                "access_token": data["access_token"],
                "refresh_token": data.get("refresh_token", ""),
                "access_token_expires_at": expires_at.replace(tzinfo=None).isoformat(),
                "token_type": data.get("token_type"),
                "scope": data.get("scope"),
            }
    except httpx.HTTPStatusError as exc:
        # Surface the Google error payload to help diagnose issues (e.g., invalid_grant/redirect mismatch)
        body = exc.response.text
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {body}")


async def list_ga4_properties(access_token: str) -> List[Dict[str, str]]:
    """List GA4 properties via Account Summaries (lightweight for selection)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(ACCOUNT_SUMMARIES_URL, headers=headers)
        resp.raise_for_status()
        payload = resp.json()
        summaries = payload.get("accountSummaries", []) or []
        properties = []
        for acct in summaries:
            for prop in acct.get("propertySummaries", []) or []:
                properties.append(
                    {
                        "property_id": prop.get("property"),
                        "display_name": prop.get("displayName"),
                        "account": acct.get("name"),
                    }
                )
        return properties


async def perform_token_exchange(code: str, db_session, accessed_by_user=None) -> Dict[str, str]:
    """Helper that loads creds and exchanges code for tokens."""
    creds = await load_ga4_credentials(db_session, accessed_by_user=accessed_by_user)
    return await exchange_code_for_tokens(code, creds["redirect_uri"], creds)
