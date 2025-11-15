(function () {
  const TABLE_ID = "tenant-benchmarks-table";
  let initialized = false;
  let successListenerAttached = false;

  function getIsGlobalAdmin() {
    const area = document.getElementById("tenant-benchmarks-area");
    return area && area.dataset.globalAdmin === "true";
  }

  function attachSuccessListener() {
    if (successListenerAttached) return;
    document.body.addEventListener("showSuccess", function () {
      if (typeof showToast === "function") {
        showToast("Operation completed successfully!", "success", 2200);
      }
    });
    successListenerAttached = true;
  }

  // Modal close is handled globally by table-base.js

  function bindTableEvents(table) {
    document.body.addEventListener("refreshTenantBenchmarks", function () {
      table.replaceData();
    });

    bindRowActionHandlers(`#${TABLE_ID}`, {
      onEdit: "openTenantBenchmarkEdit",
      onDelete: function (id) {
        deleteTabulatorRow(
          `/msp/cspm/tenant-benchmarks/api/${id}`,
          `#${TABLE_ID}`,
          {
            title: "Remove Benchmark Assignment",
            message: "Deactivate or delete this benchmark assignment? Existing scans remain intact.",
            confirmText: "Remove Assignment"
          }
        );
      }
    });
  }

  function buildColumns(isGlobalAdmin) {
    const columns = [
      {
        title: "Assignment",
        field: "display_name",
        minWidth: 220,
        headerFilter: "input",
        formatter: function (cell) {
          const value = cell.getValue() || "<span class='text-muted'>Unnamed Assignment</span>";
          const row = cell.getRow().getData();
          const tech = row.tech_type || (row.benchmark && row.benchmark.tech_type) || "";
          const benchmarkName = (row.benchmark && row.benchmark.display_name) || "";
          return `
            <div class="d-flex flex-column gap-1">
              <span class="fw-semibold">${value}</span>
              ${benchmarkName ? `<small class="text-muted">${benchmarkName}</small>` : ""}
              ${tech ? `<span class="app-badge app-badge-info align-self-start">${tech}</span>` : ""}
            </div>
          `;
        }
      },
      {
        title: "Status",
        field: "status",
        width: 120,
        headerFilter: "list",
        headerFilterParams: {
          values: {
            "": "All",
            "active": "Active",
            "inactive": "Inactive"
          }
        },
        formatter: function (cell) {
          const value = (cell.getValue() || "").toLowerCase();
          const badgeMap = {
            active: "success",
            inactive: "neutral"
          };
          const badge = badgeMap[value] || "neutral";
          const label = value ? value.charAt(0).toUpperCase() + value.slice(1) : "Unknown";
          return `<span class="app-badge app-badge-${badge}">${label}</span>`;
        }
      },
      {
        title: "Benchmark Key",
        field: "benchmark.benchmark_key",
        headerFilter: "input",
        formatter: function (cell) {
          const value = cell.getValue();
          return value ? `<code class="small">${value}</code>` : "<span class='text-muted'>-</span>";
        }
      },
      {
        title: "Config",
        field: "config",
        minWidth: 160,
        mutator: function (value) {
          if (!value || typeof value !== "object") {
            return { count: 0, keys: [] };
          }
          const keys = Object.keys(value);
          return { count: keys.length, keys };
        },
        formatter: function (cell) {
          const data = cell.getValue();
          if (!data || data.count === 0) {
            return "<span class='text-muted'>No overrides</span>";
          }
          return `
            <div class="d-flex flex-column">
              <span class="fw-semibold">${data.count} setting${data.count > 1 ? "s" : ""}</span>
              <small class="text-muted text-truncate">${data.keys.join(", ")}</small>
            </div>
          `;
        }
      },
      {
        title: "Updated",
        field: "updated_at",
        width: 170,
        formatter: formatDate,
        headerFilter: false
      },
      {
        title: "Actions",
        field: "id",
        width: 120,
        hozAlign: "left",
        headerSort: false,
        formatter: function (cell) {
          const id = cell.getValue();
          return `
            <div class="row-actions gap-2" data-id="${id}">
              <i class="ti ti-edit row-action-icon edit-btn" title="Edit Assignment"></i>
              <i class="ti ti-trash row-action-icon delete-btn text-danger" title="Remove Assignment"></i>
            </div>
          `;
        }
      }
    ];

    if (isGlobalAdmin) {
      columns.splice(1, 0, {
        title: "Tenant",
        field: "tenant_id",
        width: 160,
        headerFilter: "input",
        formatter: function (cell) {
          const value = cell.getValue();
          return value ? `<code class="small">${value}</code>` : "<span class='text-muted'>-</span>";
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

    const table = new Tabulator(`#${TABLE_ID}`, {
      ...advancedTableConfig,
      ajaxURL: "/msp/cspm/tenant-benchmarks/api",
      ajaxResponse: standardAjaxResponse,
      placeholder: "No benchmark assignments yet. Click 'Add' to enable a benchmark for this tenant.",
      columns: buildColumns(isGlobalAdmin),
      selectableRows: false,
      rowHeader: null
    });

    table.on("ajaxError", function (_url, _params, response) {
      console.error("Tenant benchmarks table load failed", response?.status, response);
    });

    window.tenantBenchmarksTable = table;
    window.appTables[TABLE_ID] = table;
    initialized = true;

    initializeQuickSearch(
      "tenant-benchmarks-quick-search",
      "tenant-benchmarks-clear-search",
      TABLE_ID
    );

    bindTableEvents(table);
    attachSuccessListener();

    window.exportTable = function (format) {
      return exportTabulatorTable(TABLE_ID, format, "tenant-benchmarks");
    };
  }

  document.addEventListener("DOMContentLoaded", initializeTable);

  document.body.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target && event.detail.target.id === "tenant-benchmarks-area") {
      initialized = false;
      setTimeout(initializeTable, 0);
    }
  });

  window.openTenantBenchmarkEdit = function (id) {
    htmx.ajax("GET", `/msp/cspm/partials/tenant-benchmark-form?assignment_id=${id}`, {
      target: "#modal-body",
      swap: "innerHTML"
    }).then(() => {
      const modal = new bootstrap.Modal(document.getElementById("modal"));
      modal.show();
    });
  };
})();
