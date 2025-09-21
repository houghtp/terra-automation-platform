console.log('[core] table-base.js loaded');

// Global table registry
window.appTables = {};

/**
 * Standard ajaxResponse handler for Tabulator tables
 */
function standardAjaxResponse(url, params, response) {
    console.log('Table AJAX Response:', response);
    if (response?.data && Array.isArray(response.data)) {
        return response.data;
    } else if (Array.isArray(response)) {
        return response;
    } else {
        console.error('Tabulator ajaxResponse: Unexpected response format:', response);
        return [];
    }
}


/**
 * Universal badge formatter - handles both single values and arrays
 * @param {Object} cell - Tabulator cell object
 * @param {string} badgeClass - CSS class for badges (default: 'type-badge')
 * @param {string} emptyText - Text to show when no values (default: 'No items')
 */
function formatBadges(cell, badgeClass = 'type-badge', emptyText = 'No items') {
    const value = cell.getValue();

    // Handle empty/null values
    if (!value || (Array.isArray(value) && value.length === 0)) {
        return `<span class="text-muted">${emptyText}</span>`;
    }

    // Convert single value to array for uniform processing
    const values = Array.isArray(value) ? value : [value];

    return values.map(item => {
        const cleanItem = item.toString().toLowerCase().replace(/\s+/g, '-');
        return `<span class="${badgeClass} ${cleanItem}">${item}</span>`;
    }).join(' ');
}
window.formatBadges = formatBadges;

// Convenience functions for common badge types
window.formatStatusBadge = (cell) => formatBadges(cell, 'status-badge', '-');
window.formatPriorityBadge = (cell) => formatBadges(cell, 'priority-badge', '-');
window.formatTypeBadge = (cell) => formatBadges(cell, 'type-badge', '-');
window.formatTags = (cell) => formatBadges(cell, 'type-badge', '');

/**
 * Reusable header filter functions
 */
// Array search filter (for tags, categories, etc.)
function arraySearchFilter(headerValue, rowValue) {
    if (!rowValue || !headerValue) return true;
    const searchTerm = headerValue.toLowerCase();
    const items = Array.isArray(rowValue) ? rowValue : [];
    return items.some(item => item.toLowerCase().includes(searchTerm));
}
window.arraySearchFilter = arraySearchFilter;

/**
 * Reusable sorter functions
 */
// Array length sorter (for tags, categories, etc.)
function arrayLengthSorter(a, b) {
    const aLen = (a || []).length;
    const bLen = (b || []).length;
    return aLen === bLen ? 0 : (aLen > bLen ? 1 : -1);
}
window.arrayLengthSorter = arrayLengthSorter;

/**
 * Date formatter - renders ISO/UTC date strings to local readable date
 */
function formatDate(cell) {
    const raw = cell.getValue();
    if (!raw) return '<span class="text-muted">-</span>';
    const d = new Date(raw);
    if (isNaN(d)) return `<span class="text-muted">${raw}</span>`;
    // Use a clearer date format: "Oct 1, 2025" or "1 Oct 2025"
    return `<span class="date-value">${d.toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    })}</span>`;
}
window.formatDate = formatDate;

/**
 * Timestamp formatter - renders ISO/UTC timestamp strings to local readable date and time
 */
function formatTimestamp(cell) {
    const value = cell.getValue();
    if (!value) return "";
    const date = new Date(value);
    if (isNaN(date)) return value;
    return date.toLocaleDateString() + " " + date.toLocaleTimeString();
}
window.formatTimestamp = formatTimestamp;

/**
 * Category badge formatter with predefined colors
 */
function formatCategoryBadge(cell) {
    const value = cell.getValue();
    const colors = {
        "AUTH": "bg-green-lt",
        "DATA": "bg-blue-lt",
        "ADMIN": "bg-purple-lt",
        "API": "bg-orange-lt",
        "SYSTEM": "bg-gray-lt"
    };
    return `<span class="badge ${colors[value] || 'bg-gray-lt'}">${value}</span>`;
}
window.formatCategoryBadge = formatCategoryBadge;

/**
 * Severity badge formatter with predefined colors
 */
function formatSeverityBadge(cell) {
    const value = cell.getValue();
    const colors = {
        "INFO": "bg-blue-lt",
        "WARNING": "bg-yellow-lt",
        "ERROR": "bg-red-lt",
        "CRITICAL": "bg-dark"
    };
    return `<span class="badge ${colors[value] || 'bg-gray-lt'}">${value}</span>`;
}
window.formatSeverityBadge = formatSeverityBadge;

/**
 * User email formatter with fallback for system actions
 */
function formatUserEmail(cell) {
    const value = cell.getValue();
    return value || "<em>System</em>";
}
window.formatUserEmail = formatUserEmail;

