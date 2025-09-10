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

// Simple toast
window.dcToast = (msg)=>{
  const root = document.getElementById("dc-toasts");
  if (!root) return;
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  root.appendChild(el);
  setTimeout(()=> el.remove(), 2500);
};
