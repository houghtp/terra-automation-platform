let auditStats = {};

document.body.addEventListener("htmx:afterSwap", (e) => {
  if (e.target.id === "audit-area") {
    setTimeout(() => {
      window.initializeAuditLogsTable?.();
    }, 0);
  }
});

// Handle modal close and table refresh
document.body.addEventListener("htmx:afterRequest", (e) => {
  if (e.target.closest('.modal')) {
    // Close the modal with proper focus restoration
    if (window.closeModal) {
      window.closeModal();
    }

    // Refresh the table after a short delay
    setTimeout(() => {
      if (window.refreshTable) {
        window.refreshTable('audit-table');
      }
    }, 100);
  }
});

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

    // Note: Category filter is now static in the template - no dynamic population needed

  } catch (error) {
    console.error('Failed to load security alert and filters:', error);
  }
}

// Initialize Audit Logs table
function initializeAuditLogsTable() {
  if (typeof Tabulator === 'undefined') {
    console.error('Tabulator not loaded');
    return;
  }

  const table = new Tabulator("#audit-table", {
    ...advancedTableConfig,
    // Audit-specific overrides
    ajaxURL: "/features/administration/audit/api/list",
    pagination: "remote",
    paginationMode: "remote",
    paginationSize: 25,
    paginationSizeSelector: [10, 25, 50, 100],
    responsiveLayout: "hide",
    selectable: true,
    selectableRangeMode: "click",
    selectableRows: true,  // Enable row selection
    rowHeader: false,  // Disable the base config row header to avoid conflicts
    headerFilterPlaceholder: "Filter...",
    columns: [
      {
        title: "<input type='checkbox' id='select-all'>",
        field: "select",
        formatter: "rowSelection",
        titleFormatter: "rowSelection",
        width: 40,
        headerSort: false,
        cellClick: function (e, cell) {
          cell.getRow().toggleSelect();
        }
      },
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
        headerFilter: "select",
        headerFilterParams: {
          values: ["", "AUTH", "DATA", "ADMIN", "API", "SYSTEM"]
        },
        formatter: formatCategoryBadge
      },
      {
        title: "Severity",
        field: "severity",
        width: 100,
        headerFilter: "select",
        headerFilterParams: {
          values: ["", "INFO", "WARNING", "ERROR", "CRITICAL"]
        },
        formatter: formatSeverityBadge
      },
      {
        title: "User",
        field: "user_email",
        width: 200,
        headerFilter: "input",
        formatter: formatUserEmail
      },
      {
        title: "Description",
        field: "description",
        minWidth: 200,
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
    ],
    ajaxResponse: function (url, params, response) {
      return {
        data: response.items || [],
        last_page: Math.ceil((response.total || 0) / (params.size || 25))
      };
    }
  });

  // Store table reference globally
  window.auditTable = table;

  // Handle select all checkbox
  const selectAllCheckbox = document.getElementById('select-all');
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', function (e) {
      if (e.target.checked) {
        table.selectRow("all");
      } else {
        table.deselectRow("all");
      }
    });
  }

  return table;
}

// Note: Advanced filtering now handled by HTMX form submission

// View audit log details
function viewAuditLog(logId) {
  // Use HTMX to load audit log details
  htmx.ajax('GET', `/features/administration/audit/partials/log_details?log_id=${logId}`, {
    target: '#modal-body',
    swap: 'innerHTML'
  }).then(() => {
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('modal'));
    modal.show();
  });
}

// Refresh table function using centralized utility
window.refreshTable = function (tableId) {
  refreshTable(tableId);
};

// Refresh audit table function
window.refreshAuditTable = function () {
  refreshTable('audit-table');
  showToast('Audit logs refreshed', 'success');
  // Refresh security alert and filters (web components handle their own refresh)
  loadSecurityAlertAndFilters();
};

// Export table function using centralized utility
window.exportTable = function (format) {
  return exportTabulatorTable('audit-table', format, 'audit_logs');
};

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

// Toast notification function
function showToast(message, type = 'info') {
  // Simple console log for now - can be enhanced with actual toast library
  console.log(`${type.toUpperCase()}: ${message}`);
};

// Initialize everything on page load
document.addEventListener('DOMContentLoaded', function () {
  // Load dashboard data (stats cards will load automatically via data-url)
  loadSecurityAlertAndFilters();

  // Initialize table
  setTimeout(() => {
    window.initializeAuditLogsTable();
  }, 100);
});
