/**
 * Tabulator table for groups (management + link to feed view).
 */

window.initializeGroupsTable = function initializeGroupsTable() {
  if (!window.appTables) {
    window.appTables = {};
  }

  const table = new Tabulator("#groups-table", {
    ...advancedTableConfig,
    ajaxURL: "/features/community/groups/api",
    ajaxResponse: standardAjaxResponse,
    columns: [
      { title: "Name", field: "name", headerFilter: "input", minWidth: 160 },
      { title: "Owner", field: "owner_id", width: 140 },
      { title: "Description", field: "description", formatter: formatDescription, minWidth: 220 },
      {
        title: "View",
        field: "view",
        width: 80,
        headerSort: false,
        formatter(cell) {
          const rowData = cell.getRow().getData();
          return `<a href="/features/community/groups/${rowData.id}/view" class="btn btn-link p-0">View</a>`;
        },
      },
      {
        title: "Actions",
        field: "actions",
        width: 140,
        headerSort: false,
        formatter(cell) {
          const rowData = cell.getRow().getData();
      return createRowCrudButtons(rowData, {
        onEdit: "editGroup",
        onDelete: "deleteGroup",
      });
    },
      },
    ],
  });

  window.appTables["groups-table"] = table;
  window.groupsTable = table;

  bindRowActionHandlers("#groups-table", {
    onEdit: "editGroup",
    onDelete: "deleteGroup",
  });

  return table;
};

window.editGroup = function editGroup(id) {
  const url = `/features/community/groups/partials/form?group_id=${id}`;
  editTabulatorRow(url);
};

window.deleteGroup = function deleteGroup(id) {
  deleteTabulatorRow(`/features/community/groups/api/${id}`, "#groups-table", {
    title: "Delete Group",
    message: "Are you sure you want to delete this group?",
    confirmText: "Delete Group",
  });
};

window.editGroupPost = function editGroupPost(id) {
  const groupId = window.groupPostsTable?.group_id;
  if (!groupId) {
    if (typeof window.showToast === "function") {
      window.showToast("Please select a group before editing posts.", "warning");
    }
    return;
  }
  const url = `/features/community/groups/${groupId}/posts/partials/form?post_id=${id}`;
  editTabulatorRow(url);
};

window.deleteGroupPost = function deleteGroupPost(id) {
  deleteTabulatorRow(`/features/community/groups/api/posts/${id}`, "#group-posts-table", {
    title: "Delete Post",
    message: "Are you sure you want to delete this post?",
    confirmText: "Delete Post",
  });
};

document.addEventListener("DOMContentLoaded", () => {
  const groupTableEl = document.getElementById("groups-table");
  if (groupTableEl && !window.groupsTableInitialized) {
    window.groupsTableInitialized = true;
    initializeGroupsTable();
    setTimeout(() => {
      initializeQuickSearch("table-quick-search", "clear-search-btn", "groups-table");
    }, 100);
  }
});

document.body.addEventListener("refreshTable", () => {
  if (window.groupsTable) {
    window.groupsTable.replaceData();
  }
});
