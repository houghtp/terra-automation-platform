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
        this.refreshInterval = null;
    }

    static get observedAttributes() {
        return [
            'title', 'value', 'description', 'icon', 'color',
            'data-url', 'data-key', 'auto-refresh', 'loading'
        ];
    }

    connectedCallback() {
        StatsCard.ensureStyles();
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
        const loadingClass = this.isLoading ? 'card-loading' : '';
        const displayValue = this.isLoading ? 'Loading…' : (this.value || '0');

        this.innerHTML = `
            <div class="card ${loadingClass}">
                <div class="card-body d-flex flex-column gap-2">
                    <div class="d-flex align-items-start">
                        <div>
                            <div class="text-secondary text-uppercase fs-6 fw-semibold">${this.title}</div>
                            <div class="fs-2 fw-bold text-body">${displayValue}</div>
                            ${this.description ? `<div class="text-secondary">${this.description}</div>` : ''}
                        </div>
                        <div class="ms-auto lh-1 text-2xl ${colorClass}">
                            <i class="${this.icon}"></i>
                        </div>
                    </div>
                </div>
                ${this.isLoading ? StatsCard.loadingTemplate() : ''}
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

StatsCard.ensureStyles = function () {
    if (document.getElementById('stats-card-styles')) {
        return;
    }

    const style = document.createElement('style');
    style.id = 'stats-card-styles';
    style.textContent = `
        stats-card {
            display: block;
        }

        stats-card .card {
            position: relative;
        }

        stats-card .card-loading .card-body {
            opacity: 0.35;
            transition: opacity 0.2s ease;
        }

        stats-card .card-overlay {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.75rem;
            background-color: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(2px);
            z-index: 5;
        }
    `;

    document.head.appendChild(style);
};

StatsCard.loadingTemplate = function () {
    return `
        <div class="card-overlay">
            <div class="spinner-border text-primary" role="status" aria-hidden="true"></div>
            <span class="text-secondary fw-semibold">Loading</span>
        </div>
    `;
};

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
