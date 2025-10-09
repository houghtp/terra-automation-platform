# FastAPI/SQLAlchemy Best Practices Implementation Guide

## 🎯 **Objective**: Make Users slice the gold standard for all other slices

### 📋 **Step-by-Step Implementation Plan**

#### **Phase 1: Core Infrastructure** ✅
- [x] Create centralized SQLAlchemy imports (`app/features/core/sqlalchemy_imports.py`)
- [x] Create enhanced BaseService with common patterns (`app/features/core/enhanced_base_service.py`)
- [x] Document proper abstraction patterns

## Phase 2: Users Slice Gold Standard Implementation

**Status**: ✅ **COMPLETED**

Converting the Users slice to demonstrate gold standard patterns:

### Users Services Refactoring
- [x] **UserCrudService** - Enhanced BaseService inheritance, centralized imports ✅
- [x] **UserFormService** - Query builders, tenant-aware forms ✅
- [x] **UserDashboardService** - Statistics with enhanced patterns ✅

#### **Phase 3: Documentation & Templates**
- [ ] **Step 10**: Create service templates based on Users implementation
- [ ] **Step 11**: Create route templates
- [ ] **Step 12**: Create model templates
- [ ] **Step 13**: Document standardization checklist

#### **Phase 4: Apply to Other Slices** (Future)
- [ ] SMTP slice standardization
- [ ] Secrets slice standardization
- [ ] Tenants slice standardization
- [ ] Audit slice standardization (readonly pattern)
- [ ] Logs slice standardization (readonly pattern)

---

## 🏗️ **Best Practices Standards**

### **Service Layer Standards**
1. **Inheritance**: All services inherit from `BaseService[T]` or `EnhancedBaseService[T]`
2. **Imports**: Use centralized `sqlalchemy_imports` module
3. **Error Handling**: Consistent error handling with `handle_error()`
4. **Logging**: Structured logging with `log_operation()`
5. **Query Building**: Use base service query builders
6. **Type Safety**: Full type hints and Generic types
7. **Validation**: Separate validation methods
8. **Response Mapping**: Consistent model-to-response conversion

### **Route Layer Standards**
1. **Dependency Injection**: Proper service injection patterns
2. **Error Responses**: Standardized HTTP error responses
3. **Request/Response Models**: Pydantic models for all endpoints
4. **Async Patterns**: Proper async/await usage
5. **Documentation**: OpenAPI docs with examples
6. **Authentication**: Consistent auth patterns

### **Model Layer Standards**
1. **Pydantic Models**: Request/Response models with validation
2. **SQLAlchemy Models**: Proper relationships and indexes
3. **Type Annotations**: Full type coverage
4. **Validation**: Custom validators where needed
5. **Serialization**: Consistent `.to_dict()` methods

### **File Organization Standards**
```
slice_name/
├── services/
│   ├── __init__.py
│   ├── crud_services.py      # Core CRUD operations
│   ├── form_services.py      # Form-specific logic
│   └── dashboard_services.py # Dashboard/stats logic
├── routes/
│   ├── __init__.py
│   ├── api_routes.py         # JSON API endpoints
│   ├── crud_routes.py        # HTMX CRUD pages
│   ├── form_routes.py        # Form handling
│   └── dashboard_routes.py   # Dashboard pages
├── models.py                 # Pydantic request/response models
├── db_models.py             # SQLAlchemy database models
└── tests/
```

---

## 📊 **Implementation Tracking**

### **Users Slice Progress**
- [x] **Infrastructure**: Core imports and enhanced BaseService created ✅
- [x] **crud_services.py**: Migrate to enhanced BaseService ✅
  - ✅ **GOLD STANDARD IMPLEMENTED**: Full FastAPI/SQLAlchemy best practices
  - ✅ Enhanced BaseService with proper abstraction
  - ✅ Centralized imports and utilities
  - ✅ Type-safe query building and tenant JOINs
  - ✅ Separated validation and helper methods
  - ✅ Consistent error handling and logging
- [ ] **form_services.py**: Apply best practices ⏳
- [ ] **dashboard_services.py**: Apply best practices
- [ ] **API routes**: Standardize error handling and responses
- [ ] **CRUD routes**: Standardize HTMX patterns
- [ ] **Form routes**: Standardize form handling
- [ ] **Dashboard routes**: Standardize dashboard patterns
- [ ] **Models**: Validate Pydantic model standards
- [ ] **Testing**: Comprehensive test coverage

### **Future Slices**
- [ ] **SMTP**: Not started
- [ ] **Secrets**: Not started
- [ ] **Tenants**: Not started
- [ ] **Audit** (readonly): Not started
- [ ] **Logs** (readonly): Not started

---

## 🔍 **Readonly Services Pattern**

For readonly services (Audit, Logs), we should still use BaseService because:

### **Benefits of BaseService for Readonly**:
1. **Consistent Patterns**: Same query building, error handling, logging
2. **Tenant Scoping**: Proper tenant isolation for security
3. **Future Extensibility**: Easy to add write operations later
4. **Code Consistency**: Developers know one pattern across all services
5. **Maintenance**: Centralized updates to query patterns

### **Readonly BaseService Usage**:
```python
class AuditService(BaseService[AuditLog]):
    # Inherit all query builders, tenant scoping, error handling
    # Just don't implement create/update/delete methods
    pass
```

---

## ✅ **Completion Checklist Per Slice**

When implementing each slice, verify:

- [ ] Services inherit from BaseService
- [ ] Centralized imports used
- [ ] Proper error handling implemented
- [ ] Structured logging added
- [ ] Query builders used instead of raw queries
- [ ] Type hints on all methods
- [ ] Validation methods separated
- [ ] Response mapping consistent
- [ ] Route dependency injection proper
- [ ] HTTP error responses standardized
- [ ] Tests cover main functionality
- [ ] Documentation updated

---

**Next Action**: Begin Phase 2, Step 1 - Update UserCrudService
