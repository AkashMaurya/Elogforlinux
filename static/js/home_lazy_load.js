document.addEventListener('DOMContentLoaded', function() {
  // Intersection Observer for lazy loading images
  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          // Check if src needs to be set from data-src (if using that pattern)
          // In this case, we are just adding a class to trigger CSS opacity transition
          img.classList.add('loaded');
          observer.unobserve(img); // Stop observing once loaded
        }
      });
    }, {
      rootMargin: '50px 0px', // Start loading images 50px before they enter viewport
      threshold: 0.01 // Trigger even if only 1% is visible
    });

    // Observe all images with lazy-image class
    document.querySelectorAll('.lazy-image').forEach(img => {
      imageObserver.observe(img);
    });

  } else {
    // Fallback for browsers that don't support Intersection Observer
    // Load all images immediately
    console.warn('Intersection Observer not supported, loading all images.');
    document.querySelectorAll('.lazy-image').forEach(img => {
      img.classList.add('loaded');
    });
  }
});