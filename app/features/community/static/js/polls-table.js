/**
 * Poll management tables and chart rendering.
 */

let selectedPollId = null;

function loadPollSummary(pollId) {
  fetch(`/features/community/polls/api/${pollId}/summary`)
    .then((resp) => resp.json())
    .then((payload) => {
      const widget = document.getElementById("poll-results-widget");
      if (!widget) return;
      const summary = payload.data || [];
      const categories = summary.map((item) => item.label);
      const values = summary.map((item) => item.votes);

      // chart-widget expects categories/values for bar charts
      if (typeof widget.renderChart === "function") {
        widget.renderChart({ categories, values });
      }

      // If no data yet, show a friendly placeholder
      if (!summary.length && typeof widget.showNoData === "function") {
        widget.showNoData();
      }
    })
    .catch((error) => {
      console.error("Failed to load poll summary", error);
      const widget = document.getElementById("poll-results-widget");
      if (widget && typeof widget.showError === "function") {
        widget.showError("Failed to load results");
      }
    });
}

function renderVotePanel(poll) {
  const panel = document.getElementById("poll-vote-panel");
  if (!panel) return;

  if (!poll || !poll.options || poll.options.length === 0) {
    panel.innerHTML = '<div class="text-muted">Select a poll to vote.</div>';
    selectedPollId = null;
    return;
  }

  selectedPollId = poll.id;
  const optionsHtml = poll.options
    .map(
      (opt, idx) => `
        <div class="form-check mb-2">
          <input class="form-check-input" type="radio" name="poll-option" id="poll-opt-${idx}" value="${opt.id}">
          <label class="form-check-label" for="poll-opt-${idx}">${opt.text}</label>
        </div>
      `
    )
    .join("");

  panel.innerHTML = `
    <div class="fw-semibold mb-2">${poll.question}</div>
    <form id="poll-vote-form">
      ${optionsHtml}
      <button type="submit" class="btn btn-primary btn-sm mt-2" disabled>
        <span class="htmx-indicator spinner-border spinner-border-sm me-2" role="status"></span>
        Vote
      </button>
    </form>
  `;

  const form = panel.querySelector("#poll-vote-form");
  const submitBtn = form.querySelector("button[type='submit']");
  form.addEventListener("change", () => {
    const checked = form.querySelector("input[name='poll-option']:checked");
    submitBtn.disabled = !checked;
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const checked = form.querySelector("input[name='poll-option']:checked");
    if (!checked) return;
    submitBtn.disabled = true;
    submitBtn.classList.add("disabled");
    fetch(`/features/community/polls/api/${poll.id}/vote`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      credentials: "same-origin",
      body: JSON.stringify({ poll_id: poll.id, option_id: checked.value }),
    })
      .then((resp) => {
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        if (typeof window.showToast === "function") {
          window.showToast("Vote recorded", "success");
        }
        loadPollSummary(poll.id);
      })
      .catch((error) => {
        console.error("Failed to submit vote", error);
        if (typeof window.showToast === "function") {
          window.showToast("Failed to submit vote.", "error");
        }
      })
      .finally(() => {
        submitBtn.disabled = false;
        submitBtn.classList.remove("disabled");
      });
  });
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
    renderVotePanel(data);
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
