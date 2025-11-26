"""
Hunter.io API client for email enrichment.

Uses Hunter.io's Email Finder and Email Verifier APIs to find
and validate professional email addresses for prospects.
"""

import httpx
from typing import Optional, Dict, Any
from app.features.core.sqlalchemy_imports import get_logger

logger = get_logger(__name__)


class HunterClient:
    """Client for Hunter.io email finding and verification."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Hunter.io client.

        Args:
            api_key: Hunter.io API key from secrets management
        """
        self.api_key = api_key
        self.base_url = "https://api.hunter.io/v2"
        self.timeout = 15.0

        if not self.api_key:
            logger.warning("Hunter.io API key not provided")

    async def find_email(
        self,
        first_name: str,
        last_name: str,
        domain: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find email address for a person at a company domain.

        Args:
            first_name: Person's first name
            last_name: Person's last name
            domain: Company domain (e.g., 'acme.com')

        Returns:
            Email data dict with email, confidence, status or None

        Example result:
            {
                "email": "john.doe@acme.com",
                "confidence": 95,
                "status": "valid",
                "sources": [...]
            }
        """
        if not self.api_key:
            logger.error("Hunter.io API key not configured")
            return None

        if not domain:
            logger.warning("Cannot find email without company domain")
            return None

        try:
            params = {
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": self.api_key
            }

            logger.info(
                "Finding email",
                first_name=first_name,
                last_name=last_name,
                domain=domain
            )

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/email-finder",
                    params=params
                )

                response.raise_for_status()
                data = response.json()

            # Parse response
            if data.get("data") and data["data"].get("email"):
                email_data = data["data"]
                result = {
                    "email": email_data.get("email"),
                    "confidence": email_data.get("score"),  # 0-100
                    "status": email_data.get("status"),  # valid, invalid, accept_all, unknown
                    "sources": email_data.get("sources", []),
                }

                logger.info(
                    "Email found",
                    email=result["email"],
                    confidence=result["confidence"],
                    status=result["status"]
                )

                return result
            else:
                logger.info(
                    "No email found",
                    first_name=first_name,
                    last_name=last_name,
                    domain=domain
                )
                return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Hunter.io rate limit exceeded")
            else:
                logger.error(
                    "Hunter.io API error",
                    status_code=e.response.status_code,
                    error=str(e)
                )
            return None
        except Exception as e:
            logger.error("Hunter.io email finding failed", error=str(e), exc_info=True)
            return None

    async def verify_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Verify an email address.

        Args:
            email: Email address to verify

        Returns:
            Verification data dict or None

        Example result:
            {
                "status": "valid",
                "score": 95,
                "regexp": True,
                "gibberish": False,
                "disposable": False,
                "webmail": False,
                "mx_records": True,
                "smtp_server": True,
                "smtp_check": True,
                "accept_all": False
            }
        """
        if not self.api_key:
            logger.error("Hunter.io API key not configured")
            return None

        try:
            params = {
                "email": email,
                "api_key": self.api_key
            }

            logger.info("Verifying email", email=email)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/email-verifier",
                    params=params
                )

                response.raise_for_status()
                data = response.json()

            # Parse response
            if data.get("data"):
                result = data["data"]

                logger.info(
                    "Email verified",
                    email=email,
                    status=result.get("status"),
                    score=result.get("score")
                )

                return result
            else:
                logger.warning("Email verification returned no data", email=email)
                return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Hunter.io rate limit exceeded")
            else:
                logger.error(
                    "Hunter.io API error",
                    status_code=e.response.status_code,
                    error=str(e)
                )
            return None
        except Exception as e:
            logger.error("Hunter.io email verification failed", error=str(e), exc_info=True)
            return None

    async def get_domain_info(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get information about email patterns for a domain.

        Args:
            domain: Company domain (e.g., 'acme.com')

        Returns:
            Domain info dict with email pattern, etc. or None

        Example result:
            {
                "domain": "acme.com",
                "pattern": "{first}.{last}",
                "organization": "Acme Corp",
                "emails": [...]
            }
        """
        if not self.api_key:
            logger.error("Hunter.io API key not configured")
            return None

        try:
            params = {
                "domain": domain,
                "api_key": self.api_key
            }

            logger.info("Getting domain info", domain=domain)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/domain-search",
                    params=params
                )

                response.raise_for_status()
                data = response.json()

            # Parse response
            if data.get("data"):
                result = {
                    "domain": data["data"].get("domain"),
                    "pattern": data["data"].get("pattern"),
                    "organization": data["data"].get("organization"),
                    "emails": data["data"].get("emails", [])
                }

                logger.info(
                    "Domain info retrieved",
                    domain=domain,
                    pattern=result.get("pattern"),
                    email_count=len(result.get("emails", []))
                )

                return result
            else:
                logger.warning("Domain search returned no data", domain=domain)
                return None

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Hunter.io rate limit exceeded")
            else:
                logger.error(
                    "Hunter.io API error",
                    status_code=e.response.status_code,
                    error=str(e)
                )
            return None
        except Exception as e:
            logger.error("Hunter.io domain search failed", error=str(e), exc_info=True)
            return None
