/**
 * AI Prompts Table Configuration
 * Tabulator table for managing AI prompt templates
 */

if (typeof window.aiPromptsIsGlobalAdmin === 'undefined') {
    window.aiPromptsIsGlobalAdmin = false;
}
if (typeof window.aiPromptsTenantId === 'undefined') {
    window.aiPromptsTenantId = null;
}

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
                minWidth: 160,
                widthGrow: 2,
                cssClass: "tabulator-cell-wrap",
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
                minWidth: 130,
                widthGrow: 1,
                cssClass: "tabulator-cell-wrap",
                headerFilter: "input",
                formatter: function (cell) {
                    return `<code class="small">${cell.getValue()}</code>`;
                }
            },
            {
                title: "Category",
                field: "category",
                widthGrow: 1,
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
                widthGrow: 1,
                headerFilter: "input",
                formatter: function (cell) {
                    const model = cell.getValue() || 'default';
                    return `<span class="app-badge app-badge-purple">${model}</span>`;
                }
            },
            {
                title: "Type",
                field: "tenant_id",
                width: 110,
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
                width: 90,
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
                width: 110,
                headerSort: false,
                formatter: function (cell) {
                    const promptId = cell.getValue();
                    const row = cell.getRow().getData();
                    const isSystem = !!row.is_system;
                    const ownedByTenant = !!row.tenant_id && row.tenant_id === window.aiPromptsTenantId;
                    const canEdit = Boolean(window.aiPromptsIsGlobalAdmin || (ownedByTenant && !isSystem));

                    return `
                        <div class="row-actions" data-id="${promptId}" style="display:flex;align-items:center;">
                            <i class="ti ti-eye row-action-icon"
                               title="View Details"
                               onclick="viewPromptDetails(${promptId})"></i>
                            ${canEdit ? `
                            <i class="ti ti-edit row-action-icon"
                               title="Edit"
                               onclick="editPrompt(${promptId})"></i>
                            ` : ''}
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
    htmx.ajax('GET', `/features/administration/ai-prompts/partials/details?prompt_id=${promptId}`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        if (typeof window.showModal === 'function') {
            window.showModal();
        }
    });
};

// Edit prompt form
window.editPrompt = function (promptId) {
    htmx.ajax('GET', `/features/administration/ai-prompts/forms/${promptId}/edit`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        if (typeof window.showModal === 'function') {
            window.showModal();
        }
    });
};

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
