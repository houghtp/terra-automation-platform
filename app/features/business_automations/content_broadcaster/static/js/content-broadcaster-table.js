window.initializeContentBroadcasterTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    const table = new Tabulator("#content-broadcaster-table", {
        ...advancedTableConfig,
        ajaxURL: "/features/business_automations/content-broadcaster/api/list",
        columns: [
            {
                title: "ID",
                field: "id",
                width: 80,
                sorter: "number",
                headerFilter: "number",
                headerFilterPlaceholder: "Filter by ID..."
            },
            {
                title: "Title",
                field: "title",
                editor: "input",
                headerFilter: "input",
                headerFilterPlaceholder: "Filter titles...",
                sorter: "string",
                width: 250
            },
            {
                title: "Content Type",
                field: "content_type",
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All Types",
                        "social_post": "Social Post",
                        "blog_article": "Blog Article",
                        "newsletter": "Newsletter",
                        "press_release": "Press Release"
                    }
                },
                sorter: "string",
                formatter: function (cell) {
                    const value = cell.getValue();
                    const badges = {
                        "social_post": '<span class="badge bg-primary">Social Post</span>',
                        "blog_article": '<span class="badge bg-info">Blog Article</span>',
                        "newsletter": '<span class="badge bg-warning">Newsletter</span>',
                        "press_release": '<span class="badge bg-success">Press Release</span>'
                    };
                    return badges[value] || `<span class="badge bg-secondary">${value}</span>`;
                },
                width: 150
            },
            {
                title: "State",
                field: "state",
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All States",
                        "draft": "Draft",
                        "pending_approval": "Pending Approval",
                        "approved": "Approved",
                        "scheduled": "Scheduled",
                        "published": "Published",
                        "archived": "Archived"
                    }
                },
                sorter: "string",
                formatter: function (cell) {
                    const value = cell.getValue();
                    const badges = {
                        "draft": '<span class="badge bg-secondary">Draft</span>',
                        "pending_approval": '<span class="badge bg-warning">Pending Approval</span>',
                        "approved": '<span class="badge bg-success">Approved</span>',
                        "scheduled": '<span class="badge bg-info">Scheduled</span>',
                        "published": '<span class="badge bg-primary">Published</span>',
                        "archived": '<span class="badge bg-dark">Archived</span>'
                    };
                    return badges[value] || `<span class="badge bg-light">${value}</span>`;
                },
                width: 140
            },
            {
                title: "Priority",
                field: "priority",
                headerFilter: "list",
                headerFilterParams: {
                    values: {
                        "": "All Priorities",
                        "low": "Low",
                        "normal": "Normal",
                        "high": "High",
                        "urgent": "Urgent"
                    }
                },
                sorter: "string",
                formatter: function (cell) {
                    const value = cell.getValue();
                    const badges = {
                        "low": '<span class="badge bg-success">Low</span>',
                        "normal": '<span class="badge bg-info">Normal</span>',
                        "high": '<span class="badge bg-warning">High</span>',
                        "urgent": '<span class="badge bg-danger">Urgent</span>'
                    };
                    return badges[value] || `<span class="badge bg-secondary">${value}</span>`;
                },
                width: 100
            },
            {
                title: "Channels",
                field: "target_channels",
                headerFilter: "input",
                headerFilterPlaceholder: "Search channels...",
                formatter: function (cell) {
                    const channels = cell.getValue();
                    if (!channels || channels.length === 0) {
                        return '<span class="text-muted">No channels</span>';
                    }
                    const channelBadges = channels.map(channel =>
                        `<span class="badge bg-light text-dark me-1">${channel}</span>`
                    ).join('');
                    return channelBadges;
                },
                width: 200
            },
            {
                title: "Scheduled Date",
                field: "scheduled_date",
                sorter: "datetime",
                formatter: function (cell) {
                    const value = cell.getValue();
                    if (!value) return '<span class="text-muted">Not scheduled</span>';
                    return new Date(value).toLocaleString();
                },
                width: 150
            },
            {
                title: "Created",
                field: "created_at",
                sorter: "datetime",
                formatter: function (cell) {
                    const value = cell.getValue();
                    return value ? new Date(value).toLocaleDateString() : '';
                },
                width: 100
            },
            {
                title: "Actions",
                field: "actions",
                formatter: function (cell) {
                    const rowData = cell.getRow().getData();
                    let actions = `
                        <i class="ti ti-eye row-action-icon" title="View Details" onclick="viewContentItem(${rowData.id})"></i>
                        <i class="ti ti-edit row-action-icon" title="Edit" onclick="editContentItem(${rowData.id})"></i>
                    `;

                    // Conditional actions based on state
                    if (rowData.state === 'pending_approval') {
                        actions += `<i class="ti ti-check row-action-icon text-success" title="Approve" onclick="approveContentItem(${rowData.id})"></i>`;
                        actions += `<i class="ti ti-x row-action-icon text-danger" title="Reject" onclick="rejectContentItem(${rowData.id})"></i>`;
                    }

                    if (rowData.state === 'approved') {
                        actions += `<i class="ti ti-calendar row-action-icon text-primary" title="Schedule" onclick="scheduleContentItem(${rowData.id})"></i>`;
                    }

                    actions += `<i class="ti ti-trash row-action-icon text-danger" title="Delete" onclick="deleteContentItem(${rowData.id})"></i>`;

                    return actions;
                },
                headerSort: false,
                width: 180
            }
        ]
    });

    // Store in global registry
    window.contentBroadcasterTable = table;
    window.appTables["content-broadcaster-table"] = table;

    // Add cellEdited event listener
    addCellEditedHandler(table, '/features/business_automations/content-broadcaster', 'Content Item');

    // Bulk Edit Selected
    addBulkEditHandler(table, '/features/business_automations/content-broadcaster');

    // Bulk Delete Selected
    addBulkDeleteHandler(table, '/features/business_automations/content-broadcaster', 'Content Item');

    // Row action handlers
    bindRowActionHandlers("#content-broadcaster-table", {
        onEdit: "editContentItem",
        onDelete: "deleteContentItem"
    });

    return table;
};