/**
 * Description formatter with truncation
 */
function formatDescription(cell, maxLength = 50) {
    const value = cell.getValue();
    if (!value) return "";
    return value.length > maxLength ? value.substring(0, maxLength) + "..." : value;
}
window.formatDescription = formatDescription;

/**
 * Action badge formatter (generic blue badge)
 */
function formatActionBadge(cell) {
    const value = cell.getValue();
    return `<span class="badge bg-blue-lt">${value}</span>`;
}
window.formatActionBadge = formatActionBadge;

/**
 * Row actions formatter - creates action buttons with standardized classes
 * @param {Object} cell - Tabulator cell object
 * @param {Array} actions - Array of action objects {icon, title, action, class}
 */
function formatRowActions(cell, actions = []) {
    const rowData = cell.getRow().getData();
    const actionsHtml = actions.map(action => {
        const actionClass = action.class || 'row-action-icon';
        const onclick = action.action ? `onclick="${action.action}(${rowData.id})"` : '';
        return `<i class="ti ${action.icon} ${actionClass}" title="${action.title}" ${onclick} style="cursor: pointer;"></i>`;
    }).join(' ');

    return `<div class="d-flex gap-1">${actionsHtml}</div>`;
}
window.formatRowActions = formatRowActions;

/**
 * View action formatter - creates a view/eye icon
 */
function formatViewAction(cell, viewFunction = 'viewDetails') {
    const rowData = cell.getRow().getData();
    return `
      <div class="d-flex gap-1">
        <i class="ti ti-eye row-action-icon"
           title="View Details"
           onclick="${viewFunction}(${rowData.id})"
           style="cursor: pointer;"></i>
      </div>
    `;
}
window.formatViewAction = formatViewAction;

/**
 * Simple date editor (HTML5 date input) for Tabulator
 */
function dateEditor(cell, onRendered, success, cancel) {
    const cellValue = cell.getValue();
    const input = document.createElement('input');
    input.setAttribute('type', 'date');
    input.style.width = '100%';
    input.style.boxSizing = 'border-box';

    let isFinished = false; // Prevent multiple calls to success

    // Initialize value if present and parseable
    if (cellValue) {
        const d = new Date(cellValue);
        if (!isNaN(d)) {
            // format YYYY-MM-DD
            const yyyy = d.getFullYear();
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            input.value = `${yyyy}-${mm}-${dd}`;
        }
    }

    onRendered(function () {
        input.focus();
        input.select();
    });

    function finish() {
        if (isFinished) return; // Prevent double-firing
        isFinished = true;

        try {
            if (input.value) {
                // Send the date as YYYY-MM-DD format (avoid timezone conversion issues)
                console.log('[dateEditor] submitting date value:', input.value);
                success(input.value); // Send as YYYY-MM-DD string
            } else {
                console.log('[dateEditor] submitting null (empty)');
                success(null);
            }
        } catch (err) {
            console.error('[dateEditor] error with date:', err, 'input value:', input.value);
            success(input.value || null);
        }
    }

    // Use multiple events to ensure cross-browser compatibility
    input.addEventListener('blur', finish);
    input.addEventListener('change', finish);
    input.addEventListener('input', function () {
        // Reset the finished flag on input to allow re-triggering
        isFinished = false;
    });

    input.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            finish();
        }
        if (e.key === 'Escape') {
            cancel();
        }
    });

    return input;
}
window.dateEditor = dateEditor;

/**
 * Assignee avatar formatter - expects a simple string (name) or object { name, avatarUrl }
 */
function formatAssignee(cell) {
    const v = cell.getValue();
    if (!v) return '<span class="text-muted">Unassigned</span>';
    let name = '';
    let avatar = null;

    if (typeof v === 'string') {
        name = v;
    } else if (v && typeof v === 'object') {
        name = v.name || '';
        avatar = v.avatarUrl || v.avatar || null;
    }

    const initials = name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
    if (avatar) {
        return `<div class="assignee-cell" style="display:flex;align-items:center;gap:8px;"><img src="${avatar}" alt="${name}" style="width:28px;height:28px;border-radius:50%;object-fit:cover;"> <span>${name}</span></div>`;
    }

    return `<div class="assignee-cell" style="display:flex;align-items:center;gap:8px;"><div style="width:28px;height:28px;border-radius:50%;background:#e5e7eb;color:#374151;display:inline-flex;align-items:center;justify-content:center;font-weight:600;">${initials}</div><span>${name}</span></div>`;
}
window.formatAssignee = formatAssignee;

/**
 * Assignee editor - simple select populated from window.availableAssignees (array of strings or objects)
 */
