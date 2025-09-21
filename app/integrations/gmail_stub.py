from typing import Dict, Any, List
from app.integrations.base import ProviderAdapter


class GmailStubAdapter(ProviderAdapter):
    def authorize_url(self, tenant_id: str, state: str) -> str:
        return f"https://accounts.google.com/o/oauth2/auth?hd={tenant_id}&state={state}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        return {"access_token": "gmail-access-" + code, "refresh_token": "gmail-refresh-" + code}

    async def list_mailboxes(self, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [
            {"email": "carol@%s" % credentials.get("domain", "example.com"), "name": "Carol"},
            {"email": "dan@%s" % credentials.get("domain", "example.com"), "name": "Dan"},
        ]
