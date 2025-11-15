/**
 * Community Members Table
 * Standardized Tabulator implementation aligned with platform patterns.
 */

function formatMemberName(cell) {
  const data = cell.getRow().getData();
  const name = cell.getValue() || "Unknown";
  const aum = data.aum_range ? `<div class="text-secondary small">AUM: ${data.aum_range}</div>` : "";
  return `<div class="fw-semibold">${name}</div>${aum}`;
}

function formatMemberEmail(cell) {
  const email = cell.getValue();
  return email ? `<a href="mailto:${email}">${email}</a>` : "<span class='text-muted'>—</span>";
}

window.initializeMembersTable = function initializeMembersTable() {
  if (!window.appTables) {
    window.appTables = {};
  }

  const columns = [
    {
      title: "Name",
      field: "name",
      headerFilter: "input",
      minWidth: 200,
      formatter: formatMemberName,
    },
    {
      title: "Email",
      field: "email",
      headerFilter: "input",
      minWidth: 220,
      formatter: formatMemberEmail,
    },
    {
      title: "Firm",
      field: "firm",
      headerFilter: "input",
      minWidth: 160,
      formatter: (cell) => cell.getValue() || "<span class='text-muted'>—</span>",
    },
    {
      title: "Location",
      field: "location",
      headerFilter: "input",
      minWidth: 140,
      formatter: (cell) => cell.getValue() || "<span class='text-muted'>—</span>",
    },
    {
      title: "Specialties",
      field: "specialties",
      headerFilter: "input",
      headerFilterFunc: arraySearchFilter,
      formatter: (cell) => formatBadges(cell, "app-badge app-badge-info me-1", "—"),
      sorter: arrayLengthSorter,
      minWidth: 220,
    },
    {
      title: "Tags",
      field: "tags",
      headerFilter: "input",
      headerFilterFunc: arraySearchFilter,
      formatter: (cell) => formatBadges(cell, "app-badge app-badge-purple me-1", "—"),
      sorter: arrayLengthSorter,
      minWidth: 160,
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
          onEdit: "editMember",
          onDelete: "deleteMember",
        });
      },
    },
  ];

  const table = new Tabulator("#members-table", {
    ...advancedTableConfig,
    ajaxURL: "/features/community/members/api/list",
    columns,
    dataTree: false,
    selectable: true,
  });

  window.appTables["members-table"] = table;
  window.membersTable = table;
  table.searchableFields = ["name", "email", "firm", "location", "aum_range", "specialties", "tags", "bio"];

  // Update total badge when data loaded
  table.on("dataProcessed", () => {
    const total = table.getDataCount();
    const badge = document.getElementById("member-total-badge");
    if (badge) {
      badge.textContent = `${total} total`;
    }
  });

  bindRowActionHandlers("#members-table", {
    onEdit: "editMember",
    onDelete: "deleteMember",
  });

  return table;
};

window.refreshMembersTable = function refreshMembersTable() {
  if (window.membersTable) {
    window.membersTable.replaceData();
  }
};

window.deleteMember = function deleteMember(id) {
  deleteTabulatorRow(`/features/community/members/${id}/delete`, "#members-table", {
    title: "Delete Member",
    message: "Are you sure you want to remove this member?",
    confirmText: "Delete Member",
  });
};

window.editMember = function editMember(id) {
  editTabulatorRow(`/features/community/members/partials/form?member_id=${id}`);
};

document.addEventListener("DOMContentLoaded", () => {
  const tableElement = document.getElementById("members-table");
  if (tableElement && !window.membersTableInitialized) {
    window.membersTableInitialized = true;
    initializeMembersTable();

    setTimeout(() => {
      initializeQuickSearch("table-quick-search", "clear-search-btn", "members-table");
    }, 100);
  }
});

document.body.addEventListener("refreshTable", refreshMembersTable);

// Modal close is handled globally by table-base.js