function assigneeEditor(cell, onRendered, success, cancel, editorParams) {
    const select = document.createElement('select');
    select.style.width = '100%';
    select.style.boxSizing = 'border-box';

    const list = (window.availableAssignees && Array.isArray(window.availableAssignees)) ? window.availableAssignees : [];

    const blank = document.createElement('option');
    blank.value = '';
    blank.textContent = 'Unassigned';
    select.appendChild(blank);

    list.forEach(item => {
        const opt = document.createElement('option');
        if (typeof item === 'string') {
            opt.value = item;
            opt.textContent = item;
        } else if (item && typeof item === 'object') {
            opt.value = item.name || item.id || JSON.stringify(item);
            opt.textContent = item.name || item.id || String(item);
        }
        select.appendChild(opt);
    });

    // Set current value
    const cur = cell.getValue();
    if (cur) {
        if (typeof cur === 'string') select.value = cur;
        else if (cur && typeof cur === 'object') select.value = cur.name || cur.id || '';
    }

    onRendered(() => select.focus());

    select.addEventListener('change', () => {
        const v = select.value || null;
        success(v);
    });

    select.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') cancel();
    });

    return select;
}
window.assigneeEditor = assigneeEditor;

/**
 * Unified table configuration - Complete settings for all tables
 */
const tableConfig = {
    layout: "fitColumns",
    layoutColumnsOnNewData: true,
    responsiveLayout: "collapse",
    responsiveLayoutCollapseStartOpen: false,
    pagination: "local",
    paginationSize: 10,
    paginationSizeSelector: [5, 10, 25, 50],
    paginationCounter: "rows",
    columnDefaults: {
        vertAlign: "middle",
    },

    // Grouping configuration
    groupBy: false,  // Start with no grouping
    groupStartOpen: true,  // Groups start expanded
    groupToggleElement: "header",  // Click header to toggle
    groupHeader: formatGroupHeader,  // Custom group header with icons
    groupHeaderPrint: formatGroupHeader,

    movableColumns: true,
    resizableColumns: true,
    resizableRows: false,
    tooltipsHeader: true,
    tooltips: true,
    ajaxConfig: "GET",
    ajaxContentType: "json",
    selectable: 1,

    // Simple CSS-based loader
    dataLoader: true,
    dataLoaderLoading: '<div class="loading-simple">Loading table data...</div>',
    dataLoaderError: '<div class="loading-error">Failed to load table data</div>',
    dataLoaderErrorTimeout: 3000,

    // No data placeholder
    placeholder: function(el) {
        return `
            <div class="no-data-placeholder" style="padding: 40px; text-align: center; color: #6c757d;">
                <i class="ti ti-database-off" style="font-size: 48px; margin-bottom: 16px; opacity: 0.5;"></i>
                <h6 style="margin-bottom: 8px; color: #495057;">No Data Available</h6>
                <p style="margin-bottom: 0; font-size: 14px;">There are currently no items to display.</p>
            </div>
        `;
    },

    // Row selection features
    selectableRows: false,
    rowHeader: {
        formatter: "rowSelection",
        titleFormatter: "rowSelection",
        headerSort: false,
        resizable: false,
        frozen: true,
        width: 40,
        headerHozAlign: "center",
        hozAlign: "center",
    },

    // Advanced features
    headerFilterPlaceholder: "",
    sortMode: "local",
    downloadConfig: {
        columnHeaders: true,
        columnGroups: false,
        rowGroups: false,
        columnCalcs: false,
        dataTree: false
    }
};

// Export with multiple names for compatibility
window.tableConfig = tableConfig;
window.commonTableConfig = tableConfig; // Legacy compatibility
window.advancedTableConfig = tableConfig; // Legacy compatibility

// /**
//  * Test function to trigger table loading state
//  */
// window.testTableLoader = function (tableId = "demo-table") {
//     const table = window.appTables[tableId];
//     if (table) {
//         console.log("Triggering data loader for table:", tableId);
//         // Simulate loading by replacing data with a delayed promise
//         table.replaceData().then(() => {
//             console.log("Table data refreshed");
//         });
//     } else {
//         console.log("Table not found:", tableId, "Available tables:", Object.keys(window.appTables));
//     }
// };

// /**
//  * Test function to demonstrate non-Tabulator loader usage (for ECharts, etc.)
//  */
// window.testContainerLoader = function (containerId = "demo-table") {
//     console.log("Testing container loader on:", containerId);
//     showModernLoader(containerId, "Loading chart data...");

//     // Simulate async operation
//     setTimeout(() => {
//         hideModernLoader(containerId);
//         console.log("Container loader hidden");
//     }, 2000);
// };

/**
 * Refresh a table manually with simple loading class
 */
