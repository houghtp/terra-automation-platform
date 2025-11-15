"""
Centralized SQLAlchemy imports and utilities.
Use this module to standardize SQLAlchemy usage across all services.
"""

# Core SQLAlchemy imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import (
    select, insert, update, delete, func, and_, or_, not_,
    cast, case, text, String, Integer, Boolean, DateTime, JSON,
    asc, desc, nulls_first, nulls_last
)
from sqlalchemy.orm import selectinload, joinedload, aliased, contains_eager
from sqlalchemy.sql import Select
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Common type imports
from typing import List, Optional, Dict, Any, TypeVar, Generic, Union, Tuple
from datetime import datetime, timedelta, timezone
import structlog

# Export commonly used combinations
__all__ = [
    # Sessions
    'AsyncSession',

    # Query builders
    'select', 'insert', 'update', 'delete', 'text',

    # Functions
    'func', 'cast', 'case',

    # Logical operators
    'and_', 'or_', 'not_',

    # Types for casting
    'String', 'Integer', 'Boolean', 'DateTime', 'JSON',

    # Ordering
    'asc', 'desc', 'nulls_first', 'nulls_last',

    # Loading strategies
    'selectinload', 'joinedload', 'aliased', 'contains_eager',

    # Advanced
    'Select', 'pg_insert',

    # Python typing
    'List', 'Optional', 'Dict', 'Any', 'TypeVar', 'Generic', 'Union', 'Tuple',
    'datetime', 'timedelta', 'timezone', 'structlog',

    # Utilities
    'get_logger', 'tenant_cast_join'
]


def get_logger(name: str):
    """Standardized logger creation."""
    return structlog.get_logger(name)


def tenant_cast_join(tenant_id_column, tenant_table_id_column):
    """
    Standard pattern for joining tenant_id (String) with tenants.id (Integer).

    Args:
        tenant_id_column: The tenant_id column (String type)
        tenant_table_id_column: The tenants.id column (Integer type)

    Returns:
        SQLAlchemy join condition with proper type casting
    """
    return tenant_id_column == cast(tenant_table_id_column, String)
