/**
 * Tabulator tables for groups and group posts.
 */

function createPostsTable() {
  return new Tabulator("#group-posts-table", {
    ...advancedTableConfig,
    placeholder: "<div class='p-4 text-center text-muted'>Select a group to view posts.</div>",
    ajaxResponse: standardAjaxResponse,
    columns: [
      { title: "Title", field: "title", headerFilter: "input", minWidth: 160 },
      { title: "Preview", field: "content", formatter: formatDescription, minWidth: 220 },
      { title: "Author", field: "author_id", width: 120 },
      { title: "Created", field: "created_at", formatter: formatTimestamp, width: 160 },
      {
        title: "Actions",
        field: "actions",
        width: 120,
        headerSort: false,
        formatter(cell) {
          const rowData = cell.getRow().getData();
          return createRowCrudButtons(rowData, {
            onEdit: "editGroupPost",
            onDelete: "deleteGroupPost",
          });
        },
      },
    ],
  });
}

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
      { title: "Privacy", field: "privacy", width: 110, headerFilter: "list", headerFilterParams: { values: { "": "All", "private": "Private", "public": "Public" } } },
      { title: "Owner", field: "owner_id", width: 140 },
      { title: "Description", field: "description", formatter: formatDescription, minWidth: 220 },
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

  const postsTable = createPostsTable();
  window.groupPostsTable = postsTable;
  window.appTables["group-posts-table"] = postsTable;

  bindRowActionHandlers("#groups-table", {
    onEdit: "editGroup",
    onDelete: "deleteGroup",
  });

  bindRowActionHandlers("#group-posts-table", {
    onEdit: "editGroupPost",
    onDelete: "deleteGroupPost",
  });

  table.on("rowClick", (e, row) => {
    const group = row.getData();
    loadGroupPosts(group.id);
    enablePostButton(group.id);
  });

  table.on("dataLoading", () => {
    disablePostButton();
    if (window.groupPostsTable) {
      window.groupPostsTable.clearData();
      delete window.groupPostsTable.group_id;
    }
  });

  return table;
};

function enablePostButton(groupId) {
  const button = document.getElementById("group-posts-add-btn");
  if (!button) return;
  button.classList.remove("disabled");
  button.removeAttribute("aria-disabled");
  button.setAttribute("hx-get", `/features/community/groups/${groupId}/posts/partials/form`);
  button.setAttribute("hx-target", "#modal-body");
  button.setAttribute("hx-swap", "innerHTML");
  button.setAttribute("data-bs-toggle", "modal");
  button.setAttribute("data-bs-target", "#modal");
  button.setAttribute("href", "javascript:void(0)");
}

function disablePostButton() {
  const button = document.getElementById("group-posts-add-btn");
  if (!button) return;
  button.classList.add("disabled");
  button.setAttribute("aria-disabled", "true");
  button.removeAttribute("hx-get");
  button.removeAttribute("hx-target");
  button.removeAttribute("hx-swap");
  button.removeAttribute("data-bs-toggle");
  button.removeAttribute("data-bs-target");
}

function loadGroupPosts(groupId) {
  if (!window.groupPostsTable) {
    return;
  }
  window.groupPostsTable.setData(`/features/community/groups/api/${groupId}/posts`);
  window.groupPostsTable.group_id = groupId;
}

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
    disablePostButton();
    initializeGroupsTable();
    setTimeout(() => {
      initializeQuickSearch("table-quick-search", "clear-search-btn", "groups-table");
      initializeQuickSearch("group-posts-quick-search", "group-posts-clear-search", "group-posts-table");
    }, 100);
  }
});

document.body.addEventListener("refreshTable", () => {
  if (window.groupsTable) {
    window.groupsTable.replaceData();
  }
  disablePostButton();
});

document.body.addEventListener("refreshPosts", () => {
  if (window.groupPostsTable && window.groupPostsTable.group_id) {
    loadGroupPosts(window.groupPostsTable.group_id);
  }
});
