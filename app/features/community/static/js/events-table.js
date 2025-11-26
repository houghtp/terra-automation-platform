/**
 * Community events page: FullCalendar (month/week) + Tabulator list view.
 */
(function () {
  const API_ENDPOINT = "/features/community/events/api";
  const MAX_EVENTS = 200;

  let calendarInstance = null;
  let tableInstance = null;

  document.addEventListener("DOMContentLoaded", () => {
    initCalendar();
    document.body.addEventListener("refreshTable", handleRefreshTrigger);
  });

  function initCalendar() {
    const calendarEl = document.getElementById("events-calendar");
    if (!calendarEl) {
      return;
    }

    if (typeof FullCalendar === "undefined") {
      console.error("FullCalendar is not available; cannot render calendar view.");
      return;
    }

    const calendar = new FullCalendar.Calendar(calendarEl, {
      plugins: resolveCalendarPlugins(),
      initialView: "dayGridMonth",
      height: "auto",
      expandRows: true,
      headerToolbar: {
        left: "prev,next today",
        center: "title",
        right: "monthToggle,weekToggle,listToggle",
      },
      customButtons: {
        monthToggle: {
          text: "Month",
          hint: "Show month calendar",
          classNames: ["fc-view-toggle", "fc-view-toggle-month"],
          click: () => showCalendarView("dayGridMonth", ".fc-monthToggle-button"),
        },
        weekToggle: {
          text: "Week",
          hint: "Show week calendar",
          classNames: ["fc-view-toggle", "fc-view-toggle-week"],
          click: () => showCalendarView("timeGridWeek", ".fc-weekToggle-button"),
        },
        listToggle: {
          text: "List",
          hint: "Show list table",
          classNames: ["fc-view-toggle", "fc-view-toggle-list"],
          click: showListView,
        },
      },
      buttonText: {
        today: "Today",
      },
      events: fetchCalendarEvents,
      dayMaxEvents: 4,
      eventDisplay: "block",
      dateClick: handleDateClick,
      eventClick: handleEventClick,
      eventDidMount: attachTooltip,
      eventWillUnmount: detachTooltip,
    });

    calendar.render();
    calendarInstance = calendar;

    decorateToolbarButtons(calendarEl);
    showCalendarView("dayGridMonth", ".fc-monthToggle-button");
  }

  function resolveCalendarPlugins() {
    const plugins = [];

    if (window.FullCalendarDayGrid) {
      plugins.push(window.FullCalendarDayGrid);
    } else {
      console.warn("FullCalendar DayGrid plugin missing; month view disabled.");
    }

    if (window.FullCalendarTimeGrid) {
      plugins.push(window.FullCalendarTimeGrid);
    } else {
      console.warn("FullCalendar TimeGrid plugin missing; week view disabled.");
    }

    if (window.FullCalendarInteraction) {
      plugins.push(window.FullCalendarInteraction);
    }

    if (window.FullCalendarBootstrap5) {
      plugins.push(window.FullCalendarBootstrap5);
    }

    return plugins;
  }

  function decorateToolbarButtons(calendarEl) {
    const root = calendarEl.closest(".fc");
    if (!root) {
      return;
    }

    const toolbarButtons = root.querySelectorAll(".fc-toolbar .fc-button");
    toolbarButtons.forEach((btn) => {
      btn.classList.add("btn", "btn-outline-secondary");
    });

    setButtonContent(root.querySelector(".fc-prev-button"), "ti ti-chevron-left", "Prev");
    setButtonContent(root.querySelector(".fc-next-button"), "ti ti-chevron-right", "Next");
    setButtonContent(root.querySelector(".fc-today-button"), "ti ti-calendar-event", "Today");
    setButtonContent(root.querySelector(".fc-monthToggle-button"), "ti ti-calendar-month", "Month");
    setButtonContent(root.querySelector(".fc-weekToggle-button"), "ti ti-calendar-week", "Week");
    setButtonContent(root.querySelector(".fc-listToggle-button"), "ti ti-list-details", "List");
  }

  function setButtonContent(button, iconClass, label) {
    if (!button) {
      return;
    }

    button.innerHTML = `<i class="${iconClass}"></i><span>${label}</span>`;
  }

  function showCalendarView(viewName, buttonSelector) {
    const { calendarWrapper, tableWrapper } = getViewWrappers();

    if (calendarWrapper) {
      calendarWrapper.classList.remove("showing-list");
      calendarWrapper.classList.add("showing-calendar");
    }
    if (tableWrapper) {
      tableWrapper.classList.add("d-none");
    }

    if (calendarInstance) {
      if (viewName && calendarInstance.view.type !== viewName) {
        calendarInstance.changeView(viewName);
      }
      setTimeout(() => calendarInstance.updateSize(), 0);
    }

    activateToolbarButton(buttonSelector);
  }

  function showListView() {
    const { calendarWrapper, tableWrapper } = getViewWrappers();

    if (calendarWrapper) {
      calendarWrapper.classList.add("showing-list");
      calendarWrapper.classList.remove("showing-calendar");
    }
    if (tableWrapper) {
      tableWrapper.classList.remove("d-none");
    }

    const table = ensureEventsTable();
    if (table) {
      setTimeout(() => table.redraw(true), 0);
    }

    activateToolbarButton(".fc-listToggle-button");
  }

  function getViewWrappers() {
    return {
      calendarWrapper: document.getElementById("events-calendar-wrapper"),
      tableWrapper: document.getElementById("events-table-wrapper"),
    };
  }

  function activateToolbarButton(selector) {
    const calendarEl = document.getElementById("events-calendar");
    if (!calendarEl) {
      return;
    }

    const root = calendarEl.closest(".fc");
    if (!root) {
      return;
    }

    root.querySelectorAll(".fc-toolbar .btn").forEach((btn) => {
      btn.classList.remove("btn-active");
    });

    if (!selector) {
      return;
    }

    const activeBtn = root.querySelector(selector);
    if (activeBtn) {
      activeBtn.classList.add("btn-active");
    }
  }

  function ensureEventsTable() {
    if (tableInstance) {
      return tableInstance;
    }

    const tableEl = document.getElementById("events-table");
    if (!tableEl) {
      return null;
    }

    if (typeof Tabulator === "undefined") {
      console.error("Tabulator is not loaded; cannot render list view.");
      return null;
    }

    if (!window.appTables) {
      window.appTables = {};
    }

    const table = new Tabulator(tableEl, {
      ...advancedTableConfig,
      rowHeader: false,
      selectable: false,
      ajaxURL: API_ENDPOINT,
      ajaxResponse: standardAjaxResponse,
      columns: [
        { title: "Title", field: "title", headerFilter: "input", minWidth: 220 },
        { title: "Start", field: "start_date", formatter: formatTimestamp, width: 170 },
        { title: "End", field: "end_date", formatter: formatTimestamp, width: 170 },
        { title: "Location", field: "location", minWidth: 160 },
        { title: "Category", field: "category", width: 140 },
        {
          title: "Actions",
          field: "actions",
          width: 140,
          headerSort: false,
          formatter(cell) {
            const rowData = cell.getRow().getData();
            return createRowCrudButtons(rowData, {
              onEdit: "editEvent",
              onDelete: "deleteEvent",
            });
          },
        },
      ],
    });

    tableInstance = table;
    window.eventsTable = table;
    window.appTables["events-table"] = table;
    bindRowActionHandlers("#events-table", {
      onEdit: "editEvent",
      onDelete: "deleteEvent",
    });

    return table;
  }

  function fetchCalendarEvents(fetchInfo, successCallback, failureCallback) {
    const params = new URLSearchParams({
      limit: MAX_EVENTS.toString(),
      offset: "0",
    });

    if (fetchInfo && fetchInfo.startStr) {
      params.set("start", fetchInfo.startStr);
    }
    if (fetchInfo && fetchInfo.endStr) {
      params.set("end", fetchInfo.endStr);
    }

    fetch(`${API_ENDPOINT}?${params.toString()}`, {
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        return response.json();
      })
      .then((payload) => {
        const events = Array.isArray(payload.data) ? payload.data.map(mapEventRecord) : [];
        successCallback(events);
      })
      .catch((error) => {
        console.error("Failed to load events:", error);
        if (typeof failureCallback === "function") {
          failureCallback(error);
        }
        if (typeof window.showToast === "function") {
          window.showToast("Unable to load events calendar data.", "error", 4000);
        }
      });
  }

  function mapEventRecord(record) {
    const startDate = record.start_date;
    const endDate = record.end_date || record.start_date;

    return {
      id: record.id,
      title: record.title,
      start: startDate,
      end: endDate,
      allDay: isAllDayEvent(startDate, record.end_date),
      extendedProps: {
        description: record.description,
        location: record.location,
        url: record.url,
        category: record.category,
      },
    };
  }

  function isAllDayEvent(start, end) {
    if (!start) {
      return false;
    }

    const startDate = new Date(start);
    if (Number.isNaN(startDate.getTime())) {
      return false;
    }

    if (!end) {
      return (
        startDate.getHours() === 0 &&
        startDate.getMinutes() === 0 &&
        startDate.getSeconds() === 0
      );
    }

    const endDate = new Date(end);
    if (Number.isNaN(endDate.getTime())) {
      return false;
    }

    return (
      startDate.getHours() === 0 &&
      startDate.getMinutes() === 0 &&
      endDate.getHours() === 0 &&
      endDate.getMinutes() === 0 &&
      startDate.toDateString() !== endDate.toDateString()
    );
  }

  function handleEventClick(info) {
    info.jsEvent.preventDefault();
    const eventId = info.event.id;
    if (!eventId || typeof htmx === "undefined") {
      if (info.event.extendedProps.url) {
        window.open(info.event.extendedProps.url, "_blank");
      }
      return;
    }

    loadModalContent(`/features/community/events/partials/form?event_id=${eventId}`);
  }

  function handleDateClick() {
    loadModalContent("/features/community/events/partials/form");
  }

  function attachTooltip(info) {
    if (typeof bootstrap === "undefined") {
      return;
    }

    const pieces = [];
    const { description, location, category } = info.event.extendedProps;
    if (description) {
      pieces.push(description);
    }
    if (location) {
      pieces.push(`<strong>Location:</strong> ${location}`);
    }
    if (category) {
      pieces.push(`<strong>Category:</strong> ${category}`);
    }

    if (pieces.length === 0) {
      return;
    }

    const tooltip = new bootstrap.Tooltip(info.el, {
      title: pieces.join("<br>"),
      html: true,
      placement: "top",
      trigger: "hover",
    });
    info.el._fcTooltip = tooltip;
  }

  function detachTooltip(info) {
    const tooltip = info.el._fcTooltip;
    if (tooltip && typeof tooltip.dispose === "function") {
      tooltip.dispose();
    }
  }

  window.editEvent = function editEvent(id) {
    editTabulatorRow(`/features/community/events/partials/form?event_id=${id}`);
  };

  window.deleteEvent = function deleteEvent(id) {
    deleteTabulatorRow(`/features/community/events/api/${id}`, "#events-table", {
      title: "Delete Event",
      message: "Are you sure you want to delete this event?",
      confirmText: "Delete Event",
    });
  };

  function handleRefreshTrigger() {
    if (calendarInstance) {
      calendarInstance.refetchEvents();
    }
    if (tableInstance) {
      tableInstance.replaceData();
    }
  }
})();
