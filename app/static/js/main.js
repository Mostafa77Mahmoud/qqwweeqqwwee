// ELHOSENY Laundry POS - Main JavaScript Functions
'use strict';

// Global variables
let currentLanguage = document.documentElement.getAttribute('lang') || 'en';
let isRTL = currentLanguage === 'ar';

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Main initialization function
function initializeApp() {
    initializeTooltips();
    initializePopovers();
    initializeFormValidation();
    initializeLanguageToggle();
    initializeLoadingStates();
    initializeAutoRefresh();
    initializePOSInterface();
    initializeNotifications();
    initializeAccessibility();
    
    // Mark app as initialized
    document.body.classList.add('app-initialized');
    console.log('ELHOSENY POS initialized successfully');
}

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize Bootstrap popovers
function initializePopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Form validation and enhancement
function initializeFormValidation() {
    // Add custom validation styles
    const forms = document.querySelectorAll('.needs-validation');
    Array.prototype.slice.call(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus on first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Real-time validation for specific fields
    initializePhoneValidation();
    initializeEmailValidation();
    initializePriceValidation();
}

// Phone number validation and formatting
function initializePhoneValidation() {
    const phoneInputs = document.querySelectorAll('input[type="tel"], input[name*="phone"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            // Remove non-digits
            let value = e.target.value.replace(/\D/g, '');
            
            // Egyptian phone number formatting
            if (value.startsWith('01') && value.length <= 11) {
                // Mobile: 01XXXXXXXXX
                if (value.length > 4 && value.length <= 7) {
                    value = value.replace(/(\d{4})(\d+)/, '$1 $2');
                } else if (value.length > 7) {
                    value = value.replace(/(\d{4})(\d{3})(\d+)/, '$1 $2 $3');
                }
            } else if (value.startsWith('2') && value.length <= 12) {
                // International: +2XXXXXXXXXXX
                value = '+' + value.replace(/(\d{2})(\d{1})(\d{4})(\d{3})(\d+)/, '$1 $2 $3 $4 $5');
            }
            
            e.target.value = value;
            
            // Validate
            const isValid = validatePhoneNumber(value);
            e.target.setCustomValidity(isValid ? '' : getLocalizedText('Invalid phone number', 'رقم هاتف غير صالح'));
        });
    });
}

// Email validation
function initializeEmailValidation() {
    const emailInputs = document.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        input.addEventListener('blur', function(e) {
            const email = e.target.value.trim();
            if (email && !validateEmail(email)) {
                e.target.setCustomValidity(getLocalizedText('Invalid email address', 'عنوان بريد إلكتروني غير صالح'));
            } else {
                e.target.setCustomValidity('');
            }
        });
    });
}

// Price validation and formatting
function initializePriceValidation() {
    const priceInputs = document.querySelectorAll('input[type="number"][step], input[name*="price"], input[name*="amount"]');
    priceInputs.forEach(input => {
        input.addEventListener('input', function(e) {
            const value = parseFloat(e.target.value);
            if (e.target.value && (isNaN(value) || value < 0)) {
                e.target.setCustomValidity(getLocalizedText('Please enter a valid positive number', 'يرجى إدخال رقم موجب صالح'));
            } else {
                e.target.setCustomValidity('');
            }
        });
        
        // Format on blur
        input.addEventListener('blur', function(e) {
            const value = parseFloat(e.target.value);
            if (!isNaN(value) && value >= 0) {
                e.target.value = value.toFixed(2);
            }
        });
    });
}

// Language toggle functionality
function initializeLanguageToggle() {
    const languageButtons = document.querySelectorAll('[href*="set_language"]');
    languageButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Add loading state
            const spinner = document.createElement('div');
            spinner.className = 'spinner-border spinner-border-sm';
            spinner.setAttribute('role', 'status');
            
            const originalContent = this.innerHTML;
            this.innerHTML = '';
            this.appendChild(spinner);
            this.disabled = true;
            
            // Restore content after navigation (in case of error)
            setTimeout(() => {
                this.innerHTML = originalContent;
                this.disabled = false;
            }, 3000);
        });
    });
}

// Loading states for buttons and forms
function initializeLoadingStates() {
    // Add loading state to form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                setButtonLoading(submitButton, true);
            }
        });
    });
    
    // Add loading state to navigation links
    const navLinks = document.querySelectorAll('.nav-link, .btn-primary');
    navLinks.forEach(link => {
        if (link.getAttribute('type') !== 'submit') {
            link.addEventListener('click', function() {
                if (!this.hasAttribute('data-bs-toggle')) {
                    setButtonLoading(this, true);
                }
            });
        }
    });
}

