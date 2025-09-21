# FastAPI Template - Quick Reference

## 🚀 Quick Start Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python3 -m uvicorn app.main:app --reload

# Run tests (clean output)
PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning" python3 -m pytest

# Run with Docker
docker-compose up

# Database migration
alembic upgrade head
```

## 📁 Key Directories

- **`app/`** - Main application code
- **`tests/`** - All test files
- **`docs/`** - Complete documentation
- **`scripts/`** - Utility scripts
- **`monitoring/`** - Observability configs

## 🔗 Important Links

- **Documentation**: [docs/INDEX.md](docs/INDEX.md)
- **API Docs**: http://localhost:8000/docs (when running)
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## 🎯 Production Ready Features

✅ Authentication & JWT tokens
✅ Multi-tenant architecture
✅ Comprehensive monitoring
✅ Database migrations
✅ Docker containerization
✅ Production configurations
✅ Complete test suite

---
*For complete setup instructions, see [README.md](README.md)*
