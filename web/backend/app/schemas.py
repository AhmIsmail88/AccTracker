# -*- coding: utf-8 -*-
"""نماذج طلبات API (Pydantic v2)."""
from typing import Optional

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    type: str = Field(description="PROJECT / REGION / ZONE / LOCATION")
    name: str
    parent_code: Optional[str] = None
    code: Optional[str] = None
    status: str = "ACTIVE"


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    parent_code: Optional[str] = None
    status: Optional[str] = None


class ConflictResolve(BaseModel):
    action: str = Field(pattern="^(RESOLVED|IGNORED)$")
