/**
 * Companies Tabulator Table for Sales Outreach Prep
 */

window.initializeCompaniesTable = function () {
    // Make sure appTables exists
    if (!window.appTables) {
        window.appTables = {};
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
                const row = cell.getRow().getData();
                const website = row.website_url ? ` <a href="${row.website_url}" target="_blank" class="text-muted" title="Website"><i class="ti ti-external-link"></i></a>` : '';
                const linkedin = row.linkedin_url ? ` <a href="${row.linkedin_url}" target="_blank" class="text-muted" title="LinkedIn"><i class="ti ti-brand-linkedin"></i></a>` : '';
                return `<strong>${row.name}</strong>${website}${linkedin}`;
            }
        },
        {
            title: "Domain",
            field: "domain",
            widthGrow: 2,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter domains..."
        },
        {
            title: "Industry",
            field: "industry",
            widthGrow: 2,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter industry..."
        },
        {
            title: "Headquarters",
            field: "headquarters",
            widthGrow: 2,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter location..."
        },
        {
            title: "Size",
            field: "size",
            widthGrow: 1,
            headerFilter: "input",
            headerFilterPlaceholder: "Filter size..."
        },
        {
            title: "Actions",
            field: "actions",
            headerSort: false,
            headerFilter: false,
            widthGrow: 2,
            hozAlign: "right",
            formatter: function (cell) {
                const rowData = cell.getRow().getData();
                return `
                    <div class="btn-group btn-group-sm" role="group">
                        <button class="btn btn-outline-secondary" onclick="editCompany('${rowData.id}')" title="Edit">
                            <i class="ti ti-edit"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="deleteCompany('${rowData.id}')" title="Delete">
                            <i class="ti ti-trash"></i>
                        </button>
                    </div>
                `;
            }
        }
    ];

    // Initialize table with advancedTableConfig
    const table = new Tabulator('#companies-table', {
        ...advancedTableConfig,
        ajaxURL: '/features/business-automations/sales-outreach-prep/companies/api/list',
        columns: columns
    });

    // Store in global registry
    window.companiesTable = table;
    window.appTables["companies-table"] = table;

    return table;
};

/**
 * Edit company
 */
window.editCompany = function (companyId) {
    editTabulatorRow(`/features/business-automations/sales-outreach-prep/companies/partials/form?company_id=${companyId}`);
};

/**
 * Delete company
 */
window.deleteCompany = function (companyId) {
    deleteTabulatorRow(`/features/business-automations/sales-outreach-prep/companies/${companyId}`, '#companies-table', {
        title: 'Delete Company',
        message: 'Are you sure you want to delete this company? This will also delete all associated prospects.',
        confirmText: 'Delete Company',
        cancelText: 'Cancel'
    });
};

// Initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
    const tableElement = document.getElementById("companies-table");

    if (tableElement && !window.companiesTableInitialized) {
        window.companiesTableInitialized = true;
        initializeCompaniesTable();

        // Initialize quick search if available
        setTimeout(() => {
            if (typeof initializeQuickSearch === 'function') {
                initializeQuickSearch('table-quick-search', 'clear-search-btn', 'companies-table');
            }
        }, 100);
    }
});
