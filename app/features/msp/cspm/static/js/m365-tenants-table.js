(function () {
  const TABLE_ID = "m365-tenants-table";
  let initialized = false;
  let successListenerAttached = false;

  function attachSuccessListener() {
    if (successListenerAttached) return;
    document.body.addEventListener("showSuccess", function () {
      if (typeof showToast === "function") {
        showToast("Operation completed successfully!", "success", 2200);
      }
    });
    successListenerAttached = true;
  }

  function getIsGlobalAdmin() {
    const area = document.getElementById("m365-tenant-area");
    return area && area.dataset.globalAdmin === "true";
  }

  // Modal close is handled globally by table-base.js

  function bindTableEvents(table) {
    document.body.addEventListener("refreshTable", function () {
      table.replaceData();
    });

    bindRowActionHandlers(`#${TABLE_ID}`, {
      onEdit: "openM365TenantEdit",
      onDelete: function (id) {
        deleteTabulatorRow(
          `/msp/cspm/m365-tenants/${id}`,
          `#${TABLE_ID}`,
          {
            title: "Delete M365 Tenant",
            message: "Are you sure you want to delete this Microsoft 365 tenant configuration?",
            confirmText: "Delete Tenant"
          }
        );
      }
    });

    const tableElement = document.getElementById(TABLE_ID);
    if (tableElement) {
      tableElement.addEventListener("click", function (event) {
        const testButton = event.target.closest(".test-tenant-btn");
        if (!testButton) return;
        const container = testButton.closest(".row-actions");
        if (!container || !container.dataset.id) return;
        event.preventDefault();
        testM365TenantConnection(container.dataset.id);
      });
    }
  }

  function buildColumns(isGlobalAdmin) {
    const columns = [
      {
        title: "Assignment",
        field: "m365_tenant_name",
        minWidth: 220,
        headerFilter: "input",
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const tenantName = cell.getValue() || row.m365_tenant_id || "Unassigned";
          const assignmentName = row.tenant_benchmark_display_name || tenantName;
          const benchmarkName = row.benchmark_display_name || "";
          const benchmarkKey = row.benchmark_key || "";
          const description = cell.getRow().getData().description;
          const status = (row.tenant_benchmark_status || "").toLowerCase();
          const statusBadge = status
            ? `<span class="app-badge app-badge-${status === 'active' ? 'success' : 'neutral'}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>`
            : "";
          const tenantId = row.m365_tenant_id
            ? `<code class="small">${row.m365_tenant_id}</code>`
            : "<span class='text-muted'>Tenant ID not set</span>";
          const benchmarkMeta = benchmarkName
            ? `<small class="text-muted">Benchmark: ${benchmarkName}${benchmarkKey ? ` (${benchmarkKey})` : ""}</small>`
            : "";
          return `
            <div class="d-flex flex-column">
              <strong>${assignmentName}</strong>
              <small class="text-muted">${tenantName} &middot; ${tenantId}</small>
              ${benchmarkMeta}
              ${description ? `<small class="text-muted">${description}</small>` : ""}
              ${statusBadge}
            </div>
          `;
        }
      },
      {
        title: "M365 Tenant ID",
        field: "m365_tenant_id",
        headerFilter: "input",
        formatter: function (cell) {
          const value = cell.getValue();
          return value ? `<code class="small">${value}</code>` : "<span class='text-muted'>-</span>";
        }
      },
      {
        title: "Primary Domain",
        field: "m365_domain",
        headerFilter: "input",
        formatter: function (cell) {
          return cell.getValue() || "<span class='text-muted'>-</span>";
        }
      },
      {
        title: "Status",
        field: "status",
        width: 110,
        headerFilter: "list",
        headerFilterParams: {
          values: {
            "": "All",
            "active": "Active",
            "inactive": "Inactive",
            "error": "Error"
          }
        },
        formatter: function (cell) {
          const value = (cell.getValue() || "").toLowerCase();
          const badgeMap = {
            active: "success",
            inactive: "neutral",
            error: "danger"
          };
          const badge = badgeMap[value] || "neutral";
          const label = value ? value.charAt(0).toUpperCase() + value.slice(1) : "Unknown";
          return `<span class="app-badge app-badge-${badge}">${label}</span>`;
        }
      },
      {
        title: "Last Test",
        field: "last_test_status",
        width: 160,
        headerFilter: "list",
        headerFilterParams: {
          values: {
            "": "All",
            "success": "Success",
            "failed": "Failed",
            "pending": "Pending"
          }
        },
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const status = (row.last_test_status || "not_tested").toLowerCase();
          const testedAt = row.last_test_at ? new Date(row.last_test_at) : null;

          if (!row.last_test_at) {
            return '<span class="text-muted">Not tested</span>';
          }

          const statusMap = {
            success: { icon: "ti ti-check", color: "text-success", label: "Success" },
            failed: { icon: "ti ti-alert-triangle", color: "text-danger", label: "Failed" },
            pending: { icon: "ti ti-clock", color: "text-warning", label: "Pending" }
          };

          const meta = statusMap[status] || statusMap.failed;
          return `
            <div class="d-flex flex-column gap-1">
              <span class="${meta.color}">
                <i class="${meta.icon} me-1"></i>${meta.label}
              </span>
              <small class="text-muted">${testedAt ? testedAt.toLocaleString() : ""}</small>
            </div>
          `;
        }
      },
      {
        title: "Actions",
        field: "id",
        width: 160,
        hozAlign: "left",
        headerSort: false,
        formatter: function (cell) {
          const id = cell.getValue();
          return `
            <div class="row-actions gap-2" data-id="${id}">
              <button type="button"
                      class="btn btn-sm btn-ghost-secondary test-tenant-btn"
                      title="Test Connection">
                <i class="ti ti-plug"></i>
              </button>
              <i class="ti ti-edit row-action-icon edit-btn" title="Edit"></i>
              <i class="ti ti-trash row-action-icon delete-btn" title="Delete"></i>
            </div>
          `;
        }
      }
    ];

    if (isGlobalAdmin) {
      columns.splice(1, 0, {
        title: "Tenant ID",
        field: "tenant_id",
        headerFilter: "input",
        width: 150,
        formatter: function (cell) {
          return `<code class="small">${cell.getValue() || '-'}</code>`;
        }
      });
    }

    return columns;
  }

  function initializeTable() {
    const container = document.getElementById(TABLE_ID);
    if (!container || initialized) {
      return;
    }

    const isGlobalAdmin = getIsGlobalAdmin();
    window.isGlobalAdmin = isGlobalAdmin;

    const table = new Tabulator(`#${TABLE_ID}`, {
      ...advancedTableConfig,
      ajaxURL: "/msp/cspm/m365-tenants/list",
      ajaxResponse: standardAjaxResponse,
      placeholder: "No M365 tenants found. Click 'Add' to configure one.",
      columns: buildColumns(isGlobalAdmin),
      selectableRows: false,
      rowHeader: null
    });

    window.m365TenantsTable = table;
    window.appTables[TABLE_ID] = table;
    initialized = true;

    initializeQuickSearch(
      "m365-tenants-quick-search",
      "m365-tenants-clear-search",
      TABLE_ID
    );

    bindTableEvents(table);
    attachSuccessListener();

    window.exportTable = function (format) {
      return exportTabulatorTable(TABLE_ID, format, "m365-tenants");
    };
  }

  document.addEventListener("DOMContentLoaded", initializeTable);

  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "m365-tenant-area") {
      initialized = false;
      setTimeout(initializeTable, 0);
    }
  });

  window.openM365TenantEdit = function (id) {
    htmx.ajax("GET", `/msp/cspm/partials/m365-tenant-form?tenant_id=${id}`, {
      target: "#modal-body",
      swap: "innerHTML"
    }).then(() => {
      const modal = new bootstrap.Modal(document.getElementById("modal"));
      modal.show();
    });
  };

  window.testM365TenantConnection = function (tenantId) {
    showToast("Testing Microsoft 365 connection...", "info", 2000);

    fetch(`/msp/cspm/m365-tenants/${tenantId}/test-connection`, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showToast(data.message || "Connection test succeeded.", "success");
        } else {
          showToast(data.message || "Connection test failed.", "error");
        }
        if (window.m365TenantsTable) {
          window.m365TenantsTable.replaceData();
        }
      })
      .catch((error) => {
        console.error("Failed to test connection", error);
        showToast("Connection test failed due to a network error.", "error");
      });
  };

  window.deleteM365Tenant = function (tenantId) {
    deleteTabulatorRow(
      `/msp/cspm/m365-tenants/${tenantId}`,
      `#${TABLE_ID}`,
      {
        title: "Delete M365 Tenant",
        message: "Are you sure you want to delete this Microsoft 365 tenant configuration?",
        confirmText: "Delete Tenant"
      }
    );
  };
})();
