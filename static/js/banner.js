document.addEventListener('DOMContentLoaded', function() {
    // Lazy load banner images
    const bannerImages = document.querySelectorAll('.banner-item img');
    bannerImages.forEach(img => {
        img.setAttribute('loading', 'lazy');
    });

    // Initialize all carousels with custom options
    const carousels = document.querySelectorAll('.carousel');
    carousels.forEach(carousel => {
        const position = carousel.dataset.position;
        new bootstrap.Carousel(carousel, {
            interval: position === 'main_hero' ? 5000 : 3000,
            pause: 'hover',
            keyboard: true,
            touch: true,
            wrap: true
        });
    });
}); 