// Auto-refresh functionality
function initializeAutoRefresh() {
    // Auto-refresh timestamp on dashboard
    const lastUpdateElement = document.getElementById('lastUpdate');
    if (lastUpdateElement) {
        setInterval(() => {
            lastUpdateElement.textContent = new Date().toLocaleTimeString();
        }, 60000);
    }
    
    // Auto-refresh order status indicators
    const orderStatusElements = document.querySelectorAll('.order-status');
    if (orderStatusElements.length > 0) {
        setInterval(refreshOrderStatuses, 300000); // 5 minutes
    }
}

// POS interface specific functionality
function initializePOSInterface() {
    initializeProductGrid();
    initializeShoppingCart();
    initializeCustomerSearch();
    initializePaymentMethods();
}

// Product grid functionality
function initializeProductGrid() {
    const productCards = document.querySelectorAll('.product-card');
    productCards.forEach(card => {
        card.addEventListener('click', function() {
            // Add click animation
            this.style.transform = 'scale(0.95)';
            setTimeout(() => {
                this.style.transform = '';
            }, 150);
            
            // Add to cart if POS interface
            const productId = this.getAttribute('data-product-id');
            if (productId && typeof addToCart === 'function') {
                addToCart(parseInt(productId));
            }
        });
        
        // Add keyboard support
        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                this.click();
            }
        });
        
        // Make focusable for accessibility
        if (!card.hasAttribute('tabindex')) {
            card.setAttribute('tabindex', '0');
        }
    });
}

// Shopping cart functionality
function initializeShoppingCart() {
    const cartContainer = document.getElementById('cartItems');
    if (!cartContainer) return;
    
    // Add event delegation for cart item controls
    cartContainer.addEventListener('click', function(e) {
        if (e.target.matches('.btn-remove-item')) {
            const productId = e.target.getAttribute('data-product-id');
            if (productId && typeof removeFromCart === 'function') {
                removeFromCart(parseInt(productId));
            }
        }
    });
    
    cartContainer.addEventListener('change', function(e) {
        if (e.target.matches('.quantity-input')) {
            const productId = e.target.getAttribute('data-product-id');
            const quantity = parseInt(e.target.value);
            if (productId && typeof updateQuantity === 'function') {
                updateQuantity(parseInt(productId), quantity);
            }
        }
    });
}

// Customer search functionality
function initializeCustomerSearch() {
    const customerSearchInput = document.getElementById('customerSearch');
    if (!customerSearchInput) return;
    
    let searchTimeout;
    customerSearchInput.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        const query = this.value.trim();
        
        if (query.length >= 2) {
            searchTimeout = setTimeout(() => {
                searchCustomers(query);
            }, 300);
        } else {
            clearCustomerResults();
        }
    });
}

// Payment method selection
function initializePaymentMethods() {
    const paymentInputs = document.querySelectorAll('input[name="payment_method"]');
    paymentInputs.forEach(input => {
        input.addEventListener('change', function() {
            updatePaymentUI(this.value);
        });
    });
}

// Notification system
function initializeNotifications() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            fadeOutElement(alert);
        }, 5000);
    });
    
    // Initialize notification permissions for future use
    if ('Notification' in window && Notification.permission === 'default') {
        // Don't request immediately, wait for user interaction
        document.addEventListener('click', requestNotificationPermission, { once: true });
    }
}

// Accessibility enhancements
function initializeAccessibility() {
    // Add skip links
    addSkipLinks();
    
    // Enhance focus management for modals
    enhanceModalFocus();
    
    // Add ARIA labels where missing
    enhanceARIALabels();
    
    // Keyboard navigation for cards
    enhanceKeyboardNavigation();
}

// Utility Functions

// Set button loading state
function setButtonLoading(button, isLoading) {
    if (isLoading) {
        const originalContent = button.innerHTML;
        button.setAttribute('data-original-content', originalContent);
        
        const spinner = document.createElement('span');
        spinner.className = 'spinner-border spinner-border-sm me-2';
        spinner.setAttribute('role', 'status');
        
        button.innerHTML = '';
        button.appendChild(spinner);
        button.appendChild(document.createTextNode(getLocalizedText('Loading...', 'جارٍ التحميل...')));
        button.disabled = true;
    } else {
        const originalContent = button.getAttribute('data-original-content');
        if (originalContent) {
            button.innerHTML = originalContent;
            button.removeAttribute('data-original-content');
        }
        button.disabled = false;
    }
}

