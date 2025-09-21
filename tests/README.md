# Testing Guide

This template provides a comprehensive testing structure designed for vertical slice architecture. Each slice contains its own complete test suite while maintaining consistency across the application.

## Test Structure

```
tests/                           # Cross-slice and integration tests
├── ui/                         # Global UI tests (Playwright)
├── conftest.py                 # Global test fixtures
└── conftest_playwright.py     # Playwright fixtures and helpers

app/{slice}/tests/              # Slice-specific tests
├── unit/                       # Fast, isolated component tests
├── integration/                # Cross-component tests within slice
├── ui/                         # Slice-specific UI tests (Playwright)
├── e2e/                        # End-to-end workflow tests
└── conftest.py                 # Slice-specific fixtures
```

## Test Categories

### Unit Tests (`unit/`)
- Test individual components in isolation
- Fast execution (< 1s per test)
- No database or external dependencies
- Mock external services

### Integration Tests (`integration/`)
- Test component interactions within a slice
- Use test database
- Test API endpoints and database operations
- Moderate execution time

### UI Tests (`ui/`)
- Test user interface using Playwright
- Test HTMX interactions and form submissions
- Browser-based testing
- Slower execution but critical for UX

### E2E Tests (`e2e/`)
- Test complete user workflows
- Cross-slice interactions
- Full application stack
- Slowest but most comprehensive

## Running Tests

```bash
# All tests
pytest

# Specific categories
pytest -m unit                  # Unit tests only
pytest -m integration          # Integration tests
pytest -m ui                   # UI tests (requires Playwright)
pytest -m e2e                  # End-to-end tests

# Specific slice
pytest app/administration/users/tests/

# Specific test file
pytest app/administration/users/tests/unit/test_models.py
```

## UI Testing with Playwright

### Setup
```bash
# Install Playwright browsers
playwright install
```

### HTMX Testing Patterns

Use the `HTMXTestHelper` for HTMX interactions:

```python
async def test_create_user_modal(self, authenticated_page: Page, htmx_helper: HTMXTestHelper):
    await authenticated_page.goto("/administration/users")

    # Click button and wait for HTMX response
    await htmx_helper.click_and_wait_htmx(
        '[data-testid="create-user-btn"]',
        "**/partials/form"
    )

    # Verify modal loaded
    await expect(authenticated_page.locator("#modal-form")).to_be_visible()
```

### Available Fixtures

- `authenticated_page`: Pre-authenticated browser page
- `mobile_page`: Mobile viewport page
- `tablet_page`: Tablet viewport page
- `htmx_helper`: HTMX interaction utilities

## Writing Tests for New Slices

### 1. Create Test Structure
```bash
mkdir -p app/your_slice/tests/{unit,integration,ui,e2e}
```

### 2. Create conftest.py
Copy and adapt from existing slice:
```python
# app/your_slice/tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tests.conftest import test_db_engine

@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
```

### 3. Unit Tests Example
```python
# app/your_slice/tests/unit/test_models.py
import pytest
from your_slice.models.models import YourModel

class TestYourModel:
    def test_model_creation(self):
        model = YourModel(name="test")
        assert model.name == "test"
```

### 4. Integration Tests Example
```python
# app/your_slice/tests/integration/test_routes.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_endpoint(async_client: AsyncClient, test_db_session):
    response = await async_client.post("/your_slice/", json={"name": "test"})
    assert response.status_code == 201
```

### 5. UI Tests Example
```python
# app/your_slice/tests/ui/test_your_slice.py
import pytest
from playwright.async_api import Page, expect

@pytest.mark.ui
@pytest.mark.asyncio
class TestYourSliceUI:
    async def test_page_loads(self, authenticated_page: Page):
        await authenticated_page.goto("/your_slice")
        await expect(authenticated_page.locator("h1")).to_be_visible()
```

## Test Data and Factories

Use Factory Boy for consistent test data:

```python
# app/your_slice/tests/factories.py
import factory
from your_slice.models.models import YourModel

class YourModelFactory(factory.Factory):
    class Meta:
        model = YourModel

    name = factory.Faker("name")
    email = factory.Faker("email")
```

## Best Practices

### General
- Keep tests independent and idempotent
- Use descriptive test names
- Follow AAA pattern: Arrange, Act, Assert
- One assertion per test when possible

### Database Tests
- Always use test database fixtures
- Clean state between tests (handled by fixtures)
- Don't rely on specific IDs or order

### UI Tests
- Use data-testid attributes for reliable selectors
- Wait for elements instead of using fixed delays
- Test user workflows, not implementation details
- Group related UI tests in classes

### Performance
- Keep unit tests fast (< 1s)
- Use appropriate test category
- Consider parallel execution for independent tests

## Debugging Tests

### Failed Tests
```bash
# Run with verbose output
pytest -v

# Stop on first failure
pytest -x

# Run specific test with output
pytest -s app/your_slice/tests/unit/test_models.py::TestYourModel::test_creation
```

### UI Test Debugging
```bash
# Run with browser visible
TEST_HEADLESS=false pytest -m ui

# Enable tracing
pytest --tracing=on -m ui
```

## CI/CD Integration

Tests are organized for efficient CI/CD pipelines:

```yaml
# Example CI stages
test-unit:
  script: pytest -m unit

test-integration:
  script: pytest -m integration
  services: [postgres]

test-ui:
  script: pytest -m ui
  artifacts:
    - test-results/
    - screenshots/
```

## Template Usage

When using this template for new projects:

1. Review and adapt test examples
2. Update authentication in `conftest_playwright.py`
3. Customize fixtures for your domain
4. Add slice-specific test utilities
5. Configure CI/CD pipeline stages

This testing structure scales with your application while maintaining consistency and reliability across all slices.
