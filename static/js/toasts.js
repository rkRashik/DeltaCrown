window.toast = (msg, kind="info") => {
  const root = document.getElementById("toast-root");
  if(!root) return;
  const el = document.createElement("div");
  el.className = "card shadow border border-dc-border bg-dc-surface mb-2";
  el.setAttribute("role","status");
  el.innerHTML = `<div class="card-b"><strong class="mr-2">${kind.toUpperCase()}</strong> ${msg}</div>`;
  root.appendChild(el);
  setTimeout(()=>{ el.remove(); }, 3000);
};
