// Main JavaScript for RiskRadar

// Risk score color coding - Global function
function updateRiskScoreColors() {
    const riskElements = document.querySelectorAll('[data-risk-score]');
    riskElements.forEach(element => {
        const score = parseFloat(element.getAttribute('data-risk-score'));
        if (!isNaN(score)) {
            // Remove existing classes
            element.classList.remove('risk-high', 'risk-medium', 'risk-low', 'bg-danger', 'bg-warning', 'bg-success');
            
            if (score >= 75) {
                element.classList.add('risk-high');
            } else if (score >= 50) {
                element.classList.add('risk-medium');
            } else {
                element.classList.add('risk-low');
            }
        }
    });
}

// Claim status badges - Global function
function updateStatusBadges() {
    const statusElements = document.querySelectorAll('[data-status]');
    statusElements.forEach(element => {
        const status = element.getAttribute('data-status');
        // Remove existing status classes
        element.className = element.className.split(' ').filter(c => !c.startsWith('status-')).join(' ');
        // Add the correct status class
        element.classList.add(`status-${status}`);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // File upload drag and drop functionality
    const fileUploadAreas = document.querySelectorAll('.file-upload-area');
    fileUploadAreas.forEach(area => {
        const input = area.querySelector('input[type="file"]');
        const label = area.querySelector('.file-upload-label');
        
        if (input && label) {
            // Handle drag and drop
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                area.addEventListener(eventName, preventDefaults, false);
            });
            
            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }
            
            ['dragenter', 'dragover'].forEach(eventName => {
                area.addEventListener(eventName, highlight, false);
            });
            
            ['dragleave', 'drop'].forEach(eventName => {
                area.addEventListener(eventName, unhighlight, false);
            });
            
            function highlight() {
                area.classList.add('dragover');
            }
            
            function unhighlight() {
                area.classList.remove('dragover');
            }
            
            // Handle file drop
            area.addEventListener('drop', handleDrop, false);
            
            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;
                input.files = files;
                updateFileName(files);
            }
            
            // Handle file selection via button
            input.addEventListener('change', function() {
                updateFileName(this.files);
            });
            
            function updateFileName(files) {
                if (files.length > 0) {
                    if (files.length === 1) {
                        label.textContent = files[0].name;
                    } else {
                        label.textContent = `${files.length} files selected`;
                    }
                } else {
                    label.textContent = 'Choose file or drag it here';
                }
            }
        }
    });

    // Call global functions
    updateRiskScoreColors();
    updateStatusBadges();

    // Form validation enhancements
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });

    // Auto-format currency inputs
    const currencyInputs = document.querySelectorAll('input[data-currency]');
    currencyInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value) {
                const value = parseFloat(this.value.replace(/[^\d.]/g, ''));
                if (!isNaN(value)) {
                    this.value = new Intl.NumberFormat('en-IN', {
                        style: 'currency',
                        currency: 'INR',
                        minimumFractionDigits: 2
                    }).format(value);
                }
            }
        });

        input.addEventListener('focus', function() {
            this.value = this.value.replace(/[^\d.]/g, '');
        });
    });

    // Responsive table handling
    function makeTablesResponsive() {
        const tables = document.querySelectorAll('table');
        tables.forEach(table => {
            if (table.parentElement.className !== 'table-responsive') {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        });
    }
    makeTablesResponsive();

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Lazy loading for images
    if ('IntersectionObserver' in window) {
        const lazyImages = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });

        lazyImages.forEach(img => {
            imageObserver.observe(img);
        });
    }
});

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2
    }).format(amount);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(date);
}

function showLoading() {
    const loadingElement = document.createElement('div');
    loadingElement.className = 'loading-overlay';
    loadingElement.innerHTML = `
        <div class="d-flex justify-content-center align-items-center" style="height: 100vh;">
            <div class="loading-spinner"></div>
        </div>
    `;
    document.body.appendChild(loadingElement);
}

function hideLoading() {
    const loadingElement = document.querySelector('.loading-overlay');
    if (loadingElement) {
        loadingElement.remove();
    }
}

// API helper functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}
