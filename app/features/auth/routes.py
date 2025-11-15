"""
Authentication routes providing JWT-based authentication endpoints.
"""
import os
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.core.database import get_db
from app.features.core.templates import templates
from app.features.core.rate_limiter import rate_limit_login, rate_limit_register, rate_limit_refresh
from app.features.core.security import validate_password_complexity
from app.features.core.sqlalchemy_imports import get_logger
from app.deps.tenant import tenant_dependency

logger = get_logger(__name__)

# Simple tenant resolution for login (avoids circular dependency)
async def simple_tenant_dependency(request: Request) -> str:
    """Simple tenant resolution for auth endpoints that doesn't depend on tokens."""
    return request.headers.get("x-tenant-id") or "global"

async def get_user_tenant_for_login(session: AsyncSession, email: str) -> str:
    """Find the tenant for a user by email for login purposes."""
    from app.features.auth.models import User

    # Look up user across all tenants to find their actual tenant
    result = await session.execute(
        select(User.tenant_id).where(User.email == email, User.is_active == True)
    )
    tenant_id = result.scalar_one_or_none()

    return tenant_id or "global"

from app.features.auth.services import AuthService
from app.features.auth.dependencies import get_current_active_user, get_optional_current_user
from app.features.auth.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse,
    AuthStatusResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordResetResponse
)
from app.features.auth.models import User

router = APIRouter(tags=["auth"])

# Include MFA routes
from .mfa_routes import router as mfa_router
router.include_router(mfa_router)

# Include Tenant Switch routes
from app.features.auth.tenant_switch_routes.tenant_switch_routes import router as tenant_switch_router
router.include_router(tenant_switch_router)


# API Endpoints (JSON)

@router.post("/register", response_model=TokenResponse)
async def register_user(
    request: Request,
    user_data: UserRegisterRequest,
    tenant_id: str = Depends(tenant_dependency),
    session: AsyncSession = Depends(get_db),
    _rate_limit: dict = Depends(rate_limit_register)
):
    """Register a new user and return tokens."""
    try:
        # Initialize auth service with session
        auth_service = AuthService(session)

        # Create user
        user = await auth_service.create_user(
            email=user_data.email,
            password=user_data.password,
            tenant_id=tenant_id,
            role=user_data.role
        )

        await session.commit()

        # Create tokens
        access_token, refresh_token = auth_service.create_tokens(user)

        # Get token expiration time
        expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expire_minutes * 60  # Convert to seconds
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    request: Request,
    login_data: UserLoginRequest,
    tenant_id: str = Depends(tenant_dependency),
    session: AsyncSession = Depends(get_db),
    _rate_limit: dict = Depends(rate_limit_login)
):
    """Authenticate user and return tokens."""
    # For API login, if no specific tenant provided, find user's actual tenant
    actual_tenant_id = tenant_id
    if tenant_id == "global":
        actual_tenant_id = await get_user_tenant_for_login(session, login_data.email)

    # Initialize auth service with session
    auth_service = AuthService(session)

    user = await auth_service.authenticate_user(
        email=login_data.email,
        password=login_data.password,
        tenant_id=actual_tenant_id
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create tokens
    access_token, refresh_token = auth_service.create_tokens(user)

    # Get token expiration time
    expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expire_minutes * 60  # Convert to seconds
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    refresh_data: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db),
    _rate_limit: dict = Depends(rate_limit_refresh)
):
    """Refresh access token using refresh token."""
    # Initialize auth service with session
    auth_service = AuthService(session)

    access_token = await auth_service.refresh_access_token(
        refresh_token=refresh_data.refresh_token
    )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Note: We don't rotate refresh tokens in this implementation
    # In production, consider rotating refresh tokens for better security

    # Get token expiration time
    expire_minutes = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_data.refresh_token,  # Return same refresh token
        expires_in=expire_minutes * 60
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user information."""
    return UserResponse(**current_user.to_dict())


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    current_user: User = Depends(get_optional_current_user)
):
    """Get authentication status (for frontend)."""
    if current_user:
        return AuthStatusResponse(
            authenticated=True,
            user=UserResponse(**current_user.to_dict())
        )
    else:
        return AuthStatusResponse(authenticated=False)


@router.post("/logout")
async def logout(
    request: Request,
    current_user: User = Depends(get_optional_current_user)
):
    """Logout endpoint - clears tokens on client side."""
    # Since we're using stateless JWT tokens, logout is handled client-side
    # by removing tokens from localStorage/cookies
    # In a production system, you might want to implement token blacklisting
    return JSONResponse(
        content={"message": "Logged out successfully"},
        status_code=200
    )


# HTML/HTMX Endpoints (Web Interface)

@router.get("/", response_class=HTMLResponse)
async def user_management_page(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Main user management page."""
    return templates.TemplateResponse(
        "auth/user_management.html",
        {
            "request": request,
            "user": current_user,
            "title": "User Management",
            "description": "Manage user accounts and permissions"
        }
    )


