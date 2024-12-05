document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh orders list every 5 minutes
    if (window.location.pathname.includes('/admin/shop/order/')) {
        setInterval(function() {
            location.reload();
        }, 300000);
    }
    
    // Confirm before marking products as trending
    document.querySelectorAll('[name="action"]').forEach(function(select) {
        select.addEventListener('change', function(e) {
            if (e.target.value === 'make_trending') {
                if (!confirm('Are you sure you want to mark these products as trending?')) {
                    e.preventDefault();
                    e.target.value = '';
                }
            }
        });
    });
}); 