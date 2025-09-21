// Store the previously focused element for proper focus restoration (make it global)
window.lastFocusedElement = null;

function showModal() {
  // Only capture focus if not already manually set (preserve button focus over table cell focus)
  if (!window.lastFocusedElement && !window.editSelectedButton) {
    window.lastFocusedElement = document.activeElement;
  }

  const modalEl = document.getElementById('modal');
  if (modalEl && window.bootstrap) {
    const modal = new bootstrap.Modal(modalEl, {
      backdrop: 'static',  // Prevent closing on outside click
      keyboard: false,     // Prevent closing on ESC key
      focus: true
    });
    modal.show();

    // Focus the modal content after it's shown
    modalEl.addEventListener('shown.bs.modal', function onShown() {
      const firstInput = modalEl.querySelector('input, textarea, select, button');
      if (firstInput) {
        firstInput.focus();
      }
      modalEl.removeEventListener('shown.bs.modal', onShown);
    });
  }
}

function closeModal() {
  const modalEl = document.getElementById('modal');
  if (modalEl && window.bootstrap) {
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) {
      modal.hide();
    }
  }
}

/**
 * Show a modern confirmation modal - general utility for the entire app
 * @param {Object} options - Configuration options
 * @param {string} options.title - Modal title
 * @param {string} options.message - Confirmation message
 * @param {string} options.confirmText - Confirm button text
 * @param {string} options.cancelText - Cancel button text
 * @param {string} options.type - Modal type: 'warning', 'danger', 'info'
 * @param {Function} options.onConfirm - Callback for confirm action
 * @param {Function} options.onCancel - Callback for cancel action
 */
function showConfirmModal(options = {}) {
  const {
    title = 'Confirm Action',
    message = 'Are you sure you want to proceed?',
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    type = 'warning', // warning, danger, info
    onConfirm = () => { },
    onCancel = () => { }
  } = options;

  // Capture the currently focused element for restoration
  const lastFocusedElement = document.activeElement;

  // Remove any existing confirm modal
  const existingModal = document.querySelector('.modern-confirm-modal');
  if (existingModal) {
    existingModal.remove();
  }

  // Create modal container
  const modal = document.createElement('div');
  modal.className = 'modern-confirm-modal';

  // Create overlay
  const overlay = document.createElement('div');
  overlay.className = 'modern-confirm-overlay';

  // Create dialog
  const dialog = document.createElement('div');
  dialog.className = 'modern-confirm-dialog';

  // Create header
  const header = document.createElement('div');
  header.className = 'modern-confirm-header';

  const iconDiv = document.createElement('div');
  iconDiv.className = 'modern-confirm-icon';
  const iconEl = document.createElement('i');
  const iconMap = {
    warning: 'ti-alert-triangle text-warning',
    danger: 'ti-trash text-danger',
    info: 'ti-info-circle text-info'
  };
  iconEl.className = `ti ${iconMap[type] || iconMap.warning}`;
  iconDiv.appendChild(iconEl);

  const titleEl = document.createElement('h4');
  titleEl.className = 'modern-confirm-title';
  titleEl.textContent = title;

  header.appendChild(iconDiv);
  header.appendChild(titleEl);

  // Create body
  const body = document.createElement('div');
  body.className = 'modern-confirm-body';
  const messageEl = document.createElement('p');
  messageEl.className = 'modern-confirm-message';
  messageEl.textContent = message;
  body.appendChild(messageEl);

  // Create footer
  const footer = document.createElement('div');
  footer.className = 'modern-confirm-footer';

  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'modern-confirm-cancel btn btn-outline-secondary';
  cancelBtn.textContent = cancelText;

  const confirmBtn = document.createElement('button');
  confirmBtn.className = `modern-confirm-confirm btn ${type === 'danger' ? 'btn-danger' : 'btn-primary'}`;
  confirmBtn.textContent = confirmText;

  footer.appendChild(cancelBtn);
  footer.appendChild(confirmBtn);

  // Assemble the modal
  dialog.appendChild(header);
  dialog.appendChild(body);
  dialog.appendChild(footer);
  overlay.appendChild(dialog);
  modal.appendChild(overlay);

  // Event handlers
  const closeModal = () => {
    modal.style.animation = 'fadeIn 0.2s ease-out reverse';
    setTimeout(() => {
      if (modal && modal.parentElement) {
        modal.remove();
      }
      // Restore focus to the original element
      if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
        try {
          lastFocusedElement.focus();
        } catch (err) {
          // Focus restoration failed, ignore silently
        }
      }
    }, 200);
  };

  confirmBtn.addEventListener('click', () => {
    closeModal();
    onConfirm();
  });

  cancelBtn.addEventListener('click', () => {
    closeModal();
    onCancel();
  });

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeModal();
      onCancel();
    }
  });

  // ESC key handler
  const escHandler = (e) => {
    if (e.key === 'Escape') {
      closeModal();
      onCancel();
      document.removeEventListener('keydown', escHandler);
    }
  };
  document.addEventListener('keydown', escHandler);

  document.body.appendChild(modal);

  // Focus confirm button by default
  setTimeout(() => confirmBtn.focus(), 100);
}

/**
 * Show a toast notification - simple implementation for general use
 * @param {string} message - Toast message
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duration in milliseconds (default: 3000)
 */
