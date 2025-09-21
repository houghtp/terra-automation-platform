/**
 * Logs table configuration using Tabulator
 */

// Base configuration for logs table
const logsTableConfig = {
    height: "600px",
    layout: "fitColumns",
    pagination: true,
    paginationMode: "remote",
    paginationSize: 50,
    paginationSizeSelector: [25, 50, 100, 200],
    ajaxURL: "/features/administration/logs/api/list",
    ajaxConfig: {
        credentials: 'same-origin'
    },
    ajaxResponse: function(url, params, response) {
        return {
            data: response.data,
            last_page: Math.ceil(response.total / params.size)
        };
    },
    columns: [
        {
            title: "Timestamp",
            field: "timestamp",
            width: 180,
            formatter: function(cell) {
                const date = new Date(cell.getValue());
                return date.toLocaleString();
            }
        },
        {
            title: "Level",
            field: "level",
            width: 100,
            formatter: function(cell) {
                const level = cell.getValue();
                return `<span class="log-level-badge log-level-${level}">${level}</span>`;
            }
        },
        {
            title: "Tenant",
            field: "tenant_id",
            width: 120
        },
        {
            title: "Logger",
            field: "logger_name",
            width: 200
        },
        {
            title: "Message",
            field: "message",
            minWidth: 300,
            formatter: function(cell) {
                const message = cell.getValue();
                if (message.length > 100) {
                    return message.substring(0, 100) + '...';
                }
                return message;
            }
        },
        {
            title: "Actions",
            field: "id",
            width: 100,
            formatter: function(cell) {
                return `<i class="ti ti-eye row-action-icon" title="View Details" onclick="viewLogDetails(${cell.getValue()})"></i>`;
            }
        }
    ],
    rowClick: function(e, row) {
        viewLogDetails(row.getData().id);
    }
};

// Export for use in templates
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { logsTableConfig };
}