@router.get("/api/list")
async def list_users_api(
    request: Request,
    tenant_id: str = Depends(tenant_dependency),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """API endpoint to list users for table."""
    try:
        # Query users directly (list_users method doesn't exist in AuthService)
        from sqlalchemy import select
        stmt = select(User).where(User.tenant_id == tenant_id)
        result = await session.execute(stmt)
        users = result.scalars().all()

        # Convert to table format
        user_data = []
        for user in users:
            user_dict = user.to_dict()
            user_dict['created_at_formatted'] = user.created_at.strftime('%Y-%m-%d %H:%M') if user.created_at else ''
            user_dict['last_login_formatted'] = user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never'
            user_data.append(user_dict)

        return JSONResponse(content=user_data)

    except Exception as e:
        logger.exception("Failed to list users")
        raise HTTPException(status_code=500, detail="Failed to load users")


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: User = Depends(get_optional_current_user)
):
    """Login page."""
    # Redirect if already authenticated
    if current_user:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "user": current_user, "redirect": True}
        )

    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request}
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: User = Depends(get_optional_current_user)
):
    """Registration page."""
    # Redirect if already authenticated
    if current_user:
        return templates.TemplateResponse(
            "auth/register.html",
            {"request": request, "user": current_user, "redirect": True}
        )

    return templates.TemplateResponse(
        "auth/register.html",
        {"request": request}
    )


@router.post("/login/form")
async def login_form_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db)
):
    """Handle login form submission via HTMX."""
    try:
        print(f"🔐 Login attempt: {email}")

        # First, find the user's actual tenant
        actual_tenant_id = await get_user_tenant_for_login(session, email)
        print(f"🔍 Found tenant for {email}: {actual_tenant_id}")

        # Create auth service instance
        auth_service = AuthService(session)

        # Authenticate user with their actual tenant
        user = await auth_service.authenticate_user(
            email=email,
            password=password,
            tenant_id=actual_tenant_id
        )

        if not user:
            print(f"❌ Invalid credentials for {email}")
            return templates.TemplateResponse(
                "auth/partials/login_form.html",
                {
                    "request": request,
                    "error": "Invalid email or password",
                    "email": email
                }
            )

        print(f"✅ Login successful for {email}")

        # Create tokens
        access_token, refresh_token = auth_service.create_tokens(user)

        # Return success response with original template
        return templates.TemplateResponse(
            "auth/partials/login_success.html",
            {
                "request": request,
                "user": user,
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        )
    except Exception as e:
        print(f"LOGIN ERROR: {str(e)}")
        return templates.TemplateResponse(
            "auth/partials/login_form.html",
            {
                "request": request,
                "error": "Login failed. Please try again.",
                "email": email
            }
        )


@router.get("/redirect-to-demo")
async def redirect_to_demo(
    request: Request,
    access_token: str = None,
    refresh_token: str = None
):
    """Handle redirect to demo page after successful login."""
    print(f"🔍 REDIRECT: access_token={bool(access_token)}, refresh_token={bool(refresh_token)}")

    # Set the access token as a cookie and return JavaScript redirect
    response_html = f"""
    <script>
        console.log('🔍 Setting access token and redirecting...');
        // Set the access token in localStorage for now
        localStorage.setItem('access_token', '{access_token}');

        // Set cookie as well
        document.cookie = 'access_token={access_token}; path=/; SameSite=Strict';

        // Redirect to demo page
        window.location.href = '/demo';
    </script>
    """

    return HTMLResponse(content=response_html)


@router.get("/redirect-to-dashboard")
async def redirect_to_dashboard(
    request: Request,
    access_token: str = None,
    refresh_token: str = None
):
    """Handle redirect to dashboard after successful login."""
    print(f"🔍 REDIRECT: access_token={bool(access_token)}, refresh_token={bool(refresh_token)}")

    from fastapi.responses import RedirectResponse

    # Create redirect response
    response = RedirectResponse(url="/dashboard", status_code=302)

    # Set cookies properly with correct attributes
    if access_token:
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,  # Allow JavaScript access for localStorage sync
            secure=False,    # Set to True in production with HTTPS
            samesite="lax",  # More permissive than strict for redirects
            path="/",
            max_age=1800     # 30 minutes
        )

    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,   # Protect refresh token from JavaScript
            secure=False,    # Set to True in production with HTTPS
            samesite="lax",
            path="/",
            max_age=86400    # 24 hours
        )

    return response
