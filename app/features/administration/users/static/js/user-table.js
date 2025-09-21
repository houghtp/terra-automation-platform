window.initializeUserManagementTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#user-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/administration/users/api",
        columns: [
            {
                title: "Name",
                field: "name",
                editor: "input",
                headerFilter: "input",
                headerFilterPlaceholder: "Filter names...",
                sorter: "string"
            },
            {
                title: "Email",
                field: "email",
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
                        "active": "Active",
                        "inactive": "Inactive",
                        "pending": "Pending"
                    }
                },
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All Statuses",
                        "active": "Active",
                        "inactive": "Inactive",
                        "pending": "Pending"
                    }
                },
                sorter: "string",
                formatter: formatStatusBadge
            },
            {
                title: "Role",
                field: "role",
                editor: "list",
                editorParams: {
                    values: {
                        "user": "User",
                        "admin": "Admin",
                        "moderator": "Moderator"
                    }
                },
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All Roles",
                        "user": "User",
                        "admin": "Admin",
                        "moderator": "Moderator"
                    }
                },
                sorter: "string",
                formatter: formatStatusBadge
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
                    return createRowCrudButtons(rowData, {
                        onEdit: "editUser",
                        onDelete: "deleteUser"
                    });
                },
                headerSort: false,
                width: 150
            }
        ]
    });

    // Store in global registry-unified.css by mistake
    window.userManagementTable = table;
    window.appTables["user-table"] = table;

    // Add cellEdited event listener (this approach works more reliably)
    addCellEditedHandler(table, '/features/administration/users', 'User');

    // Bulk Edit Selected
    addBulkEditHandler(table, '/features/administration/users');

    // Bulk Delete Selected
    addBulkDeleteHandler(table, '/features/administration/users', 'User');

    // Row action handlers for both edit and delete
    bindRowActionHandlers("#user-table", {
        onEdit: "editUser",
        onDelete: "deleteUser"
    });

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('user-table', format, 'users');
};

window.deleteUser = function (id) {
    deleteTabulatorRow(`/features/administration/users/${id}/delete`, '#user-table', {
        title: 'Delete User',
        message: 'Are you sure you want to delete this user? This action cannot be undone.',
        confirmText: 'Delete User',
        cancelText: 'Cancel'
    });
};

window.editUser = function (id) {
    editTabulatorRow(`/features/administration/users/${id}/edit`);
};


document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("user-table");

    if (tableElement && !window.userTableInitialized) {
        window.userTableInitialized = true;
        initializeUserManagementTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'user-table');
        }, 100);
    }
});

