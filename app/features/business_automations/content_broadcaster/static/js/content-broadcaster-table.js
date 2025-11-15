// Deprecated duplicate file shim.
// This file used to contain a full implementation but was duplicated.
// The canonical implementation is now in `content-table.js`.
// To avoid serving duplicate behavior, this shim will delegate initialization
// to the canonical function if present.

(function () {
    if (typeof console !== 'undefined') {
        console.warn('Deprecated: loaded content-broadcaster-table.js; use content-table.js instead.');
    }

    document.addEventListener('DOMContentLoaded', function () {
        // If the canonical initializer is available, call it.
        if (window.initializeContentTable && !window.contentTableInitialized) {
            try {
                window.contentTableInitialized = true;
                window.initializeContentTable();
            } catch (e) {
                console.error('Failed to initialize canonical content table:', e);
            }
        }
    });
})();
