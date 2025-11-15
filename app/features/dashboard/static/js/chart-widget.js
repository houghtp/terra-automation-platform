/**
 * Chart Widget Web Component
 * A reusable ECharts web component for the FastAPI template
 *
 * Usage:
 * <chart-widget
 *   type="bar|line|pie|donut|area"
 *   title="Chart Title"
 *   data-url="/api/endpoint"
 *   height="400"
 *   description="Chart description">
 * </chart-widget>
 */

class ChartWidget extends HTMLElement {
    constructor() {
        super();
        this.chart = null;
        this.resizeObserver = null;
    }

    static get observedAttributes() {
        return ['type', 'title', 'data-url', 'height', 'description'];
    }

    connectedCallback() {
        this.render();
        this.setupResizeObserver();
        this.loadData();
    }

    disconnectedCallback() {
        if (this.chart) {
            this.chart.dispose();
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
    }

    attributeChangedCallback(name, oldValue, newValue) {
        if (oldValue !== newValue && this.isConnected) {
            if (name === 'data-url') {
                this.loadData();
            } else {
                this.render();
            }
        }
    }

    render() {
        const type = this.getAttribute('type') || 'bar';
        const title = this.getAttribute('title') || 'Chart';
        const height = this.getAttribute('height') || '400';
        const description = this.getAttribute('description') || '';

        this.innerHTML = `
            <div class="card chart-widget">
                <div class="card-header border-0 pb-0">
                    <div class="d-flex align-items-start gap-3">
                        <div class="flex-grow-1">
                            <h3 class="card-title mb-1">${title}</h3>
                            ${description ? `<div class="text-secondary">${description}</div>` : ''}
                        </div>
                        <div class="chart-header-toolbar d-flex align-items-center">
                            <button class="btn btn-icon btn-outline-secondary chart-refresh" title="Refresh">
                                <i class="ti ti-refresh"></i>
                            </button>
                            <div class="dropdown">
                                <button class="btn btn-icon btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                    <i class="ti ti-dots"></i>
                                </button>
                                <ul class="dropdown-menu dropdown-menu-end">
                                    <li><a class="dropdown-item chart-export" href="#" data-format="png">
                                        <i class="ti ti-photo me-2"></i>Export as PNG</a></li>
                                    <li><a class="dropdown-item chart-export" href="#" data-format="svg">
                                        <i class="ti ti-vector me-2"></i>Export as SVG</a></li>
                                    <li><a class="dropdown-item chart-fullscreen" href="#">
                                        <i class="ti ti-maximize me-2"></i>Fullscreen</a></li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="card-body">
                    <div class="chart-container" id="${this.id}-container" style="width: 100%; height: ${height}px;">
                    </div>
                </div>
            </div>
        `;

        this.setupEventListeners();
    }

    setupEventListeners() {
        // Refresh button
        const refreshBtn = this.querySelector('.chart-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        // Export buttons
        const exportBtns = this.querySelectorAll('.chart-export');
        exportBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const format = btn.getAttribute('data-format');
                this.exportChart(format);
            });
        });

        // Fullscreen button
        const fullscreenBtn = this.querySelector('.chart-fullscreen');
        if (fullscreenBtn) {
            fullscreenBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleFullscreen();
            });
        }
    }

    setupResizeObserver() {
        if (!window.ResizeObserver) return;

        this.resizeObserver = new ResizeObserver(() => {
            if (this.chart) {
                this.chart.resize();
            }
        });

        const container = this.querySelector('.chart-container');
        if (container) {
            this.resizeObserver.observe(container);
        }
    }

    async loadData() {
        const dataUrl = this.getAttribute('data-url');
        if (!dataUrl) {
            this.showError('No data URL provided');
            return;
        }

        try {
            this.showLoading();

            const response = await fetch(dataUrl, {
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json'
                }
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.renderChart(data);
        } catch (error) {
            console.error('Chart data loading failed:', error);
            this.showError(`Failed to load chart data: ${error.message}`);
        }
    }

    renderChart(data) {
        const container = this.querySelector('.chart-container');
        if (!container) return;

        // Check if data is empty
        if (this.isDataEmpty(data)) {
            this.showNoData();
            return;
        }

        // Dispose existing chart
        if (this.chart) {
            this.chart.dispose();
        }

        // Initialize new chart
        this.chart = echarts.init(container);

        const type = this.getAttribute('type') || 'bar';
        const options = this.getChartOptions(type, data);

        this.chart.setOption(options);
        this.hideLoading();
    }

    getChartOptions(type, data) {
        const baseOptions = {
            backgroundColor: 'transparent',
            textStyle: {
                fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
            },
            tooltip: {
                trigger: 'axis',
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                borderColor: '#e5e7eb',
                textStyle: { color: '#374151' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            }
        };

        switch (type) {
            case 'bar':
                return {
                    ...baseOptions,
                    xAxis: {
                        type: 'category',
                        data: data.categories || [],
                        axisLine: { lineStyle: { color: '#e5e7eb' } },
                        axisTick: { lineStyle: { color: '#e5e7eb' } },
                        axisLabel: { color: '#6b7280' }
                    },
                    yAxis: {
                        type: 'value',
                        axisLine: { lineStyle: { color: '#e5e7eb' } },
                        axisTick: { lineStyle: { color: '#e5e7eb' } },
                        axisLabel: { color: '#6b7280' },
                        splitLine: { lineStyle: { color: '#f3f4f6' } }
                    },
                    series: [{
                        data: data.values || [],
                        type: 'bar',
                        itemStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: '#3b82f6' },
                                { offset: 1, color: '#1d4ed8' }
                            ])
                        },
                        emphasis: {
                            itemStyle: { color: '#2563eb' }
                        }
                    }]
                };

            case 'line':
                // Support both single-series (data.values) and multi-series (data.series)
                let series = [];

                if (data.series && Array.isArray(data.series)) {
                    // Multi-series line chart
                    const colors = [
                        '#3b82f6', '#ef4444', '#10b981', '#f59e0b',
                        '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
                    ];

                    series = data.series.map((seriesItem, index) => ({
                        name: seriesItem.name,
                        data: seriesItem.data,
                        type: 'line',
                        smooth: true,
                        lineStyle: {
                            color: colors[index % colors.length],
                            width: 2
                        },
                        itemStyle: {
                            color: colors[index % colors.length]
                        },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: `${colors[index % colors.length]}30` },
                                { offset: 1, color: `${colors[index % colors.length]}05` }
                            ])
                        }
                    }));
                } else {
                    // Single-series line chart (backward compatibility)
                    series = [{
                        data: data.values || [],
                        type: 'line',
                        smooth: true,
                        lineStyle: { color: '#3b82f6', width: 3 },
                        itemStyle: { color: '#3b82f6' },
                        areaStyle: {
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
                                { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
                            ])
                        }
                    }];
                }

                const lineOptions = {
                    ...baseOptions,
                    xAxis: {
                        type: 'category',
                        data: data.categories || [],
                        axisLine: { lineStyle: { color: '#e5e7eb' } },
                        axisLabel: { color: '#6b7280' }
                    },
                    yAxis: {
                        type: 'value',
                        axisLine: { lineStyle: { color: '#e5e7eb' } },
                        axisLabel: { color: '#6b7280' },
                        splitLine: { lineStyle: { color: '#f3f4f6' } }
                    },
                    series: series
                };

                // Add legend for multi-series charts
                if (data.series && data.series.length > 1) {
                    lineOptions.legend = {
                        bottom: '5%',
                        left: 'center',
                        textStyle: { color: '#6b7280' }
                    };
                }

                return lineOptions;

            case 'pie':
            case 'donut':
                return {
                    ...baseOptions,
                    tooltip: { trigger: 'item' },
                    legend: {
                        bottom: '5%',
                        left: 'center',
                        textStyle: { color: '#6b7280' }
                    },
                    series: [{
                        type: 'pie',
                        radius: type === 'donut' ? ['40%', '70%'] : '70%',
                        center: ['50%', '45%'],
                        data: data.items || [],
                        emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowOffsetX: 0,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                        },
                        label: {
                            show: type !== 'donut',
                            color: '#374151'
                        }
                    }]
                };

            default:
                return baseOptions;
        }
    }

    showLoading() {
        const card = this.querySelector('.chart-widget');
        if (!card) return;

        let overlay = card.querySelector('.chart-widget-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'chart-widget-overlay';
            overlay.innerHTML = `
                <div class="spinner-border text-primary" role="status" aria-hidden="true"></div>
                <span class="text-secondary fw-semibold">Loading</span>
            `;
            card.appendChild(overlay);
        }
    }

    hideLoading() {
        const overlay = this.querySelector('.chart-widget-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    showError(message) {
        const containerId = `${this.id}-container`;
        if (window.showUnifiedError) {
            window.showUnifiedError(containerId, message, () => this.loadData(), 'chart');
        } else {
            // Fallback error display
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #dc2626;">
                        <i class="ti ti-alert-circle" style="font-size: 2rem; margin-bottom: 0.5rem;"></i>
                        <div>${message}</div>
                        <button class="btn btn-sm btn-outline-secondary mt-2" onclick="this.closest('chart-widget').loadData()">
                            <i class="ti ti-refresh"></i> Retry
                        </button>
                    </div>
                `;
            }
        }
    }

    isDataEmpty(data) {
        if (!data) return true;

        // Check different data structures
        if (data.series && Array.isArray(data.series)) {
            return data.series.length === 0 || data.series.every(series =>
                !series.data || series.data.length === 0
            );
        }

        if (data.values && Array.isArray(data.values)) {
            return data.values.length === 0;
        }

        if (data.categories && Array.isArray(data.categories)) {
            return data.categories.length === 0;
        }

        // For timeline data (audit charts)
        if (Array.isArray(data)) {
            return data.length === 0;
        }

        return false;
    }

    showNoData() {
        const container = this.querySelector('.chart-container');
        if (container) {
            container.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #6b7280;">
                    <i class="ti ti-chart-bar" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                    <div style="font-size: 1.1rem; font-weight: 500; margin-bottom: 0.5rem;">No Data Available</div>
                    <div style="font-size: 0.9rem; opacity: 0.7;">There is no data to display for the selected time period.</div>
                    <button class="btn btn-sm btn-outline-secondary mt-3" onclick="this.closest('chart-widget').loadData()">
                        <i class="ti ti-refresh"></i> Refresh
                    </button>
                </div>
            `;
        }
        this.hideLoading();
    }

    exportChart(format) {
        if (!this.chart) return;

        const url = this.chart.getDataURL({
            type: format,
            backgroundColor: '#fff'
        });

        const link = document.createElement('a');
        link.download = `chart.${format}`;
        link.href = url;
        link.click();
    }

    toggleFullscreen() {
        const container = this.querySelector('.chart-widget');
        if (!container) return;

        if (container.classList.contains('chart-widget-fullscreen')) {
            container.classList.remove('chart-widget-fullscreen');
            document.body.classList.remove('chart-fullscreen-active');
        } else {
            container.classList.add('chart-widget-fullscreen');
            document.body.classList.add('chart-fullscreen-active');
        }

        // Resize chart after fullscreen toggle
        setTimeout(() => {
            if (this.chart) {
                this.chart.resize();
            }
        }, 300);
    }
}

// Register the web component
customElements.define('chart-widget', ChartWidget);

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ChartWidget;
}
