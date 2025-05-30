// Global variables
let currentPage = 1;
let currentFilters = {};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadStats();
    loadInquiries();
    setupEventListeners();
    setCurrentDateTime();
});

// Set current date and time for the received_date field
function setCurrentDateTime() {
    const now = new Date();
    const localDateTime = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
        .toISOString()
        .slice(0, 16);
    document.getElementById('received_date').value = localDateTime;
}

// Setup event listeners
function setupEventListeners() {
    // Create form submission
    document.getElementById('createForm').addEventListener('submit', function(e) {
        e.preventDefault();
        createInquiry();
    });

    // Update form submission
    document.getElementById('updateForm').addEventListener('submit', function(e) {
        e.preventDefault();
        updateInquiry();
    });
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
        displayResponse(data, response.status);

        return { data, status: response.status, ok: response.ok };
    } catch (error) {
        const errorData = { status: 'error', message: error.message };
        displayResponse(errorData, 500);
        return { data: errorData, status: 500, ok: false };
    }
}

// Display API response
function displayResponse(data, status) {
    const responseArea = document.getElementById('responseArea');
    responseArea.textContent = JSON.stringify(data, null, 2);
    
    // Color code based on status
    if (status >= 200 && status < 300) {
        responseArea.className = 'mb-0 text-success';
    } else if (status >= 400) {
        responseArea.className = 'mb-0 text-danger';
    } else {
        responseArea.className = 'mb-0 text-warning';
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

// Display statistics
function displayStats(stats) {
    const container = document.getElementById('statsContainer');
    container.innerHTML = `
        <div class="col-md-2">
            <div class="card bg-primary">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.total_inquiries}</h3>
                    <p class="card-text">Total Inquiries</p>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-success">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.engaged_inquiries}</h3>
                    <p class="card-text">Engaged</p>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-warning">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.pending_inquiries}</h3>
                    <p class="card-text">Pending</p>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-info">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.processed_inquiries}</h3>
                    <p class="card-text">Processed</p>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-secondary">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.ignored_inquiries}</h3>
                    <p class="card-text">Ignored</p>
                </div>
            </div>
        </div>
        <div class="col-md-2">
            <div class="card bg-dark">
                <div class="card-body text-center">
                    <h3 class="card-title">${stats.engagement_rate}%</h3>
                    <p class="card-text">Engagement Rate</p>
                </div>
            </div>
        </div>
    `;
}

// Create new inquiry
async function createInquiry() {
    const formData = {
        subject: document.getElementById('subject').value,
        body: document.getElementById('body').value,
        sender_email: document.getElementById('sender_email').value,
        sender_name: document.getElementById('sender_name').value || null,
        received_date: new Date(document.getElementById('received_date').value).toISOString()
    };

    const result = await apiRequest('/api/inquiries', {
        method: 'POST',
        body: JSON.stringify(formData)
    });

    if (result.ok) {
        // Clear form and refresh data
        document.getElementById('createForm').reset();
        setCurrentDateTime();
        loadStats();
        loadInquiries();
        
        // Show success message
        showAlert('Inquiry created successfully!', 'success');
    } else {
        showAlert('Failed to create inquiry: ' + result.data.message, 'danger');
    }
}

// Update inquiry
async function updateInquiry() {
    const inquiryId = document.getElementById('inquiry_id').value;
    
    if (!inquiryId) {
        showAlert('Please enter an Inquiry ID', 'warning');
        return;
    }

    const updateData = {};
    
    // Only include fields that have values
    const status = document.getElementById('status').value;
    if (status) updateData.status = status;
    
    const engaged = document.getElementById('engaged').value;
    if (engaged !== '') updateData.engaged = engaged === 'true';
    
    const aiResponse = document.getElementById('ai_response').value;
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
        // Clear form and refresh data
        document.getElementById('updateForm').reset();
        loadStats();
        loadInquiries();
        
        showAlert('Inquiry updated successfully!', 'success');
    } else {
        showAlert('Failed to update inquiry: ' + result.data.message, 'danger');
    }
}

// Apply filters
function applyFilters() {
    currentFilters = {};
    
    const status = document.getElementById('statusFilter').value;
    if (status) currentFilters.status = status;
    
    const engaged = document.getElementById('engagedFilter').value;
    if (engaged !== '') currentFilters.engaged = engaged;
    
    const email = document.getElementById('emailFilter').value;
    if (email) currentFilters.sender_email = email;
    
    currentPage = 1; // Reset to first page
    loadInquiries();
}

// Load inquiries
async function loadInquiries(page = 1) {
    const params = new URLSearchParams({
        page: page.toString(),
        per_page: '10',
        ...currentFilters
    });

    const result = await apiRequest(`/api/inquiries?${params}`);
    
    if (result.ok) {
        displayInquiries(result.data.data, result.data.pagination);
        currentPage = page;
    } else {
        document.getElementById('inquiriesContainer').innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load inquiries: ${result.data.message}
            </div>
        `;
    }
}

// Display inquiries
function displayInquiries(inquiries, pagination) {
    const container = document.getElementById('inquiriesContainer');
    
    if (inquiries.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No inquiries found matching your criteria.
            </div>
        `;
        return;
    }

    let html = '<div class="table-responsive"><table class="table table-hover">';
    html += `
        <thead>
            <tr>
                <th>ID</th>
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

    inquiries.forEach(inquiry => {
        const statusBadge = getStatusBadge(inquiry.status);
        const engagedBadge = inquiry.engaged 
            ? '<span class="badge bg-success">Yes</span>' 
            : '<span class="badge bg-secondary">No</span>';
        
        html += `
            <tr>
                <td>#${inquiry.id}</td>
                <td class="text-truncate" style="max-width: 200px;" title="${escapeHtml(inquiry.subject)}">
                    ${escapeHtml(inquiry.subject)}
                </td>
                <td>
                    <div>${escapeHtml(inquiry.sender_name || 'Unknown')}</div>
                    <small class="text-muted">${escapeHtml(inquiry.sender_email)}</small>
                </td>
                <td>${formatDate(inquiry.received_date)}</td>
                <td>${statusBadge}</td>
                <td>${engagedBadge}</td>
                <td>
                    <button class="btn btn-sm btn-outline-info" onclick="viewInquiry(${inquiry.id})" title="View Details">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteInquiry(${inquiry.id})" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table></div>';

    // Add pagination
    if (pagination.pages > 1) {
        html += '<nav aria-label="Inquiries pagination"><ul class="pagination justify-content-center">';
        
        // Previous button
        html += `<li class="page-item ${!pagination.has_prev ? 'disabled' : ''}">`;
        html += `<button class="page-link" onclick="loadInquiries(${pagination.page - 1})" ${!pagination.has_prev ? 'disabled' : ''}>Previous</button>`;
        html += '</li>';
        
        // Page numbers
        for (let i = 1; i <= pagination.pages; i++) {
            html += `<li class="page-item ${i === pagination.page ? 'active' : ''}">`;
            html += `<button class="page-link" onclick="loadInquiries(${i})">${i}</button>`;
            html += '</li>';
        }
        
        // Next button
        html += `<li class="page-item ${!pagination.has_next ? 'disabled' : ''}">`;
        html += `<button class="page-link" onclick="loadInquiries(${pagination.page + 1})" ${!pagination.has_next ? 'disabled' : ''}>Next</button>`;
        html += '</li>';
        
        html += '</ul></nav>';
    }

    container.innerHTML = html;
}

// View inquiry details
async function viewInquiry(id) {
    const result = await apiRequest(`/api/inquiries/${id}`);
    
    if (result.ok) {
        const inquiry = result.data.data;
        
        // Pre-fill update form
        document.getElementById('inquiry_id').value = inquiry.id;
        
        // Switch to update tab
        const updateTab = new bootstrap.Tab(document.getElementById('update-tab'));
        updateTab.show();
        
        showAlert(`Loaded inquiry #${inquiry.id} for editing`, 'info');
    }
}

// Delete inquiry
async function deleteInquiry(id) {
    if (!confirm('Are you sure you want to delete this inquiry?')) {
        return;
    }

    const result = await apiRequest(`/api/inquiries/${id}`, {
        method: 'DELETE'
    });

    if (result.ok) {
        loadStats();
        loadInquiries();
        showAlert('Inquiry deleted successfully!', 'success');
    } else {
        showAlert('Failed to delete inquiry: ' + result.data.message, 'danger');
    }
}

// Helper functions
function getStatusBadge(status) {
    const badges = {
        'pending': '<span class="badge bg-warning">Pending</span>',
        'processed': '<span class="badge bg-success">Processed</span>',
        'ignored': '<span class="badge bg-secondary">Ignored</span>'
    };
    return badges[status] || '<span class="badge bg-light">Unknown</span>';
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
