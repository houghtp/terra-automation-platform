window.initializeConnectorsManagementTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#connectors-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/connectors/api/list",
        columns: [
            {
                title: "Icon",
                field: "connector_icon_url",
                width: 60,
                formatter: function (cell) {
                    const rowData = cell.getRow().getData();
                    const iconUrl = rowData.connector_icon_url;
                    const iconClass = rowData.connector_icon_class;
                    const brandColor = rowData.connector_brand_color;

                    if (iconUrl) {
                        return `<img src="${iconUrl}" alt="Connector" style="width: 32px; height: 32px; object-fit: contain;">`;
                    } else if (iconClass) {
                        return `<i class="${iconClass}" style="font-size: 24px; ${brandColor ? `color: ${brandColor};` : ''}"></i>`;
                    } else {
                        return `<i class="ti ti-plug" style="font-size: 24px;"></i>`;
                    }
                },
                headerSort: false
            },
            {
                title: "Instance Name",
                field: "instance_name",
                editor: "input",
                headerFilter: "input",
                headerFilterPlaceholder: "Filter names...",
                sorter: "string",
                width: 200
            },
            {
                title: "Connector Type",
                field: "connector_display_name",
                headerFilter: "input",
                headerFilterPlaceholder: "Filter types...",
                sorter: "string",
                width: 150
            },
            {
                title: "Category",
                field: "connector_category",
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All Categories",
                        "social_media": "Social Media",
                        "email_marketing": "Email Marketing",
                        "marketing": "Marketing",
                        "productivity": "Productivity",
                        "ecommerce": "E-commerce",
                        "analytics": "Analytics",
                        "cms": "CMS",
                        "crm": "CRM",
                        "ai_ml": "AI/ML",
                        "data_extraction": "Data Extraction",
                        "storage": "Storage",
                        "communication": "Communication",
                        "other": "Other"
                    }
                },
                sorter: "string",
                width: 120,
                formatter: function (cell) {
                    const value = cell.getValue();
                    if (!value) return '';
                    const formatted = value.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                    return `<span class="app-badge app-badge-info">${formatted}</span>`;
                }
            },
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
                title: "Status",
                field: "status",
                editor: "list",
                editorParams: {
                    values: {
                        "pending_setup": "Pending Setup",
                        "active": "Active",
                        "error": "Error",
                        "disabled": "Disabled"
                    }
                },
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All Statuses",
                        "pending_setup": "Pending Setup",
                        "active": "Active",
                        "error": "Error",
                        "disabled": "Disabled"
                    }
                },
                sorter: "string",
                width: 120,
                formatter: function (cell) {
                    const value = cell.getValue();
                    let color = 'secondary';
                    switch (value) {
                        case 'active': color = 'success'; break;
                        case 'error': color = 'danger'; break;
                        case 'pending_setup': color = 'warning'; break;
                        case 'disabled': color = 'secondary'; break;
                    }
                    const formatted = value ? value.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()) : '';
                    return `<span class="app-badge app-badge-${color === 'secondary' ? 'neutral' : color}">${formatted}</span>`;
                }
            },
            {
                title: "Enabled",
                field: "is_enabled",
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
                title: "Last Sync",
                field: "last_sync",
                sorter: "datetime",
                width: 150,
                formatter: function (cell) {
                    const value = cell.getValue();
                    if (!value) return '<span class="text-muted">Never</span>';
                    const date = new Date(value);
                    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
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
                width: 200
            },
            {
                title: "Actions",
                field: "actions",
                formatter: function (cell) {
                    const rowData = cell.getRow().getData();
                    const extraActions = `
                        ${rowData.status === 'active' ?
                            `<i class="ti ti-power row-action-icon text-warning"
                               title="Disable"
                               onclick="disableConnector('${rowData.id}')"></i>` :
                            `<i class="ti ti-power row-action-icon text-success"
                               title="Enable"
                               onclick="enableConnector('${rowData.id}')"></i>`
                        }
                        <i class="ti ti-refresh row-action-icon text-info"
                           title="Sync Now"
                           onclick="syncConnector('${rowData.id}')"></i>
                        <i class="ti ti-test-pipe row-action-icon text-primary"
                           title="Test Connection"
                           onclick="testConnectorConnection('${rowData.id}')"></i>
                    `;
                    return `
                        <div class="d-flex gap-2">
                            <i class="ti ti-edit row-action-icon"
                               title="Edit"
                               onclick="editConnector('${rowData.id}')"></i>
                            <i class="ti ti-trash row-action-icon"
                               title="Delete"
                               onclick="deleteConnector('${rowData.id}')"></i>
                            ${extraActions}
                        </div>
                    `;
                },
                headerSort: false,
                width: 150
            }
        ]
    });

    // Store in global registry
    window.connectorsManagementTable = table;
    window.appTables["connectors-table"] = table;

    // Add cellEdited event listener
    addCellEditedHandler(table, '/features/connectors/api', 'Connector');

    // Bulk Edit Selected
    addBulkEditHandler(table, '/features/connectors/api');

    // Bulk Delete Selected
    addBulkDeleteHandler(table, '/features/connectors/api', 'Connector');

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('connectors-table', format, 'connectors');
};

