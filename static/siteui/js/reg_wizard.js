(function () {
  const form = document.getElementById('reg-form');
  if (!form) return;

  const steps = Array.from(document.querySelectorAll('[data-step]'));
  const sec1 = document.getElementById('step-1');
  const sec2 = document.getElementById('step-2');
  const sec3 = document.getElementById('step-3');

  function go(n) {
    [sec1, sec2, sec3].forEach((el, i) => {
      if (!el) return;
      el.classList.toggle('hidden', i !== (n - 1));
    });
    steps.forEach((s, i) => {
      s.classList.toggle('bg-blue-600', i === (n - 1));
      s.classList.toggle('text-white', i === (n - 1));
      s.classList.toggle('bg-slate-200', i !== (n - 1));
    });
    localStorage.setItem('reg_step', String(n));
  }

  form.addEventListener('click', (e) => {
    const next = e.target.closest('[data-next]');
    const prev = e.target.closest('[data-prev]');
    if (next) { e.preventDefault(); go(Math.min(3, (Number(localStorage.getItem('reg_step')||'1') + 1))); }
    if (prev) { e.preventDefault(); go(Math.max(1, (Number(localStorage.getItem('reg_step')||'1') - 1))); }
  });

  go(Number(localStorage.getItem('reg_step') || '1'));
})();
