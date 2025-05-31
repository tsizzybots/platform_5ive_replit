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

// Load statistics
async function loadStats() {
    const result = await apiRequest('/api/inquiries/stats');
    
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
        <div class="col-lg-2 col-md-4 col-sm-6 mb-3">
            <div class="card stats-card bg-primary text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.total_inquiries}</h3>
                    <p class="card-text mb-0">Total Tickets</p>
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-sm-6 mb-3">
            <div class="card stats-card bg-success text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.engaged_inquiries}</h3>
                    <p class="card-text mb-0">Engaged</p>
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-sm-6 mb-3">
            <div class="card stats-card bg-warning text-dark">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.pending_inquiries}</h3>
                    <p class="card-text mb-0">Pending</p>
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-sm-6 mb-3">
            <div class="card stats-card bg-info text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.processed_inquiries}</h3>
                    <p class="card-text mb-0">Processed</p>
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-sm-6 mb-3">
            <div class="card stats-card bg-secondary text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.ignored_inquiries}</h3>
                    <p class="card-text mb-0">Ignored</p>
                </div>
            </div>
        </div>
        <div class="col-lg-2 col-md-4 col-sm-6 mb-3">
            <div class="card stats-card bg-dark text-white">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.engagement_rate}%</h3>
                    <p class="card-text mb-0">Engagement Rate</p>
                </div>
            </div>
        </div>
    `;
}



// Apply filters
function applyFilters() {
    currentFilters = {};
    
    const engaged = document.getElementById('engagedFilter').value;
    if (engaged !== '') currentFilters.engaged = engaged;
    
    const status = document.getElementById('statusFilter').value;
    if (status) currentFilters.status = status;
    
    const ticketId = document.getElementById('ticketIdFilter').value;
    if (ticketId) currentFilters.ticket_id = ticketId;
    
    currentPage = 1; // Reset to first page
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
                <th>Engaged</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
    `;

    tickets.forEach(ticket => {
        const statusBadge = getStatusBadge(ticket.status);
        const engagedBadge = ticket.engaged 
            ? '<span class="badge bg-success">Yes</span>' 
            : '<span class="badge bg-secondary">No</span>';
        
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
                <td>${engagedBadge}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="editTicket(${ticket.id})" title="Edit Ticket">
                        <i class="fas fa-edit"></i>
                    </button>
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

// Edit ticket
async function editTicket(id) {
    const result = await apiRequest(`/api/inquiries/${id}`);
    
    if (result.ok) {
        const ticket = result.data.data;
        
        // Pre-fill update form
        document.getElementById('update_inquiry_id').value = ticket.id;
        document.getElementById('update_status').value = ticket.status || '';
        document.getElementById('update_engaged').value = ticket.engaged ? 'true' : 'false';
        document.getElementById('update_ai_response').value = ticket.ai_response || '';
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('updateTicketModal'));
        modal.show();
    } else {
        showAlert('Failed to load ticket details: ' + result.data.message, 'danger');
    }
}

// Update ticket
async function updateTicket() {
    const inquiryId = document.getElementById('update_inquiry_id').value;
    
    if (!inquiryId) {
        showAlert('No ticket selected for update', 'warning');
        return;
    }

    const updateData = {};
    
    // Only include fields that have values
    const status = document.getElementById('update_status').value;
    if (status) updateData.status = status;
    
    const engaged = document.getElementById('update_engaged').value;
    if (engaged !== '') updateData.engaged = engaged === 'true';
    
    const aiResponse = document.getElementById('update_ai_response').value;
    if (aiResponse) updateData.ai_response = aiResponse;

    if (Object.keys(updateData).length === 0) {
        showAlert('Please provide at least one field to update', 'warning');
        return;
    }

    const result = await apiRequest(`/api/inquiries/${inquiryId}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
    });

    if (result.ok) {
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('updateTicketModal'));
        modal.hide();
        
        // Refresh data
        loadStats();
        loadTickets();
        
        showAlert('Ticket updated successfully!', 'success');
    } else {
        showAlert('Failed to update ticket: ' + result.data.message, 'danger');
    }
}

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
                </div>
                <div class="col-md-6">
                    <p><strong>Received:</strong> ${formatDate(ticket.received_date)}</p>
                    <p><strong>Status:</strong> <span class="badge bg-${getStatusColor(ticket.status)}">${ticket.status}</span></p>
                    <p><strong>Engaged:</strong> <span class="badge bg-${ticket.engaged ? 'success' : 'secondary'}">${ticket.engaged ? 'Yes' : 'No'}</span></p>
                </div>
            </div>
            <div class="mt-3">
                <h6>Message Content:</h6>
                <div class="bg-light p-3 rounded" style="max-height: 200px; overflow-y: auto;">
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
    const badges = {
        'pending': '<span class="badge bg-warning">Pending</span>',
        'processed': '<span class="badge bg-success">Processed</span>',
        'ignored': '<span class="badge bg-secondary">Ignored</span>'
    };
    return badges[status] || '<span class="badge bg-light text-dark">Unknown</span>';
}

function getStatusColor(status) {
    const colors = {
        'pending': 'warning',
        'processed': 'success',
        'ignored': 'secondary'
    };
    return colors[status] || 'light';
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