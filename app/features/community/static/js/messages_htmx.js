/**
 * Lightweight HTMX helpers for the messaging UI.
 */

window.setThreadMeta = function setThreadMeta(subtitle, threadUrl) {
  const subtitleEl = document.getElementById("thread-subtitle");
  if (subtitleEl) {
    subtitleEl.textContent = subtitle || "Conversation";
  }
  const refreshBtn = document.getElementById("thread-refresh-btn");
  if (refreshBtn) {
    refreshBtn.disabled = false;
    refreshBtn.setAttribute("hx-get", threadUrl);
    refreshBtn.setAttribute("hx-target", "#thread-pane");
    refreshBtn.setAttribute("hx-swap", "innerHTML");
  }
};

// Reload conversations when triggered (e.g., after sending a message)
document.body.addEventListener("refreshConversations", () => {
  const rail = document.getElementById("conversation-rail");
  if (rail) {
    htmx.ajax("GET", "/features/community/messages/partials/conversations", { target: rail });
  }
});

// Open a thread after a new conversation is created
document.body.addEventListener("openThread", (event) => {
  const detail = event?.detail || {};
  const url = detail.thread_url;
  const subtitle = detail.subtitle || "Conversation";
  if (url) {
    setThreadMeta(subtitle, url);
    htmx.ajax("GET", url, { target: "#thread-pane", swap: "innerHTML" });
  }
});
