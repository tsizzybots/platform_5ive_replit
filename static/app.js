// Global variables
let currentPage = 1;
let currentFilters = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadTickets();
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
            <div class="card stats-card bg-secondary text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.total_inquiries - stats.engaged_inquiries}</h3>
                    <p class="card-text mb-0">Skipped</p>
                </div>
            </div>
        </div>
        <div class="col-lg-3 col-md-6 mb-3">
            <div class="card stats-card bg-info text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.engagement_rate}%</h3>
                    <p class="card-text mb-0">AI Engagement Rate</p>
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
            dropdown.textContent = 'Today';
            break;
        case 'yesterday':
            const yesterday = new Date(today);
            yesterday.setDate(today.getDate() - 1);
            const yesterdayStr = yesterday.toISOString().split('T')[0];
            dateFrom.value = yesterdayStr;
            dateTo.value = yesterdayStr;
            dropdown.textContent = 'Yesterday';
            break;
        case 'thisWeek':
            const startOfWeek = new Date(today);
            startOfWeek.setDate(today.getDate() - today.getDay());
            dateFrom.value = startOfWeek.toISOString().split('T')[0];
            dateTo.value = todayStr;
            dropdown.textContent = 'This Week';
            break;
        case 'lastWeek':
            const lastWeekStart = new Date(today);
            lastWeekStart.setDate(today.getDate() - today.getDay() - 7);
            const lastWeekEnd = new Date(lastWeekStart);
            lastWeekEnd.setDate(lastWeekStart.getDate() + 6);
            dateFrom.value = lastWeekStart.toISOString().split('T')[0];
            dateTo.value = lastWeekEnd.toISOString().split('T')[0];
            dropdown.textContent = 'Last Week';
            break;
        case 'thisMonth':
            const startOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            dateFrom.value = startOfMonth.toISOString().split('T')[0];
            dateTo.value = todayStr;
            dropdown.textContent = 'This Month';
            break;
        case 'lastMonth':
            const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1);
            const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);
            dateFrom.value = lastMonthStart.toISOString().split('T')[0];
            dateTo.value = lastMonthEnd.toISOString().split('T')[0];
            dropdown.textContent = 'Last Month';
            break;
    }
    applyFilters();
}

function clearDateRange() {
    document.getElementById('dateFrom').value = '';
    document.getElementById('dateTo').value = '';
    document.getElementById('dateRangeDropdown').textContent = 'Select Date Range';
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
    
    Promise.all([loadStats(), loadTickets()]).finally(() => {
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
    document.getElementById('dateRangeDropdown').textContent = 'Quick';
    
    // Clear current filters
    currentFilters = {};
    currentPage = 1;
    
    // Show loading state
    const applyBtn = document.getElementById('applyFiltersBtn');
    const resetBtn = document.getElementById('resetFiltersBtn');
    
    resetBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Resetting...';
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
                <th>Ticket ID</th>
                <th>Subject</th>
                <th>Sender</th>
                <th>Received</th>
                <th>Status</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
    `;

    tickets.forEach(ticket => {
        const statusBadge = getStatusBadge(ticket.status);
        
        html += `
            <tr>
                <td><strong>${escapeHtml(ticket.ticket_id || 'N/A')}</strong></td>
                <td class="text-truncate" style="max-width: 200px;" title="${escapeHtml(ticket.subject)}">
                    ${escapeHtml(ticket.subject)}
                </td>
                <td>
                    <div><strong>${escapeHtml(ticket.sender_name || 'Unknown')}</strong></div>
                    <small class="text-muted">${escapeHtml(ticket.sender_email)}</small>
                </td>
                <td>${formatDate(ticket.received_date)}</td>
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
                    ${ticket.inquiry_type ? `<p><strong>Type:</strong> <span class="badge bg-info">${escapeHtml(ticket.inquiry_type)}</span></p>` : ''}
                </div>
            </div>
            <div class="mt-3">
                <h6>Message Content:</h6>
                <div class="message-content p-3 rounded" style="max-height: 200px; overflow-y: auto; background-color: var(--bs-gray-700); color: white;">
                    ${escapeHtml(ticket.body).replace(/\n/g, '<br>')}
                </div>
            </div>
            ${ticket.ai_response ? `
                <div class="mt-3">
                    <h6>AI Response:</h6>
                    <div class="bg-success bg-opacity-10 p-3 rounded border border-success">
                        ${escapeHtml(ticket.ai_response).replace(/\n/g, '<br>')}
                    </div>
                </div>
            ` : ''}
        `;
        
        document.getElementById('ticketDetailsContent').innerHTML = details;
        const modal = new bootstrap.Modal(document.getElementById('ticketDetailsModal'));
        modal.show();
    } else {
        showAlert('Failed to load ticket details: ' + result.data.message, 'danger');
    }
}

// Delete ticket
async function deleteTicket(id) {
    if (!confirm('Are you sure you want to delete this ticket?')) {
        return;
    }

    const result = await apiRequest(`/api/inquiries/${id}`, {
        method: 'DELETE'
    });

    if (result.ok) {
        loadStats();
        loadTickets();
        showAlert('Ticket deleted successfully!', 'success');
    } else {
        showAlert('Failed to delete ticket: ' + result.data.message, 'danger');
    }
}

// Helper functions
function getStatusBadge(status) {
    const statusLower = status ? status.toLowerCase() : '';
    const badges = {
        'engaged': '<span class="badge bg-success">Engaged</span>',
        'skipped': '<span class="badge bg-secondary">Skipped</span>'
    };
    return badges[statusLower] || '<span class="badge bg-light text-dark">Unknown</span>';
}

function getStatusColor(status) {
    const statusLower = status ? status.toLowerCase() : '';
    const colors = {
        'engaged': 'success',
        'skipped': 'secondary'
    };
    return colors[statusLower] || 'light';
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
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