@router.post("/register/form")
async def register_form_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form(default="user"),
    tenant_id: str = Depends(tenant_dependency),
    session: AsyncSession = Depends(get_db),
    _rate_limit: dict = Depends(rate_limit_register)
):
    """Handle registration form submission via HTMX."""
    errors = []

    # Validate passwords match
    if password != confirm_password:
        errors.append("Passwords do not match")

    # Validate password complexity
    password_errors = validate_password_complexity(password)
    errors.extend(password_errors)

    # Validate role
    if role not in ["user", "admin"]:
        role = "user"

    if errors:
        return templates.TemplateResponse(
            "auth/partials/register_form.html",
            {
                "request": request,
                "errors": errors,
                "email": email,
                "role": role
            }
        )

    try:
        # Create auth service instance
        auth_service = AuthService(session)

        # Create user
        user = await auth_service.create_user(
            email=email,
            password=password,
            tenant_id=tenant_id,
            role=role
        )

        await session.commit()

        # Create tokens
        access_token, refresh_token = auth_service.create_tokens(user)

        # Return success response
        return templates.TemplateResponse(
            "auth/partials/register_success.html",
            {
                "request": request,
                "user": user,
                "access_token": access_token,
                "refresh_token": refresh_token
            }
        )

    except ValueError as e:
        await session.rollback()
        return templates.TemplateResponse(
            "auth/partials/register_form.html",
            {
                "request": request,
                "errors": [str(e)],
                "email": email,
                "role": role
            }
        )
    except Exception as e:
        await session.rollback()
        return templates.TemplateResponse(
            "auth/partials/register_form.html",
            {
                "request": request,
                "errors": ["Registration failed. Please try again."],
                "email": email,
                "role": role
            }
        )


# Password Reset Endpoints

@router.post("/password-reset", response_model=PasswordResetResponse)
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest,
    session: AsyncSession = Depends(get_db)
):
    """Request a password reset for a user."""
    from app.features.auth.password_reset_service import PasswordResetService

    # Get client info for security tracking
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    reset_service = PasswordResetService(session)
    success = await reset_service.request_password_reset(
        email=reset_request.email,
        ip_address=ip_address,
        user_agent=user_agent
    )

    # Always return success for security (don't reveal if email exists)
    return PasswordResetResponse(
        message="If an account with that email exists, a password reset link has been sent.",
        success=True
    )


