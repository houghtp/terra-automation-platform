/**
 * Campaigns Tabulator Table for Sales Outreach Prep
 * Follows CSPM pattern for real-time status updates via EventSource
 */

window.initializeCampaignsTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
    }

    // Track EventSource streams for AI research campaigns
    const campaignStreams = {};

    // Helper: Get stream URL for campaign
    function getStreamUrl(campaignId) {
        return `/features/business-automations/sales-outreach-prep/campaigns/stream/${campaignId}`;
    }

    // Helper: Close specific stream
    function closeStream(campaignId) {
        const stream = campaignStreams[campaignId];
        if (!stream) return;

        try {
            stream.close();
            console.log("[EventSource] Closed stream for campaign:", campaignId);
        } catch (error) {
            console.warn("[EventSource] Error closing stream", campaignId, error);
        }

        delete campaignStreams[campaignId];
    }

    // Helper: Close all streams
    function closeAllStreams() {
        Object.keys(campaignStreams).forEach((campaignId) => {
            closeStream(campaignId);
        });
    }

    // Helper: Apply row update from EventSource
    function applyRowUpdate(campaignId, update) {
        const table = window.campaignsTable;
        if (!table) {
            console.warn("[applyRowUpdate] Table not found");
            return;
        }

        const row = table.getRow(campaignId);
        if (!row) {
            console.warn("[applyRowUpdate] Row not found for campaign:", campaignId);
            return;
        }

        try {
            console.log("[applyRowUpdate] Updating row", campaignId, "with data:", update);
            row.update(update);
        } catch (error) {
            console.error("[applyRowUpdate] Failed to update campaign row", campaignId, error);
        }
    }

    // Helper: Open EventSource stream for campaign
    function openStream(campaignId) {
        if (campaignStreams[campaignId]) {
            console.log("🔄 [EventSource] Already connected to campaign:", campaignId);
            return;
        }

        try {
            const streamUrl = getStreamUrl(campaignId);
            console.log("🚀 [EventSource] Opening stream for campaign:", campaignId);
            console.log("📡 [EventSource] Stream URL:", streamUrl);

            const eventSource = new EventSource(streamUrl);

            eventSource.addEventListener('progress', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log("[EventSource] Progress update for campaign:", campaignId, data);

                    // Update row with new data (formatter will re-render automatically)
                    applyRowUpdate(campaignId, data);
                } catch (error) {
                    console.error("[EventSource] Failed to parse progress event:", error);
                }
            });

            eventSource.addEventListener('complete', (event) => {
                console.log("[EventSource] Research completed for campaign:", campaignId);
                closeStream(campaignId);

                // Refresh table to show sparkles icon
                const table = window.campaignsTable;
                if (table) {
                    table.replaceData();
                }
            });

            eventSource.onerror = (error) => {
                console.error("[EventSource] Error for campaign", campaignId, ":", error);
                closeStream(campaignId);
            };

            campaignStreams[campaignId] = eventSource;
            console.log("[EventSource] Connected successfully for campaign:", campaignId);
        } catch (error) {
            console.error("[EventSource] Failed to open stream", campaignId, error);
        }
    }

    // Helper: Refresh active streams based on table data
    function refreshActiveStreams(data) {
        console.log("🔍 [refreshActiveStreams] Processing", data?.length || 0, "campaigns");

        // Open EventSource streams for AI research campaigns without research_data (running)
        (data || []).forEach((item) => {
            console.log("🔍 Campaign:", item.id, "| Type:", item.discovery_type, "| Has research_data:", !!item.research_data);

            if (item.discovery_type === 'ai_research' && !item.research_data) {
                console.log("✅ Opening stream for AI research campaign:", item.id);
                openStream(item.id);
            } else if (item.research_data) {
                // Close stream for completed research
                if (campaignStreams[item.id]) {
                    console.log(`✅ [EventSource] Closing stream for completed campaign:`, item.id);
                    closeStream(item.id);
                }
            }
        });
    }

    // Build columns array
    const columns = [
        {
            title: "Name",
            field: "name",
            widthGrow: 3,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter names...",
            sorter: "string",
            formatter: function (cell) {
                const value = cell.getValue();
                return `<strong>${value}</strong>`;
            }
        },
        {
            title: "Status",
            field: "status",
            widthGrow: 2,
            headerFilter: "list",
            headerFilterParams: {
                values: {
                    "": "All Statuses",
                    "draft": "Draft",
                    "active": "Active",
                    "paused": "Paused",
                    "completed": "Completed",
                    "archived": "Archived"
                }
            },
            sorter: "string",
            formatter: function(cell) {
                const rowData = cell.getRow().getData();
                // Show "Researching..." badge for AI research campaigns with status="draft" (researching in progress)
                if (rowData.discovery_type === 'ai_research' && rowData.status === 'draft') {
                    return '<span class="app-badge app-badge-info"><i class="ti ti-loader icon-spin me-1"></i>Researching...</span>';
                }
                return formatStatusBadge(cell);  // Pass cell object, not value
            }
        },
        {
            title: "Industry",
            field: "target_industry",
            widthGrow: 2,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter industry..."
        },
        {
            title: "Geography",
            field: "target_geography",
            widthGrow: 2,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter geography..."
        },
        {
            title: "Prospects",
            field: "total_prospects",
            widthGrow: 1,
            headerFilter: false,
            sorter: "number",
            formatter: function (cell) {
                const row = cell.getRow().getData();
                const total = row.total_prospects || 0;
                const enriched = row.enriched_prospects || 0;
                return `<span class="text-muted">${enriched}</span> / <strong>${total}</strong>`;
            }
        },
        {
            title: "Created",
            field: "created_at",
            widthGrow: 2,
            headerFilter: false,
            sorter: "date",
            formatter: formatDate
        },
        {
            title: "Actions",
            field: "actions",
            headerSort: false,
            headerFilter: false,
            width: 150,
            formatter: function (cell) {
                const rowData = cell.getRow().getData();

                // Add custom research action for AI research campaigns
                let researchIcon = '';
                if (rowData.discovery_type === 'ai_research') {
                    if (rowData.research_data) {
                        // Show "View Research" icon if research is complete
                        researchIcon = `
                            <i class="ti ti-sparkles row-action-icon research-btn"
                               title="View AI Research Results"
                               style="cursor: pointer; font-size: 18px; color: #0054a6; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;">
                            </i>
                        `;
                    } else {
                        // Show "Start Research" icon if research not started
                        researchIcon = `
                            <i class="ti ti-play row-action-icon start-research-btn"
                               hx-post="/features/business-automations/sales-outreach-prep/campaigns/${rowData.id}/start-research"
                               hx-trigger="click"
                               hx-swap="none"
                               title="Start AI Research"
                               style="cursor: pointer; font-size: 18px; color: #2fb344; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;">
                            </i>
                        `;
                    }
                }

                // Add prospects view icon
                const prospectsIcon = `
                    <i class="ti ti-users row-action-icon prospects-btn"
                       title="View Prospects"
                       style="cursor: pointer; font-size: 18px; color: #0054a6; margin-right: 12px; padding: 4px; border-radius: 4px; transition: all 0.2s;">
                    </i>
                `;

                // Use standard CRUD buttons
                const crudButtons = createRowCrudButtons(rowData, {
                    onEdit: "editCampaign",
                    onDelete: "deleteCampaign"
                });

                return `
                    <div style="display: flex; align-items: center;">
                        ${researchIcon}
                        ${prospectsIcon}
                        ${crudButtons}
                    </div>
                `;
            }
        }
    ];

    // Initialize table with advancedTableConfig
    const table = new Tabulator('#campaigns-table', {
        ...advancedTableConfig,
        ajaxURL: '/features/business-automations/sales-outreach-prep/campaigns/api/list',
        columns: columns,
        // Return data array directly (Tabulator handles pagination via last_page in response)
        ajaxResponse: function(url, params, response) {
            // Store last_page for pagination (Tabulator will read it from response)
            this.lastPage = response.last_page;
            // Return just the data array
            return response.data;
        }
    });

    // Store in global registry
    window.campaignsTable = table;
    window.appTables["campaigns-table"] = table;

    // Listen for data loaded - open streams for active AI research
    table.on("dataLoaded", function (data) {
        refreshActiveStreams(data);
    });

    // Listen for row updates - open/close streams based on research status
    table.on("rowUpdated", function (row) {
        const data = row?.getData?.();
        if (!data) return;

        if (data.discovery_type === 'ai_research' && !data.research_data) {
            openStream(data.id);
        } else {
            closeStream(data.id);
        }
    });

    // Close all streams on page unload
    window.addEventListener("beforeunload", closeAllStreams);

    // Row action handlers for edit and delete (standard pattern from users table)
    bindRowActionHandlers("#campaigns-table", {
        onEdit: "editCampaign",
        onDelete: "deleteCampaign"
    });

    // Event delegation for custom action icons
    document.addEventListener('click', function(e) {
        // View Research Results
        if (e.target.classList.contains('research-btn')) {
            const rowEl = e.target.closest('.tabulator-row');
            if (rowEl) {
                const row = table.getRow(rowEl);
                const data = row.getData();
                viewResearchResults(data.id);
            }
        }

        // View Prospects
        if (e.target.classList.contains('prospects-btn')) {
            const rowEl = e.target.closest('.tabulator-row');
            if (rowEl) {
                const row = table.getRow(rowEl);
                const data = row.getData();
                viewProspects(data.id);
            }
        }
    });

    return table;
};

