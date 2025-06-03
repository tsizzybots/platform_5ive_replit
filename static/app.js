// Global variables
let currentPage = 1;
let currentFilters = {};
let dailyChart = null;
let currentChartType = 'bar';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    setDateRange('thisMonth'); // Set default date range to "This Month"
    loadStats();
    loadTickets();
    loadInquiryTypes();
    
    // Auto-dismiss success alerts after 2 seconds
    const successAlerts = document.querySelectorAll('.alert-success');
    successAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 2000);
    });
    
    // Setup chart collapse event listeners
    const chartCollapse = document.getElementById('dailyStatsChart');
    chartCollapse.addEventListener('shown.bs.collapse', function () {
        document.getElementById('chartToggleIcon').className = 'fas fa-chevron-up ms-2';
        document.getElementById('chartControls').style.display = 'block';
        loadDailyStats();
    });
    
    chartCollapse.addEventListener('hidden.bs.collapse', function () {
        document.getElementById('chartToggleIcon').className = 'fas fa-chevron-down ms-2';
        document.getElementById('chartControls').style.display = 'none';
    });
});

// Theme toggle functionality
function toggleTheme() {
    const html = document.documentElement;
    const themeIcon = document.getElementById('themeIcon');
    const currentTheme = html.getAttribute('data-bs-theme');
    
    if (currentTheme === 'dark') {
        html.setAttribute('data-bs-theme', 'light');
        themeIcon.className = 'fas fa-moon';
    } else {
        html.setAttribute('data-bs-theme', 'dark');
        themeIcon.className = 'fas fa-sun';
    }
    
    // Re-render chart with new theme colors if chart exists
    if (dailyChart && dailyChart.data.datasets.length > 0) {
        const chartData = dailyChart.data.datasets[0].data.map((_, index) => {
            return {
                date: dailyChart.data.labels[index],
                total: dailyChart.data.datasets[0].data[index] || 0,
                engaged: dailyChart.data.datasets[1].data[index] || 0,
                escalated: dailyChart.data.datasets[2].data[index] || 0,
                skipped: dailyChart.data.datasets[3].data[index] || 0
            };
        });
        renderChart(chartData);
    }
}



// API helper function
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();
        console.log(`API Response (${response.status}):`, data);

        return { data, status: response.status, ok: response.ok };
    } catch (error) {
        console.error('API Error:', error);
        const errorData = { status: 'error', message: error.message };
        return { data: errorData, status: 500, ok: false };
    }
}

// Load inquiry types and populate dropdown
async function loadInquiryTypes() {
    const result = await apiRequest('/api/inquiries/types');
    
    if (result.ok) {
        const dropdown = document.getElementById('inquiryTypeFilter');
        // Clear existing options except "All Types"
        dropdown.innerHTML = '<option value="">All Types</option>';
        
        // Add each inquiry type as an option
        result.data.data.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            dropdown.appendChild(option);
        });
    } else {
        console.error('Failed to load inquiry types:', result.data.message);
    }
}