// Fade out element
function fadeOutElement(element) {
    element.style.transition = 'opacity 0.5s ease';
    element.style.opacity = '0';
    setTimeout(() => {
        if (element.parentNode) {
            element.parentNode.removeChild(element);
        }
    }, 500);
}

// Get localized text
function getLocalizedText(englishText, arabicText) {
    return currentLanguage === 'ar' && arabicText ? arabicText : englishText;
}

// Validate phone number
function validatePhoneNumber(phone) {
    const cleanPhone = phone.replace(/\D/g, '');
    
    // Egyptian mobile numbers
    if (cleanPhone.startsWith('01') && cleanPhone.length === 11) {
        return true;
    }
    
    // International format
    if (cleanPhone.startsWith('2') && cleanPhone.length >= 11 && cleanPhone.length <= 13) {
        return true;
    }
    
    // General international format
    if (cleanPhone.length >= 10 && cleanPhone.length <= 15) {
        return true;
    }
    
    return false;
}

// Validate email
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Format currency
function formatCurrency(amount, currency = 'ج.م') {
    const formatted = parseFloat(amount).toFixed(2);
    return currentLanguage === 'ar' ? `${formatted} ${currency}` : `${currency} ${formatted}`;
}

// Show notification
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            fadeOutElement(notification);
        }
    }, duration);
}

// Confirm dialog
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

// Search customers (placeholder for AJAX implementation)
function searchCustomers(query) {
    // This would be implemented with actual AJAX call
    console.log('Searching customers:', query);
}

// Clear customer search results
function clearCustomerResults() {
    const resultsContainer = document.getElementById('customerResults');
    if (resultsContainer) {
        resultsContainer.innerHTML = '';
    }
}

// Update payment UI based on selected method
function updatePaymentUI(paymentMethod) {
    // This would update UI based on payment method selection
    console.log('Payment method selected:', paymentMethod);
}

// Refresh order statuses
function refreshOrderStatuses() {
    // This would refresh order status indicators via AJAX
    console.log('Refreshing order statuses...');
}

// Request notification permission
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// Add skip links for accessibility
function addSkipLinks() {
    const skipLink = document.createElement('a');
    skipLink.href = '#main-content';
    skipLink.textContent = getLocalizedText('Skip to main content', 'انتقال إلى المحتوى الرئيسي');
    skipLink.className = 'visually-hidden-focusable btn btn-primary position-absolute';
    skipLink.style.cssText = 'top: 10px; left: 10px; z-index: 9999;';
    
    document.body.insertBefore(skipLink, document.body.firstChild);
}

// Enhance modal focus management
function enhanceModalFocus() {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('shown.bs.modal', function() {
            const firstFocusable = this.querySelector('input, button, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (firstFocusable) {
                firstFocusable.focus();
            }
        });
    });
}

// Enhance ARIA labels
function enhanceARIALabels() {
    // Add ARIA labels to buttons without text
    const iconButtons = document.querySelectorAll('button:not([aria-label]) > i.bi');
    iconButtons.forEach(button => {
        const icon = button.querySelector('i');
        let label = '';
        
        if (icon.classList.contains('bi-eye')) {
            label = getLocalizedText('View', 'عرض');
        } else if (icon.classList.contains('bi-pencil')) {
            label = getLocalizedText('Edit', 'تعديل');
        } else if (icon.classList.contains('bi-trash')) {
            label = getLocalizedText('Delete', 'حذف');
        } else if (icon.classList.contains('bi-plus')) {
            label = getLocalizedText('Add', 'إضافة');
        }
        
        if (label) {
            button.parentElement.setAttribute('aria-label', label);
        }
    });
}

// Enhance keyboard navigation
function enhanceKeyboardNavigation() {
    // Make card elements keyboard navigable
    const cards = document.querySelectorAll('.card[data-href]');
    cards.forEach(card => {
        card.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                const href = this.getAttribute('data-href');
                if (href) {
                    window.location.href = href;
                }
            }
        });
    });
}

// Export utility functions for global use
window.ElhosenyPOS = {
    showNotification,
    confirmAction,
    formatCurrency,
    validateEmail,
    validatePhoneNumber,
    setButtonLoading,
    getLocalizedText
};

// Service Worker registration (for future PWA capabilities)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('/static/sw.js')
            .then(function(registration) {
                console.log('ServiceWorker registration successful');
            })
            .catch(function(err) {
                console.log('ServiceWorker registration failed');
            });
    });
}

// Error handling
window.addEventListener('error', function(e) {
    console.error('JavaScript error:', e.error);
    // In production, you might want to send errors to a logging service
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    e.preventDefault();
});
