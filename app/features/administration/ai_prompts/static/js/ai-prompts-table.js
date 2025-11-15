/**
 * AI Prompts Table Configuration
 * Tabulator table for managing AI prompt templates
 */

window.initializeAIPromptsTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#ai-prompts-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/administration/ai-prompts/api/list",
        placeholder: "No AI prompts found. Click 'New AI Prompt' to create one!",
        columns: [
            {
                title: "Name",
                field: "name",
                minWidth: 200,
                headerFilter: "input",
                formatter: function (cell) {
                    const name = cell.getValue();
                    const row = cell.getRow().getData();
                    const description = row.description || '';
                    const descPreview = description.length > 60 ? description.substring(0, 60) + '...' : description;

                    return `
                        <div class="d-flex flex-column">
                            <strong>${name}</strong>
                            ${descPreview ? `<small class="text-muted">${descPreview}</small>` : ''}
                        </div>
                    `;
                }
            },
            {
                title: "Key",
                field: "prompt_key",
                minWidth: 150,
                headerFilter: "input",
                formatter: function (cell) {
                    return `<code class="small">${cell.getValue()}</code>`;
                }
            },
            {
                title: "Category",
                field: "category",
                width: 130,
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All",
                        "content_generation": "Content Generation",
                        "channel_adaptation": "Channel Adaptation",
                        "seo_optimization": "SEO Optimization",
                        "general": "General"
                    }
                },
                formatter: function (cell) {
                    const category = cell.getValue() || 'general';
                    return `<span class="app-badge app-badge-info">${category}</span>`;
                }
            },
            {
                title: "AI Model",
                field: "ai_model",
                width: 120,
                headerFilter: "input",
                formatter: function (cell) {
                    const model = cell.getValue() || 'default';
                    return `<span class="app-badge app-badge-purple">${model}</span>`;
                }
            },
            {
                title: "Type",
                field: "tenant_id",
                width: 100,
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All",
                        "null": "System",
                        "custom": "Custom"
                    }
                },
                formatter: function (cell) {
                    const tenantId = cell.getValue();
                    if (tenantId) {
                        return `<span class="app-badge app-badge-success"><i class="ti ti-user me-1"></i>Custom</span>`;
                    } else {
                        return `<span class="app-badge app-badge-info"><i class="ti ti-world me-1"></i>System</span>`;
                    }
                }
            },
            {
                title: "Usage",
                field: "usage_count",
                width: 80,
                headerSort: true,
                formatter: function (cell) {
                    const count = cell.getValue() || 0;
                    return `<span class="text-muted">${count}</span>`;
                }
            },
            {
                title: "Success Rate",
                field: "success_rate",
                width: 120,
                headerSort: true,
                formatter: function (cell) {
                    const row = cell.getRow().getData();
                    const successCount = row.success_count || 0;
                    const failureCount = row.failure_count || 0;
                    const total = successCount + failureCount;

                    if (total === 0) {
                        return '<span class="text-muted">N/A</span>';
                    }

                    const rate = ((successCount / total) * 100).toFixed(1);
                    let color = 'red';
                    if (rate >= 90) color = 'green';
                    else if (rate >= 70) color = 'yellow';

                    return `<span class="app-badge app-badge-${color === 'green' ? 'success' : color === 'yellow' ? 'warning' : color === 'red' ? 'danger' : 'info'}">${rate}%</span>`;
                }
            },
            {
                title: "Status",
                field: "is_active",
                width: 100,
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All",
                        "true": "Active",
                        "false": "Inactive"
                    }
                },
                formatter: formatStatusBadge
            },
            {
                title: "Actions",
                field: "id",
                width: 120,
                headerSort: false,
                formatter: function (cell) {
                    const promptId = cell.getValue();
                    const row = cell.getRow().getData();
                    const promptName = row.name || '';

                    return `
                        <div class="btn-group" role="group">
                            <button class="btn btn-sm btn-ghost-secondary"
                                    onclick="viewPromptDetails(${promptId})"
                                    title="View Details">
                                <i class="ti ti-eye row-action-icon"></i>
                            </button>
                            <button class="btn btn-sm btn-ghost-secondary"
                                    onclick="editPrompt(${promptId})"
                                    title="Edit">
                                <i class="ti ti-edit row-action-icon"></i>
                            </button>
                            <button class="btn btn-sm btn-ghost-secondary"
                                    onclick="confirmDeletePrompt(${promptId}, '${promptName.replace(/'/g, "\\'")}')"
                                    title="Delete">
                                <i class="ti ti-trash row-action-icon text-danger"></i>
                            </button>
                        </div>
                    `;
                }
            }
        ]
    });

    // Store table reference globally
    window.aiPromptsTable = table;
    window.appTables["ai-prompts-table"] = table;

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('ai-prompts-table', format, 'ai_prompts');
};

// View prompt details modal
window.viewPromptDetails = function (promptId) {
    htmx.ajax('GET', `/features/administration/ai-prompts/partials/prompt_details?prompt_id=${promptId}`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        const modal = new bootstrap.Modal(document.getElementById('modal'));
        modal.show();
    });
};

// Edit prompt form
window.editPrompt = function (promptId) {
    htmx.ajax('GET', `/features/administration/ai-prompts/partials/prompt_form?prompt_id=${promptId}`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        const modal = new bootstrap.Modal(document.getElementById('modal'));
        modal.show();
    });
};

// Delete confirmation
window.confirmDeletePrompt = function (promptId, promptName) {
    showConfirmModal(
        'Delete AI Prompt?',
        `Are you sure you want to delete "${promptName}"? This action cannot be undone.`,
        'Delete',
        'btn-danger',
        function () {
            deletePrompt(promptId);
        }
    );
};

// Delete prompt
function deletePrompt(promptId) {
    htmx.ajax('DELETE', `/features/administration/ai-prompts/api/${promptId}`, {
        swap: 'none'
    }).then(() => {
        showToast('AI prompt deleted successfully', 'success');
        // Refresh table
        if (window.aiPromptsTable) {
            window.aiPromptsTable.replaceData();
        }
    }).catch((error) => {
        showToast('Failed to delete AI prompt', 'error');
        console.error('Delete error:', error);
    });
}

// Initialize table on page load
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("ai-prompts-table");

    if (tableElement && !window.aiPromptsTableInitialized) {
        window.aiPromptsTableInitialized = true;
        initializeAIPromptsTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'ai-prompts-table');
        }, 100);
    }
});
