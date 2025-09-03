// Mobile drawer + focus trap + scroll-shrink + generic dropdowns (bell/profile)
(function(){
  const header = document.getElementById("dc-header");
  const btn = document.getElementById("dc-menu-btn");
  const drawer = document.getElementById("dc-mobile-drawer");
  const panel = drawer ? drawer.querySelector('[role="dialog"]') : null;

  // ---------- Mobile Drawer ----------
  if (btn && drawer && panel) {
    let open = false;
    let lastFocus = null;

    function openDrawer(){
      lastFocus = document.activeElement;
      drawer.classList.remove("hidden");
      drawer.removeAttribute("aria-hidden");
      btn.setAttribute("aria-expanded", "true");
      const first = panel.querySelector("a, button, [tabindex]:not([tabindex='-1'])");
      if (first) first.focus();
      document.addEventListener("keydown", trap, true);
    }
    function closeDrawer(){
      drawer.classList.add("hidden");
      drawer.setAttribute("aria-hidden", "true");
      btn.setAttribute("aria-expanded", "false");
      document.removeEventListener("keydown", trap, true);
      if (lastFocus) lastFocus.focus();
    }
    function trap(e){
      if (e.key === "Escape") { e.preventDefault(); closeDrawer(); return; }
      if (e.key !== "Tab") return;
      const focusables = panel.querySelectorAll("a, button, input, select, textarea, [tabindex]:not([tabindex='-1'])");
      const list = Array.from(focusables).filter(el => !el.hasAttribute("disabled"));
      if (!list.length) return;
      const first = list[0], last = list[list.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
    btn.addEventListener("click", () => { open ? closeDrawer() : openDrawer(); open = !open; });
    drawer.addEventListener("click", (e) => { if (e.target && e.target.getAttribute("data-close") === "drawer") { open = false; closeDrawer(); } });
  }

  // ---------- Scroll shrink ----------
  if (header) {
    let last = 0;
    window.addEventListener("scroll", () => {
      const y = window.scrollY || 0;
      const goingDown = y > last;
      last = y;
      if (y > 8 && goingDown) header.classList.add("is-shrunk");
      else if (y < 8) header.classList.remove("is-shrunk");
    }, { passive: true });
  }

  // ---------- Dropdowns (Bell & Profile) ----------
  function makeDropdown(buttonId, menuId) {
    const btn = document.getElementById(buttonId);
    const menu = document.getElementById(menuId);
    if (!btn || !menu) return;

    function close() {
      menu.classList.add("hidden");
      btn.setAttribute("aria-expanded", "false");
      document.removeEventListener("keydown", onKeyDown, true);
      document.removeEventListener("click", onDocClick, true);
    }
    function open() {
      menu.classList.remove("hidden");
      btn.setAttribute("aria-expanded", "true");
      document.addEventListener("keydown", onKeyDown, true);
      setTimeout(() => document.addEventListener("click", onDocClick, true), 0);
    }
    function onKeyDown(e) {
      if (e.key === "Escape") { e.preventDefault(); close(); btn.focus(); }
    }
    function onDocClick(e) {
      if (!menu.contains(e.target) && !btn.contains(e.target)) close();
    }

    btn.addEventListener("click", () => {
      const isOpen = btn.getAttribute("aria-expanded") === "true";
      if (isOpen) close(); else open();
    });
  }

  makeDropdown("dc-bell-btn", "dc-bell-menu");
  makeDropdown("dc-prof-btn", "dc-prof-menu");
})();
