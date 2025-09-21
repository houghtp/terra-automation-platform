console.log('[secrets] secrets-table.js loaded');

// Note: Delete and view functionality now handled by HTMX

// HTMX event handlers for modal management
document.addEventListener('htmx:afterSwap', function(event) {
    if (event.detail.target.id === 'modal-content') {
        const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-form'));
        if (!modal._isShown) {
            modal.show();
        }
    }
});

// Close modal on successful form submission and refresh stats cards
document.addEventListener('htmx:afterRequest', function(event) {
    if (event.detail.successful && event.detail.xhr.status === 204) {
        const modal = bootstrap.Modal.getInstance(document.getElementById('modal-form'));
        if (modal) {
            modal.hide();
        }
        // Trigger refresh of stats cards (web components will handle this)
        setTimeout(() => {
            document.querySelectorAll('stats-card').forEach(card => {
                if (card.refresh) card.refresh();
            });
        }, 100);

        // Show success message
        if (window.showToast) {
            showToast('Secret saved successfully', 'success');
        }

        // Refresh the secrets list after short delay
        setTimeout(() => location.reload(), 500);
    }
});

// HTMX error handler
document.addEventListener('htmx:responseError', function(event) {
    if (window.showToast) {
        showToast('Error: Failed to process request', 'error');
    }
});

// Auto-refresh stats cards every 5 minutes (more efficient than full page reload)
setInterval(() => {
    document.querySelectorAll('stats-card').forEach(card => {
        if (card.refresh) card.refresh();
    });
}, 300000);