// Export table function
window.exportTable = function (format) {
    return exportTabulatorTable('content-broadcaster-table', format, 'content-items');
};

// Action handlers
window.viewContentItem = function (id) {
    fetch(`/features/business_automations/content-broadcaster/api/${id}`)
        .then(response => response.json())
        .then(data => {
            const modalBody = document.getElementById('modal-body');
            modalBody.innerHTML = `
                <div class="modal-header">
                    <h5 class="modal-title">View Content Item: ${data.title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <strong>Title:</strong> ${data.title}
                        </div>
                        <div class="col-md-6">
                            <strong>Type:</strong>
                            <span class="badge bg-primary">${data.content_type}</span>
                        </div>
                        <div class="col-md-6 mt-2">
                            <strong>State:</strong>
                            <span class="badge bg-info">${data.state}</span>
                        </div>
                        <div class="col-md-6 mt-2">
                            <strong>Priority:</strong>
                            <span class="badge bg-warning">${data.priority}</span>
                        </div>
                        <div class="col-12 mt-3">
                            <strong>Description:</strong>
                            <p class="mt-1">${data.description || 'No description provided'}</p>
                        </div>
                        <div class="col-12 mt-2">
                            <strong>Content:</strong>
                            <div class="bg-light p-3 rounded mt-1" style="max-height: 200px; overflow-y: auto;">
                                ${data.content || 'No content provided'}
                            </div>
                        </div>
                        <div class="col-md-6 mt-3">
                            <strong>Target Channels:</strong>
                            <div class="mt-1">
                                ${(data.target_channels || []).map(channel =>
                `<span class="badge bg-light text-dark me-1">${channel}</span>`
            ).join('')}
                            </div>
                        </div>
                        <div class="col-md-6 mt-3">
                            <strong>Scheduled Date:</strong>
                            <p class="mt-1">${data.scheduled_date ? new Date(data.scheduled_date).toLocaleString() : 'Not scheduled'}</p>
                        </div>
                        <div class="col-md-6 mt-2">
                            <strong>Created:</strong>
                            <p class="mt-1">${new Date(data.created_at).toLocaleString()}</p>
                        </div>
                        <div class="col-md-6 mt-2">
                            <strong>Updated:</strong>
                            <p class="mt-1">${data.updated_at ? new Date(data.updated_at).toLocaleString() : 'Never'}</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            `;
            new bootstrap.Modal(document.getElementById('modal')).show();
        })
        .catch(error => {
            console.error('Error loading content item:', error);
            showToast('Error loading content item details', 'error');
        });
};

window.editContentItem = function (id) {
    editTabulatorRow(`/features/business_automations/content-broadcaster/${id}/edit`);
};

window.deleteContentItem = function (id) {
    deleteTabulatorRow(`/features/business_automations/content-broadcaster/${id}/delete`, '#content-broadcaster-table', {
        title: 'Delete Content Item',
        message: 'Are you sure you want to delete this content item? This action cannot be undone.',
        confirmText: 'Delete Item',
        cancelText: 'Cancel'
    });
};

window.approveContentItem = function (id) {
    fetch(`/features/business_automations/content-broadcaster/approve/${id}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('Content item approved successfully', 'success');
                window.contentBroadcasterTable.replaceData();
            } else {
                showToast('Failed to approve content item', 'error');
            }
        })
        .catch(error => {
            console.error('Error approving content item:', error);
            showToast('Error approving content item', 'error');
        });
};

window.rejectContentItem = function (id) {
    const reason = prompt('Please provide a reason for rejection:');
    if (reason) {
        fetch(`/features/business_automations/content-broadcaster/reject/${id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ reason: reason })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Content item rejected', 'success');
                    window.contentBroadcasterTable.replaceData();
                } else {
                    showToast('Failed to reject content item', 'error');
                }
            })
            .catch(error => {
                console.error('Error rejecting content item:', error);
                showToast('Error rejecting content item', 'error');
            });
    }
};

window.scheduleContentItem = function (id) {
    editTabulatorRow(`/features/business_automations/content-broadcaster/${id}/schedule`);
};

// Initialize table when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("content-broadcaster-table");

    if (tableElement && !window.contentBroadcasterTableInitialized) {
        window.contentBroadcasterTableInitialized = true;
        initializeContentBroadcasterTable();

        // Initialize quick search after table is ready
        setTimeout(() => {
            initializeQuickSearch('table-quick-search', 'clear-search-btn', 'content-broadcaster-table');
        }, 100);
    }
});
