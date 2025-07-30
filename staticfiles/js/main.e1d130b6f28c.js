// Main JavaScript file for Zoho CRM Clone

// API Base URL
const API_BASE_URL = '/api/';

// Authentication token handling
function getToken() {
    return localStorage.getItem('access_token');
}

function getAuthHeaders() {
    const token = getToken();
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// API request helper
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = API_BASE_URL + endpoint;
    const options = {
        method: method,
        headers: getAuthHeaders()
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(data);
    }

    try {
        showSpinner();
        const response = await fetch(url, options);
        
        // Handle token refresh if needed
        if (response.status === 401) {
            const refreshed = await refreshToken();
            if (refreshed) {
                // Retry the request with new token
                options.headers = getAuthHeaders();
                const retryResponse = await fetch(url, options);
                hideSpinner();
                return processResponse(retryResponse);
            } else {
                // Redirect to login if refresh failed
                window.location.href = '/login/';
                hideSpinner();
                return null;
            }
        }
        
        hideSpinner();
        return processResponse(response);
    } catch (error) {
        hideSpinner();
        showNotification('Error', 'Network error occurred', 'error');
        console.error('API Request Error:', error);
        return null;
    }
}

async function processResponse(response) {
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        const data = await response.json();
        if (!response.ok) {
            handleApiError(response.status, data);
            return null;
        }
        return data;
    } else {
        if (!response.ok) {
            handleApiError(response.status);
            return null;
        }
        return await response.text();
    }
}

function handleApiError(status, data = {}) {
    let message = 'An error occurred';
    
    if (data.error) {
        message = data.error;
    } else if (data.detail) {
        message = data.detail;
    } else if (data.non_field_errors) {
        message = data.non_field_errors.join(', ');
    } else {
        switch (status) {
            case 400: message = 'Bad request'; break;
            case 401: message = 'Unauthorized'; break;
            case 403: message = 'Forbidden'; break;
            case 404: message = 'Not found'; break;
            case 500: message = 'Server error'; break;
            default: message = `Error (${status})`;
        }
    }
    
    showNotification('Error', message, 'error');
}

// Token refresh
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) return false;
    
    try {
        const response = await fetch('/api/token/refresh/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: refreshToken })
        });
        
        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access);
            return true;
        } else {
            // Clear tokens if refresh failed
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            return false;
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        return false;
    }
}