function refreshTable(tableId) {
    const cleanId = tableId.replace('#', '');
    const table = window.appTables[cleanId];
    const container = document.getElementById(cleanId);

    if (table && container) {
        // Show simple CSS loader
        container.classList.add('loading');

        // Refresh data and hide loader when complete
        table.replaceData().then(() => {
            container.classList.remove('loading');
        }).catch(() => {
            container.classList.remove('loading');
        });
    }
}
window.refreshTable = refreshTable;

/**
 * Bind row action buttons (edit/delete) using delegation - updated for icon-based buttons
 */
function bindRowActionHandlers(tableSelector, { onEdit, onDelete }) {
    const tableEl = document.querySelector(tableSelector);
    if (!tableEl) return;

    tableEl.addEventListener("click", (e) => {
        // Check if clicked element is an icon with action classes
        const target = e.target.closest("i.row-action-icon, button");
        const container = e.target.closest("[data-id]");
        if (!target || !container) return;

        const id = container.dataset.id;
        console.log('Row action clicked:', target.className, 'ID:', id);

        if (target.classList.contains("edit-btn")) {
            console.log('Edit button clicked, onEdit:', onEdit);
            if (typeof onEdit === 'function') {
                onEdit(id);
            } else if (typeof onEdit === 'string' && window[onEdit]) {
                console.log('Calling window[' + onEdit + '] with id:', id);
                window[onEdit](id);
            } else {
                console.warn('No edit handler found');
            }
        } else if (target.classList.contains("delete-btn")) {
            console.log('Delete button clicked, onDelete:', onDelete);
            if (typeof onDelete === 'function') {
                onDelete(id);
            } else if (typeof onDelete === 'string' && window[onDelete]) {
                window[onDelete](id);
            } else {
                console.warn('No delete handler found');
            }
        }
    });
}
window.bindRowActionHandlers = bindRowActionHandlers;

/**
 * Delete a row from a table via backend + UI update with modern confirmation modal
 */
function deleteTabulatorRow(deleteUrl, tableSelector, options = {}) {
    // Guard to prevent double execution
    if (window._deleteInProgress) return;

    const {
        title = 'Delete Item',
        message = 'Are you sure you want to delete this item? This action cannot be undone.',
        confirmText = 'Delete',
        cancelText = 'Cancel'
    } = options;

    const rowId = deleteUrl.match(/\/([^\/]+)\/delete$/)?.[1];
    const tableId = tableSelector.replace('#', '');
    const table = window.appTables[tableId];

    if (!table) {
        console.error(`Table ${tableId} not found in registry`);
        showToast("Error: Table not found", "error");
        return;
    }

    // Show modern confirmation modal
    showConfirmModal({
        title,
        message,
        confirmText,
        cancelText,
        type: 'danger',
        onConfirm: () => {
            // Set delete in progress AFTER user confirms
            window._deleteInProgress = true;

            // Show loading toast
            showToast("Deleting...", "info", 1000);

            fetch(deleteUrl, {
                method: "DELETE",
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/json"
                }
            })
                .then(async (response) => {
                    window._deleteInProgress = false;

                    if (!response.ok) {
                        const errorText = await response.text();
                        console.error("Delete failed:", response.status, errorText);
                        showToast(`Delete failed: ${response.status} ${response.statusText}`, "error");
                        return;
                    }

                    if (rowId) {
                        try {
                            // Delete the specific row - if this succeeds, the row is gone
                            await table.deleteRow(rowId);
                            // No verification needed - successful deleteRow means row is deleted
                        } catch (err) {
                            console.log("Error deleting row, refreshing table:", err);
                            table.replaceData();
                        }
                    } else {
                        // If we can't get the row ID, just refresh the table
                        table.replaceData();
                    }

                    showToast("Item deleted successfully", "success");
                })
                .catch((err) => {
                    window._deleteInProgress = false;
                    console.error("Delete error:", err);
                    showToast("Network error while deleting item", "error");

                    // Refresh table on error to ensure consistency
                    if (table) {
                        table.replaceData();
                    }
                });
        },
        onCancel: () => {
            // Do nothing on cancel
            console.log("Delete cancelled by user");
        }
    });
}
window.deleteTabulatorRow = deleteTabulatorRow;

/**
 * Generic edit function for table rows
 * @param {string} editUrl - URL to fetch the edit form
 * @param {string} targetSelector - CSS selector for where to load the form (default: "#modal-body")
 * @param {string} swapMethod - How to swap content (default: "innerHTML")
 */
function editTabulatorRow(editUrl, targetSelector = "#modal-body", swapMethod = "innerHTML") {
    htmx.ajax('GET', editUrl, {
        target: targetSelector,
        swap: swapMethod
    });
}
window.editTabulatorRow = editTabulatorRow;

