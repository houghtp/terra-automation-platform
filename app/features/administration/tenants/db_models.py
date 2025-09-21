from typing import Any, Dict, Optional
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func

from app.features.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active")
    tier = Column(String(50), nullable=True, default="free")
    
    # Contact information
    contact_email = Column(String(255), nullable=True)
    contact_name = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    
    # Limits and configuration
    max_users = Column(Integer, nullable=True, default=10)
    
    # JSON fields for flexible data
    features = Column(JSON, nullable=True, default=dict)
    settings = Column(JSON, nullable=True, default=dict)
    # `metadata` is a reserved attribute name on DeclarativeBase; use `meta` as the Python attribute
    meta = Column('metadata', JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "tier": self.tier,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "website": self.website,
            "max_users": self.max_users,
            "features": self.features or {},
            "settings": self.settings or {},
            "metadata": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
