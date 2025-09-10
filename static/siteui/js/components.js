// Drawer open/close via data-open-drawer="TARGET_ID" and [data-close-drawer]
(function () {
  document.addEventListener("click", (e) => {
    const openBtn = e.target.closest("[data-open-drawer]");
    if (openBtn) {
      const id = openBtn.getAttribute("data-open-drawer");
      const drawer = document.getElementById(id);
      if (!drawer) return;
      drawer.hidden = false;
      requestAnimationFrame(() => drawer.classList.add("open"));
      openBtn.setAttribute("aria-expanded", "true");
      drawer.querySelector("a,button")?.focus({ preventScroll: true });
      return;
    }
    const closeBtn = e.target.closest("[data-close-drawer]");
    if (closeBtn) {
      const panel = closeBtn.closest(".mobile-drawer");
      if (!panel) return;
      panel.classList.remove("open");
      panel.addEventListener("transitionend", () => (panel.hidden = true), { once: true });
    }
  });
})();