/**
 * Create CRUD action buttons for table rows - CSP-compliant with delegation
 */
function createRowCrudButtons(data, options = {}) {
    console.log('createRowCrudButtons called with data:', data, 'options:', options);
    const { onEdit, onDelete, showEdit = true, showDelete = true } = options;

    let buttons = '';

    if (showEdit) {
        buttons += `
            <i class="ti ti-edit row-action-icon edit-btn"
               title="Edit"
               style="cursor: pointer; font-size: 18px; color: #0054a6; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;">
            </i>
        `;
    }

    if (showDelete) {
        buttons += `
            <i class="ti ti-trash row-action-icon delete-btn"
               title="Delete"
               style="cursor: pointer; font-size: 18px; color: #d63939; padding: 4px; border-radius: 4px; transition: all 0.2s;">
            </i>
        `;
    }

    return `
        <div class="row-actions" data-id="${data.id}" style="display: flex; align-items: center;">
            ${buttons}
        </div>
    `;
}
window.createRowCrudButtons = createRowCrudButtons;

// === SIMPLE GENERIC TABLE UTILITIES ===

/**
 * Clean event listener by cloning element (prevents duplicate handlers)
 */
function refreshEventListener(elementId) {
    const element = document.getElementById(elementId);
    if (!element) return null;

    const newElement = element.cloneNode(true);
    element.parentNode.replaceChild(newElement, element);
    return newElement;
}
window.refreshEventListener = refreshEventListener;

/**
 * Get selected row data from any table
 */
function getSelectedTableData(table) {
    if (!table || typeof table.getSelectedRows !== 'function') return [];

    const selectedRows = table.getSelectedRows();
    return selectedRows.map(row => row.getData());
}
window.getSelectedTableData = getSelectedTableData;

/**
 * Basic table export function
 */
function exportTableData(table, format, filename) {
    if (!table || typeof table.download !== 'function') {
        console.error('Invalid table instance');
        return false;
    }

    try {
        table.download(format, filename);
        return true;
    } catch (error) {
        console.error('Export failed:', error);
        return false;
    }
}
window.exportTableData = exportTableData;

/**
 * Generic table export with automatic filename generation and toast feedback
 * @param {string} tableId - ID of the table to export
 * @param {string} format - Export format (csv, xlsx, json, etc.)
 * @param {string} entityName - Name for filename (e.g., 'users', 'demo-items')
 */
function exportTabulatorTable(tableId, format, entityName) {
    const table = window.appTables && window.appTables[tableId];

    if (!table) {
        showToast("Table not initialized", "error");
        return false;
    }

    const filename = `${entityName}-${new Date().toISOString().split('T')[0]}`;
    const success = exportTableData(table, format, `${filename}.${format}`);

    if (success) {
        showToast(`Exporting as ${format.toUpperCase()}...`, "info", 2000);
    } else {
        showToast("Export failed", "error");
    }

    return success;
}
window.exportTabulatorTable = exportTabulatorTable;

/**
 * Add generic cellEdited handler to a table for inline editing
 * @param {Object} table - Tabulator table instance
 * @param {string} baseUrl - Base URL for PATCH requests (e.g., '/administration/users')
 * @param {string} entityName - Entity name for toast messages (e.g., 'User', 'Demo item')
 */
function addCellEditedHandler(table, baseUrl, entityName) {
    table.on("cellEdited", function (cell) {
        const data = cell.getRow().getData();
        const field = cell.getField();
        const value = cell.getValue();

        console.log(`[${entityName}] cellEdited triggered:`, { id: data.id, field, value, type: typeof value });

        fetch(`${baseUrl}/${data.id}/field`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ field, value })
        }).then(res => {
            console.log(`[${entityName}] PATCH response:`, res.status, res.statusText);
            if (!res.ok) {
                return res.text().then(text => {
                    console.error(`[${entityName}] PATCH failed with body:`, text);
                    throw new Error(`HTTP ${res.status}: Failed to save`);
                });
            }
            return res.json();
        }).then((responseData) => {
            console.log(`[${entityName}] PATCH success:`, responseData);
            if (window.showToast) {
                // Custom message for enabled field toggle
                if (field === "enabled") {
                    showToast(`${entityName} ${value ? 'enabled' : 'disabled'} successfully`, "success");
                } else {
                    showToast("Saved successfully", "success");
                }
            }
        }).catch(err => {
            console.error(`Failed to save inline edit:`, err);
            if (window.showToast) {
                showToast("Save failed", "error");
            }
            // Revert the cell value on error
            cell.restoreOldValue();
        });
    });
}
window.addCellEditedHandler = addCellEditedHandler;