// Load statistics with optional date filtering
async function loadStats(dateFilters = {}) {
    const params = new URLSearchParams(dateFilters);
    const url = '/api/inquiries/stats' + (params.toString() ? '?' + params.toString() : '');
    const result = await apiRequest(url);
    
    if (result.ok) {
        displayStats(result.data.data);
    } else {
        document.getElementById('statsContainer').innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load statistics: ${result.data.message}
                </div>
            </div>
        `;
    }
}

// Display statistics as cards
function displayStats(stats) {
    const container = document.getElementById('statsContainer');
    const escalatedCount = stats.escalated_inquiries || 0;
    const skippedCount = stats.total_inquiries - stats.engaged_inquiries - escalatedCount;
    
    container.innerHTML = `
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card stats-card bg-primary text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.total_inquiries}</h3>
                    <p class="card-text mb-0">Total Tickets</p>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card stats-card bg-success text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.engaged_inquiries}</h3>
                    <p class="card-text mb-0">Engaged</p>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card stats-card bg-warning text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${escalatedCount}</h3>
                    <p class="card-text mb-0">Escalated</p>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card stats-card bg-secondary text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${skippedCount}</h3>
                    <p class="card-text mb-0">Skipped</p>
                </div>
            </div>
        </div>
    `;
}



// Date range functionality
function setDateRange(preset) {
    const dateFrom = document.getElementById('dateFrom');
    const dateTo = document.getElementById('dateTo');
    const dropdown = document.getElementById('dateRangeDropdown');
    
    const today = new Date();
    const todayStr = today.toISOString().split('T')[0];
    
    switch (preset) {
        case 'today':
            dateFrom.value = todayStr;
            dateTo.value = todayStr;
            break;
        case 'yesterday':
            const yesterday = new Date(today);
            yesterday.setDate(today.getDate() - 1);
            const yesterdayStr = yesterday.toISOString().split('T')[0];
            dateFrom.value = yesterdayStr;
            dateTo.value = yesterdayStr;
            break;
        case 'thisWeek':
            const startOfThisWeek = new Date(today);
            // Calculate Monday as start of week (0=Sunday, 1=Monday, etc.)
            const dayOfWeek = today.getDay();
            const daysFromMonday = (dayOfWeek === 0) ? 6 : dayOfWeek - 1; // Sunday = 6 days from Monday
            startOfThisWeek.setDate(today.getDate() - daysFromMonday);
            dateFrom.value = startOfThisWeek.toISOString().split('T')[0];
            dateTo.value = todayStr;
            break;
        case 'lastWeek':
            const startOfLastWeek = new Date(today);
            const currentDayOfWeek = today.getDay();
            const daysFromLastMonday = (currentDayOfWeek === 0) ? 6 : currentDayOfWeek - 1;
            // Go back to last Monday (7 days + days from current Monday)
            startOfLastWeek.setDate(today.getDate() - daysFromLastMonday - 7);
            const endOfLastWeek = new Date(startOfLastWeek);
            endOfLastWeek.setDate(startOfLastWeek.getDate() + 6); // Sunday
            dateFrom.value = startOfLastWeek.toISOString().split('T')[0];
            dateTo.value = endOfLastWeek.toISOString().split('T')[0];
            break;
        case 'thisMonth':
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            dateFrom.value = startOfMonth.toISOString().split('T')[0];
            dateTo.value = todayStr;
            break;
        case 'lastMonth':
            const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
            dateFrom.value = lastMonthStart.toISOString().split('T')[0];
            dateTo.value = lastMonthEnd.toISOString().split('T')[0];
            break;
    }
    applyFilters();
}

function clearDateRange() {
    document.getElementById('dateFrom').value = '';
    document.getElementById('dateTo').value = '';
    applyFilters();
}

// Refresh data with loading state
function refreshData() {
    const refreshBtn = document.getElementById('refreshBtn');
    const applyBtn = document.getElementById('applyFiltersBtn');
    const resetBtn = document.getElementById('resetFiltersBtn');
    
    // Show loading state
    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...';
    refreshBtn.disabled = true;
    applyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Loading...';
    applyBtn.disabled = true;
    resetBtn.disabled = true;
    
    const promises = [loadStats(), loadTickets()];
    
    // Reload chart if it's visible
    const chartCollapse = document.getElementById('dailyStatsChart');
    if (chartCollapse && chartCollapse.classList.contains('show')) {
        promises.push(loadDailyStats());
    }
    
    Promise.all(promises).finally(() => {
        // Reset button states
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Refresh';
        refreshBtn.disabled = false;
        applyBtn.innerHTML = '<i class="fas fa-filter me-1"></i>Apply';
        applyBtn.disabled = false;
        resetBtn.disabled = false;
    });
}

// Reset all filters and refresh data
function resetFilters() {
    // Clear all filter inputs
    document.getElementById('statusFilter').value = '';
    document.getElementById('inquiryTypeFilter').value = '';
    document.getElementById('emailFilter').value = '';
    document.getElementById('dateFrom').value = '';
    document.getElementById('dateTo').value = '';
    document.getElementById('dateRangeDropdown').innerHTML = '<i class="fas fa-calendar"></i>';
    
    // Clear current filters
    currentFilters = {};
    currentPage = 1;
    
    // Show loading state
    const applyBtn = document.getElementById('applyFiltersBtn');
    const resetBtn = document.getElementById('resetFiltersBtn');
    
    resetBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    resetBtn.disabled = true;
    applyBtn.disabled = true;
    
    // Refresh data without any filters
    Promise.all([loadStats(), loadTickets()]).finally(() => {
        // Reset button states
        resetBtn.innerHTML = '<i class="fas fa-times me-1"></i>Reset';
        resetBtn.disabled = false;
        applyBtn.disabled = false;
    });
}

// Apply filters
function applyFilters() {
    currentFilters = {};
    
    const status = document.getElementById('statusFilter').value;
    if (status) currentFilters.status = status;
    
    const inquiryType = document.getElementById('inquiryTypeFilter').value;
    if (inquiryType) currentFilters.inquiry_type = inquiryType;
    
    const email = document.getElementById('emailFilter').value;
    if (email) currentFilters.sender_email = email;
    
    // Date range filters
    const dateFrom = document.getElementById('dateFrom').value;
    const dateTo = document.getElementById('dateTo').value;
    if (dateFrom) currentFilters.date_from = dateFrom + 'T00:00:00';
    if (dateTo) currentFilters.date_to = dateTo + 'T23:59:59';
    
    currentPage = 1; // Reset to first page
    
    // Update stats with the same date filters
    const dateFilters = {};
    if (currentFilters.date_from) dateFilters.date_from = currentFilters.date_from;
    if (currentFilters.date_to) dateFilters.date_to = currentFilters.date_to;
    
    loadStats(dateFilters);
    loadTickets();
    
    // Update chart if it's visible
    const chartCollapse = document.getElementById('dailyStatsChart');
    if (chartCollapse && chartCollapse.classList.contains('show')) {
        loadDailyStats();
    }
}

// Load tickets (renamed from loadInquiries)
async function loadTickets(page = 1) {
    const params = new URLSearchParams({
        page: page.toString(),
        per_page: '10',
        ...currentFilters
    });

    const result = await apiRequest(`/api/inquiries?${params}`);
    
    if (result.ok) {
        displayTickets(result.data.data, result.data.pagination);
        currentPage = page;
    } else {
        document.getElementById('ticketsContainer').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load tickets: ${result.data.message}
            </div>
        `;
    }
}

