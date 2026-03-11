// planner/static/planner/js/itinerary.js

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    initializeTooltips();
    
    // Add print functionality
    setupPrintFunctionality();
    
    // Add analytics for map clicks
    trackMapClicks();
    
    // Add smooth scrolling for better UX
    setupSmoothScrolling();
});

function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function setupPrintFunctionality() {
    const printButton = document.getElementById('printItinerary');
    if (printButton) {
        printButton.addEventListener('click', function() {
            window.print();
        });
    }
}

function trackMapClicks() {
    var googleMapsLinks = document.querySelectorAll('a[href*="maps.google.com"], a[href*="google.com/maps"]');
    googleMapsLinks.forEach(function(link) {
        link.addEventListener('click', function(event) {
            // You can integrate with Google Analytics here
            console.log('Google Maps link clicked:', this.href);
            
            // Optional: Send analytics data
            // gtag('event', 'map_click', {
            //     'event_category': 'engagement',
            //     'event_label': this.href
            // });
        });
    });
}

function setupSmoothScrolling() {
    // Smooth scroll to top when printing
    window.addEventListener('beforeprint', function() {
        window.scrollTo(0, 0);
    });
}

// Additional utility functions
function shareItinerary() {
    if (navigator.share) {
        navigator.share({
            title: 'My Travel Itinerary',
            text: 'Check out my travel itinerary!',
            url: window.location.href
        })
        .then(() => console.log('Successful share'))
        .catch((error) => console.log('Error sharing:', error));
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(window.location.href).then(function() {
            alert('Itinerary link copied to clipboard!');
        });
    }
}

// Export functions for potential future use
window.ItineraryUtils = {
    shareItinerary: shareItinerary,
    printItinerary: function() { window.print(); }
};