// UI Helpers
function showSpinner() {
    // Remove existing spinner if any
    removeSpinner();
    
    // Create spinner overlay with Zoho-inspired loader
    const spinnerHtml = `
        <div class="spinner-overlay" id="spinner-overlay">
            <div class="loader-container">
                <div class="zoho-loader">
                    <div></div>
                    <div></div>
                    <div></div>
                    <div></div>
                    <div></div>
                    <div></div>
                    <div></div>
                    <div></div>
                    <div></div>
                </div>
                <div class="loader-text">LiveFxHub CRM...</div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', spinnerHtml);
}

function hideSpinner() {
    removeSpinner();
}

function removeSpinner() {
    const existingSpinner = document.getElementById('spinner-overlay');
    if (existingSpinner) {
        existingSpinner.remove();
    }
}

function showNotification(title, message, type = 'info') {
    // You can implement a toast or notification system here
    // For now, we'll use alert for simplicity
    alert(`${title}: ${message}`);
}

// Form helpers
function serializeForm(form) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    return data;
}

// Date formatting
function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function formatDateTime(dateTimeString) {
    try {
        if (!dateTimeString) return 'N/A';
        
        // Check if the date is valid
        const date = new Date(dateTimeString);
        if (isNaN(date.getTime())) {
            console.warn('Invalid date format:', dateTimeString);
            return 'Invalid Date';
        }
        
        return date.toLocaleString();
    } catch (error) {
        console.error('Error formatting date:', error, dateTimeString);
        return 'N/A';
    }
}

// Transaction handling
function showTransaction(transactionId) {
    // Set flag in sessionStorage to indicate we're coming from dashboard
    sessionStorage.setItem('from_dashboard', 'true');
    // Navigate to transaction page
    window.location.href = `/transaction/?id=${transactionId}`;
}

// Initialize page-specific scripts based on the current page
document.addEventListener('DOMContentLoaded', function() {
    const path = window.location.pathname;
    
    // Initialize specific page scripts
    if (path.includes('/dashboard/')) {
        initDashboard();
    } else if (path.includes('/leads/')) {
        initLeads();
    } else if (path.includes('/contacts/')) {
        initContacts();
    } else if (path.includes('/accounts/')) {
        initAccounts();
    } else if (path.includes('/deals/')) {
        initDeals();
    } else if (path.includes('/tasks/')) {
        initTasks();
    } else if (path.includes('/calendar/')) {
        // Calendar is initialized in its own template
    } else if (path.includes('/transaction/')) {
        initTransaction();
    }
});

// Page-specific initialization functions
function initDashboard() {
    // Load dashboard data
    loadDashboardData();
}

async function loadDashboardData() {
    // Get the current user's profile to get their manager_username and current user ID
    const userProfile = await apiRequest('profile/');
    const currentUser = JSON.parse(localStorage.getItem('user'));
    
    if (!userProfile || !userProfile.manager_username || !currentUser) {
        // If no user profile or manager username, show zeros for all counts
        document.getElementById('leads-count').textContent = '0';
        document.getElementById('contacts-count').textContent = '0';
        document.getElementById('accounts-count').textContent = '0';
        document.getElementById('deals-count').textContent = '0';
        
        // Show empty tables
        populateRecentLeads([]);
        populateRecentDeals([]);
        populateUpcomingTasks([]);
        return;
    }
    
    // Get dashboard data filtering by manager_username
    const dashboardData = await apiRequest(`dashboard/?manager_username=${userProfile.manager_username}`);
    
    // Get all data separately to apply filtering
    const leadsData = await apiRequest(`leads/?manager_username=${userProfile.manager_username}`);
    const contactsData = await apiRequest(`contacts/?manager_username=${userProfile.manager_username}`);
    const accountsData = await apiRequest(`accounts/?manager_username=${userProfile.manager_username}`);
    const dealsData = await apiRequest(`deals/?manager_username=${userProfile.manager_username}`);
    const tasksData = await apiRequest(`tasks/?manager_username=${userProfile.manager_username}`);
    
    // Update dashboard stats with accurate counts based on filtering
    // First strictly filter by matching manager_username, then filter by assignment
    
    // Filter and count leads
    let filteredLeads = [];
    if (leadsData && leadsData.results) {
        // First strictly filter by matching manager_username
        const managerLeads = leadsData.results.filter(lead => 
            lead.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredLeads = managerLeads.filter(lead => 
            !lead.assigned_to || 
            lead.assigned_to === currentUser.id || 
            (lead.assigned_to && lead.assigned_to.id === currentUser.id)
        );
    } else if (leadsData && Array.isArray(leadsData)) {
        // First strictly filter by matching manager_username
        const managerLeads = leadsData.filter(lead => 
            lead.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredLeads = managerLeads.filter(lead => 
            !lead.assigned_to || 
            lead.assigned_to === currentUser.id || 
            (lead.assigned_to && lead.assigned_to.id === currentUser.id)
        );
    }
    document.getElementById('leads-count').textContent = filteredLeads.length;
    
    // Filter and count contacts
    let filteredContacts = [];
    if (contactsData && contactsData.results) {
        // First strictly filter by matching manager_username
        const managerContacts = contactsData.results.filter(contact => 
            contact.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredContacts = managerContacts.filter(contact => 
            !contact.assigned_to || 
            contact.assigned_to === currentUser.id || 
            (contact.assigned_to && contact.assigned_to.id === currentUser.id)
        );
    } else if (contactsData && Array.isArray(contactsData)) {
        // First strictly filter by matching manager_username
        const managerContacts = contactsData.filter(contact => 
            contact.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredContacts = managerContacts.filter(contact => 
            !contact.assigned_to || 
            contact.assigned_to === currentUser.id || 
            (contact.assigned_to && contact.assigned_to.id === currentUser.id)
        );
    }
    document.getElementById('contacts-count').textContent = filteredContacts.length;
    
    // Filter and count accounts
    let filteredAccounts = [];
    if (accountsData && accountsData.results) {
        // First strictly filter by matching manager_username
        const managerAccounts = accountsData.results.filter(account => 
            account.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredAccounts = managerAccounts.filter(account => 
            !account.assigned_to || 
            account.assigned_to === currentUser.id || 
            (account.assigned_to && account.assigned_to.id === currentUser.id)
        );
    } else if (accountsData && Array.isArray(accountsData)) {
        // First strictly filter by matching manager_username
        const managerAccounts = accountsData.filter(account => 
            account.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredAccounts = managerAccounts.filter(account => 
            !account.assigned_to || 
            account.assigned_to === currentUser.id || 
            (account.assigned_to && account.assigned_to.id === currentUser.id)
        );
    }
    document.getElementById('accounts-count').textContent = filteredAccounts.length;
    
    // Filter and count deals
    let filteredDeals = [];
    if (dealsData && dealsData.results) {
        // First strictly filter by matching manager_username
        const managerDeals = dealsData.results.filter(deal => 
            deal.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredDeals = managerDeals.filter(deal => 
            !deal.assigned_to || 
            deal.assigned_to === currentUser.id || 
            (deal.assigned_to && deal.assigned_to.id === currentUser.id)
        );
    } else if (dealsData && Array.isArray(dealsData)) {
        // First strictly filter by matching manager_username
        const managerDeals = dealsData.filter(deal => 
            deal.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        filteredDeals = managerDeals.filter(deal => 
            !deal.assigned_to || 
            deal.assigned_to === currentUser.id || 
            (deal.assigned_to && deal.assigned_to.id === currentUser.id)
        );
    }
    document.getElementById('deals-count').textContent = filteredDeals.length;
    
    // Use the filtered data and dashboardData for populating the dashboard components
    
    // For recent leads, use the filtered leads directly if dashboardData.recent_leads is empty
    let recentLeads = [];
    if (dashboardData && dashboardData.recent_leads && dashboardData.recent_leads.length > 0) {
        // First strictly filter by matching manager_username
        const managerRecentLeads = dashboardData.recent_leads.filter(lead => 
            lead.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        recentLeads = managerRecentLeads.filter(lead => 
            !lead.assigned_to || 
            lead.assigned_to === currentUser.id || 
            (lead.assigned_to && lead.assigned_to.id === currentUser.id)
        );
    } else {
        // Use the filtered leads if dashboardData doesn't have recent_leads
        recentLeads = filteredLeads;
    }
    
    // Sort by date (assuming there's a created_date or similar field)
    recentLeads.sort((a, b) => {
        const dateA = new Date(a.created_at || a.date || 0);
        const dateB = new Date(b.created_at || b.date || 0);
        return dateB - dateA; // Descending (newest first)
    });
    
    // Take only the 5 most recent leads
    recentLeads = recentLeads.slice(0, 5);
    populateRecentLeads(recentLeads);
    
    // For recent deals
    let recentDeals = [];
    if (dashboardData && dashboardData.recent_deals && dashboardData.recent_deals.length > 0) {
        // First strictly filter by matching manager_username
        const managerRecentDeals = dashboardData.recent_deals.filter(deal => 
            deal.manager_username === userProfile.manager_username
        );
        // Then filter by assignment
        recentDeals = managerRecentDeals.filter(deal => 
            !deal.assigned_to || 
            deal.assigned_to === currentUser.id || 
            (deal.assigned_to && deal.assigned_to.id === currentUser.id)
        );
    } else {
        // Use filtered deals if dashboardData doesn't have recent_deals
        recentDeals = filteredDeals;
    }
    populateRecentDeals(recentDeals);
    
    // For upcoming tasks, use tasksData directly
    let upcomingTasks = [];
    if (tasksData && tasksData.results) {
        // First strictly filter by matching manager_username
        const managerTasks = tasksData.results.filter(task => 
            task.manager_username === userProfile.manager_username
        );
        // Then filter by assignment - show all tasks assigned to the current user
        upcomingTasks = managerTasks.filter(task => 
            task.assigned_to === currentUser.username || 
            task.assigned_to === currentUser.id || 
            (task.assigned_to && task.assigned_to.id === currentUser.id)
        );
        // Sort by due date
        upcomingTasks.sort((a, b) => {
            const dateA = new Date(a.due_date || 0);
            const dateB = new Date(b.due_date || 0);
            return dateA - dateB; // Ascending (closest due date first)
        });
    } else if (dashboardData && dashboardData.upcoming_tasks) {
        // Fall back to dashboard data if direct task fetch fails
        const managerUpcomingTasks = dashboardData.upcoming_tasks.filter(task => 
            task.manager_username === userProfile.manager_username
        );
        // Show all tasks assigned to the current user
        upcomingTasks = managerUpcomingTasks.filter(task => 
            task.assigned_to === currentUser.username || 
            task.assigned_to === currentUser.id || 
            (task.assigned_to && task.assigned_to.id === currentUser.id)
        );
        // Sort by due date
        upcomingTasks.sort((a, b) => {
            const dateA = new Date(a.due_date || 0);
            const dateB = new Date(b.due_date || 0);
            return dateA - dateB; // Ascending (closest due date first)
        });
    }
    populateUpcomingTasks(upcomingTasks);
}

function initTransaction() {
    // Check if we're coming from dashboard
    const fromDashboard = sessionStorage.getItem('from_dashboard') === 'true';
    if (!fromDashboard) {
        // Redirect to dashboard if not coming from there
        window.location.href = '/dashboard/';
        return;
    }
    
    // Get transaction ID from URL
    const urlParams = new URLSearchParams(window.location.search);
    const transactionId = urlParams.get('id');
    
    if (transactionId) {
        loadTransactionData(transactionId);
    } else {
        document.getElementById('transaction-container').innerHTML = '<div class="alert alert-danger">Transaction ID not provided</div>';
    }
    
    // Set up back button
    document.getElementById('back-button').addEventListener('click', function() {
        window.location.href = '/dashboard/';
    });
    
    // Set up refresh button
    document.getElementById('refresh-button').addEventListener('click', function() {
        loadTransactionData(transactionId);
    });
}

async function loadTransactionData(transactionId) {
    const data = await apiRequest(`transactions/${transactionId}/`);
    if (data) {
        // Populate transaction details
        document.getElementById('transaction-type').textContent = data.transaction_type_display;
        document.getElementById('transaction-amount').textContent = `$${data.amount}`;
        document.getElementById('transaction-date').textContent = formatDate(data.date);
        document.getElementById('transaction-status').textContent = data.status;
        document.getElementById('transaction-reference').textContent = data.reference_number || 'N/A';
        document.getElementById('transaction-account').textContent = data.account_name;
        
        // Set status class
        const statusElement = document.getElementById('transaction-status');
        statusElement.className = 'transaction-status';
        if (data.status === 'pending') {
            statusElement.classList.add('status-pending');
        } else if (data.status === 'completed') {
            statusElement.classList.add('status-completed');
        } else if (data.status === 'overdue') {
            statusElement.classList.add('status-overdue');
        }
        
        // Show description if available
        if (data.description) {
            document.getElementById('transaction-description').textContent = data.description;
            document.getElementById('description-container').style.display = 'block';
        } else {
            document.getElementById('description-container').style.display = 'none';
        }
        
        // Show deal if available
        if (data.deal_name) {
            document.getElementById('transaction-deal').textContent = data.deal_name;
            document.getElementById('deal-container').style.display = 'block';
        } else {
            document.getElementById('deal-container').style.display = 'none';
        }
    }
}