function showToast(message, type = "info", duration = 3000) {
  // Remove any existing toasts first
  const existingToasts = document.querySelectorAll('.modern-toast');
  existingToasts.forEach(toast => toast.remove());

  // Create toast container
  const toast = document.createElement('div');
  toast.className = `modern-toast modern-toast-${type}`;

  // Create toast content
  const content = document.createElement('div');
  content.className = 'modern-toast-content';

  // Add icon based on type
  const iconMap = {
    success: 'ti-check-circle',
    error: 'ti-exclamation-circle',
    warning: 'ti-alert-triangle',
    info: 'ti-info-circle'
  };

  const icon = document.createElement('i');
  icon.className = `ti ${iconMap[type] || iconMap.info}`;

  const messageEl = document.createElement('span');
  messageEl.textContent = message;

  content.appendChild(icon);
  content.appendChild(messageEl);
  toast.appendChild(content);

  // Add to page
  document.body.appendChild(toast);

  // Auto-remove after duration
  setTimeout(() => {
    if (toast && toast.parentElement) {
      toast.style.animation = 'slideOutRight 0.3s ease-out';
      setTimeout(() => toast.remove(), 300);
    }
  }, duration);
}

/**
 * Show field-level validation errors - maps server errors to specific form fields
 * @param {string} errorMessage - The error message from server
 * @param {string} formSelector - CSS selector for the form (default: current modal form)
 */
function showFieldErrors(errorMessage, formSelector = '#modal form') {
  console.log('🔍 showFieldErrors called with:', errorMessage, formSelector);
  const form = document.querySelector(formSelector);
  if (!form) {
    console.log('❌ Form not found with selector:', formSelector);
    return false;
  }

  console.log('✅ Form found:', form);

  // Clear any existing field errors first
  form.querySelectorAll('.is-invalid').forEach(input => {
    input.classList.remove('is-invalid');
  });
  form.querySelectorAll('.invalid-feedback').forEach(error => {
    error.style.display = 'none';
  });

  // Map common error messages to specific fields
  const fieldMappings = [
    {
      keywords: ['password', 'complexity', 'uppercase', 'lowercase', 'special character', 'characters long'],
      fieldId: 'password-input',
      errorId: 'password-complexity-error',
      defaultMessage: 'Password does not meet complexity requirements'
    },
    {
      keywords: ['passwords do not match', 'password confirmation'],
      fieldId: 'confirm-password-input',
      errorId: 'password-mismatch-error',
      defaultMessage: 'Passwords do not match'
    },
    {
      keywords: ['email already exists', 'duplicate email'],
      fieldId: 'email',
      errorId: 'email-error',
      defaultMessage: 'Email already exists'
    }
  ];

  // Check if error message matches any field-specific patterns
  for (const mapping of fieldMappings) {
    const matchesField = mapping.keywords.some(keyword =>
      errorMessage.toLowerCase().includes(keyword.toLowerCase())
    );

    console.log(`🔍 Checking mapping for ${mapping.fieldId}:`, matchesField, mapping.keywords);

    if (matchesField) {
      const field = form.querySelector(`#${mapping.fieldId}, [name="${mapping.fieldId}"]`);
      const errorDiv = form.querySelector(`#${mapping.errorId}`);

      console.log('🔍 Field found:', !!field, 'Error div found:', !!errorDiv);

      if (field) {
        field.classList.add('is-invalid');

        if (errorDiv) {
          errorDiv.textContent = errorMessage;
          errorDiv.style.display = 'block';
        }

        // Focus the problematic field
        field.focus();
        console.log('✅ Field error displayed successfully');
        return true; // Successfully mapped to field
      }
    }
  }

  console.log('❌ No field mapping found for error message');
  return false; // No field mapping found
}// Make functions globally available
window.showModal = showModal;
window.closeModal = closeModal;
window.showConfirmModal = showConfirmModal;
window.showToast = showToast;
window.showFieldErrors = showFieldErrors;

document.addEventListener("DOMContentLoaded", function () {
  // Global modal close handler - catches ALL modal closes
  const modalEl = document.getElementById('modal');
  if (modalEl) {
    modalEl.addEventListener('hidden.bs.modal', function () {
      // FORCE CLEANUP: Remove any leftover modal backdrops and restore body
      const backdrops = document.querySelectorAll('.modal-backdrop');
      backdrops.forEach(backdrop => backdrop.remove());
      document.body.classList.remove('modal-open');
      document.body.style.removeProperty('padding-right');
      document.body.style.removeProperty('overflow');

      // Use setTimeout to let Bootstrap finish its cleanup before restoring focus
      setTimeout(() => {
        // Special case: if this was triggered by "Edit Selected", focus the button directly
        if (window.editSelectedButton && typeof window.editSelectedButton.focus === 'function') {
          window.editSelectedButton.focus();
          window.editSelectedButton = null;
        } else if (window.lastFocusedElement && typeof window.lastFocusedElement.focus === 'function') {
          window.lastFocusedElement.focus();
        }
        window.lastFocusedElement = null;
      }, 50);
    });
  }

  document.body.addEventListener("htmx:afterSwap", (e) => {
    const modalBody = document.getElementById('modal-body');
    if (modalBody && e.target === modalBody) {
      // Capture focus before showing modal (prefer manually set focus target)
      if (!window.lastFocusedElement) {
        window.lastFocusedElement = document.activeElement;
      }
      showModal();
    }
  });
});
