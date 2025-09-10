(function(){
  const paymentFields = new Set(['payment_method','payment_reference','payer_account_number','amount_bdt']);
  function setupWizard(form){
    const steps = Array.from(form.querySelectorAll('[data-step-panel]'));
    if (!steps.length) return;
    const tabs = form.querySelectorAll('.t-tab[data-step]');
    const nextBtn = form.querySelector('[data-next]');
    const backBtn = form.querySelector('[data-back]');
    const submitBtn = form.querySelector('[data-submit]');
    let current = Number((new URL(location.href)).hash.split('step=')[1]) || 1;
    function toStep(n){
      current = Math.max(1, Math.min(3, n));
      steps.forEach(s => s.hidden = Number(s.getAttribute('data-step-panel')) !== current);
      tabs.forEach(t => {
        const on = Number(t.getAttribute('data-step'))===current;
        t.classList.toggle('is-active', on);
        t.setAttribute('aria-current', on ? 'step' : 'false');
      });
      backBtn.disabled = current===1;
      nextBtn.hidden = current===3;
      submitBtn.hidden = current!==3;
      const live = form.querySelector('#aria-live,#t-aria-live');
      if (live) live.textContent = `Step ${current} of 3` + (current===1?': Player/Team':current===2?': Payment':': Review');
      const u = new URL(location.href); u.hash = `#step=${current}`; history.replaceState({},'',u);
      // focus first input in step
      const first = steps[current-1].querySelector('input,select,textarea,button');
      first && first.focus && first.focus();
    }
    tabs.forEach(t=>t.addEventListener('click',e=>{e.preventDefault(); /* stepper not clickable */ }));
    nextBtn && nextBtn.addEventListener('click',()=>{ if(validateStep()) toStep(current+1);});
    backBtn && backBtn.addEventListener('click',()=>toStep(current-1));
    function moveFields(){
      const all = form.querySelectorAll('.all-fields [data-fieldwrap]');
      all.forEach(w=>{
        const el = w.querySelector('input,select,textarea');
        if(!el) return;
        const name = el.getAttribute('name')||'';
        const target = paymentFields.has(name) ? 2 : 1;
        form.querySelector(`[data-step-panel="${target}"]`).appendChild(w);
      });
      // Amount field: set from data or server value; make readonly when paid
      const amt = form.querySelector('[name="amount_bdt"]');
      const paid = !!amt;
      if (amt){ amt.readOnly = true; }
      // Build review summary template
      const rv = form.querySelector('#review-summary, #t-review-summary');
      if (rv){
        const rows = Array.from(form.querySelectorAll('[data-fieldwrap] input, [data-fieldwrap] select')).slice(0,10);
        rv.innerHTML = rows.map(inp=>{
          const label = inp.closest('[data-fieldwrap]').querySelector('label')?.textContent || inp.name;
          let val = inp.value || '';
          if (inp.type==='checkbox' || inp.type==='radio') return '';
          return `<div class="flex items-center justify-between py-1 border-b border-border"><div class="text-muted text-sm">${label}</div><div class="text-sm">${val||'—'}</div></div>`;
        }).join('');
      }
    }
    function maskUppercase(e){ e.target.value = (e.target.value||'').toUpperCase().replace(/[^A-Z0-9-]/g,'');}
    function maskPhone(e){ e.target.value = (e.target.value||'').replace(/[^0-9+]/g,'').slice(0,14);}
    function maskAmount(e){ let v=(e.target.value||'').replace(/[^0-9]/g,''); e.target.value=v.replace(/\B(?=(\d{3})+(?!\d))/g, ',');}
    form.addEventListener('input', (e)=>{
      const n = e.target.name||'';
      if (n==='payment_reference') maskUppercase(e);
      if (n==='payer_account_number') maskPhone(e);
      if (n==='amount_bdt') maskAmount(e);
      validateStep();
    });
    function validateStep(){
      // Basic required checks in current step
      const panel = form.querySelector(`[data-step-panel="${current}"]`);
      const summaryTop = panel.querySelector('.step-errors') || document.createElement('div');
      summaryTop.className='step-errors text-red-400 text-sm'; summaryTop.innerHTML='';
      if (!panel.querySelector('.step-errors')) panel.prepend(summaryTop);
      let ok = true;
      const inputs = panel.querySelectorAll('input,select,textarea');
      inputs.forEach(inp=>{
        const wrap = inp.closest('[data-fieldwrap]')||inp.closest('div');
        const errSel = wrap && wrap.querySelector('.inline-error');
        if (errSel) errSel.remove();
        const req = inp.required || inp.getAttribute('aria-required')==='true';
        if (req && !inp.value){ ok=false; if(wrap){ const p=document.createElement('p'); p.className='inline-error text-xs text-red-400'; p.textContent='This field is required'; wrap.appendChild(p);} }
        if (inp.name==='payment_reference' && inp.value && !/^[A-Z0-9-]{6,}$/.test(inp.value)){ ok=false; if(wrap){ const p=document.createElement('p'); p.className='inline-error text-xs text-red-400'; p.textContent='Use uppercase letters/numbers (min 6)'; wrap.appendChild(p);} }
        if (inp.name==='payer_account_number' && inp.value){ const re=/(?:^|\s)(?:\+?88)?01[3-9]\d{8}$/; if(!re.test(inp.value)){ ok=false; if(wrap){ const p=document.createElement('p'); p.className='inline-error text-xs text-red-400'; p.textContent='Enter a valid BD mobile number'; wrap.appendChild(p);} } }
      });
      if (current===3){
        const consents = form.querySelectorAll('[data-consent]');
        ok = ok && Array.from(consents).every(c=>c.checked);
        form.querySelector('[data-submit]').disabled = !ok;
      } else if (current===2){
        // If entry is free, allow skipping payment requirements
        const amt = form.querySelector('[name="amount_bdt"]');
        const hasAmt = amt && amt.value && amt.value.replace(/[^0-9]/g,'')!=='0';
        if (!hasAmt){ ok = true; const pr = panel.querySelectorAll('[data-fieldwrap]'); pr.forEach(w=>w.classList.add('opacity-70')); }
      } else {
        if (form.querySelector('[data-next]')) form.querySelector('[data-next]').disabled = !ok;
      }
      if (!ok){ summaryTop.textContent = 'Please correct the highlighted fields.'; const firstInvalid = panel.querySelector('.inline-error'); if(firstInvalid){ const parent = firstInvalid.closest('[data-fieldwrap]')||panel; (parent.querySelector('input,select,textarea')||parent).focus(); } }
      return ok;
    }
    // initialize
    moveFields();
    const h = (new URL(location.href)).hash; const m = /step=(\d+)/.exec(h); if(m) current=Number(m[1]);
    toStep(current);
  }
  document.querySelectorAll('form[data-wizard]').forEach(setupWizard);

  // Drop-zone: simple preview and guard
  document.addEventListener('change', (e)=>{
    const input = e.target;
    if (input.type==='file'){
      const f = input.files && input.files[0]; if (!f) return;
      const okType = /\.(png|jpe?g|webp|pdf)$/i.test(f.name);
      const okSize = f.size <= 5*1024*1024;
      const wrap = input.closest('[data-fieldwrap]')||input.parentElement;
      wrap.querySelectorAll('.inline-error').forEach(n=>n.remove());
      if (!okType || !okSize){ const p=document.createElement('p'); p.className='inline-error text-xs text-red-400'; p.textContent = !okType? 'Allowed: PNG/JPG/WEBP/PDF' : 'File must be ≤ 5 MB'; wrap.appendChild(p); input.value=''; }
      else {
        let prev = wrap.querySelector('.file-preview'); if (!prev){ prev=document.createElement('div'); prev.className='file-preview text-xs text-muted mt-1'; wrap.appendChild(prev); }
        prev.textContent = f.name + ' (' + Math.round(f.size/1024) + ' KB)';
      }
    }
  });
})();
