/**
 * DeltaCrown Organization Detail Page
 * Extracted from: templates/My drafts/Org_create/Org_detail.html
 * Handles: Navigation, smooth scrolling, animations
 */

document.addEventListener('DOMContentLoaded', () => {

    // --- NAVIGATION TAB FILTERING ---
    const links = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('main section');

    links.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();

            // 1. Update UI
            links.forEach(l => {
                l.classList.remove('active', 'border-delta-gold', 'text-white');
                l.classList.add('text-slate-400', 'border-transparent');
            });
            e.currentTarget.classList.add('active', 'border-delta-gold', 'text-white');
            e.currentTarget.classList.remove('text-slate-400', 'border-transparent');

            // 2. Scroll to Section (Smooth)
            const targetId = e.currentTarget.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);

            if (targetSection) {
                const navHeight = 100; // Approx height of sticky nav
                const targetPosition = targetSection.getBoundingClientRect().top + window.pageYOffset - navHeight;

                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // --- STICKY NAV VISUALS ---
    const nav = document.querySelector('nav');
    if (nav) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                nav.classList.add('bg-delta-base/95', 'backdrop-blur-xl', 'shadow-lg');
                nav.classList.remove('border-transparent');
            } else {
                nav.classList.remove('bg-delta-base/95', 'backdrop-blur-xl', 'shadow-lg');
                nav.classList.add('border-transparent');
            }
        });
    }

});
