"""
Tests for LogService.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.administration.logs.models import ApplicationLog
from app.features.administration.logs.services import LogService


@pytest.mark.asyncio
async def test_get_logs_list(test_db_session: AsyncSession):
    """Test getting paginated logs list."""
    service = LogService(test_db_session)

    # Create test logs
    logs = [
        ApplicationLog(
            tenant_id="tenant1",
            level="INFO",
            logger_name="test.logger",
            message=f"Test message {i}"
        ) for i in range(5)
    ]

    for log in logs:
        test_db_session.add(log)
    await test_db_session.commit()

    # Test pagination
    result = await service.get_logs_list(limit=3, offset=0)

    assert "data" in result
    assert "total" in result
    assert result["total"] == 5
    assert len(result["data"]) == 3
    assert result["limit"] == 3
    assert result["offset"] == 0


@pytest.mark.asyncio
async def test_get_logs_list_with_filters(test_db_session: AsyncSession):
    """Test getting logs with filters."""
    service = LogService(test_db_session)

    # Create test logs with different levels and tenants
    logs = [
        ApplicationLog(tenant_id="tenant1", level="INFO", logger_name="test.logger", message="Info message"),
        ApplicationLog(tenant_id="tenant1", level="ERROR", logger_name="test.logger", message="Error message"),
        ApplicationLog(tenant_id="tenant2", level="INFO", logger_name="test.logger", message="Another info"),
    ]

    for log in logs:
        test_db_session.add(log)
    await test_db_session.commit()

    # Test tenant filter
    result = await service.get_logs_list(tenant_id="tenant1")
    assert result["total"] == 2

    # Test level filter
    result = await service.get_logs_list(level="ERROR")
    assert result["total"] == 1
    assert result["data"][0]["level"] == "ERROR"

    # Test logger name filter
    result = await service.get_logs_list(logger_name="test")
    assert result["total"] == 3


@pytest.mark.asyncio
async def test_get_log_by_id(test_db_session: AsyncSession):
    """Test getting a specific log by ID."""
    service = LogService(test_db_session)

    log = ApplicationLog(
        tenant_id="test-tenant",
        level="DEBUG",
        logger_name="test.logger",
        message="Debug message"
    )

    test_db_session.add(log)
    await test_db_session.commit()
    await test_db_session.refresh(log)

    # Test getting existing log
    result = await service.get_log_by_id(log.id)
    assert result is not None
    assert result.id == log.id
    assert result.message == "Debug message"

    # Test getting non-existent log
    result = await service.get_log_by_id(99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_logs_summary(test_db_session: AsyncSession):
    """Test getting logs summary statistics."""
    service = LogService(test_db_session)

    # Create test logs with different levels
    logs = [
        ApplicationLog(tenant_id="tenant1", level="INFO", logger_name="test", message="Info 1"),
        ApplicationLog(tenant_id="tenant1", level="INFO", logger_name="test", message="Info 2"),
        ApplicationLog(tenant_id="tenant1", level="ERROR", logger_name="test", message="Error 1"),
        ApplicationLog(tenant_id="tenant2", level="WARNING", logger_name="test", message="Warning 1"),
    ]

    for log in logs:
        test_db_session.add(log)
    await test_db_session.commit()

    result = await service.get_logs_summary()

    assert "level_counts" in result
    assert "total_logs" in result
    assert "tenants" in result
    assert "recent_errors" in result

    assert result["level_counts"]["INFO"] == 2
    assert result["level_counts"]["ERROR"] == 1
    assert result["level_counts"]["WARNING"] == 1
    assert result["total_logs"] == 4
    assert len(result["tenants"]) == 2


@pytest.mark.asyncio
async def test_get_tenant_list(test_db_session: AsyncSession):
    """Test getting list of tenants with log counts."""
    service = LogService(test_db_session)

    # Create logs for different tenants
    logs = [
        ApplicationLog(tenant_id="tenant-a", level="INFO", logger_name="test", message="Message 1"),
        ApplicationLog(tenant_id="tenant-a", level="ERROR", logger_name="test", message="Message 2"),
        ApplicationLog(tenant_id="tenant-b", level="INFO", logger_name="test", message="Message 3"),
    ]

    for log in logs:
        test_db_session.add(log)
    await test_db_session.commit()

    result = await service.get_tenant_list()

    assert len(result) == 2
    tenant_dict = {item["tenant_id"]: item["log_count"] for item in result}
    assert tenant_dict["tenant-a"] == 2
    assert tenant_dict["tenant-b"] == 1


@pytest.mark.asyncio
async def test_cleanup_old_logs(test_db_session: AsyncSession):
    """Test cleaning up old log entries."""
    service = LogService(test_db_session)

    # Create logs with different timestamps
    old_time = datetime.now(timezone.utc) - timedelta(days=40)
    recent_time = datetime.now(timezone.utc) - timedelta(days=10)

    logs = [
        ApplicationLog(tenant_id="test", level="INFO", logger_name="test", message="Old log", timestamp=old_time),
        ApplicationLog(tenant_id="test", level="INFO", logger_name="test", message="Recent log", timestamp=recent_time),
    ]

    for log in logs:
        test_db_session.add(log)
    await test_db_session.commit()

    # Clean up logs older than 30 days
    result = await service.cleanup_old_logs(days=30)

    assert result["deleted_count"] == 1
    assert result["days"] == 30

    # Verify only recent log remains
    remaining_result = await service.get_logs_list()
    assert remaining_result["total"] == 1
    assert remaining_result["data"][0]["message"] == "Recent log"