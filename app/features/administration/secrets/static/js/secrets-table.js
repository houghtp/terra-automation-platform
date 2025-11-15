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
                width: 130,
                headerSort: false,
                formatter: (cell) => formatRowActions(cell, [
                    { icon: 'ti-eye', title: 'View Secret', action: 'viewSecretDetails' },
                    { icon: 'ti-edit', title: 'Edit Secret', action: 'editSecret' },
                    { icon: 'ti-trash', title: 'Delete Secret', action: 'deleteSecret', class: 'row-action-icon text-danger' }
                ])
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

function showSecretsModal() {
    const modalEl = document.getElementById('modal');
    if (!modalEl) {
        console.warn('[secrets] modal element not found');
        return;
    }
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl, {
        backdrop: "static",
        keyboard: false,
        focus: true
    });
    modal.show();
}

window.viewSecretDetails = function (secretId) {
    htmx.ajax('GET', `/features/administration/secrets/partials/secret_details?secret_id=${secretId}`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        showSecretsModal();
    });
};

window.editSecret = function (secretId) {
    const url = secretId
        ? `/features/administration/secrets/${secretId}/edit`
        : `/features/administration/secrets/partials/form`;

    htmx.ajax('GET', url, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        showSecretsModal();
    });
};

window.deleteSecret = function (secretId) {
    const rowData = window.secretsTable?.getRow(secretId)?.getData();
    const secretName = rowData?.name || 'this secret';

    showConfirmModal({
        title: 'Delete Secret',
        message: `Are you sure you want to delete "${secretName}"? This action cannot be undone.`,
        type: 'danger',
        confirmText: 'Delete',
        cancelText: 'Cancel',
        onConfirm: function () {
            htmx.ajax('DELETE', `/features/administration/secrets/api/${secretId}`, {
                swap: 'none'
            }).then(() => {
                if (window.showToast) {
                    window.showToast('Secret deleted successfully', 'success');
                }
                if (window.refreshSecrets) {
                    window.refreshSecrets();
                }
            }).catch((error) => {
                console.error('[secrets] failed to delete secret', error);
                if (window.showToast) {
                    window.showToast('Failed to delete secret', 'error');
                }
            });
        }
    });
};

window.refreshSecrets = function () {
    if (window.refreshTable) {
        window.refreshTable('secrets-table');
        return;
    }
    if (window.secretsTable) {
        window.secretsTable.setData();
    }
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
