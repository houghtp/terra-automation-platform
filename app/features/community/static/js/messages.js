/**
 * Messaging utilities for community hub.
 */

function renderThread(messages) {
  const container = document.getElementById("thread-view");
  if (!container) return;

  if (!messages.length) {
    container.innerHTML = "<div class='p-4 text-muted text-center'>No messages in this conversation yet.</div>";
    return;
  }

  const fragments = messages.map((message) => {
    const alignment = message.sender_id === window.currentMemberId ? "text-end" : "";
    return `
      <div class="mb-3 ${alignment}">
        <div class="d-inline-block px-3 py-2 rounded-3 ${message.sender_id === window.currentMemberId ? 'bg-primary text-white' : 'bg-light'}">
          <div class="small fw-semibold mb-1">${message.sender_id}</div>
          <div>${message.content}</div>
          <div class="small text-muted mt-1">${new Date(message.created_at).toLocaleString()}</div>
        </div>
      </div>`;
  }).join("\n");

  container.innerHTML = `<div class="px-3 py-2">${fragments}</div>`;
}

function loadThread(threadId) {
  if (!window.currentMemberId) return;
  const url = new URL("/features/community/messages/api/thread", window.location.origin);
  url.searchParams.set("member_id", window.currentMemberId);
  if (threadId) {
    url.searchParams.set("thread_id", threadId);
  }

  fetch(url, { headers: { "Accept": "application/json" } })
    .then((resp) => resp.json())
    .then((data) => {
      renderThread(data.data || []);
      const refreshBtn = document.getElementById("refresh-thread-btn");
      if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.onclick = () => loadThread(threadId);
      }
    })
    .catch((error) => {
      console.error("Failed to load thread", error);
    });
}

window.initializeMessagesTable = function initializeMessagesTable() {
  if (!window.appTables) {
    window.appTables = {};
  }

  const memberId = window.currentMemberId;
  const table = new Tabulator("#messages-table", {
    ...advancedTableConfig,
    ajaxURL: `/features/community/messages/api?member_id=${memberId}`,
    ajaxResponse: standardAjaxResponse,
    columns: [
      { title: "From", field: "sender_id", width: 140 },
      { title: "To", field: "recipient_id", width: 140 },
      { title: "Snippet", field: "content", formatter: formatDescription, minWidth: 220 },
      { title: "Created", field: "created_at", formatter: formatTimestamp, width: 160 },
    ],
  });

  window.appTables["messages-table"] = table;
  window.messagesTable = table;

  table.on("rowClick", (e, row) => {
    const data = row.getData();
    loadThread(data.thread_id || null);
  });

  return table;
};

document.addEventListener("DOMContentLoaded", () => {
  const tableEl = document.getElementById("messages-table");
  if (tableEl && !window.messagesTableInitialized) {
    window.messagesTableInitialized = true;
    initializeMessagesTable();
  }
});

document.body.addEventListener("refreshTable", () => {
  if (window.messagesTable) {
    window.messagesTable.replaceData();
  }
});
