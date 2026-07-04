// Supabase Initialization
const SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"; // Need to be replaced when UI runs if not using proxy
const SUPABASE_ANON_KEY = "YOUR_SUPABASE_KEY_HERE"; 

// Using REST directly or passing JWT to our backend
// The simplest is to manage session via localStorage

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    
    // Remove existing classes
    toast.classList.remove('toast-success', 'toast-error');
    
    if (type === 'error') {
        toast.classList.add('toast-error');
    } else {
        toast.classList.add('toast-success');
    }
    
    toast.style.display = 'block';
    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}

function showSpinner() {
    const spinner = document.getElementById('spinner-overlay');
    if(spinner) spinner.style.display = 'flex';
}

function hideSpinner() {
    const spinner = document.getElementById('spinner-overlay');
    if(spinner) spinner.style.display = 'none';
}

async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    // Remove Content-Type if sending FormData (browser sets it automatically with boundary)
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(endpoint, {
        ...options,
        headers
    });

    if (res.status === 401 && window.location.pathname !== '/' && window.location.pathname !== '/register') {
        localStorage.removeItem('token');
        window.location.href = '/';
        return;
    }

    if (res.headers.get('content-type')?.includes('application/json')) {
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'API Error');
        return data;
    } else {
        if (!res.ok) {
            const text = await res.text();
            throw new Error(text || 'API Error');
        }
        return res;
    }
}

function logout() {
    localStorage.removeItem('token');
    window.location.href = '/';
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    document.querySelector(`[onclick="switchTab('${tabId}')"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
}

// Global hook to check auth on protected pages
document.addEventListener("DOMContentLoaded", () => {
    const currentPath = window.location.pathname;
    if (['/dashboard', '/add_expense', '/history', '/settings'].includes(currentPath)) {
        if (!localStorage.getItem('token')) {
            window.location.href = '/';
        }
    }
});