/**
 * Add bulk edit handler for selected table rows
 * @param {Object} table - Tabulator table instance
 * @param {string} editUrl - Base URL for edit (e.g., '/administration/users')
 * @param {string} buttonId - ID of the edit button (default: 'edit-selected-btn')
 */
function addBulkEditHandler(table, editUrl, buttonId = "edit-selected-btn") {
    const editBtn = refreshEventListener(buttonId);
    if (editBtn) {
        editBtn.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();

            const selected = getSelectedTableData(table);

            if (selected.length === 0) {
                showToast("No rows selected", "error");
                return;
            }
            if (selected.length > 1) {
                showToast("Please select only one row to edit", "warning");
                return;
            }

            window.editSelectedButton = event.currentTarget;
            const id = selected[0].id;

            // Single item edit - use existing form
            htmx.ajax('GET', `${editUrl}/${id}/edit`, {
                target: '#modal-body',
                swap: 'innerHTML'
            });
        });
    }
}
window.addBulkEditHandler = addBulkEditHandler;

/**
 * Add bulk delete handler to a table
 */
function addBulkDeleteHandler(table, deleteUrl, entityName, buttonId = "delete-selected-btn") {
    const deleteBtn = refreshEventListener(buttonId);
    if (deleteBtn) {
        deleteBtn.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();

            const selected = getSelectedTableData(table);

            if (selected.length === 0) {
                showToast("No rows selected", "error");
                return;
            }

            showConfirmModal({
                title: `Delete Selected ${entityName}s`,
                message: `Are you sure you want to delete ${selected.length} ${entityName.toLowerCase()}(s)? This action cannot be undone.`,
                confirmText: `Delete ${selected.length} ${entityName}${selected.length > 1 ? 's' : ''}`,
                cancelText: 'Cancel',
                type: 'danger',
                onConfirm: () => {
                    // Capture the selected items at confirmation time to ensure they're still available
                    const itemsToDelete = [...selected]; // Create a copy
                    showToast(`Deleting selected ${entityName.toLowerCase()}s...`, "info", 1000);
                    Promise.all(
                        itemsToDelete.map(row =>
                            fetch(`${deleteUrl}/${row.id}/delete`, { method: "POST" })
                        )
                    ).then(() => {
                        table.replaceData();
                        showToast(`Deleted ${itemsToDelete.length} ${entityName.toLowerCase()}(s) successfully`, "success");
                    }).catch(err => {
                        console.error(err);
                        showToast(`Error deleting ${entityName.toLowerCase()}s`, "error");
                    });
                }
            });
        });
    }
}
window.addBulkDeleteHandler = addBulkDeleteHandler;

/**
 * Initialize a tag selector dropdown for forms
 * @param {string} selectorId - ID of the tag selector element (default: 'tagSelector')
 * @param {Object} options - Configuration options
 * @param {string} options.fieldName - Name of the checkbox inputs (default: 'tags')
 * @param {string} options.placeholder - Placeholder text (default: 'Select tags...')
 */
function initializeTagSelector(selectorId = 'tagSelector', options = {}) {
    const config = {
        fieldName: 'tags',
        placeholder: 'Select tags...',
        ...options
    };

    // Small delay to ensure DOM is ready when called from HTMX-loaded content
    setTimeout(function () {
        try {
            const tagSelector = document.getElementById(selectorId);
            const tagDisplay = tagSelector ? tagSelector.querySelector('.tag-display') : null;
            const checkboxes = document.querySelectorAll(`input[name="${config.fieldName}"]`);

            if (!tagSelector || !tagDisplay) {
                console.warn(`Tag selector elements not found for ID: ${selectorId}`);
                return;
            }

            function updateTagDisplay() {
                try {
                    const selectedTags = Array.from(checkboxes)
                        .filter(cb => cb.checked)
                        .map(cb => cb.nextElementSibling.textContent.trim());

                    if (selectedTags.length === 0) {
                        tagDisplay.textContent = config.placeholder;
                        tagDisplay.classList.remove('has-selection');
                    } else if (selectedTags.length === 1) {
                        tagDisplay.textContent = selectedTags[0];
                        tagDisplay.classList.add('has-selection');
                    } else {
                        // Create badges for multiple selections
                        const badgeHtml = selectedTags.map(tag =>
                            `<span class="selected-tag">${tag}</span>`
                        ).join(' ');
                        tagDisplay.innerHTML = badgeHtml;
                        tagDisplay.classList.add('has-selection');
                    }
                } catch (error) {
                    console.error('Error updating tag display:', error);
                }
            }

            // Remove existing event listeners to prevent duplicates
            checkboxes.forEach(checkbox => {
                checkbox.removeEventListener('change', updateTagDisplay);
                checkbox.addEventListener('change', updateTagDisplay);
            });

            // Initialize display immediately (important for edit mode)
            updateTagDisplay();

            // Prevent dropdown from closing when clicking checkboxes
            const dropdownMenu = tagSelector.parentElement.querySelector('.dropdown-menu');
            if (dropdownMenu) {
                dropdownMenu.removeEventListener('click', stopPropagation);
                dropdownMenu.addEventListener('click', stopPropagation);
            }

            function stopPropagation(e) {
                e.stopPropagation();
            }

            console.log(`Tag selector initialized for: ${selectorId}`);
        } catch (error) {
            console.error(`Error initializing tag selector for ${selectorId}:`, error);
        }
    }, 50);
}