/**
 * View AI research results for a campaign
 */
window.viewResearchResults = function (campaignId) {
    editTabulatorRow(`/features/business-automations/sales-outreach-prep/campaigns/partials/research_results?campaign_id=${campaignId}`);
};

/**
 * View prospects for a campaign
 */
window.viewProspects = function (campaignId) {
    window.location.href = `/features/business-automations/sales-outreach-prep/prospects?campaign_id=${campaignId}`;
};

/**
 * Edit campaign (standard pattern from users slice)
 */
window.editCampaign = function (campaignId) {
    editTabulatorRow(`/features/business-automations/sales-outreach-prep/campaigns/${campaignId}/edit`);
};

/**
 * Delete campaign
 */
window.deleteCampaign = function (campaignId) {
    deleteTabulatorRow(`/features/business-automations/sales-outreach-prep/campaigns/${campaignId}`, '#campaigns-table', {
        title: 'Delete Campaign',
        message: 'Are you sure you want to delete this campaign? This will also delete all associated prospects.',
        confirmText: 'Delete Campaign',
        cancelText: 'Cancel'
    });
};

// Initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("campaigns-table");

    if (tableElement && !window.campaignsTableInitialized) {
        window.campaignsTableInitialized = true;
        initializeCampaignsTable();

        // Initialize quick search if available
        setTimeout(() => {
            if (typeof initializeQuickSearch === 'function') {
                initializeQuickSearch('table-quick-search', 'clear-search-btn', 'campaigns-table');
            }
        }, 100);
    }
});

// Listen for campaign form submission - auto-open stream for AI research campaigns
// Following CSPM pattern for immediate feedback after form submission
document.body.addEventListener("htmx:afterRequest", function(event) {
    // Only handle campaign-form submissions
    if (event.target.id === "campaign-form" && event.detail.successful) {
        console.log("🎯 [Campaign Form] Form submitted successfully");

        // After modal closes and table refreshes, table dataLoaded event will open streams
        // This ensures the newly created campaign is visible in the table first
        setTimeout(() => {
            if (window.campaignsTable) {
                window.campaignsTable.replaceData();
            }
        }, 500);
    }
});
