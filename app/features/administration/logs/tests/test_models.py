"""
Tests for ApplicationLog model.
"""

import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.administration.logs.models import ApplicationLog


@pytest.mark.asyncio
async def test_application_log_creation(test_db_session: AsyncSession):
    """Test basic application log creation."""
    log = ApplicationLog(
        tenant_id="test-tenant",
        level="INFO",
        logger_name="test.logger",
        message="Test log message",
        user_id="test-user"
    )

    test_db_session.add(log)
    await test_db_session.commit()
    await test_db_session.refresh(log)

    assert log.id is not None
    assert log.tenant_id == "test-tenant"
    assert log.level == "INFO"
    assert log.logger_name == "test.logger"
    assert log.message == "Test log message"
    assert log.user_id == "test-user"
    assert isinstance(log.timestamp, datetime)


@pytest.mark.asyncio
async def test_application_log_to_dict(test_db_session: AsyncSession):
    """Test ApplicationLog to_dict method."""
    log = ApplicationLog(
        tenant_id="test-tenant",
        level="ERROR",
        logger_name="test.logger",
        message="Test error message",
        exception_type="ValueError",
        exception_message="Invalid value",
        extra_data={"key": "value"}
    )

    test_db_session.add(log)
    await test_db_session.commit()
    await test_db_session.refresh(log)

    log_dict = log.to_dict()

    assert isinstance(log_dict, dict)
    assert log_dict["id"] == log.id
    assert log_dict["tenant_id"] == "test-tenant"
    assert log_dict["level"] == "ERROR"
    assert log_dict["logger_name"] == "test.logger"
    assert log_dict["message"] == "Test error message"
    assert log_dict["exception_type"] == "ValueError"
    assert log_dict["exception_message"] == "Invalid value"
    assert log_dict["extra_data"] == {"key": "value"}
    assert "timestamp" in log_dict


@pytest.mark.asyncio
async def test_application_log_jsonb_field(test_db_session: AsyncSession):
    """Test JSONB extra_data field."""
    extra_data = {
        "request_id": "req-123",
        "user_agent": "test-agent",
        "nested": {"key": "value"}
    }

    log = ApplicationLog(
        tenant_id="test-tenant",
        level="DEBUG",
        logger_name="test.logger",
        message="Test with JSONB data",
        extra_data=extra_data
    )

    test_db_session.add(log)
    await test_db_session.commit()
    await test_db_session.refresh(log)

    assert log.extra_data == extra_data
    assert log.extra_data["nested"]["key"] == "value"