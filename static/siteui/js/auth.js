// Password show/hide
(function(){
  document.addEventListener("click", (e)=>{
    const btn = e.target.closest("[data-toggle-password]");
    if (!btn) return;
    const inputId = btn.getAttribute("data-toggle-password");
    const input = document.getElementById(inputId);
    if (!input) return;
    const t = input.getAttribute("type") === "password" ? "text" : "password";
    input.setAttribute("type", t);
    btn.setAttribute("aria-pressed", t === "text" ? "true" : "false");
  });
})();

// Legacy toast removed - now using DC.toast from notifications.js
// Kept for backward compatibility, but redirects to new system
window.dcToast = (msg) => {
  if (window.DC && DC.toast) {
    DC.toast.info(msg);
  } else {
    console.warn('Toast system not loaded');
  }
};
