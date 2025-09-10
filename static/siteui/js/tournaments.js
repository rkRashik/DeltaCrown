// Tabs: activate on click + highlight
(function(){
  const tabs = document.querySelectorAll(".t-tab");
  if (!tabs.length) return;
  function activate(link){
    tabs.forEach(t => t.classList.remove("is-active"));
    link.classList.add("is-active");
  }
  tabs.forEach(t => t.addEventListener("click", (e) => {
    activate(t);
  }));
})();

// Filter bar: auto-submit on change (progressive enhancement)
(function(){
  const form = document.getElementById("t-filter");
  if (!form) return;
  form.addEventListener("change", (e) => {
    const target = e.target;
    if (target.matches("select") || target.matches("input[type=radio]")) {
      form.requestSubmit ? form.requestSubmit() : form.submit();
    }
  });
})();
