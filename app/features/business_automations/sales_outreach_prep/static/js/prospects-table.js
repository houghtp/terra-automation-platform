/**
 * Prospects Tabulator Table for Sales Outreach Prep
 */

window.initializeProspectsTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    // Build URL with campaign filter if present
    let apiUrl = '/features/business-automations/sales-outreach-prep/prospects/api/list';
    if (typeof CAMPAIGN_ID !== 'undefined' && CAMPAIGN_ID) {
        apiUrl += `?campaign_id=${CAMPAIGN_ID}`;
    }

    // Build columns array
    const columns = [
        {
            title: "Name",
            field: "full_name",
            widthGrow: 3,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter names...",
            sorter: "string",
            formatter: function (cell) {
                const row = cell.getRow().getData();
                const linkedin = row.linkedin_url ? ` <a href="${row.linkedin_url}" target="_blank" class="text-muted"><i class="ti ti-brand-linkedin"></i></a>` : '';
                return `<strong>${row.full_name}</strong>${linkedin}`;
            }
        },
        {
            title: "Title",
            field: "job_title",
            widthGrow: 3,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter titles..."
        },
        {
            title: "Email",
            field: "email",
            widthGrow: 3,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter emails...",
            formatter: function (cell) {
                const email = cell.getValue();
                const row = cell.getRow().getData();
                if (email) {
                    const confidence = row.email_confidence ? ` <span class="text-muted">(${row.email_confidence}%)</span>` : '';
                    return `${email}${confidence}`;
                }
                return '<span class="text-muted">-</span>';
            }
        },
        {
            title: "Location",
            field: "location",
            widthGrow: 2,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter location..."
        },
        {
            title: "Status",
            field: "status",
            widthGrow: 2,
            headerFilter: "list",
            headerFilterParams: {
                values: {
                    "": "All Statuses",
                    "new": "New",
                    "enriched": "Enriched",
                    "qualified": "Qualified",
                    "contacted": "Contacted",
                    "unqualified": "Unqualified",
                    "bounced": "Bounced"
                }
            },
            sorter: "string",
            formatter: formatStatusBadge
        },
        {
            title: "Enrichment",
            field: "enrichment_status",
            widthGrow: 2,
            headerFilter: "list",
            headerFilterParams: {
                values: {
                    "": "All",
                    "not_started": "Not Started",
                    "in_progress": "In Progress",
                    "enriched": "Enriched",
                    "failed": "Failed"
                }
            },
            sorter: "string",
            formatter: function (cell) {
                const value = cell.getValue();
                if (!value) return '<span class="app-badge app-badge-neutral">-</span>';
                const normalized = value.toString().toLowerCase();
                const variant = normalized === 'enriched' ? 'success'
                    : normalized === 'in_progress' ? 'warning'
                    : normalized === 'failed' ? 'danger'
                    : 'neutral';
                const display = value.replace('_', ' ');
                return `<span class="app-badge app-badge-${variant}">${display}</span>`;
            }
        },
        {
            title: "Actions",
            field: "actions",
            headerSort: false,
            headerFilter: false,
            width: 80,
            hozAlign: "right",
            formatter: function (cell) {
                const rowData = cell.getRow().getData();
                // Use standard CRUD buttons
                return createRowCrudButtons(rowData, {
                    onEdit: "editProspect",
                    onDelete: "deleteProspect"
                });
            }
        }
    ];

    // Initialize table with advancedTableConfig
    const table = new Tabulator('#prospects-table', {
        ...advancedTableConfig,
        ajaxURL: apiUrl,
        columns: columns,
        // Return data array directly (Tabulator handles pagination via last_page in response)
        ajaxResponse: function(url, params, response) {
            // Store last_page for pagination (Tabulator will read it from response)
            this.lastPage = response.last_page;
            // Return just the data array
            return response.data;
        }
    });

    // Store in global registry
    window.prospectsTable = table;
    window.appTables["prospects-table"] = table;

    return table;
};

/**
 * Edit prospect
 */
window.editProspect = function (prospectId) {
    editTabulatorRow(`/features/business-automations/sales-outreach-prep/prospects/partials/form?prospect_id=${prospectId}`);
};

/**
 * Delete prospect
 */
window.deleteProspect = function (prospectId) {
    deleteTabulatorRow(`/features/business-automations/sales-outreach-prep/prospects/${prospectId}`, '#prospects-table', {
        title: 'Delete Prospect',
        message: 'Are you sure you want to delete this prospect?',
        confirmText: 'Delete Prospect',
        cancelText: 'Cancel'
    });
};

/**
 * Trigger manual enrichment for campaign prospects
 */
window.enrichProspects = async function (campaignId) {
    if (!confirm('This will enrich all prospects in this campaign with email addresses using Hunter.io credits. Continue?')) {
        return;
    }

    const btn = document.getElementById('enrich-prospects-btn');
    if (!btn) return;

    // Disable button and show loading state
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Enriching...';

    try {
        const response = await fetch(`/features/business-automations/sales-outreach-prep/prospects/enrich`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ campaign_id: campaignId })
        });

        if (response.ok) {
            const data = await response.json();
            showToast(`Enrichment task started! Task ID: ${data.task_id}`, 'success');

            // Refresh table after a delay to show status updates
            setTimeout(() => {
                if (window.prospectsTable) {
                    window.prospectsTable.setData();
                }
            }, 2000);
        } else {
            const error = await response.json();
            showToast(error.detail || 'Failed to start enrichment', 'error');
        }
    } catch (error) {
        console.error('Enrichment error:', error);
        showToast('Failed to start enrichment task', 'error');
    } finally {
        // Re-enable button
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-mail icon"></i> Enrich Prospects';
    }
};

// Initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("prospects-table");

    if (tableElement && !window.prospectsTableInitialized) {
        window.prospectsTableInitialized = true;
        initializeProspectsTable();

        // Initialize quick search if available
        setTimeout(() => {
            if (typeof initializeQuickSearch === 'function') {
                initializeQuickSearch('table-quick-search', 'clear-search-btn', 'prospects-table');
            }
        }, 100);
    }
});
