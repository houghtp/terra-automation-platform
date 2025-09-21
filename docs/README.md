# 🚀 TerraAutomationPlatform

A modern, production-ready template for building FastAPI applications using **Vertical Slice Architecture** with HTMX and Tabler Admin Dashboard.

## 🎯 Features

- **Vertical Slice Architecture** - Each feature owns its complete stack (models, routes, services, templates, tests)
- **FastAPI** - Modern, fast Python web framework with automatic API docs
- **HTMX** - Dynamic web pages without complex JavaScript frameworks
- **Tabler** - Beautiful, responsive admin dashboard UI
- **PostgreSQL** - Robust database with async SQLAlchemy
- **Alembic** - Database migrations
- **Docker** - Containerized for easy deployment
- **Type Hints** - Fully typed Python code
- **SOLID Principles** - Clean, maintainable architecture

## 🏗️ Architecture Overview

```
app/
├── core/               # Shared infrastructure
├── demo/              # Example vertical slice
│   ├── models/        # SQLAlchemy models
│   ├── routes/        # FastAPI endpoints
│   ├── services/      # Business logic
│   ├── templates/     # Jinja2 templates
│   └── tests/         # Unit tests
├── static/            # CSS, JS, images
└── templates/         # Shared templates
```

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone <your-repo> my-new-project
cd my-new-project
cp .env.example .env  # Configure your database
```

### 2. Run with Docker
```bash
docker-compose up -d
```

### 3. Setup Database
```bash
# Run migrations
python manage_db.py upgrade

# Seed demo data
python app/seed_data.py
```

### 4. Visit Your App
- **Web App**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🔧 Creating New Slices

To add a new feature (e.g., "products"):

### 1. Create Slice Structure
```bash
mkdir -p app/products/{models,routes,services,templates/products/partials,tests}
```

### 2. Create Model (`app/products/models/product.py`)
```python
from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description
        }
```

### 3. Create Service (`app/products/services/product_service.py`)
```python
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.products.models.product import Product

class ProductService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> List[Product]:
        result = await self.session.execute(select(Product))
        return result.scalars().all()

    async def create(self, name: str, description: str) -> Product:
        product = Product(name=name, description=description)
        self.session.add(product)
        await self.session.commit()
        return product
```

### 4. Create Routes (`app/products/routes/routes.py`)
```python
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_session
from app.core.templates import templates
from app.products.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])

@router.get("/")
async def list_products(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    service = ProductService(session)
    products = await service.get_all()

    return templates.TemplateResponse(
        "products/list.html",
        {"request": request, "products": products}
    )
```

### 5. Add to Main App (`app/main.py`)
```python
from app.products.routes import routes as product_routes
app.include_router(product_routes.router)
```

## 🎨 Frontend Patterns

### HTMX Modal Forms
```html
<button class="btn btn-outline-primary"
        hx-get="/products/partials/form"
        hx-target="#modal-body"
        hx-swap="innerHTML">
    Add Product
</button>
```

### Tabulator Tables
```javascript
new Tabulator("#products-table", {
    ajaxURL: "/products/api/data",
    layout: "fitColumns",
    columns: [
        {title: "Name", field: "name"},
        {title: "Description", field: "description"}
    ]
});
```

## 🛠️ Development

### Database Migrations
```bash
# Create migration
python manage_db.py revision --autogenerate -m "Add products table"

# Apply migrations
python manage_db.py upgrade
```

### Running Tests
```bash
pytest app/products/tests/
```

### Code Style
- Use **type hints** everywhere
- Add **docstrings** to all functions/classes
- Follow **SOLID principles**
- Keep slices **independent**

## 📁 Slice Guidelines

Each vertical slice should:
- ✅ Be **self-contained** (own models, routes, services, templates)
- ✅ Have **clear boundaries** (minimal dependencies on other slices)
- ✅ Follow **consistent patterns** (same structure across slices)
- ✅ Include **tests** for all layers
- ❌ Not access other slices' models directly
- ❌ Not share services between slices

## 🔒 Security

- CSP-compliant (no inline scripts/styles)
- Type-safe database queries
- Input validation with Pydantic
- Environment-based configuration

## 📦 Deployment

### Production Docker
```bash
docker build -t my-app .
docker run -p 8000:8000 my-app
```

### Environment Variables
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
SECRET_KEY=your-secret-key
DEBUG=false
```

## 🤝 Contributing

1. Follow the vertical slice architecture
2. Add tests for new features
3. Update documentation
4. Use type hints and docstrings

## 📄 License

MIT License - feel free to use this template for any project!

---

## Multi-tenant features (summary)

This template includes multi-tenant readiness scaffolding. Key points:

- `app/middleware/tenant.py` sets a per-request `tenant_id` ContextVar for logging and request-scoped logic.
- `app/deps/tenant.py` provides `tenant_dependency()` which prefers a verified token tenant, validates header mismatches, and falls back to middleware or `unknown`.
- Demo slice updated: `app/demo/models/models.py` includes a `tenant_id` column and services/routes are tenant-scoped.
- Structured JSON logging includes `request_id` and `tenant_id` for easy observability and correlation.
- The migration example `migrations/versions/20250831_add_tenant_id_demo_items.py` is included for demo usage.

Run `./scripts/setup_dev.sh` to bootstrap a development environment quickly (installs deps, runs migrations, seeds demo data).

See `PRODUCTION.md` for full details about tenant onboarding, provider integrations, secrets, and operational controls.

**Happy coding!** 🎉 This template gives you a solid foundation for building scalable FastAPI applications.
