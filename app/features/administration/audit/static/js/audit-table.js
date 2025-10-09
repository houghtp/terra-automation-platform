window.initializeAuditLogsTable = function () {
  // Make sure appTables exists
  if (!window.appTables) {
    window.appTables = {};
  }

  const table = new Tabulator("#audit-table", {
    ...advancedTableConfig,
    ajaxURL: "/features/administration/audit/api/list",
    columns: [
      {
        title: "Timestamp",
        field: "timestamp",
        width: 180,
        formatter: formatTimestamp,
        headerFilter: "input"
      },
      {
        title: "Action",
        field: "action",
        width: 150,
        headerFilter: "input",
        formatter: formatActionBadge
      },
      {
        title: "Category",
        field: "category",
        width: 120,
        headerFilter: "input",
        formatter: formatCategoryBadge
      },
      {
        title: "Severity",
        field: "severity",
        width: 100,
        headerFilter: "input",
        formatter: formatSeverityBadge
      },
      {
        title: "User",
        field: "user_email",
        width: 180,
        headerFilter: "input",
        formatter: formatUserEmail
      },
      {
        title: "User Role",
        field: "user_role",
        width: 100,
        headerFilter: "input",
      },
      {
        title: "Resource Type",
        field: "resource_type",
        width: 120,
        headerFilter: "input"
      },
      {
        title: "Resource ID",
        field: "resource_id",
        width: 120,
        headerFilter: "input"
      },
      {
        title: "Request ID",
        field: "request_id",
        width: 140,
        headerFilter: "input"
      },
      {
        title: "Endpoint",
        field: "endpoint",
        width: 180,
        headerFilter: "input",
        formatter: function (cell) {
          const endpoint = cell.getValue() || '';
          if (endpoint.length > 25) {
            return endpoint.substring(0, 25) + '...';
          }
          return endpoint;
        }
      },
      {
        title: "Method",
        field: "method",
        width: 80,
        headerFilter: "input",
      },
      {
        title: "Description",
        field: "description",
        minWidth: 150,
        headerFilter: "input",
        formatter: formatDescription
      },
      {
        title: "IP Address",
        field: "ip_address",
        width: 130,
        headerFilter: "input"
      },
      {
        title: "Actions",
        field: "actions",
        width: 100,
        headerSort: false,
        formatter: (cell) => formatViewAction(cell, 'viewAuditLog')
      }
    ]
  });

  // Store table reference globally
  window.auditTable = table;
  window.appTables["audit-table"] = table;

  return table;
};

// Export table function
window.exportTable = function (format) {
  return exportTabulatorTable('audit-table', format, 'audit_logs');
};

window.viewAuditLog = function (logId) {
  // Use HTMX to load audit log details
  htmx.ajax('GET', `/features/administration/audit/partials/log_details?log_id=${logId}`, {
    target: '#modal-body',
    swap: 'innerHTML'
  }).then(() => {
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('modal'));
    modal.show();
  });
};

// Handle security alerts and populate filters (stats-card web components handle the rest)
async function loadSecurityAlertAndFilters() {
  try {
    const response = await fetch('/features/administration/audit/api/stats', {
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json'
      }
    });
    const auditStats = await response.json();

    // Handle security alert (this is UI logic not handled by web components)
    if (auditStats.security_events > 0) {
      const alert = document.getElementById('security-alert');
      alert.classList.remove('d-none');
      document.getElementById('security-alert-count').textContent = auditStats.security_events;
    } else {
      const alert = document.getElementById('security-alert');
      alert.classList.add('d-none');
    }

  } catch (error) {
    console.error('Failed to load security alert and filters:', error);
  }
}

// Apply table filters
function applyTableFilters() {
  const table = window.auditTable;
  if (!table) return;

  const filters = [];

  // Category filter
  const category = document.getElementById('filter-category')?.value;
  if (category) {
    filters.push({ field: "category", type: "=", value: category });
  }

  // Severity filter
  const severity = document.getElementById('filter-severity')?.value;
  if (severity) {
    filters.push({ field: "severity", type: "=", value: severity });
  }

  // User filter
  const user = document.getElementById('filter-user')?.value;
  if (user) {
    filters.push({ field: "user_email", type: "like", value: user });
  }

  // Action filter
  const action = document.getElementById('filter-action')?.value;
  if (action) {
    filters.push({ field: "action", type: "like", value: action });
  }

  // Date filters (will be sent as AJAX parameters)
  const dateFrom = document.getElementById('filter-date-from')?.value;
  const dateTo = document.getElementById('filter-date-to')?.value;

  // Update AJAX URL with date parameters
  let ajaxURL = "/features/administration/audit/api/list";
  const params = new URLSearchParams();
  if (dateFrom) params.append('date_from', dateFrom);
  if (dateTo) params.append('date_to', dateTo);
  if (params.toString()) {
    ajaxURL += '?' + params.toString();
  }

  table.setData(ajaxURL);
  table.setFilter(filters);
}

// Clear table filters
function clearTableFilters() {
  const table = window.auditTable;
  if (!table) return;

  // Clear filter form
  document.getElementById('filter-category').value = '';
  document.getElementById('filter-severity').value = '';
  document.getElementById('filter-user').value = '';
  document.getElementById('filter-action').value = '';
  document.getElementById('filter-date-from').value = '';
  document.getElementById('filter-date-to').value = '';

  // Clear table filters
  table.clearFilter();
  table.setData("/features/administration/audit/api/list");
}

// Filter by severity (used by security alert)
function filterBySeverity(severityList) {
  const table = window.auditTable;
  if (!table) return;

  const severities = severityList.split(',');
  const filters = severities.map(severity => ({
    field: "severity",
    type: "=",
    value: severity.trim()
  }));

  table.setFilter(filters);

  // Update form to reflect filter
  if (severities.length === 1) {
    document.getElementById('filter-severity').value = severities[0];
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const tableElement = document.getElementById("audit-table");

  if (tableElement && !window.auditTableInitialized) {
    window.auditTableInitialized = true;

    // Load dashboard data (stats cards will load automatically via data-url)
    loadSecurityAlertAndFilters();

    initializeAuditLogsTable();

    // Initialize quick search after table is ready
    setTimeout(() => {
      initializeQuickSearch('table-quick-search', 'clear-search-btn', 'audit-table');
    }, 100);
  }
});