// Row action handlers
window.deleteConnector = function (id) {
    showConfirmModal({
        title: 'Delete Connector',
        message: 'Are you sure you want to delete this connector? This action cannot be undone.',
        confirmText: 'Delete Connector',
        cancelText: 'Cancel',
        onConfirm: function () {
            fetch(`/features/connectors/api/${id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => {
                    if (response.ok) {
                        // Refresh the table
                        if (window.connectorsManagementTable) {
                            window.connectorsManagementTable.replaceData();
                        }
                        showToast('Connector deleted successfully', 'success');
                    } else {
                        throw new Error('Failed to delete connector');
                    }
                })
                .catch(error => {
                    console.error('Error deleting connector:', error);
                    showToast('Error deleting connector', 'error');
                });
        }
    });
};

window.editConnector = function (id) {
    // Use HTMX to load the edit form
    htmx.ajax('GET', `/features/connectors/partials/form?connector_id=${id}`, {
        target: '#modal-body',
        swap: 'innerHTML'
    }).then(() => {
        // Show the modal
        const modal = new bootstrap.Modal(document.getElementById('modal'));
        modal.show();
    });
};

window.enableConnector = function (id) {
    fetch(`/features/connectors/api/${id}/enable`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => {
            if (response.ok) {
                // Refresh the table
                if (window.connectorsManagementTable) {
                    window.connectorsManagementTable.replaceData();
                }
                showToast('Connector enabled successfully', 'success');
            } else {
                throw new Error('Failed to enable connector');
            }
        })
        .catch(error => {
            console.error('Error enabling connector:', error);
            showToast('Error enabling connector', 'error');
        });
};

window.disableConnector = function (id) {
    showConfirmModal({
        title: 'Disable Connector',
        message: 'Are you sure you want to disable this connector?',
        confirmText: 'Disable',
        cancelText: 'Cancel',
        onConfirm: function () {
            fetch(`/features/connectors/api/${id}/disable`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
                .then(response => {
                    if (response.ok) {
                        // Refresh the table
                        if (window.connectorsManagementTable) {
                            window.connectorsManagementTable.replaceData();
                        }
                        showToast('Connector disabled successfully', 'success');
                    } else {
                        throw new Error('Failed to disable connector');
                    }
                })
                .catch(error => {
                    console.error('Error disabling connector:', error);
                    showToast('Error disabling connector', 'error');
                });
        }
    });
};

window.syncConnector = function (id) {
    showToast('Sync functionality will be implemented in a future update', 'info');
    // TODO: Implement sync functionality
    // This would trigger a background job to sync the connector
};

window.testConnectorConnection = function (id) {
    // Show loading toast
    showToast('Testing connection...', 'info');

    fetch(`/features/connectors/${id}/test-connection`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showToast('Connection test successful!', 'success');

                // Optionally show more details in a modal or expanded toast
                if (result.metadata && Object.keys(result.metadata).length > 0) {
                    console.log('Connection test metadata:', result.metadata);
                }
            } else {
                showToast(`Connection test failed: ${result.error || 'Unknown error'}`, 'danger');
                console.error('Connection test details:', result);
            }
        })
        .catch(error => {
            console.error('Error testing connection:', error);
            showToast('Error testing connection', 'danger');
        });
};

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("connectors-table");

    if (tableElement && !window.connectorsTableInitialized) {
        window.connectorsTableInitialized = true;
        initializeConnectorsManagementTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'connectors-table');
        }, 100);
    }
