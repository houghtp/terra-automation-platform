/**
 * Centralized Form Validation and Handling Utilities
 * Core infrastructure - reusable across all slices
 */

class FormValidator {
    constructor(formSelector, options = {}) {
        this.form = document.querySelector(formSelector);
        this.options = {
            realTimeValidation: true,
            submitButtonControl: true,
            fieldErrorMapping: true,
            ...options
        };

        this.validators = new Map();
        this.fieldErrors = new Map();

        if (this.form) {
            this.init();
        }
    }

    init() {
        // Set up real-time validation if enabled
        if (this.options.realTimeValidation) {
            this.setupRealTimeValidation();
        }

        // Set up form submission handling
        this.setupFormSubmission();
    }

    setupRealTimeValidation() {
        this.form.addEventListener('input', (e) => {
            this.validateField(e.target);
        });

        this.form.addEventListener('blur', (e) => {
            this.validateField(e.target, true); // Force validation on blur
        }, true);
    }

    setupFormSubmission() {
        this.form.addEventListener('submit', (e) => {
            if (!this.validateAllFields()) {
                e.preventDefault();
                return false;
            }
        });
    }

    /**
     * Add validator for a specific field
     * @param {string} fieldName - Name or ID of the field
     * @param {Function} validatorFunc - Function that returns {valid: boolean, message: string}
     * @param {string} errorElementId - ID of element to show error message
     */
    addValidator(fieldName, validatorFunc, errorElementId = null) {
        this.validators.set(fieldName, {
            validator: validatorFunc,
            errorElementId: errorElementId || `${fieldName}-error`
        });
    }

    /**
     * Validate a specific field
     * @param {HTMLElement} field - The field element to validate
     * @param {boolean} forceValidation - Force validation even if field is empty
     */
    validateField(field, forceValidation = false) {
        const fieldName = field.name || field.id;
        const validatorConfig = this.validators.get(fieldName);

        if (!validatorConfig) return true;

        const value = field.value;

        // Skip validation for empty fields unless forced
        if (!forceValidation && !value.trim()) {
            this.clearFieldError(field, validatorConfig.errorElementId);
            return true;
        }

        const result = validatorConfig.validator(value, field);

        if (result.valid) {
            this.clearFieldError(field, validatorConfig.errorElementId);
            this.fieldErrors.delete(fieldName);
        } else {
            this.showFieldError(field, validatorConfig.errorElementId, result.message);
            this.fieldErrors.set(fieldName, result.message);
        }

        // Update submit button state if enabled
        if (this.options.submitButtonControl) {
            this.updateSubmitButton();
        }

        return result.valid;
    }

    /**
     * Validate all fields in the form
     */
    validateAllFields() {
        let allValid = true;

        for (const [fieldName, config] of this.validators) {
            const field = this.form.querySelector(`[name="${fieldName}"], #${fieldName}`);
            if (field && !this.validateField(field, true)) {
                allValid = false;
            }
        }

        return allValid;
    }

    /**
     * Show error for a specific field
     */
    showFieldError(field, errorElementId, message) {
        field.classList.add('is-invalid');

        const errorElement = document.getElementById(errorElementId);
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
        }
    }

    /**
     * Clear error for a specific field
     */
    clearFieldError(field, errorElementId) {
        field.classList.remove('is-invalid');

        const errorElement = document.getElementById(errorElementId);
        if (errorElement) {
            errorElement.style.display = 'none';
        }
    }

    /**
     * Update submit button state based on validation
     */
    updateSubmitButton() {
        const submitButton = this.form.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = this.fieldErrors.size > 0;
        }
    }

    /**
     * Clear all field errors
     */
    clearAllErrors() {
        this.form.querySelectorAll('.is-invalid').forEach(field => {
            field.classList.remove('is-invalid');
        });

        this.form.querySelectorAll('.invalid-feedback').forEach(error => {
            error.style.display = 'none';
        });

        this.fieldErrors.clear();
        this.updateSubmitButton();
    }
}

/**
 * Common Validation Functions
 */
