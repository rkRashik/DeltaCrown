
/* ============================================
   GLASSY NAVBAR SCROLL EFFECT
   ============================================ */

document.addEventListener('DOMContentLoaded', function() {
    const desktopNav = document.querySelector('.unified-nav-desktop');
    const mobileNav = document.querySelector('.unified-nav-mobile__top');
    
    let lastScrollY = window.pageYOffset;
    let ticking = false;
    
    function updateNavbar() {
        const scrollY = window.pageYOffset;
        
        // Add/remove scrolled class based on scroll position
        if (scrollY > 50) {
            if (desktopNav) desktopNav.classList.add('scrolled');
            if (mobileNav) mobileNav.classList.add('scrolled');
        } else {
            if (desktopNav) desktopNav.classList.remove('scrolled');
            if (mobileNav) mobileNav.classList.remove('scrolled');
        }
        
        lastScrollY = scrollY;
        ticking = false;
    }
    
    function requestTick() {
        if (!ticking) {
            window.requestAnimationFrame(updateNavbar);
            ticking = true;
        }
    }
    
    window.addEventListener('scroll', requestTick, { passive: true });
    
    // Initial check
    updateNavbar();
});