@router.post("/password-reset/verify", response_model=PasswordResetResponse)
async def verify_password_reset_token(
    token: str,
    session: AsyncSession = Depends(get_db)
):
    """Verify a password reset token."""
    from app.features.auth.password_reset_service import PasswordResetService

    reset_service = PasswordResetService(session)
    token_info = await reset_service.verify_reset_token(token)

    if token_info:
        return PasswordResetResponse(
            message="Token is valid.",
            success=True
        )
    else:
        return PasswordResetResponse(
            message="Invalid or expired token.",
            success=False
        )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
async def confirm_password_reset(
    reset_confirm: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db)
):
    """Confirm password reset with new password."""
    from app.features.auth.password_reset_service import PasswordResetService

    reset_service = PasswordResetService(session)
    success = await reset_service.reset_password(
        token=reset_confirm.token,
        new_password=reset_confirm.new_password,
        confirm_password=reset_confirm.confirm_password
    )

    if success:
        return PasswordResetResponse(
            message="Password has been reset successfully.",
            success=True
        )
    else:
        return PasswordResetResponse(
            message="Failed to reset password. Token may be invalid or passwords don't match.",
            success=False
        )


# HTML/HTMX Password Reset Endpoints

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    """Forgot password page."""
    return templates.TemplateResponse(
        "auth/forgot_password.html",
        {"request": request}
    )


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str = None
):
    """Reset password page with token."""
    if not token:
        return templates.TemplateResponse(
            "auth/forgot_password.html",
            {
                "request": request,
                "error": "Invalid reset link. Please request a new password reset."
            }
        )

    # Verify token
    from app.features.auth.password_reset_service import PasswordResetService
    from app.features.core.database import get_db

    async with get_db() as session:
        reset_service = PasswordResetService(session)
        token_info = await reset_service.verify_reset_token(token)

        if not token_info:
            return templates.TemplateResponse(
                "auth/forgot_password.html",
                {
                    "request": request,
                    "error": "Invalid or expired reset token. Please request a new password reset."
                }
            )

    return templates.TemplateResponse(
        "auth/reset_password.html",
        {
            "request": request,
            "token": token,
            "email": token_info.get("email") if token_info else ""
        }
    )


@router.post("/forgot-password/form")
async def forgot_password_form_submit(
    request: Request,
    email: str = Form(...),
    session: AsyncSession = Depends(get_db)
):
    """Handle forgot password form submission via HTMX."""
    from app.features.auth.password_reset_service import PasswordResetService

    try:
        # Get client info for security tracking
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

        reset_service = PasswordResetService(session)
        await reset_service.request_password_reset(
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )

        return templates.TemplateResponse(
            "auth/partials/forgot_password_success.html",
            {
                "request": request,
                "email": email
            }
        )

    except Exception as e:
        logger.error(f"Forgot password form error: {e}")
        return templates.TemplateResponse(
            "auth/partials/forgot_password_form.html",
            {
                "request": request,
                "error": "An error occurred. Please try again.",
                "email": email
            }
        )


@router.post("/reset-password/form")
async def reset_password_form_submit(
    request: Request,
    token: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    session: AsyncSession = Depends(get_db)
):
    """Handle reset password form submission via HTMX."""
    from app.features.auth.password_reset_service import PasswordResetService

    try:
        reset_service = PasswordResetService(session)
        success = await reset_service.reset_password(
            token=token,
            new_password=new_password,
            confirm_password=confirm_password
        )

        if success:
            return templates.TemplateResponse(
                "auth/partials/reset_password_success.html",
                {"request": request}
            )
        else:
            return templates.TemplateResponse(
                "auth/partials/reset_password_form.html",
                {
                    "request": request,
                    "token": token,
                    "error": "Failed to reset password. Please check your passwords and try again."
                }
            )

    except Exception as e:
        logger.error(f"Reset password form error: {e}")
        return templates.TemplateResponse(
            "auth/partials/reset_password_form.html",
            {
                "request": request,
                "token": token,
                "error": "An error occurred. Please try again."
            }
        )