const CommonValidators = {
    required: (fieldName = 'Field') => (value) => ({
        valid: value && value.trim().length > 0,
        message: `${fieldName} is required`
    }),

    email: () => (value) => ({
        valid: !value || /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value),
        message: 'Please enter a valid email address'
    }),

    passwordComplexity: () => (value) => {
        const requirements = {
            length: value.length >= 8,
            uppercase: /[A-Z]/.test(value),
            lowercase: /[a-z]/.test(value),
            number: /\d/.test(value),
            special: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(value)
        };

        const valid = Object.values(requirements).every(req => req);
        let message = 'Password must contain: ';
        const missing = [];

        if (!requirements.length) missing.push('8+ characters');
        if (!requirements.uppercase) missing.push('uppercase letter');
        if (!requirements.lowercase) missing.push('lowercase letter');
        if (!requirements.number) missing.push('number');
        if (!requirements.special) missing.push('special character');

        return {
            valid,
            message: valid ? '' : message + missing.join(', ')
        };
    },

    passwordConfirmation: (originalFieldId) => (value, field) => {
        const originalField = document.getElementById(originalFieldId);
        const originalValue = originalField ? originalField.value : '';

        return {
            valid: value === originalValue,
            message: 'Passwords do not match'
        };
    },

    minLength: (min, fieldName = 'Field') => (value) => ({
        valid: !value || value.length >= min,
        message: `${fieldName} must be at least ${min} characters long`
    }),

    maxLength: (max, fieldName = 'Field') => (value) => ({
        valid: !value || value.length <= max,
        message: `${fieldName} must be no more than ${max} characters long`
    })
};

/**
 * Enhanced global showFieldErrors function with centralized mapping
 */
function showFieldErrors(errorMessage, formSelector = '#modal form') {
    console.log('🔍 showFieldErrors called with:', errorMessage, formSelector);
    const form = document.querySelector(formSelector);
    if (!form) {
        console.log('❌ Form not found with selector:', formSelector);
        return false;
    }

    // Clear existing errors
    form.querySelectorAll('.is-invalid').forEach(input => {
        input.classList.remove('is-invalid');
    });
    form.querySelectorAll('.invalid-feedback').forEach(error => {
        error.style.display = 'none';
    });

    // Centralized field mappings - expandable across slices
    const fieldMappings = [
        // Password validation
        {
            keywords: ['password', 'complexity', 'uppercase', 'lowercase', 'special character', 'characters long'],
            fieldId: 'password-input',
            errorId: 'password-complexity-error'
        },
        {
            keywords: ['passwords do not match', 'password confirmation'],
            fieldId: 'confirm-password-input',
            errorId: 'password-mismatch-error'
        },

        // Email validation
        {
            keywords: ['email already exists', 'duplicate email', 'email'],
            fieldId: 'email',
            errorId: 'email-error'
        },

        // General field mappings
        {
            keywords: ['name is required'],
            fieldId: 'name',
            errorId: 'name-error'
        },
        {
            keywords: ['description'],
            fieldId: 'description',
            errorId: 'description-error'
        }
    ];

    // Check for field-specific error mapping
    for (const mapping of fieldMappings) {
        const matchesField = mapping.keywords.some(keyword =>
            errorMessage.toLowerCase().includes(keyword.toLowerCase())
        );

        if (matchesField) {
            const field = form.querySelector(`#${mapping.fieldId}, [name="${mapping.fieldId}"]`);
            const errorDiv = form.querySelector(`#${mapping.errorId}`);

            if (field) {
                field.classList.add('is-invalid');

                if (errorDiv) {
                    errorDiv.textContent = errorMessage;
                    errorDiv.style.display = 'block';
                }

                field.focus();
                console.log('✅ Field error displayed successfully');
                return true;
            }
        }
    }

    console.log('❌ No field mapping found for error message');
    return false;
}

/**
 * Initialize form validation for common patterns
 */
function initializeFormValidation(formSelector, validationConfig = {}) {
    const validator = new FormValidator(formSelector, validationConfig);

    // Add common validators based on form fields
    const form = document.querySelector(formSelector);
    if (!form) return null;

    // Auto-detect and setup common field validations
    const emailField = form.querySelector('[name="email"], #email');
    if (emailField) {
        validator.addValidator('email', CommonValidators.email(), 'email-error');
    }

    const passwordField = form.querySelector('[name="password"], #password-input');
    if (passwordField) {
        validator.addValidator('password', CommonValidators.passwordComplexity(), 'password-complexity-error');
    }

    const confirmPasswordField = form.querySelector('[name="confirm_password"], #confirm-password-input');
    if (confirmPasswordField && passwordField) {
        validator.addValidator('confirm_password',
            CommonValidators.passwordConfirmation(passwordField.id || 'password-input'),
            'password-mismatch-error'
        );
    }

    const nameField = form.querySelector('[name="name"], #name');
    if (nameField) {
        validator.addValidator('name', CommonValidators.required('Name'), 'name-error');
    }

    return validator;
}

// Make utilities globally available
window.FormValidator = FormValidator;
window.CommonValidators = CommonValidators;
window.showFieldErrors = showFieldErrors;
window.initializeFormValidation = initializeFormValidation;
