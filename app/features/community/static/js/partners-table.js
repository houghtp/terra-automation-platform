/**
 * Community Partners Table
 * Tabulator configuration following project standards.
 */

function formatPartnerName(cell) {
  const data = cell.getRow().getData();
  const name = cell.getValue() || "Unknown Partner";
  const description = data.description
    ? `<div class="text-secondary small mt-1">${data.description}</div>`
    : "";
  const logo = data.logo_url
    ? `<span class="avatar avatar-sm" style="background-image: url('${data.logo_url}');"></span>`
    : '<span class="avatar avatar-sm bg-secondary-lt text-uppercase fw-medium">' +
      (name ? name.charAt(0) : "P") +
      "</span>";

  return `<div class="d-flex align-items-start gap-2">
            ${logo}
            <div>
              <div class="fw-semibold">${name}</div>
              ${description}
            </div>
          </div>`;
}

function formatPartnerCategory(cell) {
  const category = cell.getValue();
  if (!category) {
    return "<span class='text-muted'>—</span>";
  }
  return `<span class="app-badge app-badge-teal">${category}</span>`;
}

function formatPartnerWebsite(cell) {
  const url = cell.getValue();
  if (!url) {
    return "<span class='text-muted'>—</span>";
  }
  const safeUrl = url.replace(/"/g, "&quot;");
  return `<a href="${safeUrl}" target="_blank" rel="noopener">${url}</a>`;
}

window.initializePartnersTable = function initializePartnersTable() {
  if (!window.appTables) {
    window.appTables = {};
  }

  const columns = [
    {
      title: "Partner",
      field: "name",
      headerFilter: "input",
      minWidth: 240,
      formatter: formatPartnerName,
    },
    {
      title: "Category",
      field: "category",
      headerFilter: "input",
      minWidth: 140,
      formatter: formatPartnerCategory,
    },
    {
      title: "Offer",
      field: "offer",
      headerFilter: "input",
      minWidth: 220,
      formatter: (cell) => cell.getValue() || "<span class='text-muted'>—</span>",
    },
    {
      title: "Website",
      field: "website",
      headerFilter: "input",
      minWidth: 220,
      formatter: formatPartnerWebsite,
    },
    {
      title: "Actions",
      field: "actions",
      hozAlign: "center",
      headerSort: false,
      width: 140,
      formatter(cell) {
        const rowData = cell.getRow().getData();
        return createRowCrudButtons(rowData, {
          onEdit: "editPartner",
          onDelete: "deletePartner",
        });
      },
    },
  ];

  const table = new Tabulator("#partners-table", {
    ...advancedTableConfig,
    ajaxURL: "/features/community/partners/api",
    ajaxResponse: standardAjaxResponse,
    columns,
    selectable: true,
  });

  window.appTables["partners-table"] = table;
  window.partnersTable = table;

  table.searchableFields = ["name", "category", "offer", "website", "description"];

  table.on("dataProcessed", () => {
    const total = table.getDataCount();
    const badge = document.getElementById("partner-total-badge");
    if (badge) {
      badge.textContent = `${total} total`;
    }
  });

  bindRowActionHandlers("#partners-table", {
    onEdit: "editPartner",
    onDelete: "deletePartner",
  });

  return table;
};

window.refreshPartnersTable = function refreshPartnersTable() {
  if (window.partnersTable) {
    window.partnersTable.replaceData();
  }
};

window.deletePartner = function deletePartner(id) {
  deleteTabulatorRow(`/features/community/partners/${id}/delete`, "#partners-table", {
    title: "Delete Partner",
    message: "Are you sure you want to delete this partner?",
    confirmText: "Delete Partner",
  });
};

window.editPartner = function editPartner(id) {
  editTabulatorRow(`/features/community/partners/partials/form?partner_id=${id}`);
};

document.addEventListener("DOMContentLoaded", () => {
  const tableElement = document.getElementById("partners-table");
  if (tableElement && !window.partnersTableInitialized) {
    window.partnersTableInitialized = true;
    initializePartnersTable();

    setTimeout(() => {
      initializeQuickSearch("table-quick-search", "clear-search-btn", "partners-table");
    }, 100);
  }
});

document.body.addEventListener("refreshTable", () => {
  refreshPartnersTable();
});

// Modal close is handled globally by table-base.js
