/**
 * Poll management tables and chart rendering.
 */

let pollResultChart = null;

function loadPollSummary(pollId) {
  fetch(`/features/community/polls/api/${pollId}/summary`)
    .then((resp) => resp.json())
    .then((payload) => {
      const widget = document.getElementById("poll-results-widget");
      if (!widget) return;
      const items = (payload.data || []).map((item) => ({
        name: item.label,
        value: item.votes,
      }));
      widget.setAttribute("data-type", "bar");
      widget.setAttribute("data-title", "Poll Results");
      widget.chartData = { items };
      if (typeof widget.loadData === "function") {
        widget.loadData();
      }
    })
    .catch((error) => console.error("Failed to load poll summary", error));
}

window.initializePollsTable = function initializePollsTable() {
  if (!window.appTables) {
    window.appTables = {};
  }

  const table = new Tabulator("#polls-table", {
    ...advancedTableConfig,
    rowHeader: false,
    selectable: false,
    ajaxURL: "/features/community/polls/api",
    ajaxResponse: standardAjaxResponse,
    columns: [
      { title: "Question", field: "question", headerFilter: "input", minWidth: 220 },
      { title: "Status", field: "status", width: 120, headerFilter: "list", headerFilterParams: { values: { "": "All", "draft": "Draft", "active": "Active", "closed": "Closed" } } },
      { title: "Expires", field: "expires_at", formatter: formatTimestamp, width: 160 },
      {
        title: "Actions",
        field: "actions",
        width: 140,
        headerSort: false,
        formatter(cell) {
          const rowData = cell.getRow().getData();
          return createRowCrudButtons(rowData, {
            onEdit: "editPoll",
            onDelete: "deletePoll",
          });
        },
      },
    ],
  });

  table.on("rowClick", (event, row) => {
    const data = row.getData();
    loadPollSummary(data.id);
  });

  window.pollsTable = table;
  window.appTables["polls-table"] = table;
  bindRowActionHandlers("#polls-table", {
    onEdit: "editPoll",
    onDelete: "deletePoll",
  });
  return table;
};

window.editPoll = function editPoll(id) {
  editTabulatorRow(`/features/community/polls/partials/form?poll_id=${id}`);
};

window.deletePoll = function deletePoll(id) {
  deleteTabulatorRow(`/features/community/polls/api/${id}`, "#polls-table", {
    title: "Delete Poll",
    message: "Are you sure you want to delete this poll?",
    confirmText: "Delete Poll",
  });
};

document.addEventListener("DOMContentLoaded", () => {
  const tableElement = document.getElementById("polls-table");
  if (tableElement && !window.pollsTableInitialized) {
    window.pollsTableInitialized = true;
    initializePollsTable();
  }
});

document.body.addEventListener("refreshTable", () => {
  if (window.pollsTable) {
    window.pollsTable.replaceData();
  }
});
