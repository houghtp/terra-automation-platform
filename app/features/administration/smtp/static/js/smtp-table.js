window.initializeSMTPManagementTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    // Check if user is global admin (set in template)
    const isGlobalAdmin = window.isGlobalAdmin || false;

    // Define base columns
    const columns = [
        {
            title: "Name",
            field: "name",
            editor: "input",
            headerFilter: "input",
            headerFilterPlaceholder: "Filter names...",
            sorter: "string"
        },
    ];

    // Add tenant column for global admins (after Name column)
    if (isGlobalAdmin) {
        columns.push({
            title: "Tenant",
            field: "tenant_name",
            headerFilter: "input",
            headerFilterPlaceholder: "Filter tenants...",
            width: 150,
            sorter: "string"
        });
    }

    // Add remaining columns
    columns.push(
        {
            title: "Description",
            field: "description",
            editor: "input",
            headerFilter: "input",
            headerFilterPlaceholder: "Filter descriptions...",
            sorter: "string",
            width: 200
        },
        {
            title: "Host",
            field: "host",
            editor: "input",
            headerFilter: "input",
            headerFilterPlaceholder: "Filter hosts...",
            sorter: "string"
        },
        {
            title: "Port",
            field: "port",
            editor: "number",
            headerFilter: "number",
            headerFilterPlaceholder: "Filter ports...",
            sorter: "number",
            width: 100
        },
        {
            title: "From Email",
            field: "from_email",
            editor: "input",
            headerFilter: "input",
            headerFilterPlaceholder: "Filter emails...",
            sorter: "string"
        },
        {
            title: "Status",
            field: "status",
            editor: "list",
            editorParams: {
                values: {
                    "inactive": "Inactive",
                    "active": "Active",
                    "testing": "Testing",
                    "failed": "Failed"
                }
            },
            headerFilter: "list",
            headerFilterParams: {
                values: {
                    "": "All Statuses",
                    "inactive": "Inactive",
                    "active": "Active",
                    "testing": "Testing",
                    "failed": "Failed"
                }
            },
            sorter: "string",
            formatter: formatStatusBadge
        },
        {
            title: "Encryption",
            field: "encryption",
            headerFilter: "list",
            headerFilterParams: {
                values: {
                    "": "All",
                    "TLS": "TLS",
                    "SSL": "SSL",
                    "None": "None"
                }
            },
            sorter: "string",
            width: 120,
            formatter: function (cell) {
                const value = cell.getValue();
                const color = value === 'TLS' ? 'success' : value === 'SSL' ? 'info' : 'neutral';
                return `<span class="app-badge app-badge-${color}">${value || 'None'}</span>`;
            }
        },
        {
            title: "Enabled",
            field: "enabled",
            headerFilter: "list",
            headerFilterParams: {
                values: {
                    "": "All",
                    "true": "Enabled",
                    "false": "Disabled"
                }
            },
            sorter: "boolean",
            width: 100,
            formatter: "toggle",
            formatterParams: {
                size: 20,
                onValue: true,
                offValue: false,
                onTruthy: true,
                onColor: "#10b981",
                offColor: "#ef4444",
                clickable: true
            }
        },
        {
            title: "Tags",
            field: "tags",
            headerFilter: "input",
            headerFilterPlaceholder: "Search tags...",
            headerFilterFunc: arraySearchFilter,
            formatter: formatTags,
            sorter: arrayLengthSorter,
            width: 300
        },
        {
            title: "Actions",
            field: "actions",
            formatter: function (cell) {
                const rowData = cell.getRow().getData();
                const extraActions = `
                    <button type="button" class="btn btn-sm btn-outline-info me-1"
                            onclick="testSMTPConfiguration('${rowData.id}')"
                            title="Test Configuration">
                        <i class="ti ti-mail-check"></i>
                    </button>
                    ${rowData.status === 'active' ?
                        `<button type="button" class="btn btn-sm btn-outline-warning me-1"
                                 onclick="deactivateSMTPConfiguration('${rowData.id}')"
                                 title="Deactivate">
                            <i class="ti ti-power"></i>
                         </button>` :
                        `<button type="button" class="btn btn-sm btn-outline-success me-1"
                                 onclick="activateSMTPConfiguration('${rowData.id}')"
                                 title="Activate">
                            <i class="ti ti-power"></i>
                         </button>`
                    }
                `;
                return createRowCrudButtons(rowData, {
                    onEdit: "editSMTPConfiguration",
                    onDelete: "deleteSMTPConfiguration"
                }, extraActions);
            },
            headerSort: false,
            width: 200
        }
    );

    const table = new Tabulator("#smtp-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/administration/smtp/api/list",
        columns: columns
    });

    // Store in global registry
    window.smtpManagementTable = table;
    window.appTables["smtp-table"] = table;

    // Add cellEdited event listener
    addCellEditedHandler(table, '/features/administration/smtp', 'SMTP Configuration');

    // Bulk Edit Selected
    addBulkEditHandler(table, '/features/administration/smtp');

    // Bulk Delete Selected
    addBulkDeleteHandler(table, '/features/administration/smtp', 'SMTP Configuration');

    // Row action handlers for both edit and delete
    bindRowActionHandlers("#smtp-table", {
        onEdit: "editSMTPConfiguration",
        onDelete: "deleteSMTPConfiguration"
    });

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('smtp-table', format, 'smtp_configurations');
};

