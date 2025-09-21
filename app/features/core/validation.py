"""
Centralized validation utilities for form handling across all slices.
"""
from typing import Dict, List, Any, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
import re


class ValidationError(Exception):
    """Custom validation error with field mapping support."""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class FormValidator:
    """Base form validator with common validation rules."""

    @staticmethod
    def validate_email(email: str) -> List[str]:
        """Validate email format."""
        errors = []
        if not email:
            errors.append("Email is required")
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            errors.append("Invalid email format")
        return errors

    @staticmethod
    def validate_required(value: Any, field_name: str) -> List[str]:
        """Validate required fields."""
        errors = []
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(f"{field_name} is required")
        return errors

    @staticmethod
    def validate_password_complexity(password: str) -> List[str]:
        """Validate password complexity requirements."""
        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
            errors.append("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
        return errors

    @staticmethod
    def validate_password_confirmation(password: str, confirm_password: str) -> List[str]:
        """Validate password confirmation matches."""
        errors = []
        if password != confirm_password:
            errors.append("Passwords do not match")
        return errors

    @staticmethod
    def validate_length(value: str, min_length: int = None, max_length: int = None, field_name: str = "Field") -> List[str]:
        """Validate string length requirements."""
        errors = []
        if min_length and len(value) < min_length:
            errors.append(f"{field_name} must be at least {min_length} characters long")
        if max_length and len(value) > max_length:
            errors.append(f"{field_name} must be no more than {max_length} characters long")
        return errors


class FormHandler:
    """Centralized form handling with validation and error responses."""

    def __init__(self, request: Request):
        self.request = request
        self.errors: Dict[str, List[str]] = {}
        self.form_data: Dict[str, Any] = {}
        self.raw_form = None  # Store raw form for multi-select access

    async def parse_form(self) -> Dict[str, Any]:
        """Parse form data and store in form_data."""
        self.raw_form = await self.request.form()
        self.form_data = dict(self.raw_form)
        return self.form_data

    def get_list_values(self, field_name: str) -> List[str]:
        """Get list of values for multi-select fields."""
        if self.raw_form:
            return self.raw_form.getlist(field_name)
        return []

    def add_error(self, field: str, message: str):
        """Add validation error for a specific field."""
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)

    def validate_field(self, field: str, value: Any, validators: List[callable], field_display_name: str = None) -> bool:
        """Run multiple validators on a field."""
        display_name = field_display_name or field.replace('_', ' ').title()
        field_errors = []

        for validator in validators:
            if hasattr(validator, '__call__'):
                try:
                    # Different validators may have different signatures
                    if 'field_name' in validator.__code__.co_varnames:
                        errors = validator(value, field_name=display_name)
                    else:
                        errors = validator(value)
                    field_errors.extend(errors)
                except Exception as e:
                    field_errors.append(f"Validation error for {display_name}: {str(e)}")

        if field_errors:
            self.errors[field] = field_errors
            return False
        return True

    def has_errors(self) -> bool:
        """Check if any validation errors exist."""
        return bool(self.errors)

    def get_first_error(self) -> Optional[str]:
        """Get the first error message (for toast display)."""
        if not self.errors:
            return None

        first_field = next(iter(self.errors))
        return self.errors[first_field][0]

    def create_error_response(self) -> JSONResponse:
        """Create standardized JSON error response."""
        if not self.errors:
            return JSONResponse(
                status_code=400,
                content={"detail": "Validation failed"}
            )

        # Return the first error for toast display, plus field mapping data
        first_error = self.get_first_error()

        return JSONResponse(
            status_code=400,
            content={
                "detail": first_error,
                "field_errors": self.errors,  # For advanced field mapping
                "type": "validation_error"
            }
        )

    def validate_password_fields(self, password_field: str = "password", confirm_field: str = "confirm_password") -> bool:
        """Common password validation for user forms."""
        password = self.form_data.get(password_field, "")
        confirm_password = self.form_data.get(confirm_field, "")

        # Validate password complexity
        complexity_errors = FormValidator.validate_password_complexity(password)
        if complexity_errors:
            self.errors[password_field] = complexity_errors

        # Validate password confirmation
        confirmation_errors = FormValidator.validate_password_confirmation(password, confirm_password)
        if confirmation_errors:
            self.errors[confirm_field] = confirmation_errors

        return not (complexity_errors or confirmation_errors)

    def validate_email_field(self, email_field: str = "email") -> bool:
        """Common email validation."""
        email = self.form_data.get(email_field, "")

        email_errors = FormValidator.validate_email(email)
        if email_errors:
            self.errors[email_field] = email_errors
            return False
        return True

    def validate_required_fields(self, required_fields: List[str]) -> bool:
        """Validate multiple required fields."""
        all_valid = True

        for field in required_fields:
            value = self.form_data.get(field, "")
            field_display_name = field.replace('_', ' ').title()

            required_errors = FormValidator.validate_required(value, field_display_name)
            if required_errors:
                self.errors[field] = required_errors
                all_valid = False

        return all_valid


def handle_form_validation(validator_func):
    """Decorator for route functions to handle common form validation patterns."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ValidationError as e:
                return JSONResponse(
                    status_code=400,
                    content={"detail": e.message, "field": e.field}
                )
            except Exception as e:
                return JSONResponse(
                    status_code=500,
                    content={"detail": f"Internal server error: {str(e)}"}
                )
        return wrapper
    return decorator