// Display tickets in table format
function displayTickets(tickets, pagination) {
    const container = document.getElementById('ticketsContainer');
    
    if (tickets.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No tickets found matching your criteria.
            </div>
        `;
        return;
    }

    let html = '<div class="table-responsive"><table class="table table-hover ticket-table">';
    html += `
        <thead>
            <tr>
                <th style="width: 12%;">Received</th>
                <th style="width: 10%;">Ticket ID</th>
                <th style="width: 12%;">Inquiry Type</th>
                <th style="width: 25%;">Subject</th>
                <th style="width: 20%;">Sender</th>
                <th style="width: 10%;">Status</th>
                <th style="width: 11%;">Actions</th>
            </tr>
        </thead>
        <tbody>
    `;

    tickets.forEach(ticket => {
        const statusBadge = getStatusBadge(ticket.status);
        
        html += `
            <tr>
                <td>${formatDate(ticket.received_date)}</td>
                <td><strong>${escapeHtml(ticket.ticket_id || 'N/A')}</strong></td>
                <td>
                    ${escapeHtml(ticket.inquiry_type || 'N/A')}
                </td>
                <td class="text-truncate" style="max-width: 200px;" title="${escapeHtml(ticket.subject)}">
                    ${escapeHtml(ticket.subject)}
                </td>
                <td>
                    <div><strong>${escapeHtml(ticket.sender_name || 'Unknown')}</strong></div>
                    <small class="text-muted">${escapeHtml(ticket.sender_email)}</small>
                </td>
                <td>${statusBadge}</td>
                <td>
                    <button class="btn btn-sm btn-outline-info me-1" onclick="viewTicketDetails(${ticket.id})" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteTicket(${ticket.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';

    // Add pagination
    if (pagination.pages > 1) {
        html += '<nav aria-label="Tickets pagination"><ul class="pagination justify-content-center">';
        
        // Previous button
        html += `<li class="page-item ${!pagination.has_prev ? 'disabled' : ''}">`;
        html += `<button class="page-link" onclick="loadTickets(${pagination.page - 1})" ${!pagination.has_prev ? 'disabled' : ''}>Previous</button>`;
        html += '</li>';
        
        // Page numbers
        for (let i = 1; i <= pagination.pages; i++) {
            html += `<li class="page-item ${i === pagination.page ? 'active' : ''}">`;
            html += `<button class="page-link" onclick="loadTickets(${i})">${i}</button>`;
            html += '</li>';
        }
        
        // Next button
        html += `<li class="page-item ${!pagination.has_next ? 'disabled' : ''}">`;
        html += `<button class="page-link" onclick="loadTickets(${pagination.page + 1})" ${!pagination.has_next ? 'disabled' : ''}>Next</button>`;
        html += '</li>';
        
        html += '</ul></nav>';
    }

    container.innerHTML = html;
}

// Removed edit functionality as requested

// View ticket details
async function viewTicketDetails(id) {
    const result = await apiRequest(`/api/inquiries/${id}`);
    
    if (result.ok) {
        const ticket = result.data.data;
        
        const details = `
            <div class="row">
                <div class="col-md-6">
                    <p><strong>Ticket ID:</strong> ${escapeHtml(ticket.ticket_id || 'N/A')}</p>
                    <p><strong>Subject:</strong> ${escapeHtml(ticket.subject)}</p>
                    <p><strong>Sender:</strong> ${escapeHtml(ticket.sender_name || 'Unknown')}</p>
                    <p><strong>Email:</strong> ${escapeHtml(ticket.sender_email)}</p>
                    ${ticket.ticket_url ? `<p><strong>View in Gorgias:</strong> <a href="${escapeHtml(ticket.ticket_url)}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="fas fa-external-link-alt me-1"></i>Open Ticket</a></p>` : ''}
                </div>
                <div class="col-md-6">
                    <p><strong>Received:</strong> ${formatDate(ticket.received_date)}</p>
                    <p><strong>Status:</strong> ${getStatusBadge(ticket.status)}</p>
                    ${ticket.inquiry_type ? `<p><strong>Type:</strong> ${escapeHtml(ticket.inquiry_type)}</p>` : ''}
                </div>
            </div>
            <div class="mt-3">
                <h6>Message Content:</h6>
                <div class="message-content p-3 rounded" style="max-height: 200px; overflow-y: auto; background-color: var(--bs-gray-700); color: white;">
                    ${escapeHtml(ticket.body).replace(/\n/g, '<br>')}
                </div>
                ${ticket.status === 'Skipped' ? `
                    <div class="alert alert-info mt-3" role="alert">
                        <i class="fas fa-info-circle me-2"></i>
                        This ticket was not engaged by AI, and was left in the Gorgias inbox for the Sweats team to respond to.
                    </div>
                ` : ''}
            </div>
            ${ticket.ai_response ? `
                <div class="mt-3">
                    <h6>AI Response:</h6>
                    <div class="bg-success bg-opacity-10 p-3 rounded border border-success">
                        ${ticket.ai_response}
                    </div>
                </div>
            ` : ''}
        `;
        
        document.getElementById('ticketDetailsContent').innerHTML = details;
        const modal = new bootstrap.Modal(document.getElementById('ticketDetailsModal'));
        
        // Add event listener to ensure proper cleanup when modal is hidden
        const modalElement = document.getElementById('ticketDetailsModal');
        modalElement.addEventListener('hidden.bs.modal', function () {
            // Ensure backdrop is completely removed
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());
            
            // Restore body scroll and remove modal classes
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true });
        
        modal.show();
    } else {
        showAlert('Failed to load ticket details: ' + result.data.message, 'danger');
    }
}

// Delete ticket with modal confirmation
let ticketToDelete = null;

async function deleteTicket(id) {
    ticketToDelete = id;
    const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    modal.show();
}

// Handle confirm delete button click
document.addEventListener('DOMContentLoaded', function() {
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async function() {
            if (ticketToDelete) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal'));
                modal.hide();
                
                const result = await apiRequest(`/api/inquiries/${ticketToDelete}`, {
                    method: 'DELETE'
                });

                if (result.ok) {
                    loadStats();
                    loadTickets();
                    showAlert('Ticket deleted successfully!', 'success');
                } else {
                    showAlert('Failed to delete ticket: ' + result.data.message, 'danger');
                }
                
                ticketToDelete = null;
            }
        });
    }
});

// Helper functions
function getStatusBadge(status) {
    const statusLower = status ? status.toLowerCase() : '';
    const badges = {
        'engaged': '<span class="badge bg-success">Engaged</span>',
        'escalated': '<span class="badge bg-warning">Escalated</span>',
        'skipped': '<span class="badge bg-secondary">Skipped</span>'
    };
    return badges[statusLower] || '<span class="badge bg-light text-dark">Unknown</span>';
}

function getStatusColor(status) {
    const statusLower = status ? status.toLowerCase() : '';
    const colors = {
        'engaged': 'success',
        'escalated': 'warning',
        'skipped': 'secondary'
    };
    return colors[statusLower] || 'light';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    const day = date.getDate().toString().padStart(2, '0');
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const year = date.getFullYear();
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showAlert(message, type) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alert.style.zIndex = '9999';
    alert.style.maxWidth = '400px';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Initialize page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Ensure calendar icon is displayed in date button
    const dateButton = document.getElementById('dateRangeDropdown');
    if (dateButton) {
        dateButton.innerHTML = '<i class="fas fa-calendar"></i>';
    }
    
    // Load inquiry types for dropdown
    loadInquiryTypes();
    
    // Load initial data
    loadStats();
    loadTickets();
});

// Daily Statistics Chart Functions
async function loadDailyStats() {
    try {
        const dateFrom = document.getElementById('dateFrom').value;
        const dateTo = document.getElementById('dateTo').value;
        
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        
        const response = await apiRequest(`/api/inquiries/daily-stats?${params}`);
        console.log('Daily Stats Response:', response);
        
        if (response.data && response.data.status === 'success') {
            renderChart(response.data.data);
            updateChartDateRange(dateFrom, dateTo);
        } else {
            showAlert('Failed to load daily statistics', 'danger');
        }
    } catch (error) {
        console.error('Error loading daily stats:', error);
        showAlert('Error loading daily statistics', 'danger');
    }
}

function getThemeColors() {
    const isDarkMode = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    return {
        textColor: isDarkMode ? '#ffffff' : '#212529',
        gridColor: isDarkMode ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)',
        titleColor: isDarkMode ? '#ffffff' : '#212529',
        legendColor: isDarkMode ? '#ffffff' : '#212529'
    };
}

function renderChart(data) {
    const ctx = document.getElementById('dailyChart').getContext('2d');
    
    // Destroy existing chart if it exists
    if (dailyChart) {
        dailyChart.destroy();
    }
    
    const themeColors = getThemeColors();
    
    // Prepare chart data
    const labels = data.map(item => {
        const date = new Date(item.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });
    
    const datasets = [
        {
            label: 'Total',
            data: data.map(item => item.total || 0),
            backgroundColor: 'rgba(108, 117, 125, 0.6)',
            borderColor: 'rgba(108, 117, 125, 1)',
            borderWidth: 2,
            fill: false
        },
        {
            label: 'Engaged',
            data: data.map(item => item.engaged || 0),
            backgroundColor: 'rgba(25, 135, 84, 0.6)',
            borderColor: 'rgba(25, 135, 84, 1)',
            borderWidth: 2,
            fill: false
        },
        {
            label: 'Escalated',
            data: data.map(item => item.escalated || 0),
            backgroundColor: 'rgba(255, 193, 7, 0.6)',
            borderColor: 'rgba(255, 193, 7, 1)',
            borderWidth: 2,
            fill: false
        },
        {
            label: 'Skipped',
            data: data.map(item => item.skipped || 0),
            backgroundColor: 'rgba(220, 53, 69, 0.6)',
            borderColor: 'rgba(220, 53, 69, 1)',
            borderWidth: 2,
            fill: false
        }
    ];
    
    // Chart configuration
    const config = {
        type: currentChartType,
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Daily Ticket Statistics',
                    color: themeColors.titleColor
                },
                legend: {
                    display: true,
                    labels: {
                        color: themeColors.legendColor,
                        usePointStyle: false,
                        generateLabels: function(chart) {
                            const datasets = chart.data.datasets;
                            return datasets.map((dataset, i) => ({
                                text: dataset.label,
                                fillStyle: dataset.backgroundColor,
                                strokeStyle: dataset.borderColor,
                                lineWidth: dataset.borderWidth,
                                hidden: !chart.isDatasetVisible(i),
                                datasetIndex: i
                            }));
                        }
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: themeColors.textColor
                    },
                    grid: {
                        color: themeColors.gridColor
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: themeColors.textColor,
                        stepSize: 1,
                        callback: function(value) {
                            if (Number.isInteger(value)) {
                                return value;
                            }
                        }
                    },
                    grid: {
                        color: themeColors.gridColor
                    }
                }
            },
            elements: {
                bar: {
                    borderWidth: 2,
                }
            }
        }
    };
    
    // Create new chart
    dailyChart = new Chart(ctx, config);
}

function changeChartType(type) {
    currentChartType = type;
    
    // Update button states
    document.querySelectorAll('#chartControls button').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('button').classList.add('active');
    
    // Re-render chart with new type
    if (dailyChart && dailyChart.data.datasets.length > 0) {
        dailyChart.config.type = type;
        dailyChart.update();
    }
}

function updateChartDateRange(dateFrom, dateTo) {
    const chartDateRangeElement = document.getElementById('chartDateRange');
    
    if (dateFrom && dateTo) {
        const fromDate = new Date(dateFrom);
        const toDate = new Date(dateTo);
        
        const fromFormatted = fromDate.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        const toFormatted = toDate.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        
        chartDateRangeElement.textContent = `${fromFormatted} - ${toFormatted}`;
    } else {
        chartDateRangeElement.textContent = 'Current Month';
    }
}