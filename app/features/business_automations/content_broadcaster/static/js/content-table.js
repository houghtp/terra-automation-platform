/**
 * Content Table JavaScript
 * Consolidated implementation for Content Library table.
 * This file is the canonical content table used by the templates.
 */

const htmlEscape = window.escapeHtml || function (value) {
    if (value == null) {
        return '';
    }
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
};

const relativeTime = window.formatRelativeTime || function (value) {
    if (!value && value !== 0) return '';
    const date = value instanceof Date ? value : new Date(value);
    if (isNaN(date)) return '';
    const diff = Date.now() - date.getTime();
    if (diff < 1000) return 'just now';
    if (diff < 60_000) return `${Math.max(1, Math.round(diff / 1000))}s ago`;
    if (diff < 3_600_000) return `${Math.round(diff / 60000)}m ago`;
    if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
    return date.toLocaleString();
};

const dateFormatter = window.formatDate || function (cell) {
    const value = cell.getValue();
    if (!value) return '<span class="text-muted">—</span>';
    return value;
};

function formatSeoScore(cell) {
    const score = cell.getValue();
    if (score == null || score === '') {
        return '<span class="text-muted">—</span>';
    }
    let variant = 'neutral';
    if (score >= 95) {
        variant = 'success';
    } else if (score >= 90) {
        variant = 'info';
    } else if (score >= 80) {
        variant = 'warning';
    } else {
        variant = 'danger';
    }
    return `<span class="status-badge status-${variant} text-normal">${htmlEscape(score)}</span>`;
}

const GENERATION_STATUS_LABELS = {
    running: 'In Progress',
    success: 'Completed',
    error: 'Failed'
};

const GENERATION_STATUS_CLASSES = {
    running: 'bg-primary',
    success: 'bg-success',
    error: 'bg-danger'
};

const GenerationTracker = (() => {
    const endpoint = '/features/content-broadcaster/api/generation-stream';
    const listeners = new Set();
    const jobs = new Map();
    const completedRetentionMs = 60_000;
    let eventSource = null;
    let reconnectTimer = null;
    let panelInitialized = false;

    function init() {
        setupPanel();
        connect();
    }

    function setupPanel() {
        if (panelInitialized) {
            return;
        }
        const clearButton = document.getElementById('clear-generation-activity');
        if (clearButton) {
            clearButton.addEventListener('click', () => {
                for (const [jobId, job] of jobs.entries()) {
                    if (job.completed) {
                        jobs.delete(jobId);
                    }
                }
                render();
            });
            panelInitialized = true;
        }
    }

    function connect() {
        if (!window.EventSource || eventSource) {
            return;
        }
        eventSource = new EventSource(endpoint);
        eventSource.addEventListener('generation', (event) => {
            try {
                const payload = JSON.parse(event.data);
                handleEvent(payload);
            } catch (error) {
                console.error('Failed to parse generation event', error);
            }
        });
        eventSource.onerror = () => {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            if (!reconnectTimer) {
                reconnectTimer = setTimeout(() => {
                    reconnectTimer = null;
                    connect();
                }, 5000);
            }
        };
    }

    function handleEvent(event) {
        if (!event || !event.job_id) {
            return;
        }
        const updatedAt = event.timestamp ? new Date(event.timestamp) : new Date();
        const job = jobs.get(event.job_id) || {
            jobId: event.job_id,
            history: [],
            createdAt: updatedAt,
            title: event.data && event.data.title ? event.data.title : 'SEO Content Generation'
        };

        job.history.push(event);
        job.stage = event.stage;
        job.message = event.message;
        job.status = event.status || job.status || 'running';
        job.data = event.data || {};
        job.updatedAt = updatedAt;
        if (job.data && job.data.title && !job.title) {
            job.title = job.data.title;
        }

        if (job.status === 'success' || job.status === 'error') {
            job.completed = true;
            job.completedAt = updatedAt;
        }

        jobs.set(event.job_id, job);
        notify(event);
        pruneJobs();
        render();
    }

    function pruneJobs() {
        const now = Date.now();
        for (const [jobId, job] of jobs.entries()) {
            if (job.completed && job.completedAt && now - job.completedAt.getTime() > completedRetentionMs) {
                jobs.delete(jobId);
            }
        }
    }

    function render() {
        const panel = document.getElementById('generation-activity-panel');
        const list = document.getElementById('generation-activity-list');
        if (!panel || !list) {
            return;
        }

        const activeJobs = Array.from(jobs.values()).sort((a, b) => {
            return b.updatedAt.getTime() - a.updatedAt.getTime();
        });

        if (activeJobs.length === 0) {
            panel.classList.add('d-none');
            list.innerHTML = '';
            return;
        }

        panel.classList.remove('d-none');

        const html = activeJobs.map(renderJob).join('');
        list.innerHTML = html;
    }

    function renderJob(job) {
        const statusClass = GENERATION_STATUS_CLASSES[job.status] || GENERATION_STATUS_CLASSES.running;
        const statusLabel = GENERATION_STATUS_LABELS[job.status] || GENERATION_STATUS_LABELS.running;
        const title = htmlEscape(job.title);
        const message = htmlEscape(job.message);
        const stage = htmlEscape(job.stage);
        const seoScore = job.data && job.data.seo_score != null ? job.data.seo_score : null;
        const contentId = job.data && job.data.content_id ? job.data.content_id : null;
        const extraInfo = [];
        if (seoScore != null) {
            extraInfo.push(`SEO Score: <strong>${htmlEscape(seoScore)}</strong>`);
        }
        if (contentId) {
            extraInfo.push(`Content ID: <code>${htmlEscape(contentId)}</code>`);
        }
        const extraHtml = extraInfo.length ? `<div class="small text-muted mt-1">${extraInfo.join(' • ')}</div>` : '';
        const spinner = job.status === 'running' ? '<span class="spinner-border spinner-border-sm text-primary me-2"></span>' : '';

        return `
            <li class="mb-2" data-job-id="${htmlEscape(job.jobId)}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="me-3">
                        <div class="fw-semibold">${title}</div>
                        <div class="small text-muted">${spinner}${message || stage}</div>
                        ${extraHtml}
                    </div>
                    <div class="text-end">
                        <span class="badge ${statusClass}">${statusLabel}</span>
                        <div class="small text-muted">${relativeTime(job.updatedAt)}</div>
                    </div>
                </div>
            </li>
        `;
    }

    function notify(event) {
        listeners.forEach((callback) => {
            try {
                callback(event);
            } catch (error) {
                console.error('GenerationTracker subscriber error', error);
            }
        });
    }

    function subscribe(callback) {
        listeners.add(callback);
        return () => listeners.delete(callback);
    }

    return {
        init,
        subscribe,
        getJobs: () => jobs
    };
})();

