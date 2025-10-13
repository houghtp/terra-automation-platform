/**
 * Stats Card Web Component
 *
 * A reusable dashboard statistics card component with support for:
 * - Icons, titles, values, and descriptions
 * - Loading states and animations
 * - Color themes and customization
 * - Data fetching from URLs
 * - Auto-refresh capabilities
 *
 * Usage:
 * <stats-card
 *   title="Total Items"
 *   value="123"
 *   description="All items in system"
 *   icon="ti-database"
 *   color="green"
 *   data-url="/api/stats"
 *   data-key="total_items"
 *   auto-refresh="300000">
 * </stats-card>
 */

class StatsCard extends HTMLElement {
    constructor() {
        super();
        this.shadow = this.attachShadow({ mode: 'open' });
        this.refreshInterval = null;
    }

    static get observedAttributes() {
        return [
            'title', 'value', 'description', 'icon', 'color',
            'data-url', 'data-key', 'auto-refresh', 'loading'
        ];
    }

    connectedCallback() {
        this.render();
        this.setupDataFetching();
        this.setupAutoRefresh();
    }

    disconnectedCallback() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue) {
            this.render();
            if (name === 'auto-refresh') {
                this.setupAutoRefresh();
            }
        }
    }

    get title() { return this.getAttribute('title') || ''; }
    get value() { return this.getAttribute('value') || ''; }
    get description() { return this.getAttribute('description') || ''; }
    get icon() { return this.getAttribute('icon') || 'ti-info-circle'; }
    get color() { return this.getAttribute('color') || 'blue'; }
    get dataUrl() { return this.getAttribute('data-url') || ''; }
    get dataKey() { return this.getAttribute('data-key') || ''; }
    get autoRefresh() { return parseInt(this.getAttribute('auto-refresh')) || 0; }
    get isLoading() { return this.hasAttribute('loading'); }

    render() {
        const colorClass = `text-${this.color}`;
        const loadingClass = this.isLoading ? 'loading' : '';
        const displayValue = this.isLoading ? 'Loading stats...' : this.value;

        this.shadow.innerHTML = `
            <style>
                :host {
                    display: block;
                }

                .card {
                    background: white;
                    border: 1px solid #e6e7e9;
                    border-radius: 0.375rem;
                    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                    transition: all 0.2s ease;
                }

                .card:hover {
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                }

                .card-body {
                    padding: 1.5rem;
                }

                .d-flex {
                    display: flex;
                }

                .align-items-center {
                    align-items: center;
                }

                .ms-auto {
                    margin-left: auto;
                }

                .me-1 {
                    margin-right: 0.25rem;
                }

                .mb-2 {
                    margin-bottom: 0.5rem;
                }

                .mb-3 {
                    margin-bottom: 1rem;
                }

                .subheader {
                    font-size: 0.875rem;
                    font-weight: 500;
                    color: #6c757d;
                }

                .h1 {
                    font-size: 2.5rem;
                    font-weight: 700;
                    line-height: 1.2;
                    color: #1a202c;
                    margin: 0;
                }

                .description {
                    font-size: 0.875rem;
                    color: #6c757d;
                }

                .icon {
                    width: 1.5rem;
                    height: 1.5rem;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                }

                .text-blue { color: #0066cc; }
                .text-green { color: #28a745; }
                .text-red { color: #dc3545; }
                .text-orange { color: #fd7e14; }
                .text-purple { color: #6f42c1; }
                .text-primary { color: #0d6efd; }
                .text-gray { color: #6c757d; }

                .loading .h1 {
                    opacity: 0.7;
                    animation: pulse 1.5s ease-in-out infinite;
                }

                /* Loading overlay for stats cards - matches chart loader style */
                .loading .card-body {
                    position: relative;
                }

                .loading .card-body::before {
                    content: 'Loading stats...';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(255, 255, 255, 0.9);
                    backdrop-filter: blur(2px);
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-direction: column;
                    color: #6b7280;
                    font-size: 14px;
                    font-weight: 500;
                    border-radius: 0.375rem;
                }

                .loading .card-body::after {
                    content: '';
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    width: 40px;
                    height: 40px;
                    margin: -30px 0 0 -20px; /* Adjusted to center above text */
                    border: 3px solid #e5e7eb;
                    border-top: 3px solid #3b82f6;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    z-index: 1001;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                @keyframes pulse {
                    0%, 100% { opacity: 0.7; }
                    50% { opacity: 0.4; }
                }

                .lh-1 {
                    line-height: 1;
                }

                .d-inline-flex {
                    display: inline-flex;
                }
            </style>

            <div class="card ${loadingClass}">
                <div class="card-body">
                    <div class="d-flex align-items-center">
                        <div class="subheader">${this.title}</div>
                        <div class="ms-auto">
                            <span class="${colorClass} d-inline-flex align-items-center lh-1">
                                <i class="icon ${this.icon} me-1"></i>
                            </span>
                        </div>
                    </div>
                    <div class="h1 mb-3">${displayValue}</div>
                    <div class="d-flex mb-2">
                        <div class="description">${this.description}</div>
                    </div>
                </div>
            </div>
        `;
    }

    async setupDataFetching() {
        if (!this.dataUrl) return;

        try {
            console.log(`[stats-card:${this.id || 'unnamed'}] Loading data from:`, this.dataUrl);
            this.setAttribute('loading', '');
            const response = await fetch(this.dataUrl, {
                credentials: 'same-origin'  // Include cookies for authentication
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();

            let value = data;
            if (this.dataKey) {
                // Support nested keys like "stats.total_items"
                const keys = this.dataKey.split('.');
                for (const key of keys) {
                    value = value?.[key];
                }
            }

            // Format the value
            if (typeof value === 'number') {
                // Check if this is a percentage field (completion_rate, etc.)
                if (this.dataKey && (this.dataKey.includes('rate') || this.dataKey.includes('percentage'))) {
                    value = value + '%';
                } else {
                    value = value.toLocaleString();
                }
            }

            this.setAttribute('value', value || '0');
            this.removeAttribute('loading');
            console.log(`[stats-card:${this.id || 'unnamed'}] Data loaded successfully:`, value);

        } catch (error) {
            console.error(`[stats-card:${this.id || 'unnamed'}] Failed to fetch data:`, error);
            this.setAttribute('value', 'Error');
            this.removeAttribute('loading');
        }
    }

    setupAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }

        if (this.autoRefresh > 0 && this.dataUrl) {
            this.refreshInterval = setInterval(() => {
                this.setupDataFetching();
            }, this.autoRefresh);
        }
    }

    // Public method to manually refresh data
    refresh() {
        this.setupDataFetching();
    }

    // Public method to update value programmatically
    updateValue(newValue) {
        this.setAttribute('value', newValue);
    }

    // Public method to set loading state
    setLoading(loading = true) {
        if (loading) {
            this.setAttribute('loading', '');
        } else {
            this.removeAttribute('loading');
        }
    }
}

// Register the custom element
customElements.define('stats-card', StatsCard);

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StatsCard;
}

// Global utility functions for stats cards
window.StatsCardUtils = {
    // Refresh all stats cards on the page
    refreshAll() {
        const cards = document.querySelectorAll('stats-card[data-url]');
        cards.forEach(card => card.refresh());
    },

    // Update multiple cards with data object
    updateMultiple(dataMap) {
        Object.entries(dataMap).forEach(([selector, value]) => {
            const card = document.querySelector(selector);
            if (card) {
                card.updateValue(value);
            }
        });
    },

    // Set loading state for multiple cards
    setLoadingMultiple(selectors, loading = true) {
        selectors.forEach(selector => {
            const card = document.querySelector(selector);
            if (card) {
                card.setLoading(loading);
            }
        });
    }
};
