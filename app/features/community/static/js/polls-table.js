/**
 * Poll management tables and chart rendering.
 */

let pollResultChart = null;

function renderPollChart(data) {
  const element = document.getElementById("poll-results");
  if (!element) return;

  if (!pollResultChart) {
    pollResultChart = echarts.init(element);
  }

  const labels = data.map((item) => item.label);
  const values = data.map((item) => item.votes);

  pollResultChart.setOption({
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        data: labels.map((label, idx) => ({ value: values[idx], name: label })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: "rgba(0,0,0,0.4)",
          },
        },
      },
    ],
  });
}

function loadPollSummary(pollId) {
  fetch(`/features/community/polls/api/${pollId}/summary`)
    .then((resp) => resp.json())
    .then((payload) => {
      renderPollChart(payload.data || []);
      const refreshBtn = document.getElementById("refresh-poll-results");
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.onclick = () => loadPollSummary(pollId);
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
  return table;
};

window.editPoll = function editPoll(id) {
  htmx.ajax("GET", `/features/community/polls/partials/form?poll_id=${id}`, "#modal-body");
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