window.GenerationTracker = GenerationTracker;

// Initialize Content Table
window.initializeContentTable = function () {
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#content-broadcaster-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/content-broadcaster/library/api/list",
        columns: [
            {
                title: "Title",
                field: "title",
                minWidth: 200,
                headerFilter: "input",
                cssClass: "tabulator-cell-wrap",
                formatter: function (cell) {
                    return `<strong>${cell.getValue()}</strong>`;
                }
            },
            {
                title: "State",
                field: "state",
                width: 130,
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All States",
                        "draft": "Draft",
                        "pending_approval": "Pending Approval",
                        "in_review": "In Review",
                        "approved": "Approved",
                        "failed": "Failed",
                        "scheduled": "Scheduled",
                        "published": "Published",
                        "archived": "Archived"
                    }
                },
                sorter: "string",
                formatter: function (cell) {
                    const value = cell.getValue();
                    const labels = {
                        "draft": "Draft",
                        "pending_approval": "Pending Approval",
                        "in_review": "In Review",
                        "approved": "Approved",
                        "failed": "Failed",
                        "scheduled": "Scheduled",
                        "published": "Published",
                        "archived": "Archived"
                    };
                    const variants = {
                        "draft": "neutral",
                        "pending_approval": "warning",
                        "in_review": "warning",
                        "approved": "success",
                        "failed": "danger",
                        "scheduled": "info",
                        "published": "info",
                        "archived": "neutral"
                    };
                    return `<span class="status-badge status-${variants[value] || 'neutral'} text-normal">${labels[value] || value || ''}</span>`;
                }
            },
            {
                title: "SEO Score",
                field: "content_metadata.seo_score",
                width: 110,
                sorter: "number",
                headerFilter: "number",
                headerFilterPlaceholder: "Min score...",
                formatter: formatSeoScore
            },
            {
                title: "Channels",
                field: "target_channels",
                minWidth: 150,
                headerFilter: "input",
                formatter: function (cell) {
                    const channels = cell.getValue();
                    if (!channels || channels.length === 0) {
                        return '<span class="text-muted">None</span>';
                    }
                    return channels.map(channel =>
                        `<span class="status-badge status-neutral text-normal me-1">${htmlEscape(channel)}</span>`
                    ).join('');
                }
            },
            {
                title: "Scheduled",
                field: "scheduled_at",
                minWidth: 120,
                headerFilter: "input",
                formatter: dateFormatter
            },
            {
                title: "Created",
                field: "created_at",
                minWidth: 120,
                headerFilter: "input",
                formatter: dateFormatter
            },
            {
                title: "Actions",
                field: "id",
                width: 180,
                headerSort: false,
                formatter: function (cell) {
                    const rowData = cell.getRow().getData();
                    let buttons = '';

                    // View button (always available)
                    buttons += `
                        <i class="ti ti-eye row-action-icon"
                           title="View Details"
                           style="cursor: pointer; font-size: 18px; color: #0054a6; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;"
                           onclick="viewContentItem('${rowData.id}')"></i>`;

                    // Approve button (only if pending_approval)
                    if (rowData.state === 'pending_approval') {
                        buttons += `
                            <i class="ti ti-check row-action-icon"
                               title="Approve"
                               style="cursor: pointer; font-size: 18px; color: #2fb344; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;"
                               onclick="approveContentItem('${rowData.id}')"></i>`;
                    }

                    // Reject button (only if pending_approval)
                    if (rowData.state === 'pending_approval') {
                        buttons += `
                            <i class="ti ti-x row-action-icon"
                               title="Reject"
                               style="cursor: pointer; font-size: 18px; color: #d63939; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;"
                               onclick="rejectContentItem('${rowData.id}')"></i>`;
                    }

                    // Schedule button (only if approved)
                    if (rowData.state === 'approved') {
                        buttons += `
                            <i class="ti ti-calendar row-action-icon"
                               title="Schedule"
                               style="cursor: pointer; font-size: 18px; color: #0054a6; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;"
                               onclick="scheduleContentItem('${rowData.id}')"></i>`;
                    }

                    // Publish button (only if scheduled)
                    if (rowData.state === 'scheduled') {
                        buttons += `
                            <i class="ti ti-rocket row-action-icon"
                               title="Publish Now"
                               style="cursor: pointer; font-size: 18px; color: #2fb344; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;"
                               onclick="publishContentItem('${rowData.id}')"></i>`;
                    }

                    // Delete button (only draft/rejected)
                    buttons += `
                        <i class="ti ti-trash row-action-icon"
                           title="Delete"
                           style="cursor: pointer; font-size: 18px; color: #d63939; padding: 4px; border-radius: 4px; transition: all 0.2s;"
                           onclick="deleteContentItem('${rowData.id}')"></i>`;

                    return `<div class="row-actions" style="display: flex; align-items: center;">${buttons}</div>`;
                }
            }
        ]
    });

    // Store in global registry
    window.contentTable = table;
    window.appTables["content-broadcaster-table"] = table;

    // Bulk Delete Selected (keep for bulk operations)
    addBulkDeleteHandler(table, '/features/content-broadcaster', 'Content Item');

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('content-broadcaster-table', format, 'content-items');
};

