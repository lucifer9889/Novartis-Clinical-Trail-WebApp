/**
 * Main JavaScript for Clinical Trial Control Tower
 * Handles global functionality, navigation, and utilities
 */

// Global application state
const CTCT = {
    currentStudy: null,
    currentUser: null,
    filters: {},

    /**
     * Initialize the application
     */
    init: function() {
        console.log('Initializing Clinical Trial Control Tower...');

        // Set up event listeners
        this.setupEventListeners();

        // Load initial data (mock for now)
        this.loadInitialData();

        console.log('CTCT initialized successfully');
    },

    /**
     * Set up global event listeners
     */
    setupEventListeners: function() {
        // Tab change events — trigger chart resize on switch
        document.querySelectorAll('[data-bs-toggle="tab"]').forEach(tab => {
            tab.addEventListener('shown.bs.tab', function(event) {
                const tabId = event.target.getAttribute('data-bs-target');
                console.log('Tab changed to:', tabId);
                window.dispatchEvent(new Event('resize'));
            });
        });

        // Window resize handler
        window.addEventListener('resize', this.handleResize.bind(this));
    },

    /**
     * Load initial mock data (replaced by API calls in Phase 4)
     */
    loadInitialData: function() {
        this.currentStudy = {
            study_id: 'NVS-OBE-203',
            study_name: 'Clinical Trial Study NVS-OBE-203',
            phase: 'Phase 3',
            region: 'APAC',
            country: 'India',
            sites: 'All',
            status: 'Active'
        };

        this.currentUser = {
            username: 'cra_user',
            role: 'CRA',
            name: 'John Doe'
        };

        console.log('Study loaded:', this.currentStudy.study_id);
    },

    /**
     * Handle window resize for responsive adjustments
     */
    handleResize: function() {
        // Could resize charts, toggle sidebar visibility, etc.
    },

    /* -----------------------------------------------
       UTILITY FUNCTIONS
       ----------------------------------------------- */

    /**
     * Format number with commas  (1234 → "1,234")
     */
    formatNumber: function(num) {
        if (num === null || num === undefined) return '—';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },

    /**
     * Format date string → "Jan 15, 2026"
     */
    formatDate: function(dateString) {
        if (!dateString) return '—';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    },

    /**
     * Calculate percentage with 1 decimal place
     */
    calculatePercentage: function(value, total) {
        if (!total || total === 0) return '0.0';
        return ((value / total) * 100).toFixed(1);
    },

    /**
     * Return Bootstrap / custom CSS class for a status string
     */
    getStatusClass: function(status) {
        const map = {
            'completed':    'status-dot green',
            'clean':        'status-dot green',
            'in-progress':  'status-dot blue',
            'pending':      'status-dot yellow',
            'open':         'status-dot yellow',
            'blocked':      'status-dot red',
            'not-clean':    'status-dot red',
            'closed':       'status-dot green',
            'critical':     'status-dot red',
            'high':         'status-dot orange',
            'medium':       'status-dot yellow',
            'low':          'status-dot green'
        };
        return map[(status || '').toLowerCase()] || 'status-dot gray';
    },

    /**
     * Show spinner inside a container
     */
    showLoading: function(containerId) {
        var el = document.getElementById(containerId);
        if (el) {
            el.innerHTML =
                '<div class="text-center py-5">' +
                '  <div class="spinner-border text-primary" role="status">' +
                '    <span class="visually-hidden">Loading...</span>' +
                '  </div>' +
                '  <p class="mt-2 text-muted">Loading data...</p>' +
                '</div>';
        }
    },

    /**
     * Show an error alert inside a container
     */
    showError: function(containerId, message) {
        var el = document.getElementById(containerId);
        if (el) {
            el.innerHTML =
                '<div class="alert alert-danger" role="alert">' +
                '  <i class="fas fa-exclamation-triangle me-2"></i>' +
                '  <strong>Error:</strong> ' + message +
                '</div>';
        }
    },

    /**
     * Export an HTML table to CSV and download it
     */
    exportTableToCSV: function(tableId, filename) {
        var table = document.getElementById(tableId);
        if (!table) { console.error('Table not found:', tableId); return; }

        var csv = [];
        var rows = table.querySelectorAll('tr');

        rows.forEach(function(row) {
            var cols = row.querySelectorAll('td, th');
            var rowData = [];
            cols.forEach(function(col) {
                rowData.push('"' + col.innerText.replace(/"/g, '""') + '"');
            });
            csv.push(rowData.join(','));
        });

        this.downloadCSV(csv.join('\n'), filename);
    },

    /**
     * Trigger browser download for CSV string
     */
    downloadCSV: function(csv, filename) {
        var blob = new Blob([csv], { type: 'text/csv' });
        var link = document.createElement('a');
        link.download = filename;
        link.href = window.URL.createObjectURL(blob);
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
};

// Boot on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    CTCT.init();
});

// Expose globally
window.CTCT = CTCT;
