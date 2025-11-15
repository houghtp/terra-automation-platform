"""
Pydantic schemas for the connectors feature slice.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.features.core.schemas import PaginatedRequest
from .models import ConnectorStatus


class ConnectorCatalogResponse(BaseModel):
    """Response schema for catalog connector."""

    id: str
    key: str
    name: str
    description: Optional[str] = None
    category: str
    icon: Optional[str] = None
    auth_type: str
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    default_config_schema: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }


class ConnectorCreate(BaseModel):
    """Schema for creating a new connector instance."""

    catalog_id: str = Field(..., description="ID of the catalog connector to install")
    name: str = Field(..., min_length=2, max_length=255, description="User-defined name for this connector instance")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration matching catalog schema")
    auth: Dict[str, Any] = Field(default_factory=dict, description="Authentication credentials (will be encrypted)")
    tags: List[str] = Field(default_factory=list, description="Tags for organization")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Connector name cannot be empty")
        return value.strip()


class ConnectorUpdate(BaseModel):
    """Schema for updating a connector instance."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    config: Optional[Dict[str, Any]] = None
    auth: Optional[Dict[str, Any]] = None
    status: Optional[ConnectorStatus] = None
    tags: Optional[List[str]] = None


class ConnectorResponse(BaseModel):
    """Response schema for connector instance with joined catalog info."""

    id: str
    tenant_id: str
    catalog_id: str
    name: str
    status: str
    config: Dict[str, Any]
    auth_configured: bool
    tags: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None

    # Joined fields from catalog
    catalog_key: Optional[str] = None
    catalog_name: Optional[str] = None
    catalog_description: Optional[str] = None
    catalog_category: Optional[str] = None
    catalog_icon: Optional[str] = None
    catalog_auth_type: Optional[str] = None
    catalog_capabilities: Optional[Dict[str, Any]] = None

    model_config = {
        "from_attributes": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat() if v else None
        }
    }


class ConnectorSearchFilter(PaginatedRequest):
    """Search and filter parameters for connectors."""

    search: Optional[str] = None
    category: Optional[str] = None
    status: Optional[ConnectorStatus] = None


class ConfigValidationRequest(BaseModel):
    """Request for validating config against catalog schema."""

    catalog_key: str = Field(..., description="Catalog connector key (e.g., 'twitter')")
    config: Dict[str, Any] = Field(..., description="Configuration to validate")


class ConfigValidationResponse(BaseModel):
    """Response from config validation."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


__all__ = [
    "ConfigValidationRequest",
    "ConfigValidationResponse",
    "ConnectorCatalogResponse",
    "ConnectorCreate",
    "ConnectorResponse",
    "ConnectorSearchFilter",
    "ConnectorUpdate",
]
