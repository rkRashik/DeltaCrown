/* DeltaCrown Registration Wizard - v1.1.0 (Team • Payment • Review)
   - Real step gating with inline errors
   - Hash persistence (#step=1|2|3)
   - Works even if template wasn't split into steps
   - No backend changes or field renames required
*/
(function(){
  window.DC_REG_WIZARD_VERSION = "1.1.0";
  document.addEventListener("DOMContentLoaded", initRegWizard);

  function $(sel, root){ return (root||document).querySelector(sel); }
  function $all(sel, root){ return Array.from((root||document).querySelectorAll(sel)); }

  function initRegWizard(){
    const form = $('#solo-form') || $('#team-form') || document.querySelector('form[action*="/register"]');
    if(!form) return;

    // Create or locate step containers
    const steps = ensureStepContainers(form);
    ensureStepper(form);
    ensureNavButtons(form);

    // Payment amount (paid vs free)
    prefillDynamic(form);

    // Bind navigation and validation
    bindNav(form);

    // If server returned errors, prefer the step that contains them
    const errStep = detectServerErrorStep(form);
    // Start at hash step, error step, or 1
    const n = readHashStep() || errStep || 1;
    goToStep(form, n, /*announce*/false);
    if (errStep){
      const panel = form.querySelector(`[data-step-panel="${errStep}"]`) || form.querySelector(`[data-step="${errStep}"]`);
      try { panel && panel.scrollIntoView({behavior:'smooth', block:'start'}); } catch(e){}
    }
  }

  // ---------- Step containers ----------
  function ensureStepContainers(form){
    let s1 = form.querySelector('[data-step="1"]') || form.querySelector('[data-step-panel="1"]');
    let s2 = form.querySelector('[data-step="2"]') || form.querySelector('[data-step-panel="2"]');
    let s3 = form.querySelector('[data-step="3"]') || form.querySelector('[data-step-panel="3"]');

    if (s1 && s2 && s3) return [s1,s2,s3];

    // Create wrappers
    s1 = s1 || document.createElement('section'); s1.setAttribute('data-step','1');
    s2 = s2 || document.createElement('section'); s2.setAttribute('data-step','2');
    s3 = s3 || document.createElement('section'); s3.setAttribute('data-step','3');

    // Titles (a11y)
    if(!s1.querySelector('h2')){ const h=document.createElement('h2'); h.className='wizard-h'; h.textContent='Team'; s1.prepend(h); }
    if(!s2.querySelector('h2')){ const h=document.createElement('h2'); h.className='wizard-h'; h.textContent='Payment'; s2.prepend(h); }
    if(!s3.querySelector('h2')){ const h=document.createElement('h2'); h.className='wizard-h'; h.textContent='Review & Submit'; s3.prepend(h); }

    // Insert wrappers at the top of the form
    if(!form.querySelector('[data-step="1"]') && !form.querySelector('[data-step-panel="1"]')){
      const anchor = form.firstElementChild;
      form.insertBefore(s3, anchor);
      form.insertBefore(s2, s3);
      form.insertBefore(s1, s2);
    }

    // Move fields by name pattern if they are loose
    const P_STEP1 = /(existing[_-]?team|team[_-]?|captain|display[_-]?name)/i; // captain consent stays here
    const P_STEP2 = /(payment|payer|phone|amount|transaction|txn|proof)/i;
    const P_STEP3 = /(agree|consent)/i;

    $all('input,select,textarea', form).forEach(el=>{
      // Skip buttons & CSRF
      if (el.type === 'hidden' || el.type === 'submit' || el.name === 'csrfmiddlewaretoken') return;
      const name = (el.name || el.id || '').toLowerCase();
      if(!name) return;
      if(P_STEP1.test(name)) s1.appendChild(wrapField(el));
      else if(P_STEP2.test(name)) s2.appendChild(wrapField(el));
      else if(P_STEP3.test(name)) s3.appendChild(wrapField(el));
    });

    // Hide other steps initially
    s2.hidden = true; s3.hidden = true;

    // Live region for announcements
    if(!form.querySelector('[data-wizard-live]')){
      const live = document.createElement('div');
      live.setAttribute('data-wizard-live','');
      live.setAttribute('role','status');
      live.setAttribute('aria-live','polite');
      live.className = 'sr-only';
      form.prepend(live);
    }
    // Error summary region
    if(!form.querySelector('[data-wizard-errors]')){
      const sum = document.createElement('div');
      sum.setAttribute('data-wizard-errors','');
      sum.className = 'wizard-errors';
      form.prepend(sum);
    }

    return [s1,s2,s3];
  }

  function wrapField(el){
    const row = document.createElement('div');
    row.className = 'form-row';
    const label = el.id ? document.querySelector(`label[for="${el.id}"]`) : null;
    if(label && label.parentElement !== row){
      row.appendChild(label);
    } else if (label==null && el.name){
      const l = document.createElement('label');
      l.className = 'form-label';
      l.textContent = prettify(el.name);
      if(el.id){ l.setAttribute('for', el.id); }
      row.appendChild(l);
    }
    row.appendChild(el);
    return row;
  }

  function prettify(s){ try{ return s.replace(/[_-]+/g,' ').replace(/\b\w/g,c=>c.toUpperCase()); }catch(e){ return s; } }

  // ---------- Stepper ----------
  function ensureStepper(form){
    let bar = form.previousElementSibling;
    if(!bar || !bar.hasAttribute('data-reg-stepper')){
      bar = document.createElement('nav');
      bar.setAttribute('data-reg-stepper','');
      bar.className = 'wizard-stepper';
      bar.innerHTML = `
        <ol class="wizard-steps" role="tablist">
          <li class="wizard-step" data-step-index="1"><span class="wizard-dot" aria-hidden="true"></span><span class="wizard-label">Team</span></li>
          <li class="wizard-step" data-step-index="2"><span class="wizard-dot" aria-hidden="true"></span><span class="wizard-label">Payment</span></li>
          <li class="wizard-step" data-step-index="3"><span class="wizard-dot" aria-hidden="true"></span><span class="wizard-label">Review</span></li>
        </ol>`;
      form.parentElement.insertBefore(bar, form);
    }
    return bar;
  }

  function ensureNavButtons(form){
    let back = form.querySelector('[data-back]');
    let next = form.querySelector('[data-next]');
    let submit = form.querySelector('[data-submit]');
    if(!back || !next || !submit){
      const row = document.createElement('div');
      row.className = 'flex items-center justify-between mt-2';
      row.innerHTML = `
        <button class="btn-ghost" type="button" data-back disabled>Back</button>
        <div class="flex gap-2">
          <button class="btn-secondary" type="button" data-next>Next</button>
          <button class="btn-primary" type="submit" data-submit disabled>Submit Registration</button>
        </div>`;
      form.appendChild(row);
      back = row.querySelector('[data-back]'); next = row.querySelector('[data-next]'); submit = row.querySelector('[data-submit]');
    }
  }

  function announce(form, msg){ const live=form.querySelector('[data-wizard-live]'); if(live){ live.textContent=''; setTimeout(()=>{ live.textContent=msg; }, 0);} }
  function setHashStep(n){ try{ history.replaceState(null,'',`#step=${n}`); }catch(e){} }
  function goToStep(form, n, announceIt=true){
    const steps = [1,2,3].map(i=> form.querySelector(`[data-step="${i}"]`) || form.querySelector(`[data-step-panel="${i}"]`) );
    steps.forEach((s,i)=>{ if(s){ s.hidden = (i+1)!==n; } });
    const back = form.querySelector('[data-back]');
    const next = form.querySelector('[data-next]');
    const submit = form.querySelector('[data-submit]');
    if(back) back.disabled = (n===1);
    if(next) next.hidden = (n===3);
    if(submit) submit.disabled = (n!==3);
    setHashStep(n);
    if(announceIt) announce(form, `Step ${n} of 3`);
    highlightStepper(form, n);
  }
  function highlightStepper(form, n){
    const bar = form.parentElement.querySelector('[data-reg-stepper]'); if(!bar) return;
    $all('.wizard-step', bar).forEach(li=>{
      const idx = Number(li.getAttribute('data-step-index'));
      li.classList.toggle('is-active', idx===n);
      li.classList.toggle('is-done', idx<n);
    });
  }
  function bindNav(form){
    const back = form.querySelector('[data-back]');
    const next = form.querySelector('[data-next]');
    if(back){ back.addEventListener('click', ()=>{ const n=currentStepFromHash(); goToStep(form, Math.max(1, n-1)); }); }
    if(next){ next.addEventListener('click', ()=>{
      const n = currentStepFromHash();
      const val = validateStep(form, n);
      renderErrors(form, val);
      if(val.ok){ goToStep(form, Math.min(3, n+1)); }
    }); }
    form.addEventListener('submit', (e)=>{
      const n = 3; const val = validateStep(form, n);
      renderErrors(form, val);
      if(!val.ok){ e.preventDefault(); goToStep(form, n); }
    });
  }

  function validateStep(form, step){
    const errors = [];
    const find = (sels)=> sels.map(s=>form.querySelector(s)).find(Boolean);

    if (step===1){
      const existingTeam = find(['[name*="existing_team" i]','[id*="existing"][id*="team" i]','select[placeholder*="team" i]','[name="team"]']);
      const teamName = find(['[name*="team_name" i]','[id*="team"][id*="name" i]']);
      const hasExisting = !!(existingTeam && existingTeam.value);
      const hasName = !!(teamName && (teamName.value||'').trim().length >= 3);
      if (!hasExisting && teamName && !hasName){ errors.push({el: teamName||existingTeam||form, message: 'Select a team or enter a team name (≥ 3 chars).'}); }
      const cap = find(['#id_agree_captain_consent','[name*="agree_captain" i]']);
      if (cap && !cap.checked) errors.push({el: cap, message: 'Captain consent is required.'});
    }

    if (step===2){
      const amountEl = find(['[name*="amount_bdt" i]','[name*="entry_fee" i]','[name="amount" i]']);
      const amount = amountEl ? Number((amountEl.value||'').replace(/[^\d.]/g,'')) : (window.DC_ENTRY_AMOUNT||0);
      const isPaid = amount > 0;

      if (isPaid){
        const method = find(['[name*="payment_method" i]']);
        const phone  = find(['[name*="payer" i]','[name*="phone" i]']);
        const txn    = find(['[name*="transaction" i]','[name*="txn" i]','[name*="reference" i]']);
        const proof  = form.querySelector('input[type="file"][name*="proof" i]');

        const BD = /^(?:\+?88)?01[3-9]\d{8}$/;
        if (!(method && method.value)) errors.push({el: method||form, message: 'Choose a payment method.'});
        if (!(phone && BD.test(phone.value||''))) errors.push({el: phone||form, message: 'Enter a valid Bangladesh mobile number.'});
        if (!(txn && (txn.value||'').length >= 6)) errors.push({el: txn||form, message: 'Enter a valid Transaction ID.'});
        if (proof && proof.files && proof.files[0]){
          const f = proof.files[0];
          const okType = f.type.startsWith('image/') || f.type === 'application/pdf';
          if (f.size > 5*1024*1024) errors.push({el: proof, message: 'Proof must be ≤ 5MB.'});
          if (!okType) errors.push({el: proof, message: 'Proof must be an image or PDF.'});
        }
      }
    }

    if (step===3){
      const c1 = form.querySelector('#id_agree_rules, [name*="agree_rules" i]');
      const c2 = form.querySelector('#id_agree_enforcement, [name*="agree_enforcement" i]');
      const c3 = form.querySelector('#id_agree_no_cheat, [name*="agree_no_cheat" i], #id_agree_payout_policy, [name*="agree_payout" i]');
      if (c1 && !c1.checked) errors.push({el: c1, message: 'You must agree to the rules.'});
      if (c2 && !c2.checked) errors.push({el: c2, message: 'You must agree to fair play enforcement.'});
      if (c3 && !c3.checked) errors.push({el: c3, message: 'You must confirm the no-cheat / payout policy.'});
    }

    return { ok: errors.length===0, errors };
  }

  function renderErrors(form, result){
    // Clear previous
    $all('.form-err', form).forEach(e=>e.remove());
    const sum = form.querySelector('[data-wizard-errors]');
    if (sum) sum.innerHTML = '';

    if (result.ok) return;

    // Inline
    result.errors.forEach(({el, message})=>{
      if(!el) return;
      const row = el.closest('.form-row') || el.parentElement;
      const p = document.createElement('div');
      p.className = 'form-err';
      p.textContent = message;
      (row||el).appendChild(p);
    });

    // Summary
    if (sum){
      const ul = document.createElement('ul');
      ul.className = 'form-err-list';
      result.errors.forEach(({message})=>{
        const li = document.createElement('li'); li.textContent = message; ul.appendChild(li);
      });
      sum.appendChild(ul);
    }
  }

  function prefillDynamic(form){
    // Paid vs Free: if amount is 0 hide payment fields
    const amountEl = form.querySelector('[name*="amount_bdt" i], [name*="entry_fee" i], [name="amount" i]');
    let amount = 0;
    if (amountEl){
      const v = (amountEl.value||'').replace(/[^\d.]/g,'');
      amount = Number(v||0);
      amountEl.readOnly = true;
    } else if (typeof window.DC_ENTRY_AMOUNT === 'number') {
      amount = window.DC_ENTRY_AMOUNT;
    }

    if (amount <= 0){
      const step2 = form.querySelector('[data-step="2"]') || form.querySelector('[data-step-panel="2"]');
      if (step2){
        $all('[name*="payment" i], [name*="payer" i], [name*="phone" i], [name*="transaction" i], [name*="txn" i], input[type="file"][name*="proof" i]', step2).forEach(el=>{
          el.closest('.form-row')?.setAttribute('hidden','');
        });
      }
    }
  }

  function readHashStep(){
    const m = /step=(\d+)/.exec(location.hash||''); return m ? Number(m[1]) : null;
  }
  function currentStepFromHash(){ return readHashStep() || 1; }

  function detectServerErrorStep(form){
    const panels = [1,2,3].map(i=>({i, el: form.querySelector(`[data-step-panel="${i}"]`) || form.querySelector(`[data-step="${i}"]`)}));
    const hasErr = (root)=> !!(root && (root.querySelector('.form-errors, .form-err, .errorlist, .text-red-400, [aria-invalid="true"]')));
    for (const p of panels){ if (hasErr(p.el)) return p.i; }
    // Also check summary level errors at top but try to infer by common field names
    if (form.querySelector('.form-errors, .form-err-list')){
      // default to step 1 when unknown
      return 1;
    }
    return null;
  }

})();
