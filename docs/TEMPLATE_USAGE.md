# 🚀 FastAPI Vertical Slice Template - Quick Start Guide

This guide shows you how to use this template to create a new FastAPI project.

## 🎯 Creating a New Project

### Option 1: Using the Creation Script (Recommended)

The template includes a script that handles all the setup and renaming for you:

```bash
# From the template directory
./scripts/create_new_project.sh my-awesome-app

# Or specify a target directory
./scripts/create_new_project.sh my-awesome-app /path/to/projects
```

**What the script does:**
- ✅ Copies all template files to a new directory
- ✅ Removes git history and initializes a new repo
- ✅ Renames all references from `fastapi-vertical-slice-template` to your project name
- ✅ Updates database names, Docker services, and configurations
- ✅ Creates a new `.env` file from the template
- ✅ Updates Python imports and module references
- ✅ Creates an initial commit

### Option 2: Manual Setup

If you prefer to do it manually:

```bash
# 1. Clone and rename
git clone <this-template-repo> my-new-project
cd my-new-project

# 2. Remove template git history
rm -rf .git
git init

# 3. Create environment file
cp .env.example .env

# 4. Manually update references in:
#    - README.md
#    - docker-compose.yml (database names)
#    - app/main.py (project description)
#    - Any other files with "fastapi-vertical-slice-template"
```

## 🛠️ After Creating Your Project

### 1. Configure Environment
```bash
cd your-new-project
nano .env  # Update with your settings
```

Key settings to review:
- Database connection details
- Secret keys
- Debug settings
- SMTP configuration (if using email features)

### 2. Start Development Environment
```bash
# Using Docker (recommended)
docker-compose up -d

# Or using the setup script
./setup.sh
```

### 3. Initialize Database
```bash
# Run migrations
python manage_db.py upgrade

# Seed demo data (optional)
python app/seed_data.py
```

### 4. Verify Installation
- **Web App**: http://localhost:8000
- **Admin Dashboard**: http://localhost:8000/administration
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📁 Project Structure After Creation

```
your-new-project/
├── app/
│   ├── features/           # All feature slices
│   │   ├── auth/          # Authentication
│   │   ├── administration/ # Admin features
│   │   ├── demo/          # Demo slice (can be removed)
│   │   └── core/          # Shared infrastructure
│   ├── static/            # Frontend assets
│   └── templates/         # Shared templates
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── migrations/            # Database migrations
├── docker-compose.yml     # Docker setup
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables
└── README.md             # Project documentation
```

## 🎯 Next Steps

### 1. Customize Your Project
- Update `README.md` with your project details
- Modify the demo slice or remove it entirely
- Add your own vertical slices following the pattern

### 2. Set Up Version Control
```bash
# Add your remote repository
git remote add origin https://github.com/yourusername/your-new-project.git

# Push to your repo
git push -u origin main
```

### 3. Create Your First Feature Slice
```bash
# Use the slice creation guide
mkdir -p app/features/products/{models,routes,services,templates/products/partials,tests}

# Follow the patterns in docs/slice_creation_guide.md
```

## 🔧 Development Workflow

### Adding New Features
1. Create a new vertical slice in `app/features/`
2. Follow the established patterns (models, routes, services, templates)
3. Add tests for your feature
4. Update routing in `app/main.py`

### Database Changes
```bash
# Create migration
python manage_db.py revision --autogenerate -m "Add products table"

# Apply migration
python manage_db.py upgrade
```

### Running Tests
```bash
pytest                    # All tests
pytest app/features/auth/ # Specific feature tests
```

## 📚 Documentation

After creating your project, check out:
- `docs/README.md` - Main documentation
- `docs/slice_creation_guide.md` - How to add new features
- `docs/INDEX.md` - Complete documentation index

## 🎉 You're Ready!

Your FastAPI Vertical Slice project is now set up and ready for development. The template provides:

- ✅ **Multi-tenant architecture** ready
- ✅ **Authentication system** with JWT
- ✅ **Admin dashboard** with HTMX
- ✅ **Database setup** with migrations
- ✅ **Docker configuration** for easy deployment
- ✅ **Comprehensive test suite** structure
- ✅ **Production-ready** configuration

Happy coding! 🚀
