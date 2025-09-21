window.initializeTenantManagementTable = function () {
  if (!window.appTables) {
    window.appTables = {};
  }

  const table = new Tabulator("#tenant-table", {
    ...advancedTableConfig,
    ajaxURL: "/features/administration/tenants/api",
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
        title: "Status",
        field: "status",
        editor: "list",
        editorParams: {
          values: {
            "active": "Active",
            "inactive": "Inactive",
            "suspended": "Suspended",
            "pending": "Pending"
          }
        },
        headerFilter: "list",
        headerFilterParams: {
          values: {
            "": "All Statuses",
            "active": "Active",
            "inactive": "Inactive",
            "suspended": "Suspended",
            "pending": "Pending"
          }
        },
        sorter: "string",
        formatter: formatStatusBadge
      },
      {
        title: "Tier",
        field: "tier",
        editor: "list",
        editorParams: {
          values: {
            "free": "Free",
            "basic": "Basic",
            "professional": "Professional",
            "enterprise": "Enterprise"
          }
        },
        headerFilter: "list",
        headerFilterParams: {
          values: {
            "": "All Tiers",
            "free": "Free",
            "basic": "Basic",
            "professional": "Professional",
            "enterprise": "Enterprise"
          }
        },
        sorter: "string"
      },
      {
        title: "Users",
        field: "user_count",
        formatter: function (cell, formatterParams, onRendered) {
          const rowData = cell.getRow().getData();
          const userCount = cell.getValue() || 0;
          const maxUsers = rowData.max_users || 0;
          const percentage = maxUsers > 0 ? (userCount / maxUsers) * 100 : 0;

          let colorClass = "text-success";
          if (percentage > 80) colorClass = "text-danger";
          else if (percentage > 60) colorClass = "text-warning";

          return `<span class="${colorClass}">${userCount}/${maxUsers}</span>`;
        },
        sorter: "number"
      },
      {
        title: "Contact",
        field: "contact_email",
        headerFilter: "input",
        headerFilterPlaceholder: "Filter contacts...",
        sorter: "string",
        width: 180
      },
      {
        title: "Contact Name",
        field: "contact_name",
        headerFilter: "input",
        headerFilterPlaceholder: "Filter names...",
        sorter: "string"
      },
      {
        title: "Created",
        field: "created_at",
        formatter: function (cell) {
          if (!cell.getValue()) return "";
          const date = new Date(cell.getValue());
          return date.toLocaleDateString();
        },
        sorter: "date"
      },
      {
        title: "Actions",
        field: "actions",
        formatter: function (cell, formatterParams, onRendered) {
          const rowData = cell.getRow().getData();
          return createRowCrudButtons(rowData, {
            onEdit: "editTenantItem",
            onDelete: "deleteTenantItem",
            additionalButtons: [
              {
                text: "Users",
                class: "btn-outline-info btn-sm",
                onclick: `viewTenantUsers('${rowData.id}')`
              }
            ]
          });
        },
        headerSort: false,
        width: 150
      }
    ]
  });

  // Bulk Edit Selected
  addBulkEditHandler(table, '/features/administration/tenants');

  // Bulk Delete Selected
  addBulkDeleteHandler(table, '/features/administration/tenants', 'Tenant');

  // Row action handlers for both edit and delete
  bindRowActionHandlers("#tenant-table", {
    onEdit: "editTenantItem",
    onDelete: "deleteTenantItem"
  });

  // Store in global registry
  window.tenantManagementTable = table;
  window.appTables["tenant-table"] = table;

  // Add cellEdited event listener (this approach works more reliably)
  addCellEditedHandler(table, '/features/administration/tenants', 'Tenant');

  return table;
};

// Export table function
window.exportTable = function (format) {
  return exportTabulatorTable('tenant-table', format, 'tenants');
};

window.editTenantItem = function (id) {
  editTabulatorRow(`/features/administration/tenants/${id}/edit`);
};

window.deleteTenantItem = function (id) {
  deleteTabulatorRow(`/features/administration/tenants/${id}/delete`, "#tenant-table", {
    title: 'Delete Tenant',
    message: 'Are you sure you want to delete this tenant? This action cannot be undone and will fail if the tenant has users.',
    confirmText: 'Delete Tenant',
    cancelText: 'Cancel'
  });
};

window.viewTenantUsers = function (id) {
  htmx.ajax('GET', `/features/administration/tenants/${id}/users`, { target: "#modal-body", swap: "innerHTML" });
};

document.addEventListener("DOMContentLoaded", () => {
  const tableElement = document.getElementById("tenant-table");
  if (tableElement && !window.tenantTableInitialized) {
    window.tenantTableInitialized = true;
    initializeTenantManagementTable();
  }
});