window.deleteSMTPConfiguration = function (id) {
    deleteTabulatorRow(`/features/administration/smtp/${id}/delete`, '#smtp-table', {
        title: 'Delete SMTP Configuration',
        message: 'Are you sure you want to delete this SMTP configuration? This action cannot be undone.',
        confirmText: 'Delete Configuration',
        cancelText: 'Cancel'
    });
};

window.editSMTPConfiguration = function (id) {
    editTabulatorRow(`/features/administration/smtp/${id}/edit`);
};

window.testSMTPConfiguration = function (id) {
    const testEmail = prompt('Enter email address to test SMTP configuration:');
    if (testEmail && testEmail.trim()) {
        fetch(`/features/administration/smtp/${id}/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `test_email=${encodeURIComponent(testEmail.trim())}`
        })
            .then(response => response.text())
            .then(html => {
                // Show result in a modal or alert
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = html;
                const resultText = tempDiv.textContent || tempDiv.innerText || '';
                alert(resultText);

                // Refresh the table to show any status updates
                if (window.smtpManagementTable) {
                    window.smtpManagementTable.replaceData();
                }
            })
            .catch(error => {
                console.error('Error testing SMTP configuration:', error);
                alert('Error testing SMTP configuration. Please try again.');
            });
    }
};

window.activateSMTPConfiguration = function (id) {
    if (confirm('Are you sure you want to activate this SMTP configuration?')) {
        fetch(`/features/administration/smtp/${id}/activate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => {
                if (response.ok) {
                    // Refresh the table
                    if (window.smtpManagementTable) {
                        window.smtpManagementTable.replaceData();
                    }
                    showToast('SMTP configuration activated successfully', 'success');
                } else {
                    throw new Error('Failed to activate configuration');
                }
            })
            .catch(error => {
                console.error('Error activating SMTP configuration:', error);
                showToast('Error activating SMTP configuration', 'error');
            });
    }
};

window.deactivateSMTPConfiguration = function (id) {
    if (confirm('Are you sure you want to deactivate this SMTP configuration?')) {
        fetch(`/features/administration/smtp/${id}/deactivate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
            .then(response => {
                if (response.ok) {
                    // Refresh the table
                    if (window.smtpManagementTable) {
                        window.smtpManagementTable.replaceData();
                    }
                    showToast('SMTP configuration deactivated successfully', 'success');
                } else {
                    throw new Error('Failed to deactivate configuration');
                }
            })
            .catch(error => {
                console.error('Error deactivating SMTP configuration:', error);
                showToast('Error deactivating SMTP configuration', 'error');
            });
    }
};

document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("smtp-table");

    if (tableElement && !window.smtpTableInitialized) {
        window.smtpTableInitialized = true;
        initializeSMTPManagementTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'smtp-table');
        }, 100);
    }
});
