(function () {
  console.log("🚀 [CSPM Scans Table] JavaScript module loading...");

  const TABLE_ID = "cspm-scans-table";
  let initialized = false;
  let successListenerAttached = false;
  let refreshHandler = null;
  let cancelHandler = null;
  let tableElementRef = null;
  const scanStreams = {}; // EventSource connections for active scans

  function getStreamUrl(scanId) {
    return `/msp/cspm/stream/${scanId}`;
  }

  function closeAllStreams() {
    Object.keys(scanStreams).forEach((scanId) => {
      closeStream(scanId);
    });
  }

  function buildStatusUpdate(statusPayload) {
    if (!statusPayload) return {};
    return {
      status: statusPayload.status,
      progress_percentage: statusPayload.progress_percentage ?? 0,
      current_check: statusPayload.current_check || null,
      total_checks: statusPayload.total_checks ?? 0,
      passed: statusPayload.passed ?? 0,
      failed: statusPayload.failed ?? 0,
      errors: statusPayload.errors ?? 0,
      started_at: statusPayload.started_at || null,
      completed_at: statusPayload.completed_at || null,
      error_message: statusPayload.error_message || null
    };
  }

  function applyRowUpdate(scanId, update) {
    const table = window.cspmScansTable;
    if (!table) {
      console.warn("[applyRowUpdate] Table not found");
      return;
    }

    const row = table.getRow(scanId);
    if (!row) {
      console.warn("[applyRowUpdate] Row not found for scan:", scanId);
      return;
    }

    try {
      console.log("[applyRowUpdate] Updating row", scanId, "with data:", update);
      row.update(update);
      console.log("[applyRowUpdate] Row data updated successfully");
    } catch (error) {
      console.error("[applyRowUpdate] Failed to update scan row", scanId, error);
    }
  }

  function closeStream(scanId) {
    const stream = scanStreams[scanId];
    if (!stream) return;

    try {
      stream.close();
      console.log("[EventSource] Closed stream for scan:", scanId);
    } catch (error) {
      console.warn("[EventSource] Error closing stream", scanId, error);
    }

    delete scanStreams[scanId];
  }

  function handleSocketMessage(scanId, rawMessage) {
    let payload = null;
    try {
      payload = JSON.parse(rawMessage);
    } catch (error) {
      console.warn("Invalid scan progress payload", rawMessage);
      return;
    }

    // DEBUG: Log all incoming messages
    console.log("[WebSocket] Received message for scan", scanId, ":", payload);

    const eventType = payload?.event;
    if (!eventType) {
      console.warn("[WebSocket] Message missing 'event' field:", payload);
      return;
    }

    switch (eventType) {
      case "snapshot":
        if (payload.data) {
          applyRowUpdate(scanId, buildStatusUpdate(payload.data));
        }
        break;
      case "scan-started":
        applyRowUpdate(scanId, { status: "running", progress_percentage: 0 });
        break;
      case "status": {
        const update = {};
        if (payload.status) {
          update.status = payload.status;

          // Clear current_check when scan reaches terminal state
          const normalized = payload.status.toLowerCase();
          if (["completed", "failed", "cancelled"].includes(normalized)) {
            update.current_check = null;
          }
        }
        if (payload.error) {
          update.error_message = payload.error;
        }
        if (payload.progress_percentage !== undefined) {
          update.progress_percentage = payload.progress_percentage;
          console.log(`[WebSocket] Progress: ${payload.progress_percentage}%`);
        }
        if (payload.current_check) {
          update.current_check = payload.current_check;
        }

        // Update result counts if provided
        if (payload.passed !== undefined) update.passed = payload.passed;
        if (payload.failed !== undefined) update.failed = payload.failed;
        if (payload.errors !== undefined) update.errors = payload.errors;
        if (payload.total_checks !== undefined) update.total_checks = payload.total_checks;

        // Update timestamps if provided
        if (payload.started_at) update.started_at = payload.started_at;
        if (payload.completed_at) update.completed_at = payload.completed_at;

        applyRowUpdate(scanId, update);

        // Handle explicit terminal status - ONLY close on completed/failed/cancelled
        // Don't close on 100% progress or "finalizing" - Celery task continues after PowerShell finishes
        if (payload.status) {
          const normalized = payload.status.toLowerCase();
          if (["completed", "failed", "cancelled"].includes(normalized)) {
            console.log(`🎯 [WebSocket] TERMINAL STATUS: ${normalized} - TRIGGERING DATABASE REFRESH`);
            closeStream(scanId);
            if (window.cspmScansTable) {
              window.cspmScansTable.replaceData();
            }
          }
        }
        break;
      }
      case "results-inserted":
      case "powershell-finished":
        if (window.cspmScansTable) {
          window.cspmScansTable.replaceData();
        }
        break;
      default:
        break;
    }
  }

  function openStream(scanId) {
    if (scanStreams[scanId]) {
      console.log("[EventSource] Already connected to scan:", scanId);
      return;
    }

    try {
      const streamUrl = getStreamUrl(scanId);
      console.log("[EventSource] Connecting to:", streamUrl);

      const eventSource = new EventSource(streamUrl);

      eventSource.addEventListener('progress', (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[EventSource] Progress update:", data.progress_percentage + "%");

          // Build update object
          const update = {
            status: data.status,
            progress_percentage: data.progress_percentage,
            current_check: data.current_check,
            total_checks: data.total_checks,
            passed: data.passed,
            failed: data.failed,
            errors: data.errors,
            started_at: data.started_at,
            completed_at: data.completed_at,
            error_message: data.error_message
          };

          applyRowUpdate(scanId, update);
        } catch (error) {
          console.error("[EventSource] Failed to parse progress event:", error);
        }
      });

      eventSource.addEventListener('complete', (event) => {
        console.log("[EventSource] Scan completed:", scanId);
        closeStream(scanId);

        // Refresh table to get final state
        const table = window.cspmScansTable;
        if (table) {
          table.replaceData();
        }
      });

      eventSource.onerror = (error) => {
        console.error("[EventSource] Error for scan", scanId, ":", error);
        closeStream(scanId);
      };

      scanStreams[scanId] = eventSource;
      console.log("[EventSource] Connected successfully for scan:", scanId);
    } catch (error) {
      console.error("[EventSource] Failed to open stream", scanId, error);
    }
  }

  function refreshActiveStreams(data) {
    // Open EventSource streams for running/pending scans
    (data || []).forEach((item) => {
      const status = (item.status || "").toLowerCase();
      if (status === "running" || status === "pending") {
        openStream(item.scan_id);
      } else if (status === "completed" || status === "failed" || status === "cancelled") {
        // Close stream for terminal scans
        if (scanStreams[item.scan_id]) {
          console.log(`[EventSource] Closing stream for ${status} scan:`, item.scan_id);
          closeStream(item.scan_id);
        }
      }
    });

    // NOTE: We don't auto-close streams that aren't in the data because of race conditions:
    // - New scans might not be in DB yet when replaceData() is called
    // - Streams will be explicitly closed when scan reaches terminal status (above)
  }

  function attachSuccessListener() {
    if (successListenerAttached) return;

    document.body.addEventListener("showSuccess", function () {
      if (typeof showToast === "function") {
        showToast("Operation completed successfully!", "success", 2200);
      }
    });

    successListenerAttached = true;
  }

  function renderStatusBadge(status) {
    const normalized = (status || "pending").toLowerCase();
    const map = {
      completed: { variant: "success", label: "Completed" },
      running: { variant: "info", label: "Running" },
      failed: { variant: "danger", label: "Failed" },
      cancelled: { variant: "neutral", label: "Cancelled" },
      pending: { variant: "neutral", label: "Pending" }
    };

    const meta = map[normalized] || map.pending;
    return `<span class="app-badge app-badge-${meta.variant}">${meta.label}</span>`;
  }

  function renderProgress(row) {
    const percent = row.progress_percentage || 0;
    // Don't show current_check in table view - only percentage

    return `
      <div class="d-flex align-items-center gap-2">
        <div class="flex-fill">
          <div class="progress progress-sm">
            <div class="progress-bar" style="width: ${percent}%" role="progressbar"></div>
          </div>
        </div>
        <span class="text-muted small">${percent}%</span>
      </div>
    `;
  }

  function renderResults(row) {
    const total = row.total_checks || 0;
    if (!total) {
      return '<span class="text-muted">-</span>';
    }

    const passed = row.passed || 0;
    const failed = row.failed || 0;
    const errors = row.errors || 0;

    return `
      <div class="d-flex gap-2">
        <span class="app-badge app-badge-success"><i class="ti ti-check me-1"></i>${passed}</span>
        <span class="app-badge app-badge-danger"><i class="ti ti-x me-1"></i>${failed}</span>
        ${errors ? `<span class="app-badge app-badge-warning"><i class="ti ti-alert-triangle me-1"></i>${errors}</span>` : ""}
      </div>
    `;
  }

  function renderTimestamp(value) {
    if (!value) return '<span class="text-muted">-</span>';

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return `<span class="text-muted">${value}</span>`;
    }

    return `
      <div>${date.toLocaleDateString()}</div>
      <div class="text-muted small">${date.toLocaleTimeString()}</div>
    `;
  }

  function buildColumns() {
    return [
      {
        title: "Assignment",
        field: "assignment_display_name",
        minWidth: 200,
        headerFilter: "input",
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const displayName = row.assignment_display_name || row.target_display_name || cell.getValue() || row.tenant_display_name || "Unknown";
          const identifier = row.target_identifier || row.m365_tenant_id || row.tenant_benchmark_id;
          const tech = (row.tech_type || "").toUpperCase();
          return `
            <div class="d-flex flex-column">
              <strong>${displayName}</strong>
              <small class="text-muted">${tech ? tech + " · " : ""}${identifier || ""}</small>
            </div>
          `;
        }
      },
      {
        title: "Benchmark",
        field: "benchmark_display_name",
        minWidth: 200,
        headerFilter: "input",
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const display = cell.getValue() || row.benchmark_key || "-";
          const key = row.benchmark_key;
          return `
            <div class="d-flex flex-column">
              <span>${display}</span>
              ${key ? `<small class="text-muted">${key}</small>` : ""}
            </div>
          `;
        }
      },
      {
        title: "Tech",
        field: "tech_type",
        width: 100,
        headerFilter: "input",
        formatter: function (cell) {
          const value = (cell.getValue() || "").toUpperCase();
          return value ? `<span class="app-badge app-badge-info">${value}</span>` : "<span class='text-muted'>-</span>";
        }
      },
      {
        title: "Status",
        field: "status",
        width: 120,
        headerFilter: "list",
        headerFilterParams: {
          values: {
            "": "All",
            completed: "Completed",
            running: "Running",
            failed: "Failed",
            pending: "Pending",
            cancelled: "Cancelled"
          }
        },
        formatter: function (cell) {
          return renderStatusBadge(cell.getValue());
        }
      },
      {
        title: "Progress",
        field: "progress_percentage",
        width: 180,
        hozAlign: "left",
        headerSort: false,
        formatter: function (cell) {
          return renderProgress(cell.getRow().getData());
        }
      },
      {
        title: "Results",
        field: "passed",
        width: 160,
        headerSort: false,
        formatter: function (cell) {
          return renderResults(cell.getRow().getData());
        }
      },
      {
        title: "Started",
        field: "started_at",
        width: 150,
        formatter: function (cell) {
          return renderTimestamp(cell.getValue());
        }
      },
      {
        title: "Completed",
        field: "completed_at",
        width: 150,
        formatter: function (cell) {
          return renderTimestamp(cell.getValue());
        }
      },
      {
        title: "Actions",
        field: "scan_id",
        width: 120,
        headerSort: false,
        formatter: function (cell) {
          const row = cell.getRow().getData();
          const scanId = cell.getValue();
          const status = (row.status || "").toLowerCase();
          const viewIcon = status === "completed" ? "ti ti-report" : "ti ti-eye";
          const viewTitle = status === "completed" ? "View Results" : "View Details";
          const viewHref = `/msp/cspm/scans/${scanId}`;
          const canCancel = status === "running";
          const cancelIcon = canCancel ? `
            <i class="ti ti-square-off row-action-icon text-danger cancel-scan-btn"
               data-scan-id="${scanId}"
               title="Cancel Scan"
               style="cursor: pointer;"></i>
          ` : "";

          return `
            <div class="row-actions d-flex gap-2" data-id="${scanId}">
              <a href="${viewHref}" title="${viewTitle}">
                <i class="${viewIcon} row-action-icon"></i>
              </a>
              ${cancelIcon}
            </div>
          `;
        }
      }
    ];
  }

  function confirmCancelScan(scanId, table) {
    if (typeof showConfirmModal !== "function") {
      return;
    }

    showConfirmModal({
      title: "Cancel Scan",
      message: "Are you sure you want to cancel this running scan?",
      confirmText: "Cancel Scan",
      cancelText: "Keep Running",
      type: "warning",
      onConfirm: () => {
        fetch(`/msp/cspm/scans/${scanId}/cancel`, {
          method: "DELETE",
          credentials: "same-origin",
          headers: {
            "X-Requested-With": "XMLHttpRequest"
          }
        })
          .then(async (response) => {
            const data = await response.json().catch(() => null);

            if (!response.ok) {
              const message = data?.detail || "Cancellation failed";
              if (typeof showToast === "function") {
                showToast(message, "error");
              }
              return;
            }

            if (typeof showToast === "function") {
              showToast(data?.message || "Scan cancelled", "success");
            }

            if (table) {
              table.replaceData();
            }
          })
          .catch(() => {
            if (typeof showToast === "function") {
              showToast("Network error cancelling scan", "error");
            }
          });
      }
    });
  }

  function bindTableEvents(table) {
    if (refreshHandler) {
      document.body.removeEventListener("refreshTable", refreshHandler);
      refreshHandler = null;
    }

    refreshHandler = function (event) {
      const targetId = event?.detail?.tableId;
      if (!targetId || targetId === TABLE_ID) {
        table.replaceData();
      }
    };

    document.body.addEventListener("refreshTable", refreshHandler);

    if (tableElementRef && cancelHandler) {
      tableElementRef.removeEventListener("click", cancelHandler);
    }

    tableElementRef = document.getElementById(TABLE_ID);
    if (!tableElementRef) {
      cancelHandler = null;
      return;
    }

    cancelHandler = function (event) {
      const cancelBtn = event.target.closest(".cancel-scan-btn");
      if (!cancelBtn) return;

      const scanId = cancelBtn.dataset.scanId;
      if (!scanId) return;

      event.preventDefault();
      confirmCancelScan(scanId, table);
    };

    tableElementRef.addEventListener("click", cancelHandler);
  }

  function initializeTable() {
    const container = document.getElementById(TABLE_ID);
    if (!container || initialized) {
      return;
    }

    if (!window.appTables) {
      window.appTables = {};
    }

    closeAllStreams();

    if (window.cspmScansTable && typeof window.cspmScansTable.destroy === "function") {
      window.cspmScansTable.destroy();
    }

    const table = new Tabulator(`#${TABLE_ID}`, {
      ...advancedTableConfig,
      index: "scan_id",
      ajaxURL: "/msp/cspm/scans/api/list",
      ajaxResponse: standardAjaxResponse,
      placeholder: "No scans have been run yet. Click 'Start Scan' to begin.",
      columns: buildColumns(),
      selectableRows: false,
      rowHeader: null
    });

    table.on("dataLoaded", function (data) {
      refreshActiveStreams(data);
    });

    table.on("rowUpdated", function (row) {
      const data = row?.getData?.();
      if (!data) return;

      const status = (data.status || "").toLowerCase();
      if (status === "running" || status === "pending") {
        openStream(data.scan_id);
      } else {
        closeStream(data.scan_id);
      }
    });

    window.cspmScansTable = table;
    window.appTables[TABLE_ID] = table;
    initialized = true;

    initializeQuickSearch(
      "cspm-scans-quick-search",
      "cspm-scans-clear-search",
      TABLE_ID
    );

    bindTableEvents(table);
    attachSuccessListener();

    window.exportTable = function (format) {
      return exportTabulatorTable(TABLE_ID, format, "cspm-scans");
    };
  }

  document.addEventListener("DOMContentLoaded", initializeTable);

  document.body.addEventListener("htmx:afterSwap", function (event) {
    const target = event?.detail?.target;
    if (!target || target.id !== "scan-area") {
      return;
    }

    initialized = false;

    if (refreshHandler) {
      document.body.removeEventListener("refreshTable", refreshHandler);
      refreshHandler = null;
    }

    if (tableElementRef && cancelHandler) {
      tableElementRef.removeEventListener("click", cancelHandler);
      tableElementRef = null;
      cancelHandler = null;
    }

    if (window.cspmScansTable && typeof window.cspmScansTable.destroy === "function") {
      window.cspmScansTable.destroy();
    }

    window.cspmScansTable = null;
    closeAllStreams();

    setTimeout(initializeTable, 0);
  });

  console.log("✅ [CSPM Scans Table] Event listeners attached");

  // Debug: Listen to ALL HTMX events to see what's happening
  document.body.addEventListener("htmx:afterSettle", function(event) {
    const xhr = event.detail?.xhr;
    const url = xhr?.responseURL || "unknown";
    const status = xhr?.status || "unknown";
    console.log(`[HTMX Debug] afterSettle - URL: ${url}, Status: ${status}`);

    if (xhr) {
      const triggerHeader = xhr.getResponseHeader("HX-Trigger");
      const triggerAfterSettle = xhr.getResponseHeader("HX-Trigger-After-Settle");
      console.log("[HTMX Debug] HX-Trigger:", triggerHeader);
      console.log("[HTMX Debug] HX-Trigger-After-Settle:", triggerAfterSettle);

      // Check if this is a form submission response
      if (status === 204) {
        console.log("[HTMX Debug] ⚠️ This is a 204 response (likely form submission) - scanStarted should trigger!");
      }
    }
  });

  // CRITICAL FIX: Listen to htmx:afterRequest instead of scanStarted
  // The global form handler closes modal before HTMX processes HX-Trigger-After-Settle header
  // So we need to intercept the form submission directly
  document.body.addEventListener("htmx:afterRequest", function(event) {
    // Only handle scan-form submissions
    if (event.target.id === "scan-form" && event.detail.successful) {
      console.log("🎯 [Scan Form] Form submitted successfully");

      // Extract scan_id from response headers
      const xhr = event.detail.xhr;
      const triggerAfterSettle = xhr.getResponseHeader("HX-Trigger-After-Settle");

      console.log("[Scan Form] HX-Trigger-After-Settle:", triggerAfterSettle);

      // Try to extract scan_id from HX-Trigger-After-Settle header
      if (triggerAfterSettle) {
        try {
          // Format: scanStarted:{"scan_id":"..."}
          const match = triggerAfterSettle.match(/scanStarted:\{"scan_id":"([^"]+)"\}/);
          if (match && match[1]) {
            const scanId = match[1];
            console.log("✅ [Scan Form] Extracted scan_id:", scanId, "- Opening EventSource");
            openStream(scanId);
          }
        } catch (e) {
          console.error("[Scan Form] Failed to parse HX-Trigger-After-Settle:", e);
        }
      }
    }
  });

  // Keep the old scanStarted listener as backup (in case HTMX fixes timing)
  document.body.addEventListener("scanStarted", function (event) {
    console.log("🎬 [Event] scanStarted received (backup handler)");
    const scanId = event?.detail?.scan_id;
    if (scanId) {
      console.log("✅ [Event] Opening EventSource for scan:", scanId);
      openStream(scanId);
    }
  });

  window.addEventListener("beforeunload", closeAllStreams);
})();