// Export to global scope
window.initializeTagSelector = initializeTagSelector;

// === TABLE GROUPING UTILITIES ===

/**
 * Set table grouping for demo table or any registered table
 * @param {string} field - Field to group by ('none', 'status', 'assignee', 'enabled')
 * @param {string} tableId - Table ID (defaults to 'demo-table')
 */
function setTableGrouping(field, tableId = 'demo-table') {
    const table = window.appTables && window.appTables[tableId];
    if (!table) {
        console.error(`Table ${tableId} not found in registry`);
        return;
    }

    try {
        if (field === 'none' || field === false) {
            table.setGroupBy(false);
            console.log(`[${tableId}] Grouping disabled`);
        } else {
            table.setGroupBy(field);
            console.log(`[${tableId}] Grouped by: ${field}`);
        }
    } catch (error) {
        console.error(`Error setting table grouping:`, error);
    }
}

/**
 * Custom group header formatter with icons and styling
 * @param {*} value - Group value
 * @param {number} count - Number of items in group
 * @param {Array} data - Group data
 * @param {Object} group - Group object
 * @returns {string} HTML for group header
 */
function formatGroupHeader(value, count, data, group) {
    const field = group.getField();
    let icon = 'ti ti-folder';
    let displayValue = value || 'Unknown';

    // Customize icons based on field type
    switch (field) {
        case 'status':
            icon = getStatusIcon(value);
            break;
        case 'assignee':
            icon = 'ti ti-user';
            displayValue = value || 'Unassigned';
            break;
        case 'enabled':
            icon = value ? 'ti ti-toggle-right' : 'ti ti-toggle-left';
            displayValue = value ? 'Enabled' : 'Disabled';
            break;
        default:
            icon = 'ti ti-folder';
    }

    return `
        <div class="group-header-content">
            <i class="${icon}"></i>
            <span class="group-title">${displayValue}</span>
            <span class="group-count badge bg-secondary ms-2">${count}</span>
        </div>
    `;
}

/**
 * Get status icon for group headers
 */
function getStatusIcon(status) {
    const icons = {
        'active': 'ti ti-circle-check',
        'inactive': 'ti ti-circle-x',
        'pending': 'ti ti-clock',
    };
    return icons[status] || 'ti ti-circle-dot';
}

// Export grouping functions
window.setTableGrouping = setTableGrouping;
window.formatGroupHeader = formatGroupHeader;

// === QUICK SEARCH UTILITIES ===

/**
 * Initialize quick search functionality for any table
 * @param {string} searchInputId - ID of search input (default: 'table-quick-search')
 * @param {string} clearButtonId - ID of clear button (default: 'clear-search-btn')
 * @param {string} tableId - Table ID to search (default: 'demo-table')
 */
function initializeQuickSearch(searchInputId = 'table-quick-search', clearButtonId = 'clear-search-btn', tableId = 'demo-table') {
    const searchInput = document.getElementById(searchInputId);
    const clearButton = document.getElementById(clearButtonId);
    const table = window.appTables && window.appTables[tableId];

    if (!searchInput || !table) {
        console.warn(`Quick search initialization failed: missing search input (${searchInputId}) or table (${tableId})`);
        return;
    }

    let searchTimeout;

    // Real-time search with debounce
    searchInput.addEventListener('input', function (e) {
        const query = e.target.value.trim();

        // Clear previous timeout
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }

        // Debounce search to avoid excessive filtering
        searchTimeout = setTimeout(() => {
            if (query === '') {
                // Clear all filters
                table.clearFilter();
                toggleClearButton(false);
                console.log(`[${tableId}] Search cleared`);
            } else {
                // Apply global search filter using the performGlobalSearch function
                performGlobalSearch(table, query);
                toggleClearButton(true);
                console.log(`[${tableId}] Global search: "${query}"`);
            }
        }, 300); // 300ms debounce
    });

    // Clear search functionality
    if (clearButton) {
        clearButton.addEventListener('click', function () {
            searchInput.value = '';
            table.clearFilter();
            toggleClearButton(false);
            searchInput.focus();
            console.log(`[${tableId}] Search manually cleared`);
        });
    }

    // Show/hide clear button
    function toggleClearButton(show) {
        if (clearButton) {
            clearButton.style.display = show ? 'block' : 'none';
        }
    }

    // Keyboard shortcuts
    searchInput.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            searchInput.value = '';
            table.clearFilter();
            toggleClearButton(false);
            searchInput.blur();
        }
    });

    console.log(`Quick search initialized for table: ${tableId}`);
}

