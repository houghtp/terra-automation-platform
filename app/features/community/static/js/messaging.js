/**
 * Lightweight messaging client helpers for the community hub.
 */

let currentThreadId = null;

function renderMessages(messages) {
  const pane = document.getElementById("message-pane");
  if (!pane) return;

  if (!messages.length) {
    pane.innerHTML = "<div class='text-muted text-center py-4'>No messages yet.</div>";
    return;
  }

  const html = messages
    .map((message) => {
      const sentAt = message.created_at ? new Date(message.created_at).toLocaleString() : "";
      return `
        <div class="mb-3">
          <div class="d-flex justify-content-between">
            <span class="fw-semibold">${message.sender_id}</span>
            <span class="text-muted small">${sentAt}</span>
          </div>
          <div>${message.content}</div>
        </div>
      `;
    })
    .join("");

  pane.innerHTML = `<div class="messages-list">${html}</div>`;
  pane.scrollTop = pane.scrollHeight;
}

function loadThreads() {
  fetch("/features/community/messaging/threads")
    .then((response) => response.json())
    .then((payload) => {
      const tableElement = document.getElementById("threads-table");
      if (!tableElement) return;

      const rows = payload.data
        .map((thread) => {
          const updated = thread.updated_at ? new Date(thread.updated_at).toLocaleString() : "";
          return `
            <div class="list-group-item list-group-item-action" data-thread-id="${thread.id}">
              <div class="fw-semibold">${thread.subject || "Untitled Thread"}</div>
              <div class="text-muted small">Updated ${updated}</div>
            </div>
          `;
        })
        .join("");

      tableElement.innerHTML = `<div class="list-group list-group-flush">${rows}</div>`;
      const badge = document.getElementById("threads-total-badge");
      if (badge) {
        badge.textContent = `${payload.total || 0} total`;
      }

      tableElement.querySelectorAll("[data-thread-id]").forEach((el) => {
        el.addEventListener("click", () => {
          const threadId = el.getAttribute("data-thread-id");
          selectThread(threadId, el.textContent.trim());
        });
      });
    });
}

function selectThread(threadId, subject) {
  currentThreadId = threadId;
  const subjectEl = document.getElementById("thread-subject");
  if (subjectEl) {
    subjectEl.textContent = subject || "Thread";
  }

  fetch(`/features/community/messaging/threads/${threadId}/messages`)
    .then((response) => response.json())
    .then((payload) => renderMessages(payload.data || []));
}

window.sendMessage = function sendMessage(event) {
  event.preventDefault();
  if (!currentThreadId) return;

  const textarea = document.getElementById("message-input");
  const content = textarea.value.trim();
  if (!content) return;

  fetch(`/features/community/messaging/threads/${currentThreadId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, sender_id: "self", recipient_id: "tenant" }),
  })
    .then((response) => {
      if (!response.ok) throw new Error("Failed to send message");
      textarea.value = "";
      return fetch(`/features/community/messaging/threads/${currentThreadId}/messages`);
    })
    .then((response) => response.json())
    .then((payload) => renderMessages(payload.data || []))
    .catch((err) => console.error(err));
};

window.composeThread = function composeThread() {
  editTabulatorRow("/features/community/messaging/partials/form");
};

document.addEventListener("DOMContentLoaded", () => {
  loadThreads();
});

document.body.addEventListener("refreshTable", loadThreads);
