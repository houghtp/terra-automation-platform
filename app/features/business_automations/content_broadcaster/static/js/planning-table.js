/**
 * Content Planning Table Configuration
 * Manages the Tabulator table for content planning/ideas
 */

// Status badge formatter
function formatStatus(cell) {
    const status = cell.getValue();
    const statusClass = `status-${status}`;
    return `<span class="status-badge ${statusClass}">${status.replace('_', ' ')}</span>`;
}

// SEO Score formatter
function formatSEOScore(cell) {
    const score = cell.getValue();
    if (!score) return '<span class="text-muted">-</span>';

    let scoreClass = 'seo-fail';
    if (score >= 95) scoreClass = 'seo-excellent';
    else if (score >= 90) scoreClass = 'seo-good';
    else if (score >= 80) scoreClass = 'seo-fair';
    else if (score >= 70) scoreClass = 'seo-poor';

    return `<span class="seo-score ${scoreClass}">${score}</span>`;
}

// Actions formatter - create action buttons based on status
function formatActions(cell) {
    const rowData = cell.getRow().getData();
    const status = rowData.status;
    const planId = rowData.id;

    // Build extra action buttons first
    let extraButtons = '';

    // Generate button (only if planned or failed)
    if (status === 'planned' || status === 'failed') {
        extraButtons += `
            <i class="ti ti-robot row-action-icon generate-btn ms-2"
               title="Generate with AI"
               onclick="generateContent('${planId}')"></i>`;
    }

    // View draft button (only if draft_ready or approved)
    if (status === 'draft_ready' || status === 'approved') {
        extraButtons += `
            <i class="ti ti-eye row-action-icon view-draft-btn ms-2"
               title="View Draft"
               onclick="viewDraft('${planId}')"></i>`;
    }

    // Standard edit/delete buttons - pass extra buttons to be included inside the container
    return `
        <div class="row-actions" data-id="${rowData.id}" style="display: flex; align-items: center;">
            <i class="ti ti-edit row-action-icon edit-btn"
               title="Edit"
               style="cursor: pointer; font-size: 18px; color: #0054a6; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;">
            </i>
            <i class="ti ti-trash row-action-icon delete-btn"
               title="Delete"
               style="cursor: pointer; font-size: 18px; color: #d63939; padding: 4px; border-radius: 4px; transition: all 0.2s;">
            </i>
            ${extraButtons}
        </div>
    `;
}

// Initialize Content Plans Table
window.initializeContentPlansTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#content-plans-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/content-broadcaster/planning/api/list",
        placeholder: "No content ideas yet. Click 'Add Content Idea' to get started!",
        columns: [
            {
                title: "Title",
                field: "title",
                minWidth: 200,
                headerFilter: "input",
                formatter: function (cell) {
                    return `<strong>${cell.getValue()}</strong>`;
                }
            },
            {
                title: "Status",
                field: "status",
                width: 130,
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All",
                        "planned": "Planned",
                        "researching": "Researching",
                        "generating": "Generating",
                        "refining": "Refining",
                        "draft_ready": "Draft Ready",
                        "approved": "Approved",
                        "failed": "Failed"
                    }
                },
                formatter: formatStatus
            },
            {
                title: "Target Audience",
                field: "target_audience",
                minWidth: 150,
                headerFilter: "input",
                formatter: function (cell) {
                    const val = cell.getValue();
                    return val || '<span class="text-muted">General</span>';
                }
            },
            {
                title: "Tone",
                field: "tone",
                width: 120,
                headerFilter: "list",
                headerFilterParams: {
                    values: { "": "All", "professional": "Professional", "casual": "Casual", "friendly": "Friendly" }
                }
            },
            {
                title: "Research Mode",
                field: "skip_research",
                width: 140,
                headerFilter: "list",
                headerFilterParams: {
                    values: { "": "All", "false": "With Research", "true": "Direct Gen" }
                },
                formatter: function (cell) {
                    const skipped = cell.getValue();
                    if (skipped === true) {
                        return '<span class="badge bg-info"><i class="ti ti-bolt me-1"></i>Direct Gen</span>';
                    } else {
                        return '<span class="badge bg-primary"><i class="ti ti-search me-1"></i>With Research</span>';
                    }
                }
            },
            {
                title: "SEO Score",
                field: "seo_score",
                width: 100,
                headerSort: true,
                formatter: formatSEOScore
            },
            {
                title: "Created",
                field: "created_at",
                minWidth: 120,
                headerFilter: "input",
                formatter: formatDate
            },
            {
                title: "Actions",
                field: "id",
                width: 150,
                headerSort: false,
                formatter: formatActions
            }
        ]
    });

    // Store table reference globally
    window.contentPlansTable = table;
    window.appTables["content-plans-table"] = table;

    // Bulk Edit Selected
    addBulkEditHandler(table, '/features/content-broadcaster/planning');

    // Bulk Delete Selected
    addBulkDeleteHandler(table, '/features/content-broadcaster/planning', 'Content Plan');

    // Row action handlers for edit/delete buttons
    bindRowActionHandlers("#content-plans-table", {
        onEdit: "editContentPlan",
        onDelete: "deleteContentPlan"
    });

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('content-plans-table', format, 'content_plans');
};

// Edit content plan
window.editContentPlan = function (planId) {
    editTabulatorRow(`/features/content-broadcaster/planning/${planId}/edit`);
};

// Delete content plan
window.deleteContentPlan = function (planId) {
    deleteTabulatorRow(
        `/features/content-broadcaster/planning/${planId}/delete`,
        '#content-plans-table',
        {
            title: 'Delete Content Plan',
            message: 'Are you sure you want to delete this content plan? This action cannot be undone.',
            confirmText: 'Delete'
        }
    );
};

// Generate content with AI
window.generateContent = function (planId) {
    showConfirmModal({
        title: 'Generate AI Content',
        message: 'This will use AI to research, generate, and optimize content. It may take 1-2 minutes. Continue?',
        type: 'warning',
        confirmText: 'Generate',
        cancelText: 'Cancel',
        onConfirm: function () {
            // Show loading state
            showToast('Starting AI content generation...', 'info');

            // Use HTMX to make the request
            htmx.ajax('POST', `/features/content-broadcaster/planning/${planId}/process`, {
                values: { use_research: 'true' },
                swap: 'none'
            });
        }
    });
};

// View content plan - navigate to full page viewer
window.viewDraft = function (planId) {
    window.location.href = `/features/content-broadcaster/planning/${planId}/view`;
};

// Listen for HX-Trigger events from the server
document.body.addEventListener('showSuccess', function () {
    showToast('Action completed successfully', 'success');
});

document.body.addEventListener('refreshTable', function () {
    if (window.contentPlansTable) {
        window.contentPlansTable.setData();
    }
});

document.body.addEventListener('closeModal', function () {
    const modalElement = document.getElementById('modal');
    if (!modalElement || typeof bootstrap === 'undefined') {
        return;
    }
    const modalInstance = bootstrap.Modal.getInstance(modalElement);
    if (modalInstance) {
        modalInstance.hide();
    }
});

// Initialize table on page load
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("content-plans-table");

    if (tableElement && !window.contentPlansTableInitialized) {
        window.contentPlansTableInitialized = true;
        initializeContentPlansTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'content-plans-table');
        }, 100);
    }
});