// === View/Detail Functions ===

// View content item - navigate to full page viewer
window.viewContentItem = function (id) {
    window.location.href = `/features/content-broadcaster/${id}/view`;
};

// === Workflow Action Functions (Frontend stubs - backend not implemented yet) ===

// Approve content item
window.approveContentItem = function (id) {
    showToast('Approve workflow - Backend not implemented yet', 'info');
    console.log('TODO: Approve content item:', id);
    // TODO: Implement approve workflow backend
};

// Reject content item
window.rejectContentItem = function (id) {
    showToast('Reject workflow - Backend not implemented yet', 'info');
    console.log('TODO: Reject content item:', id);
    // TODO: Implement reject workflow backend with reason prompt
};

// Schedule content item
window.scheduleContentItem = function (id) {
    showToast('Schedule workflow - Backend not implemented yet', 'info');
    console.log('TODO: Schedule content item:', id);
    // TODO: Implement schedule workflow backend with date picker
};

// Publish content item
window.publishContentItem = function (id) {
    showToast('Publish workflow - Backend not implemented yet', 'info');
    console.log('TODO: Publish content item:', id);
    // TODO: Implement publish workflow backend
};

// Delete content item (draft/rejected)
window.deleteContentItem = function (id) {
    showConfirmModal({
        title: 'Delete Content',
        message: 'Deleting this content will remove all associated variants and metadata. This action cannot be undone.',
        confirmText: 'Delete',
        type: 'danger',
        onConfirm: () => {
            fetch(`/features/content-broadcaster/api/${id}/delete`, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            }).then((response) => {
                if (!response.ok) {
                    return response.json().catch(() => ({})).then((data) => {
                        throw new Error(data.detail || 'Failed to delete content');
                    });
                }
                return response.json();
            }).then(() => {
                showToast('Content deleted successfully', 'success');
                if (window.contentTable) {
                    window.contentTable.setData();
                }
            }).catch((error) => {
                console.error('Delete content error', error);
                showToast(error.message || 'Failed to delete content', 'error');
            });
        }
    });
};

// === Event Listeners ===

// Listen for HX-Trigger events from the server
document.body.addEventListener('showSuccess', function () {
    showToast('✅ Operation completed successfully!', 'success');
});

document.body.addEventListener('refreshTable', function () {
    if (window.contentTable) {
        window.contentTable.setData();
    }
});

// === Initialization ===

// Standard initialization pattern
document.addEventListener("DOMContentLoaded", () => {
    if (window.GenerationTracker) {
        window.GenerationTracker.init();
    }
    const tableElement = document.getElementById("content-broadcaster-table");
    if (tableElement && !window.contentTableInitialized) {
        window.contentTableInitialized = true;
        initializeContentTable();

        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'content-broadcaster-table');
        }, 100);
    }
});
