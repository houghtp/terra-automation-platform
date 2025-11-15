/**
 * Content Planning Table Configuration
 * Manages the Tabulator table for content planning/ideas
 */

function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value).replace(/[&<>"']/g, function (char) {
        const ESCAPE_MAP = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        };
        return ESCAPE_MAP[char] || char;
    });
}

// Status badge formatter
function formatStatus(cell) {
    const status = cell.getValue();
    const rowData = cell.getRow().getData() || {};
    const statusClass = `status-${status}`;
    const normalizedLabel = (status || "unknown").replace(/_/g, " ");
    const displayLabel = normalizedLabel.charAt(0).toUpperCase() + normalizedLabel.slice(1);

    let tooltip = displayLabel;
    let leadingIcon = "";

    if (status === "failed" && rowData.error_log) {
        let errorMessage = String(rowData.error_log).trim();
        if (errorMessage.length > 220) {
            errorMessage = `${errorMessage.slice(0, 217)}…`;
        }
        tooltip = `Failed: ${errorMessage}`;
        leadingIcon = '<i class="ti ti-alert-triangle me-1"></i>';
    }

    return `<span class="status-badge ${statusClass}" data-status="${escapeHtml(status)}" title="${escapeHtml(tooltip)}">${leadingIcon}${escapeHtml(displayLabel)}</span>`;
}

// SEO Score formatter with iteration indicator
function formatSEOScore(cell) {
    const rowData = cell.getRow().getData();
    const score = rowData.latest_seo_score;

    if (!score && score !== 0) return '<span class="text-muted">Pending</span>';

    let scoreClass = 'seo-fail';
    let scoreLabel = 'Needs Work';
    let scoreIcon = 'ti-alert-circle';

    if (score >= 95) {
        scoreClass = 'seo-excellent';
        scoreLabel = 'Excellent';
        scoreIcon = 'ti-circle-check';
    } else if (score >= 90) {
        scoreClass = 'seo-good';
        scoreLabel = 'Good';
        scoreIcon = 'ti-circle-check';
    } else if (score >= 80) {
        scoreClass = 'seo-fair';
        scoreLabel = 'Fair';
        scoreIcon = 'ti-alert-triangle';
    } else if (score >= 70) {
        scoreClass = 'seo-poor';
        scoreLabel = 'Poor';
        scoreIcon = 'ti-alert-triangle';
    }

    // Get iteration count if available
    const iterations = rowData.refinement_history ? rowData.refinement_history.length : 1;
    const iterationBadge = iterations > 1 ? `<small class="ms-1 text-muted" style="font-size: 0.75em;">×${iterations}</small>` : '';

    return `
        <div class="d-flex align-items-center gap-1">
            <span class="seo-score ${scoreClass}" title="${scoreLabel}: ${score}/100">
                <i class="ti ${scoreIcon}" style="font-size: 0.9em;"></i> ${score}
            </span>
            ${iterationBadge}
        </div>
    `;
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

            if (window.contentPlansTable) {
                const row = window.contentPlansTable.getRow(planId);
                if (row) {
                    const currentData = row.getData() || {};
                    const skipResearch = currentData.skip_research === true || currentData.skip_research === "true";
                    row.update({
                        status: skipResearch ? 'generating' : 'researching',
                        error_log: null
                    });
                }
            }

            // Use HTMX to make the request
            htmx.ajax('POST', `/features/content-broadcaster/planning/${planId}/process-async`, {
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

document.body.addEventListener("htmx:afterRequest", function (event) {
    const xhr = event.detail && event.detail.xhr;
    if (!xhr) {
        return;
    }

    if (xhr.status >= 400) {
        let message = "Request failed. Please try again.";
        const contentType = (xhr.getResponseHeader("content-type") || "").toLowerCase();
        const responseText = xhr.responseText || "";

        if (contentType.includes("application/json")) {
            try {
                const parsed = JSON.parse(responseText);
                if (parsed?.detail) {
                    message = parsed.detail;
                }
            } catch (jsonError) {
                // Fall back to default message
            }
        } else if (responseText) {
            const trimmed = responseText.trim();
            const titleMatch = trimmed.match(/<title>(.*?)<\/title>/i);
            if (titleMatch && titleMatch[1]) {
                message = titleMatch[1];
            } else if (trimmed.length < 300) {
                message = trimmed;
            } else if (xhr.statusText) {
                message = `${xhr.status} ${xhr.statusText}`;
            }
        } else if (xhr.statusText) {
            message = `${xhr.status} ${xhr.statusText}`;
        }

        if (typeof window.showToast === "function") {
            window.showToast(message, "error", 7000);
        }

        if (window.contentPlansTable) {
            window.contentPlansTable.setData();
        }
    }

    // Note: Modal close is handled globally by table-base.js
    // No need for custom closeModal logic here
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
