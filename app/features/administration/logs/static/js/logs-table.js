window.initializeLogsTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#logs-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/administration/logs/api/list",
        columns: [
            {
                title: "Timestamp",
                field: "timestamp",
                minWidth: 150,
                headerFilter: "input",
                formatter: formatTimestamp
            },
            {
                title: "Level",
                field: "level",
                width: 80,
                headerFilter: "input",
                formatter: function (cell) {
                    const level = cell.getValue();
                    return `<span class="log-level-badge log-level-${level}">${level}</span>`;
                }
            },
            {
                title: "Tenant",
                field: "tenant_id",
                minWidth: 80,
                headerFilter: "input"
            },
            {
                title: "Logger",
                field: "logger_name",
                minWidth: 120,
                headerFilter: "input"
            },
            {
                title: "User ID",
                field: "user_id",
                minWidth: 80,
                headerFilter: "input"
            },
            {
                title: "Request ID",
                field: "request_id",
                minWidth: 100,
                headerFilter: "input"
            },
            {
                title: "Endpoint",
                field: "endpoint",
                minWidth: 120,
                headerFilter: "input",
                formatter: function (cell) {
                    const endpoint = cell.getValue() || '';
                    if (endpoint.length > 30) {
                        return endpoint.substring(0, 30) + '...';
                    }
                    return endpoint;
                }
            },
            {
                title: "Method",
                field: "method",
                width: 70,
                headerFilter: "input"
            },
            {
                title: "IP Address",
                field: "ip_address",
                minWidth: 100,
                headerFilter: "input"
            },
            {
                title: "Message",
                field: "message",
                minWidth: 200,
                headerFilter: "input",
                formatter: function (cell) {
                    const message = cell.getValue() || '';
                    if (message.length > 60) {
                        return message.substring(0, 60) + '...';
                    }
                    return message;
                }
            },
            {
                title: "Actions",
                field: "id",
                width: 80,
                headerSort: false,
                formatter: (cell) => formatViewAction(cell, 'viewLogDetails')
            }
        ]
    });

    // Store table reference globally
    window.logsTable = table;
    window.appTables["logs-table"] = table;

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('logs-table', format, 'application_logs');
};

window.viewLogDetails = function (logId) {
    const url = `/features/administration/logs/partials/log_details?log_id=${logId}`;

    if (typeof window.loadModalContent === 'function') {
        window.loadModalContent(url, { modalId: 'modal' });
        return;
    }

    fetch(url, {
        headers: {
            'HX-Request': 'true',
            'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Request failed with status ${response.status}`);
            }
            return response.text();
        })
        .then(html => {
            const modalBody = document.getElementById('modal-body');
            if (modalBody) {
                modalBody.innerHTML = html;
                if (typeof window.showModal === 'function') {
                    window.showModal();
                }
            }
        })
        .catch(error => {
            console.error('Failed to load log details:', error);
            if (typeof window.showToast === 'function') {
                window.showToast('Failed to load log details. Please try again.', 'error');
            }
        });
};

window.refreshLogs = function () {
    window.refreshTable && window.refreshTable('logs-table');
};

document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("logs-table");

    if (tableElement && !window.logsTableInitialized) {
        window.logsTableInitialized = true;
        initializeLogsTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'logs-table');
        }, 100);
    }
});
