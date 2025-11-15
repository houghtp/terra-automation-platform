// Store the previously focused element for proper focus restoration (make it global)
window.lastFocusedElement = null;
const fallbackModalState = {
  backdrop: null,
};

(function enforceGlobalModalDefaults() {
  const applyDefaults = () => {
    if (window.bootstrap && window.bootstrap.Modal && window.bootstrap.Modal.Default) {
      window.bootstrap.Modal.Default.backdrop = "static";
      window.bootstrap.Modal.Default.keyboard = false;
      return true;
    }
    return false;
  };

  if (!applyDefaults()) {
    document.addEventListener("DOMContentLoaded", () => {
      if (!applyDefaults()) {
        const interval = setInterval(() => {
          if (applyDefaults()) {
            clearInterval(interval);
          }
        }, 100);
      }
    });
  }
})();

function enforceModalElementDefaults(root = document) {
  root.querySelectorAll(".modal").forEach((modalEl) => {
    modalEl.setAttribute("data-bs-backdrop", "static");
    modalEl.setAttribute("data-bs-keyboard", "false");
  });
}

document.addEventListener("DOMContentLoaded", () => {
  enforceModalElementDefaults();
  registerModalShowHandler();
});

document.addEventListener("htmx:afterSwap", () => {
  enforceModalElementDefaults();
  registerModalShowHandler();
});

function registerModalShowHandler() {
  if (!window.bootstrap || !window.bootstrap.Modal || registerModalShowHandler._bound) {
    return;
  }
  document.addEventListener("show.bs.modal", (event) => {
    const modalEl = event.target;
    enforceModalElementDefaults(modalEl.parentElement || document);
    const instance = window.bootstrap.Modal.getOrCreateInstance(modalEl, {
      backdrop: "static",
      keyboard: false,
      focus: true
    });
    if (instance && instance._config) {
      instance._config.backdrop = "static";
      instance._config.keyboard = false;
    }
  });
  registerModalShowHandler._bound = true;
}

registerModalShowHandler();

function fallbackModalDismissHandler(event) {
  event.preventDefault();
  closeModal();
}

function cleanupFallbackModal(modalEl) {

  if (modalEl.dataset.fallbackActive) {
    modalEl.querySelectorAll('[data-bs-dismiss="modal"]').forEach((btn) => {
      btn.removeEventListener('click', fallbackModalDismissHandler);
    });
    delete modalEl.dataset.fallbackActive;
  }

  if (modalEl._fallbackClickHandler) {
    modalEl.removeEventListener('click', modalEl._fallbackClickHandler);
    delete modalEl._fallbackClickHandler;
  }

  if (modalEl._fallbackKeyHandler) {
    document.removeEventListener('keydown', modalEl._fallbackKeyHandler);
    delete modalEl._fallbackKeyHandler;
  }

  modalEl.style.display = 'none';
  modalEl.setAttribute('aria-hidden', 'true');
  modalEl.removeAttribute('aria-modal');
  document.body.classList.remove('modal-open');
  document.body.style.removeProperty('overflow');
  document.body.style.removeProperty('padding-right');

  const allBackdrops = document.querySelectorAll('.modal-backdrop, .fallback-modal-backdrop');

  if (fallbackModalState.backdrop) {
    fallbackModalState.backdrop.remove();
    fallbackModalState.backdrop = null;
  }

  // Remove ALL backdrop elements just to be safe
  allBackdrops.forEach(backdrop => {
    backdrop.remove();
  });

}

function removeBootstrapModalArtifacts(modalEl) {
  if (!modalEl) return;

  const cleanup = () => {
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach((backdrop) => backdrop.remove());

    document.body.classList.remove('modal-open');
    document.body.style.removeProperty('padding-right');
    document.body.style.removeProperty('overflow');

    if (modalEl.classList.contains('show')) {
      modalEl.classList.remove('show');
    }
    modalEl.style.display = 'none';
    modalEl.setAttribute('aria-hidden', 'true');
    modalEl.removeAttribute('aria-modal');
  };

  cleanup();
  setTimeout(cleanup, 200);
}