/**
 * Advanced search across all searchable columns
 * @param {Object} table - Tabulator table instance
 * @param {string} query - Search query
 * @param {Array} searchableFields - Fields to search (default: auto-detect)
 */
function performGlobalSearch(table, query, searchableFields = null) {
    if (!table || !query) {
        table?.clearFilter();
        return;
    }

    // Auto-detect searchable fields if not provided
    if (!searchableFields) {
        const columns = table.getColumnDefinitions();
        searchableFields = columns
            .filter(col => col.field && col.field !== 'actions' && col.field !== 'id')
            .map(col => col.field);
    }

    console.log('Searching fields:', searchableFields, 'for query:', query);

    // Use a custom filter function that handles different data types
    table.setFilter(function (data) {
        const searchTerm = query.toLowerCase();

        return searchableFields.some(field => {
            const value = data[field];

            if (value === null || value === undefined) {
                return false;
            }

            // Handle different data types
            if (typeof value === 'string') {
                return value.toLowerCase().includes(searchTerm);
            } else if (typeof value === 'boolean') {
                return value.toString().toLowerCase().includes(searchTerm);
            } else if (Array.isArray(value)) {
                // Handle arrays (like tags)
                return value.some(item =>
                    item && item.toString().toLowerCase().includes(searchTerm)
                );
            } else if (typeof value === 'object') {
                // Handle objects (like assignee)
                const objStr = JSON.stringify(value).toLowerCase();
                return objStr.includes(searchTerm);
            } else {
                // Handle numbers, dates, etc.
                return value.toString().toLowerCase().includes(searchTerm);
            }
        });
    });

    console.log(`Global search applied: "${query}" across fields:`, searchableFields);
}

// Export search functions
window.initializeQuickSearch = initializeQuickSearch;
window.performGlobalSearch = performGlobalSearch;

// === GLOBAL HTMX FORM HANDLER ===

/**
 * Global HTMX form submission handler for all table forms
 * Handles modal closing and table refresh for any form ending with "-form"
 */
function initializeGlobalFormHandler() {
    document.body.addEventListener("htmx:afterRequest", (e) => {
        // Only handle forms that end with "-form"
        if (e.target.id && e.target.id.endsWith('-form')) {
            // Check if request was successful (status 200-299)
            if (e.detail.xhr.status >= 200 && e.detail.xhr.status < 300) {
                // Determine if it was create or edit based on the form action
                const isCreate = e.target.hasAttribute('hx-post');
                const isEdit = e.target.hasAttribute('hx-put');

                // Extract entity name from form ID (e.g., "user-form" -> "User")
                const entityName = e.target.id.replace('-form', '').replace('-', ' ')
                    .split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

                // Show success toast
                if (isCreate) {
                    showToast(`${entityName} created successfully`, "success");
                } else if (isEdit) {
                    showToast(`${entityName} updated successfully`, "success");
                } else {
                    showToast("Operation completed successfully", "success");
                }

                // Close the modal with proper focus restoration
                if (window.closeModal) {
                    window.closeModal();
                }

                // Refresh the table after a short delay
                setTimeout(() => {
                    // Try to find the associated table by common naming patterns
                    const possibleTableIds = [
                        e.target.id.replace('-form', '-table'),
                        e.target.id.replace('-form', '') + 's-table',
                        e.target.id.replace('-form', '') + '-table',
                        'demo-table', // fallback for demo
                        'user-table'  // fallback for users
                    ];

                    let tableRefreshed = false;
                    for (const tableId of possibleTableIds) {
                        if (window.appTables && window.appTables[tableId]) {
                            window.appTables[tableId].replaceData();
                            tableRefreshed = true;
                            break;
                        }
                    }

                    // Additional refresh methods as fallback
                    if (!tableRefreshed && window.refreshTable) {
                        for (const tableId of possibleTableIds) {
                            try {
                                window.refreshTable(tableId);
                                break;
                            } catch (e) {
                                // Continue to next table ID
                            }
                        }
                    }
                }, 100);
            }
        }
    });
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeGlobalFormHandler);
} else {
    // DOM is already loaded
    initializeGlobalFormHandler();
}
