from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, constr


class Ga4ClientCreate(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    notes: Optional[str] = None
    status: Optional[constr(strip_whitespace=True, max_length=32)] = "active"


class Ga4ClientUpdate(BaseModel):
    name: Optional[constr(strip_whitespace=True, max_length=255)] = None
    notes: Optional[str] = None
    status: Optional[constr(strip_whitespace=True, max_length=32)] = None


class Ga4ClientResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    notes: Optional[str]
    status: str

    class Config:
        orm_mode = True