function showModal() {
  // Only capture focus if not already manually set (preserve button focus over table cell focus)
  if (!window.lastFocusedElement && !window.editSelectedButton) {
    window.lastFocusedElement = document.activeElement;
  }

  const modalEl = document.getElementById('modal');
  if (!modalEl) {
    console.warn('showModal called but #modal element not found');
    return;
  }

  if (window.bootstrap && window.bootstrap.Modal) {
    const modal = bootstrap.Modal.getInstance(modalEl) ||
      new bootstrap.Modal(modalEl, {
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
    return;
  }

  // Fallback if Bootstrap JS isn't available
  console.debug('Bootstrap Modal not available; using fallback modal display.');
  if (!fallbackModalState.backdrop) {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop fade show fallback-modal-backdrop';
    document.body.appendChild(backdrop);
    fallbackModalState.backdrop = backdrop;
  }

  modalEl.classList.add('fade');
  modalEl.classList.add('show');
  modalEl.style.display = 'block';
  modalEl.removeAttribute('aria-hidden');
  modalEl.setAttribute('aria-modal', 'true');
  document.body.classList.add('modal-open');
  document.body.style.overflow = 'hidden';
  document.body.style.paddingRight = '0px';

  // Trigger CSS transition
  // Remove and re-add show to restart animation when repeated
  modalEl.classList.remove('show');
  // Force reflow so the transition restarts properly
  // eslint-disable-next-line no-unused-expressions
  modalEl.offsetHeight;
  modalEl.classList.add('show');

  modalEl.dataset.fallbackActive = 'true';
  modalEl.querySelectorAll('[data-bs-dismiss="modal"]').forEach((btn) => {
    btn.removeEventListener('click', fallbackModalDismissHandler);
    btn.addEventListener('click', fallbackModalDismissHandler);
  });

  if (modalEl._fallbackClickHandler) {
    modalEl.removeEventListener('click', modalEl._fallbackClickHandler);
    delete modalEl._fallbackClickHandler;
  }

  if (modalEl._fallbackKeyHandler) {
    document.removeEventListener('keydown', modalEl._fallbackKeyHandler);
    delete modalEl._fallbackKeyHandler;
  }

  const firstInput = modalEl.querySelector('input, textarea, select, button');
  if (firstInput) {
    setTimeout(() => firstInput.focus(), 50);
  }
}

function closeModal() {
  const modalEl = document.getElementById('modal');
  if (!modalEl) return;

  if (window.bootstrap && window.bootstrap.Modal) {
    const modal = bootstrap.Modal.getInstance(modalEl);
    if (modal) {
      modal.hide();
      // DON'T call removeBootstrapModalArtifacts here - let Bootstrap fire hidden.bs.modal event first
      // The cleanup will happen in the hidden.bs.modal event handler
      return;
    } else {
      console.warn('[SITE.JS] Bootstrap Modal class exists but no instance found for modalEl');
    }
  } else {
    console.warn('[SITE.JS] Bootstrap Modal not available, using fallback');
  }

  // Fallback cleanup
  let finalized = false;
  const finalizeClose = () => {
    if (finalized) {
      return;
    }
    finalized = true;

    cleanupFallbackModal(modalEl);
    modalEl.removeEventListener('transitionend', onTransitionEnd);

    // Restore focus (same logic as Bootstrap's hidden.bs.modal handler)
    restoreFocusAfterModalClose();
  };

  const onTransitionEnd = (event) => {
    if (event.target === modalEl) {
      finalizeClose();
    }
  };

  const computedStyle = window.getComputedStyle(modalEl);
  const hasTransition =
    computedStyle.transitionDuration && computedStyle.transitionDuration !== '0s';

  modalEl.classList.remove('show');

  if (hasTransition) {
    modalEl.addEventListener('transitionend', onTransitionEnd);
    setTimeout(finalizeClose, 200); // Safety timeout
  } else {
    finalizeClose();
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
  toast.style.animation = 'toastEnter 0.35s ease-out';

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
      toast.style.animation = 'toastExit 0.25s ease-in forwards';
      setTimeout(() => toast.remove(), 250);
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
// Shared focus restoration logic for both Bootstrap and fallback modals
function restoreFocusAfterModalClose() {

  setTimeout(() => {
    const restoreFocus = (el) => {
      if (!el || typeof el.focus !== 'function') {
        return false;
      }
      try {
        el.focus({ preventScroll: false });
        // Verify focus actually moved to the target element
        const success = document.activeElement === el;
        if (!success) {
          console.log('[modal] focus() called but activeElement did not change', {
            attempted: el,
            actual: document.activeElement
          });
        }
        return success;
      } catch (err) {
        console.log('[modal] unable to restore focus', err);
        return false;
      }
    };

    const tryRestore = (attempt = 0) => {
      if (attempt > 10) {
        // Clear stored references only after all retries exhausted
        window.editSelectedButton = null;
        window.lastFocusedElement = null;
        console.warn('[modal] Focus restoration failed after 10 attempts');
        return;
      }

      let candidate = null;

      // Priority 1: editSelectedButton (don't clear yet - needed for retries)
      if (!candidate && window.editSelectedButton && document.contains(window.editSelectedButton)) {
        candidate = window.editSelectedButton;
      }

      // Priority 2: lastFocusedElement (don't clear yet - needed for retries)
      if (!candidate && window.lastFocusedElement && document.contains(window.lastFocusedElement)) {
        candidate = window.lastFocusedElement;
      }

      // Priority 3: data-default-focus fallback
      if (!candidate) {
        candidate = document.querySelector('[data-default-focus]');
      }

      // Priority 4: any focusable element
      if (!candidate) {
        candidate = document.querySelector('button, [href], input, select, textarea');
      }

      // Priority 5: body fallback
      if (!candidate) {
        candidate = document.body;
      }

      console.log('[modal] Focus restoration attempt', attempt + 1, 'candidate:', candidate);

      if (!restoreFocus(candidate)) {
        // Focus failed, retry
        setTimeout(() => tryRestore(attempt + 1), 100);
      } else {
        // Focus succeeded, clear stored references
        window.editSelectedButton = null;
        window.lastFocusedElement = null;
        console.log('[modal] Focus successfully restored to:', candidate);
      }
    };

    tryRestore();
  }, 50);
}

window.showModal = showModal;
window.closeModal = closeModal;
window.showConfirmModal = showConfirmModal;
window.showToast = showToast;
window.showFieldErrors = showFieldErrors;
window.restoreFocusAfterModalClose = restoreFocusAfterModalClose;

document.addEventListener("DOMContentLoaded", function () {
  // Global modal close handler - catches ALL modal closes
  const modalEl = document.getElementById('modal');
  if (modalEl) {
    modalEl.addEventListener('hidden.bs.modal', function () {
      removeBootstrapModalArtifacts(modalEl);
      // Use shared focus restoration function
      restoreFocusAfterModalClose();
    });
  }

  document.body.addEventListener("htmx:afterSwap", (e) => {
    console.debug('[htmx] afterSwap target:', e.target);
    const modalBody = document.getElementById('modal-body');
    if (modalBody && e.target === modalBody) {
      // Capture focus before showing modal (prefer manually set focus target)
      if (!window.lastFocusedElement) {
        window.lastFocusedElement = document.activeElement;
      }
      showModal();
    }
  });

  // Remember the control that triggered modal or HTMX actions
  document.body.addEventListener('click', (event) => {
    const focusCandidate = event.target.closest('[data-default-focus]');
    if (focusCandidate) {
      window.lastFocusedElement = focusCandidate;
    }
  }, true);

  document.body.addEventListener('htmx:beforeRequest', (event) => {
    const swapTarget = event.detail && event.detail.target;
    if (swapTarget && swapTarget.id === 'modal-body') {
      swapTarget.innerHTML = `
        <div class="modal-loading-state text-center py-5">
          <div class="spinner-border text-primary mb-3" role="status"></div>
          <p class="text-muted mb-0">Loading content…</p>
        </div>
      `;
    }

    if (!window.lastFocusedElement) {
      const active = document.activeElement;
      if (active && active !== document.body) {
        window.lastFocusedElement = active.closest('[data-default-focus]') || active;
      }
    }
  });
});
