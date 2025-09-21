from typing import Dict, Any, List
from app.integrations.base import ProviderAdapter


class M365StubAdapter(ProviderAdapter):
    def authorize_url(self, tenant_id: str, state: str) -> str:
        return f"https://login.microsoftonline.com/{tenant_id}/oauth2/authorize?state={state}"

    async def exchange_code(self, code: str) -> Dict[str, Any]:
        # Return a fake token payload for development
        return {"access_token": "m365-access-" + code, "refresh_token": "m365-refresh-" + code}

    async def list_mailboxes(self, credentials: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Fake mailbox list
        return [
            {"email": "alice@%s" % credentials.get("domain", "example.com"), "name": "Alice"},
            {"email": "bob@%s" % credentials.get("domain", "example.com"), "name": "Bob"},
        ]
