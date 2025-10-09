window.initializeSecretsTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#secrets-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/administration/secrets/api/list",
        columns: [
            {
                title: "Name",
                field: "name",
                minWidth: 150,
                headerFilter: "input",
                formatter: function (cell) {
                    return `<strong>${cell.getValue()}</strong>`;
                }
            },
            {
                title: "Type",
                field: "secret_type",
                width: 120,
                headerFilter: "input",
                formatter: function (cell) {
                    const type = cell.getValue();
                    const color = type === 'api_key' ? 'blue' : 'gray';
                    return `<span class="badge bg-${color}">${type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>`;
                }
            },
            {
                title: "Description",
                field: "description",
                minWidth: 200,
                headerFilter: "input",
                formatter: function (cell) {
                    const desc = cell.getValue() || '';
                    if (desc.length > 80) {
                        return desc.substring(0, 80) + '...';
                    }
                    return desc;
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
                title: "Created",
                field: "created_at",
                minWidth: 120,
                headerFilter: "input",
                formatter: formatDate
            },
            {
                title: "Actions",
                field: "id",
                width: 100,
                headerSort: false,
                formatter: (cell) => formatViewAction(cell, 'viewSecretDetails')
            }
        ]
    });

    // Store table reference globally
    window.secretsTable = table;
    window.appTables["secrets-table"] = table;

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('secrets-table', format, 'secrets');
};

window.viewSecretDetails = function (secretId) {
    // Use HTMX to load secret details
    htmx.ajax('GET', `/features/administration/secrets/partials/secret_details?secret_id=${secretId}`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('modal'));
        modal.show();
    });
};

document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("secrets-table");

    if (tableElement && !window.secretsTableInitialized) {
        window.secretsTableInitialized = true;
        initializeSecretsTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'secrets-table');
        }, 100);
    }
});
