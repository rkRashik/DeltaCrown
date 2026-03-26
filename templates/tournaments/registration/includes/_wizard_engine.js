/* ═══════════════════════════════════════════════════════════════
   DeltaCrown — Smart Registration Wizard Engine v3
   Complete rewrite for the new registration flow:
     Team:  Select Team → Squad Lineup → Coordinator → Extras → Payment → Review
     Solo:  Profile → Contact Info → Extras → Payment → Review
     Guest: Guest Team → Coordinator → Extras → Payment → Review
   ═══════════════════════════════════════════════════════════════ */

(function() {
    'use strict';

    // ── Configuration ─────────────────────────────────────────
    const stepsConfig = JSON.parse(document.getElementById('wizard-steps-config').textContent);
    const runtimeConfig = JSON.parse(document.getElementById('runtime-config').textContent);
    const TOTAL_STEPS = stepsConfig.length;

    let currentStep = 0;
    let stepValidity = new Array(TOTAL_STEPS).fill(false);
    let guestMemberCount = 1;

    // ── Init ──────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function() {
        buildSidebar();
        const requestedStepKey = (runtimeConfig.startStepKey || '').toString().trim();
        const requestedStepIndex = requestedStepKey
            ? Math.max(0, stepsConfig.findIndex(step => step.key === requestedStepKey))
            : 0;
        showStep(requestedStepIndex);
        updateRosterCounts();
        initBioCounter();
        lucide.createIcons();

        // Pre-populate first mobile payment tab details (without selecting the radio)
        const firstMobileTab = document.querySelector('.mobile-tab');
        if (firstMobileTab) {
            const subInput = document.getElementById('payment-sub-method');
            if (subInput) subInput.value = firstMobileTab.dataset.mobileMethod;
        }

        // Auto-validate first step after brief delay
        setTimeout(() => checkStep(stepsConfig[requestedStepIndex]?.key || stepsConfig[0].key), 150);
    });

    // ══════════════════════════════════════════════════════════
    //  SIDEBAR & MOBILE PROGRESS
    // ══════════════════════════════════════════════════════════

    function buildSidebar() {
        const container = document.getElementById('sidebar-steps');
        if (!container) return;
        container.innerHTML = '';

        stepsConfig.forEach((step, idx) => {
            const el = document.createElement('div');
            el.className = 'flex items-center gap-3 cursor-pointer group p-2.5 rounded-xl transition-all duration-300 hover:bg-white/[0.03]';
            el.setAttribute('data-sidebar-step', idx);
            el.onclick = () => goToStep(idx);

            el.innerHTML = `
                <div class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all duration-500 step-indicator relative"
                     style="border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03);" data-step-indicator="${idx}">
                    <i data-lucide="${step.icon}" class="w-3.5 h-3.5 text-slate-500 step-icon"></i>
                    <div class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-green-500 items-center justify-center hidden step-check-badge" style="box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);">
                        <i data-lucide="check" class="w-2.5 h-2.5 text-white"></i>
                    </div>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between">
                        <p class="text-xs font-bold text-slate-400 group-hover:text-white transition-colors step-label truncate">${step.label}</p>
                        <span class="text-[9px] font-mono text-slate-600 step-number">${idx + 1}/${stepsConfig.length}</span>
                    </div>
                    <p class="text-[10px] text-slate-500 mt-0.5 truncate step-subtitle">${step.subtitle}</p>
                </div>
            `;
            container.appendChild(el);
        });

        lucide.createIcons({ attrs: { class: '' }, nameAttr: 'data-lucide' });

        // Build mobile progress dots
        const mobileContainer = document.getElementById('mobile-steps');
        if (mobileContainer) {
            mobileContainer.innerHTML = '';
            stepsConfig.forEach((step, idx) => {
                const dot = document.createElement('button');
                dot.type = 'button';
                dot.className = 'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold transition-all whitespace-nowrap shrink-0';
                dot.setAttribute('data-mobile-step', idx);
                dot.style.cssText = idx === 0
                    ? 'background: rgba(var(--accent-rgb), 0.15); color: var(--accent); border: 1px solid rgba(var(--accent-rgb), 0.3);'
                    : 'background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.08);';
                dot.innerHTML = `<span class="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black" style="${idx === 0 ? 'background: var(--accent); color: black;' : 'background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5);'}">${idx + 1}</span> ${step.label}`;
                dot.onclick = () => goToStep(idx);
                mobileContainer.appendChild(dot);
            });
        }
    }

    // ══════════════════════════════════════════════════════════
    //  STEP NAVIGATION
    // ══════════════════════════════════════════════════════════

    function clearHiddenRequiredAttributes() {
        document.querySelectorAll('[data-wizard-step]').forEach(function(stepEl) {
            const isHidden = stepEl.classList.contains('step-hidden');
            stepEl.querySelectorAll('input, select, textarea').forEach(function(inp) {
                if (isHidden && inp.hasAttribute('required')) {
                    inp.dataset.wasRequired = 'true';
                    inp.removeAttribute('required');
                }
                if (!isHidden && inp.dataset.wasRequired === 'true' && inp.dataset.contactField !== 'true') {
                    inp.setAttribute('required', '');
                    delete inp.dataset.wasRequired;
                }
            });
        });
    }

    function showStep(idx) {
        if (idx < 0 || idx >= TOTAL_STEPS) return;
        currentStep = idx;

        // Hide all steps
        document.querySelectorAll('[data-wizard-step]').forEach(el => {
            el.classList.add('step-hidden');
        });

        // Show current
        const key = stepsConfig[idx].key;
        const stepEl = document.querySelector(`[data-wizard-step="${key}"]`);
        if (stepEl) {
            stepEl.classList.remove('step-hidden');
            // Re-trigger animation
            stepEl.style.animation = 'none';
            stepEl.offsetHeight;
            stepEl.style.animation = '';
        }

        // Prevent browser validation from targeting required fields in hidden steps
        clearHiddenRequiredAttributes();

        updateSidebarIndicators();
        updateFooterButtons();
        updateProgress();
        lucide.createIcons();

        // Scroll wizard content to top
        const content = document.getElementById('wizard-content');
        if (content) content.scrollTop = 0;

        // Sync review on arrival
        if (key === 'review') syncReview();
    }

    function clearStepValidationUI(stepEl) {
        if (!stepEl) return;
        const banner = stepEl.querySelector('[data-step-error-banner]');
        if (banner) banner.remove();
        stepEl.querySelectorAll('.input-error').forEach(function(el) {
            if (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
                el.classList.remove('input-error');
            }
        });
    }

    function showStepValidationError(stepEl, message) {
        if (!stepEl) return;
        clearStepValidationUI(stepEl);
        const box = document.createElement('div');
        box.setAttribute('data-step-error-banner', '1');
        box.className = 'mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-300';
        box.textContent = message || 'Please complete required fields before continuing.';
        stepEl.insertBefore(box, stepEl.firstChild);
    }

    function getFirstVisibleInvalidInput(stepEl) {
        if (!stepEl) return null;
        const candidates = stepEl.querySelectorAll('input[required], select[required], textarea[required]');
        for (const input of candidates) {
            if (input.offsetParent === null) continue;
            if (input.disabled || input.readOnly) continue;
            const value = (input.value || '').trim();
            if (!value) return input;
            if (input.validity && !input.validity.valid) return input;
        }
        return null;
    }

    function guardCurrentStepBeforeAdvance(targetIdx) {
        const currentKey = stepsConfig[currentStep]?.key;
        const currentEl = document.querySelector(`[data-wizard-step="${currentKey}"]`);
        if (!currentKey || !currentEl) return true;

        const isValid = checkStep(currentKey);
        if (isValid) {
            clearStepValidationUI(currentEl);
            return true;
        }

        const invalidInput = getFirstVisibleInvalidInput(currentEl);
        if (invalidInput) {
            invalidInput.classList.add('input-error');
            invalidInput.focus();
            showStepValidationError(currentEl, 'This field is required before moving to the next step.');
        } else {
            showStepValidationError(currentEl, 'Please complete all required information in this step before continuing.');
        }

        if (typeof targetIdx === 'number' && targetIdx !== currentStep) {
            const content = document.getElementById('wizard-content');
            if (content) content.scrollTop = 0;
        }
        return false;
    }

    function nextStep() {
        if (currentStep < TOTAL_STEPS - 1) {
            if (!guardCurrentStepBeforeAdvance(currentStep + 1)) return;
            showStep(currentStep + 1);
        }
    }
    window.nextStep = nextStep;

    function prevStep() {
        if (currentStep > 0) {
            showStep(currentStep - 1);
        }
    }
    window.prevStep = prevStep;

    function goToStep(idx) {
        if (idx < 0 || idx >= TOTAL_STEPS) return;
        if (idx > currentStep && !guardCurrentStepBeforeAdvance(idx)) return;
        showStep(idx);
    }
    window.goToStep = goToStep;

    function goToStepByKey(key) {
        const idx = stepsConfig.findIndex(s => s.key === key);
        if (idx >= 0) showStep(idx);
    }
    window.goToStepByKey = goToStepByKey;

    // ── Sidebar Indicator Updates ─────────────────────────────
    function updateSidebarIndicators() {
        stepsConfig.forEach((step, idx) => {
            const indicator = document.querySelector(`[data-step-indicator="${idx}"]`);
            const sidebarItem = document.querySelector(`[data-sidebar-step="${idx}"]`);
            if (!indicator || !sidebarItem) return;

            const icon = indicator.querySelector('.step-icon');
            const label = sidebarItem.querySelector('.step-label');
            const subtitle = sidebarItem.querySelector('.step-subtitle');
            const checkBadge = indicator.querySelector('.step-check-badge');

            if (idx === currentStep) {
                // Active step — accent highlight with card bg
                sidebarItem.style.background = 'rgba(var(--accent-rgb), 0.06)';
                sidebarItem.style.border = '1px solid rgba(var(--accent-rgb), 0.15)';
                indicator.style.borderColor = 'var(--accent)';
                indicator.style.background = 'rgba(var(--accent-rgb), 0.2)';
                indicator.style.boxShadow = '0 0 12px rgba(var(--accent-rgb), 0.3)';
                if (icon) icon.style.color = 'var(--accent)';
                if (label) { label.style.color = 'white'; label.style.fontWeight = '800'; }
                if (subtitle) subtitle.style.color = 'rgba(var(--accent-rgb), 0.6)';
                if (checkBadge) checkBadge.style.display = 'none';
            } else if (stepValidity[idx]) {
                // Completed step — green check
                sidebarItem.style.background = 'transparent';
                sidebarItem.style.border = '1px solid transparent';
                indicator.style.borderColor = 'rgba(74, 222, 128, 0.3)';
                indicator.style.background = 'rgba(74, 222, 128, 0.08)';
                indicator.style.boxShadow = 'none';
                if (icon) icon.style.color = '#4ade80';
                if (label) { label.style.color = 'rgba(255,255,255,0.6)'; label.style.fontWeight = '700'; }
                if (subtitle) subtitle.style.color = 'rgba(255,255,255,0.2)';
                if (checkBadge) checkBadge.style.display = 'flex';
            } else {
                // Default
                sidebarItem.style.background = 'transparent';
                sidebarItem.style.border = '1px solid transparent';
                indicator.style.borderColor = 'rgba(255,255,255,0.08)';
                indicator.style.background = 'rgba(255,255,255,0.03)';
                indicator.style.boxShadow = 'none';
                if (icon) icon.style.color = 'rgba(255,255,255,0.2)';
                if (label) { label.style.color = 'rgba(255,255,255,0.4)'; label.style.fontWeight = '700'; }
                if (subtitle) subtitle.style.color = 'rgba(255,255,255,0.15)';
                if (checkBadge) checkBadge.style.display = 'none';
            }
        });

        // Vertical progress line (desktop sidebar)
        const vProgress = document.getElementById('vertical-progress');
        if (vProgress) {
            const pct = TOTAL_STEPS > 1 ? (currentStep / (TOTAL_STEPS - 1)) * 100 : 0;
            vProgress.style.height = pct + '%';
        }

        // Mobile progress bar + dots
        const mobileBar = document.getElementById('mobile-bar');
        if (mobileBar) {
            const barPct = TOTAL_STEPS > 1 ? (currentStep / (TOTAL_STEPS - 1)) * 100 : 0;
            mobileBar.style.width = barPct + '%';
        }
        const mobilePct = document.getElementById('mobile-pct');
        if (mobilePct) {
            const completedCount = stepValidity.filter(v => v).length;
            mobilePct.textContent = Math.round((completedCount / TOTAL_STEPS) * 100) + '%';
        }
        document.querySelectorAll('[data-mobile-step]').forEach((dot, idx) => {
            const numSpan = dot.querySelector('span');
            if (idx === currentStep) {
                dot.style.cssText = 'background: rgba(var(--accent-rgb), 0.15); color: var(--accent); border: 1px solid rgba(var(--accent-rgb), 0.3);';
                if (numSpan) numSpan.style.cssText = 'background: var(--accent); color: black;';
            } else if (stepValidity[idx]) {
                dot.style.cssText = 'background: rgba(74,222,128,0.1); color: #4ade80; border: 1px solid rgba(74,222,128,0.2);';
                if (numSpan) numSpan.style.cssText = 'background: rgba(74,222,128,0.2); color: #4ade80;';
            } else {
                dot.style.cssText = 'background: rgba(255,255,255,0.05); color: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.08);';
                if (numSpan) numSpan.style.cssText = 'background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5);';
            }
        });
        // Scroll active mobile step into view
        const activeMobile = document.querySelector(`[data-mobile-step="${currentStep}"]`);
        if (activeMobile) activeMobile.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
    }

    // ── Footer Buttons ────────────────────────────────────────
    function updateFooterButtons() {
        const btnBack = document.getElementById('btn-back');
        const btnNext = document.getElementById('btn-next');
        const btnSubmit = document.getElementById('btn-submit');

        if (btnBack) {
            btnBack.style.opacity = currentStep === 0 ? '0' : '1';
            btnBack.style.pointerEvents = currentStep === 0 ? 'none' : 'auto';
        }

        const isLastStep = currentStep === TOTAL_STEPS - 1;
        if (btnNext) btnNext.style.display = isLastStep ? 'none' : 'flex';
        if (btnSubmit) btnSubmit.style.display = isLastStep ? 'flex' : 'none';
    }

    // ── Progress Bar + Ring ──────────────────────────────────
    function updateProgress() {
        const completedSteps = stepValidity.filter(v => v).length;
        const pct = Math.round((completedSteps / TOTAL_STEPS) * 100);

        const bar = document.getElementById('readiness-bar');
        const pctEl = document.getElementById('readiness-pct');
        if (bar) bar.style.width = pct + '%';
        if (pctEl) pctEl.textContent = pct + '%';

        // SVG Progress Ring
        const ring = document.getElementById('progress-ring-circle');
        if (ring) {
            const circumference = 2 * Math.PI * 24; // r=24
            const offset = circumference - (pct / 100) * circumference;
            ring.style.strokeDashoffset = offset;
        }

        // Status text
        const statusText = document.getElementById('progress-status-text');
        if (statusText) {
            if (pct === 0) statusText.textContent = 'Getting started...';
            else if (pct < 50) statusText.textContent = `${completedSteps} of ${TOTAL_STEPS} steps complete`;
            else if (pct < 100) statusText.textContent = 'Almost there!';
            else statusText.textContent = 'Ready to submit!';
        }
    }

    // ══════════════════════════════════════════════════════════
    //  STEP VALIDATION
    // ══════════════════════════════════════════════════════════

    function checkStep(stepKey) {
        const idx = stepsConfig.findIndex(s => s.key === stepKey);
        if (idx < 0) return true;

        let valid = true;

        switch (stepKey) {
            case 'select_team':
                valid = validateSelectTeam();
                break;
            case 'guest_team':
                valid = validateGuestTeam();
                break;
            case 'profile':
                valid = validateProfile();
                break;
            case 'roster':
                valid = validateRoster();
                break;
            case 'coordinator':
                valid = validateCoordinator();
                break;
            case 'extras':
                valid = validateExtras();
                break;
            case 'payment':
                valid = validatePayment();
                break;
            case 'review':
                valid = validateReview();
                break;
            default:
                valid = true;
        }

        stepValidity[idx] = valid;
        const stepEl = document.querySelector(`[data-wizard-step="${stepKey}"]`);
        if (valid && stepEl) clearStepValidationUI(stepEl);
        updateSidebarIndicators();
        updateProgress();
        return valid;
    }
    window.checkStep = checkStep;

    function validateSelectTeam() {
        // Valid if a team_id is set (either hidden input for single team or radio selected)
        const hidden = document.querySelector('input[name="team_id"]');
        if (hidden && hidden.value) return true;
        const radio = document.querySelector('input[name="team_id"]:checked');
        return !!radio;
    }

    function validateGuestTeam() {
        const name = document.querySelector('[name="guest_team_name"]');
        const tag = document.querySelector('[name="guest_team_tag"]');
        if (!name || !name.value.trim()) return false;
        if (!tag || !tag.value.trim()) return false;
        // Need at least min_team_size guest members with game_id
        const rows = document.querySelectorAll('[data-guest-row]');
        if (rows.length < runtimeConfig.rosterConfig.minTeamSize) return false;
        for (const row of rows) {
            const idx = row.getAttribute('data-guest-row');
            const gameId = row.querySelector(`[name="member_game_id_${idx}"]`);
            if (!gameId || !gameId.value.trim()) return false;
        }
        return true;
    }

    function validateProfile() {
        // Game ID is the key required field for solo
        const gameId = document.querySelector('[data-wizard-step="profile"] [name="game_id"]');
        if (gameId && !gameId.value.trim()) return false;
        // Check required fields (age if enabled)
        const stepEl = document.querySelector('[data-wizard-step="profile"]');
        if (stepEl) {
            const required = stepEl.querySelectorAll('input[required], select[required]');
            for (const inp of required) {
                if (!inp.value.trim()) return false;
            }
        }
        return true;
    }

    function validateRoster() {
        if (!runtimeConfig.isTeam || runtimeConfig.isGuestTeam) return true;
        const members = document.querySelectorAll('[data-member-id]');
        return members.length >= runtimeConfig.rosterConfig.minTeamSize;
    }

    function validateCoordinator() {
        const stepEl = document.querySelector('[data-wizard-step="coordinator"]');
        if (!stepEl) return true;

        // For team mode: check coordinator selection
        if (runtimeConfig.isTeam) {
            const selfRadio = document.querySelector('input[name="coordinator_is_self"][value="false"]:checked');
            if (selfRadio) {
                // Delegate mode — must pick a member
                const memberRadio = document.querySelector('input[name="coordinator_member_id"]:checked');
                if (!memberRadio) return false;
            }
        }

        // Check any required inputs visible in this step
        const requiredInputs = stepEl.querySelectorAll('input[required]:not([type="radio"]):not([type="checkbox"])');
        for (const inp of requiredInputs) {
            if (inp.offsetParent !== null && !inp.value.trim()) return false;
        }

        return true;
    }

    function validateExtras() {
        const stepEl = document.querySelector('[data-wizard-step="extras"]');
        if (!stepEl) return true;
        const required = stepEl.querySelectorAll('input[required], select[required], textarea[required]');
        for (const inp of required) {
            if (!inp.value.trim()) return false;
        }
        return true;
    }

    function validatePayment() {
        if (!runtimeConfig.hasEntryFee) return true;
        const method = document.querySelector('input[name="payment_method"]:checked');
        if (!method) return false;
        if (method.value === 'deltacoin') return true;
        // Mobile payment — need a sub-method selected and valid TrxID
        const subMethod = document.getElementById('payment-sub-method');
        if (!subMethod || !subMethod.value) return false;
        const trxid = document.getElementById('trxid');
        if (!trxid || !/^[A-Za-z0-9]{10}$/.test(trxid.value.trim())) return false;
        // Payment mobile number if visible
        const mobileNum = document.getElementById('payment_mobile');
        if (mobileNum && mobileNum.offsetParent !== null && !mobileNum.value.trim()) return false;
        return true;
    }

    function validateReview() {
        const terms = document.getElementById('terms-checkbox');
        return terms && terms.checked;
    }

    // ══════════════════════════════════════════════════════════
    //  COORDINATOR MODE TOGGLE (Team mode)
    // ══════════════════════════════════════════════════════════

    function toggleCoordinatorMode(isSelf) {
        const delegatePanel = document.getElementById('coordinator-delegate-panel');
        const contactHint = document.getElementById('contact-source-hint');

        if (delegatePanel) {
            delegatePanel.classList.toggle('hidden', isSelf);
        }
        if (contactHint) {
            contactHint.textContent = isSelf
                ? 'These are auto-filled from your profile. Update if needed.'
                : 'Contact info for the selected coordinator. Fill in their details.';
        }
    }
    window.toggleCoordinatorMode = toggleCoordinatorMode;

    function selectCoordinatorMember(radio) {
        // Update review coordinator name
        const label = radio.closest('label');
        if (label) {
            const name = label.querySelector('.text-sm.font-bold');
            const reviewCoord = document.getElementById('review-coordinator');
            if (name && reviewCoord) reviewCoord.textContent = name.textContent.trim();
        }
        checkStep('coordinator');
    }
    window.selectCoordinatorMember = selectCoordinatorMember;

    // ══════════════════════════════════════════════════════════
    //  INPUT VALIDATION STYLING
    // ══════════════════════════════════════════════════════════

    function applyInputValidation(input) {
        if (!input) return;
        const val = input.value.trim();

        if (input.type === 'email' && val) {
            const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
            input.classList.toggle('input-valid', valid);
            input.classList.toggle('input-error', !valid);
        } else if (input.type === 'tel' && val) {
            const valid = /^[\d+\-() ]{7,20}$/.test(val);
            input.classList.toggle('input-valid', valid);
            input.classList.toggle('input-error', !valid);
        } else if (val) {
            input.classList.add('input-valid');
            input.classList.remove('input-error');
        } else {
            input.classList.remove('input-valid', 'input-error');
        }
    }
    window.applyInputValidation = applyInputValidation;

    // ══════════════════════════════════════════════════════════
    //  PAYMENT METHOD LOGIC
    // ══════════════════════════════════════════════════════════

    function selectPaymentMethod(method) {
        const dcPanel = document.getElementById('panel-deltacoin');
        const mobilePanel = document.getElementById('panel-mobile');

        // Ensure the correct radio is checked (handles programmatic calls)
        const radio = document.querySelector(`input[name="payment_method"][value="${method === 'deltacoin' ? 'deltacoin' : 'mobile'}"]`);
        if (radio && !radio.checked) radio.checked = true;

        if (method === 'deltacoin') {
            if (dcPanel) dcPanel.classList.remove('step-hidden');
            if (mobilePanel) mobilePanel.classList.add('step-hidden');
        } else {
            if (dcPanel) dcPanel.classList.add('step-hidden');
            if (mobilePanel) mobilePanel.classList.remove('step-hidden');
            // Always (re)populate the active sub-method details when mobile panel opens
            const subInput = document.getElementById('payment-sub-method');
            const activeMethod = subInput?.value || '';
            const targetTab = activeMethod
                ? document.querySelector(`.mobile-tab[data-mobile-method="${activeMethod}"]`)
                : document.querySelector('.mobile-tab');
            if (targetTab) selectMobileMethod(targetTab.dataset.mobileMethod);
        }
        checkStep('payment');
        if (typeof lucide !== 'undefined') lucide.createIcons();
    }
    window.selectPaymentMethod = selectPaymentMethod;

    function selectMobileMethod(method) {
        // Update hidden sub-method tracker
        const subInput = document.getElementById('payment-sub-method');
        if (subInput) subInput.value = method;

        // Highlight the active tab
        document.querySelectorAll('.mobile-tab').forEach(tab => {
            const isActive = tab.getAttribute('data-mobile-method') === method;
            if (isActive) {
                tab.className = 'mobile-tab group flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold border transition-all duration-200 bg-bkash-pink/10 border-bkash-pink/30 text-bkash-pink ring-1 ring-bkash-pink/20';
            } else {
                tab.className = 'mobile-tab group flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold border transition-all duration-200 bg-white/[0.03] border-white/10 text-gray-400 hover:text-white hover:border-white/20';
            }

            // Populate payment details from the active tab's data attributes
            if (isActive) {
                const acctNum = document.getElementById('pm-account-number');
                const acctName = document.getElementById('pm-account-name');
                const acctType = document.getElementById('pm-account-type');
                const customInstr = document.getElementById('pm-custom-instructions');
                const instrTitle = document.getElementById('pm-instructions-title');
                const bankDetails = document.getElementById('pm-bank-details');
                const label = tab.dataset.pmLabel || method;

                // Update title based on provider
                if (instrTitle) {
                    instrTitle.textContent = method === 'bank_transfer' ? 'Bank Transfer Details' : `Send Money via ${label}`;
                }

                if (acctNum) acctNum.textContent = tab.dataset.pmAccount || '—';
                if (acctName) acctName.textContent = tab.dataset.pmName ? `(${tab.dataset.pmName})` : '';
                if (acctType) acctType.textContent = tab.dataset.pmType ? `Account type: ${tab.dataset.pmType}` : '';

                // Bank transfer extra details
                if (bankDetails) {
                    if (method === 'bank_transfer') {
                        const bankName = document.getElementById('pm-bank-name');
                        const bankBranch = document.getElementById('pm-bank-branch');
                        const bankRouting = document.getElementById('pm-bank-routing');
                        if (bankName) bankName.textContent = tab.dataset.pmBankName || '—';
                        if (bankBranch) bankBranch.textContent = tab.dataset.pmBankBranch || '—';
                        if (bankRouting) bankRouting.textContent = tab.dataset.pmBankRouting || '—';
                        bankDetails.classList.remove('hidden');
                    } else {
                        bankDetails.classList.add('hidden');
                    }
                }

                if (customInstr) {
                    const instr = tab.dataset.pmInstructions || '';
                    if (instr) {
                        customInstr.textContent = instr;
                        customInstr.classList.remove('hidden');
                    } else {
                        customInstr.classList.add('hidden');
                    }
                }
            }
        });

        if (typeof lucide !== 'undefined') lucide.createIcons();
    }
    window.selectMobileMethod = selectMobileMethod;

    // Copy account number with visual feedback
    function copyNumber(el) {
        const numEl = el.querySelector('#pm-account-number') || el.querySelector('.select-all');
        if (!numEl) return;
        const text = numEl.textContent.trim();
        if (!text || text === '—') return;

        function onSuccess() {
            const label = el.querySelector('.copy-label');
            if (label) {
                label.textContent = 'Copied!';
                label.classList.add('text-green-400');
                setTimeout(() => { label.textContent = 'Copy'; label.classList.remove('text-green-400'); }, 2000);
            }
        }

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(onSuccess).catch(function() {});
        } else {
            // Fallback for non-HTTPS / insecure contexts
            var ta = document.createElement('textarea');
            ta.value = text;
            ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
            document.body.appendChild(ta);
            ta.select();
            try { document.execCommand('copy'); onSuccess(); } catch(e) {}
            document.body.removeChild(ta);
        }
    }
    window.copyNumber = copyNumber;

    // Handle payment proof upload display
    function handlePaymentProof(input) {
        const label = document.getElementById('proof-label');
        if (label && input.files.length) {
            label.textContent = input.files[0].name;
            label.classList.add('text-white');
        } else if (label) {
            label.textContent = 'Upload screenshot of transaction';
            label.classList.remove('text-white');
        }
    }
    window.handlePaymentProof = handlePaymentProof;

    // ── Transaction ID Validation ─────────────────────────────
    function validateTrxId() {
        const input = document.getElementById('trxid');
        const status = document.getElementById('trx-status');
        const icon = document.getElementById('trx-icon');
        if (!input || !status) return;

        const val = input.value.trim().toUpperCase();
        input.value = val;

        if (val.length === 0) {
            status.innerHTML = 'Enter the 10-character alphanumeric Transaction ID';
            status.className = 'flex items-center justify-center gap-2 text-xs font-medium text-gray-500 h-5';
            input.classList.remove('input-valid', 'input-error');
            if (icon) icon.innerHTML = '';
        } else if (/^[A-Z0-9]{10}$/.test(val)) {
            status.innerHTML = '<i data-lucide="check-circle-2" class="w-4 h-4"></i> Valid Transaction ID';
            status.className = 'flex items-center justify-center gap-2 text-xs font-medium text-green-400 h-5';
            input.classList.add('input-valid');
            input.classList.remove('input-error');
            if (icon) icon.innerHTML = '<i data-lucide="check" class="w-4 h-4 text-green-400"></i>';
        } else {
            const remaining = 10 - val.length;
            status.innerHTML = remaining > 0
                ? `${remaining} more character${remaining !== 1 ? 's' : ''} needed`
                : 'Must be exactly 10 alphanumeric characters';
            status.className = 'flex items-center justify-center gap-2 text-xs font-medium text-yellow-400 h-5';
            input.classList.remove('input-valid');
            if (val.length === 10) input.classList.add('input-error');
            if (icon) icon.innerHTML = '';
        }

        lucide.createIcons();
        checkStep('payment');
    }
    window.validateTrxId = validateTrxId;

    // ══════════════════════════════════════════════════════════
    //  GUEST MEMBER MANAGEMENT
    // ══════════════════════════════════════════════════════════

    function addGuestMember() {
        const maxRoster = runtimeConfig.rosterConfig.maxRoster || 10;
        if (guestMemberCount >= maxRoster) {
            alert(`Maximum ${maxRoster} members allowed.`);
            return;
        }

        const idx = guestMemberCount;
        const list = document.getElementById('guest-members-list');
        if (!list) return;

        const rc = runtimeConfig.rosterConfig;
        const coachOption = rc.allowCoaches ? '<option value="coach">Coach</option>' : '';

        // Build game role selector
        let gameRoleSelector = '';
        const roles = runtimeConfig.rosterRoles || [];
        if (roles.length > 0) {
            const opts = roles.map(r => `<option value="${r.code}">${r.name}</option>`).join('');
            gameRoleSelector = `
                <div class="mt-3 pt-3 border-t border-white/5">
                    <label class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 block">In-Game Role</label>
                    <select name="member_game_role_${idx}" class="input-premium text-xs py-2 w-48">
                        <option value="">— Select Role —</option>
                        ${opts}
                    </select>
                </div>
            `;
        }

        const row = document.createElement('div');
        row.className = 'player-slot slot-starter p-4 rounded-xl animate-fade-in';
        row.setAttribute('data-guest-row', idx);
        row.innerHTML = `
            <div class="flex flex-col sm:flex-row gap-3">
                <div class="flex items-center gap-3 shrink-0">
                    <span class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-black" style="background: var(--accent);">${idx + 1}</span>
                    <select name="member_role_${idx}" class="input-premium text-xs w-28 py-2 px-3" onchange="updateRosterCounts()">
                        <option value="starter">Starter</option>
                        <option value="substitute">Substitute</option>
                        ${coachOption}
                    </select>
                </div>
                <div class="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <input type="text" name="member_game_id_${idx}" class="input-premium text-sm" placeholder="${runtimeConfig.gameIdLabel}" required oninput="checkStep('guest_team')">
                    <input type="text" name="member_display_name_${idx}" class="input-premium text-sm" placeholder="Display Name" required oninput="checkStep('guest_team')">
                </div>
                <button type="button" class="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-gray-500 hover:text-red-400 hover:border-red-400/30 transition-all shrink-0" onclick="removeGuestMember(this)" title="Remove">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>
            ${gameRoleSelector}
        `;

        list.appendChild(row);
        guestMemberCount++;
        updateRosterCounts();
        lucide.createIcons();
        checkStep('guest_team');
    }
    window.addGuestMember = addGuestMember;

    function removeGuestMember(btn) {
        const row = btn.closest('[data-guest-row]');
        if (row) {
            row.style.opacity = '0';
            row.style.transform = 'translateX(20px)';
            row.style.transition = 'all 0.3s ease';
            setTimeout(() => {
                row.remove();
                renumberGuestMembers();
                updateRosterCounts();
                checkStep('guest_team');
            }, 300);
        }
    }
    window.removeGuestMember = removeGuestMember;

    function renumberGuestMembers() {
        const rows = document.querySelectorAll('[data-guest-row]');
        rows.forEach((row, i) => {
            row.setAttribute('data-guest-row', i);
            const num = row.querySelector('.rounded-full:not(input)');
            if (num && !num.querySelector('i') && !num.querySelector('svg')) num.textContent = i + 1;
        });
        guestMemberCount = rows.length;
    }

    // ══════════════════════════════════════════════════════════
    //  ROSTER COUNTS
    // ══════════════════════════════════════════════════════════

    function updateRosterCounts() {
        if (runtimeConfig.isGuestTeam) {
            const rows = document.querySelectorAll('[data-guest-row]');
            const countText = document.getElementById('roster-count-text');
            if (countText) countText.textContent = rows.length;
        } else if (runtimeConfig.isTeam) {
            // Count by slot from hidden inputs
            let starters = 0, subs = 0, coaches = 0;
            document.querySelectorAll('[data-member-id]').forEach(card => {
                const slot = card.dataset.memberRosterSlot || 'STARTER';
                if (slot === 'SUBSTITUTE') subs++;
                else if (slot === 'COACH') coaches++;
                else starters++;
            });

            const cs = document.getElementById('count-starters');
            const csub = document.getElementById('count-subs');
            const ccoach = document.getElementById('count-coaches');
            const total = document.getElementById('roster-count-text');

            if (cs) cs.textContent = starters;
            if (csub) csub.textContent = subs;
            if (ccoach) ccoach.textContent = coaches;
            if (total) total.textContent = starters + subs + coaches;

            // Validation message
            const valMsg = document.getElementById('roster-validation');
            if (valMsg) {
                const min = runtimeConfig.rosterConfig.minTeamSize;
                if (starters < min) {
                    valMsg.classList.remove('hidden');
                    valMsg.className = 'mt-4 p-3 rounded-xl border text-xs font-medium border-yellow-500/20 bg-yellow-500/5 text-yellow-400';
                    valMsg.innerHTML = `<i data-lucide="alert-triangle" class="w-4 h-4 inline mr-1"></i> Need at least ${min} starters. Currently: ${starters}`;
                    lucide.createIcons();
                } else {
                    valMsg.classList.add('hidden');
                }
            }
        }
    }
    window.updateRosterCounts = updateRosterCounts;

    // ══════════════════════════════════════════════════════════
    //  MEMBER DETAIL MODAL (Rich Game Passport View)
    // ══════════════════════════════════════════════════════════

    let activeModalMemberId = null;
    let activeModalTab = 'edit';

    function switchModalTab(tab) {
        activeModalTab = tab;
        document.querySelectorAll('[data-modal-tab-btn]').forEach(btn => {
            const isActive = btn.dataset.modalTabBtn === tab;
            btn.className = `px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                isActive
                    ? 'text-white'
                    : 'text-gray-500 hover:text-white hover:bg-white/5'
            }`;
            if (isActive) btn.style.cssText = 'background: rgba(var(--accent-rgb), 0.15); color: var(--accent); border: 1px solid rgba(var(--accent-rgb), 0.2);';
            else btn.style.cssText = 'background: transparent; border: 1px solid transparent;';
        });
        document.querySelectorAll('[data-modal-tab]').forEach(panel => {
            panel.classList.toggle('hidden', panel.dataset.modalTab !== tab);
        });
    }
    window.switchModalTab = switchModalTab;

    function openMemberModal(cardEl) {
        const modal = document.getElementById('member-modal-overlay');
        const body = document.getElementById('member-modal-body');
        const title = document.getElementById('member-modal-title');
        if (!modal || !body) return;

        activeModalMemberId = cardEl.dataset.memberId;
        const d = cardEl.dataset;
        const displayName = d.memberDisplayName || d.memberUsername;
        const username = d.memberUsername || '';
        const rosterSlot = d.memberRosterSlot || 'STARTER';
        const playerRole = d.memberPlayerRole || '';
        const isCaptain = d.memberIsCaptain === 'true';

        // Game passport data
        const gpIGN = d.memberGpIgn || '';
        const gpDisc = d.memberGpDiscriminator || '';
        const gpInGameName = d.memberGpInGameName || '';
        const gpRank = d.memberGpRank || '';
        const gpRankImage = d.memberGpRankImage || '';
        const gpPlatform = d.memberGpPlatform || '';
        const gpRegion = d.memberGpRegion || '';
        const gpMainRole = d.memberGpMainRole || '';
        const gpMatches = parseInt(d.memberGpMatches) || 0;
        const gpWinrate = parseInt(d.memberGpWinrate) || 0;
        const gpKD = d.memberGpKd || '';
        const gpHours = d.memberGpHours || '';
        const hasPassport = d.memberGpHasPassport === 'true';

        // Player profile data
        const profileFullName = d.memberProfileFullName || '';
        const profileEmail = d.memberProfileEmail || '';
        const profileDiscord = d.memberProfileDiscord || '';
        const profilePronouns = d.memberProfilePronouns || '';
        const profilePhone = d.memberProfilePhone || '';
        const profileDob = d.memberProfileDob || '';
        const profileCountry = d.memberProfileCountry || '';
        const profileGender = d.memberProfileGender || '';

        if (title) title.textContent = displayName;

        // Build avatar
        const avatarImg = cardEl.querySelector('img');
        const avatarSrc = avatarImg ? avatarImg.src : `https://ui-avatars.com/api/?name=${encodeURIComponent(username)}&background=111&color=fff&size=96`;

        // Role options
        const roles = runtimeConfig.rosterRoles || [];
        let roleOptions = '<option value="">— None —</option>';
        roles.forEach(r => {
            const selected = r.code === playerRole ? 'selected' : '';
            roleOptions += `<option value="${r.code}" ${selected}>${r.name}</option>`;
        });

        // Slot options
        const rc = runtimeConfig.rosterConfig;
        let slotOptions = `
            <option value="STARTER" ${rosterSlot === 'STARTER' ? 'selected' : ''}>⚔️ Starter</option>
            <option value="SUBSTITUTE" ${rosterSlot === 'SUBSTITUTE' ? 'selected' : ''}>🔄 Substitute</option>
        `;
        if (rc.allowCoaches) {
            slotOptions += `<option value="COACH" ${rosterSlot === 'COACH' ? 'selected' : ''}>🎓 Coach</option>`;
        }

        // Passport display name — discriminator already includes # prefix (e.g. "#SIUU")
        const passportDisplay = gpInGameName || (gpIGN ? (gpDisc ? `${gpIGN}${gpDisc}` : gpIGN) : '—');

        // Stats bar HTML
        const statsBar = hasPassport ? `
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4">
                <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 text-center">
                    <div class="text-base font-black text-white">${gpMatches.toLocaleString()}</div>
                    <div class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mt-0.5">Matches</div>
                </div>
                <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 text-center">
                    <div class="text-base font-black ${gpWinrate >= 50 ? 'text-green-400' : 'text-red-400'}">${gpWinrate}%</div>
                    <div class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mt-0.5">Win Rate</div>
                </div>
                <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 text-center">
                    <div class="text-base font-black text-white">${gpKD || '—'}</div>
                    <div class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mt-0.5">K/D</div>
                </div>
                <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 text-center">
                    <div class="text-base font-black text-white">${gpHours ? gpHours + 'h' : '—'}</div>
                    <div class="text-[10px] font-bold text-gray-500 uppercase tracking-wider mt-0.5">Hours</div>
                </div>
            </div>
        ` : '';

        // Calculate age from DOB
        let profileAge = '';
        if (profileDob) {
            const birth = new Date(profileDob);
            const now = new Date();
            let age = now.getFullYear() - birth.getFullYear();
            if (now.getMonth() < birth.getMonth() || (now.getMonth() === birth.getMonth() && now.getDate() < birth.getDate())) age--;
            profileAge = age > 0 ? age + ' years old' : '';
        }

        // Helper: build a read-only or editable row for player details
        function detailRow(label, value, fieldName, inputType) {
            if (value) {
                // User has provided this — show read-only
                return `<div class="flex justify-between items-center py-1.5">
                    <span class="text-xs text-gray-400">${label}</span>
                    <span class="text-sm font-medium text-white">${value}</span>
                </div>`;
            } else if (fieldName) {
                // Empty + editable by coordinator
                return `<div class="flex justify-between items-center gap-3 py-1.5">
                    <span class="text-xs text-gray-400 shrink-0">${label} <span class="text-orange-400 text-[10px]">*</span></span>
                    <input type="${inputType || 'text'}" id="modal-pi-${fieldName}" class="input-premium text-sm py-1.5 px-2.5 max-w-[180px]" placeholder="Enter ${label.toLowerCase()}">
                </div>`;
            }
            return '';
        }

        body.innerHTML = `
            {# ── Header Card ── #}
            <div class="flex items-center gap-4 pb-4 border-b border-white/10">
                <div class="w-16 h-16 rounded-full overflow-hidden border-2 ${isCaptain ? 'border-dc-gold' : 'border-white/10'} shadow-xl shrink-0 relative">
                    <img src="${avatarSrc}" class="w-full h-full object-cover" alt="${displayName}">
                    ${isCaptain ? '<div class="absolute -top-0.5 -right-0.5 w-5 h-5 bg-dc-gold rounded-full flex items-center justify-center shadow"><i data-lucide="crown" class="w-3 h-3 text-black"></i></div>' : ''}
                </div>
                <div class="flex-1 min-w-0">
                    <h4 class="text-lg font-black text-white truncate">${displayName}</h4>
                    <p class="text-xs text-gray-500 font-mono">@${username}</p>
                    <div class="flex items-center gap-2 mt-1.5 flex-wrap">
                        ${isCaptain ? '<span class="px-1.5 py-0.5 text-[10px] font-black uppercase rounded bg-dc-gold/20 text-dc-gold border border-dc-gold/30">Captain</span>' : ''}
                        ${hasPassport ? `<span class="px-1.5 py-0.5 text-[10px] font-black uppercase rounded bg-green-500/15 text-green-400 border border-green-500/20"><i data-lucide="shield-check" class="w-2.5 h-2.5 inline -mt-0.5"></i> Passport</span>` : '<span class="px-1.5 py-0.5 text-[10px] font-bold uppercase rounded bg-orange-500/15 text-orange-400 border border-orange-500/20">No Passport</span>'}
                    </div>
                </div>
            </div>

            {# ── Tabs ── #}
            <div class="flex gap-1 mt-3 mb-3 p-1 rounded-xl bg-black/40 border border-white/5 flex-wrap">
                <button type="button" data-modal-tab-btn="edit" onclick="switchModalTab('edit')" class="px-3 py-2 rounded-lg text-xs font-bold transition-all" style="background: rgba(var(--accent-rgb), 0.15); color: var(--accent); border: 1px solid rgba(var(--accent-rgb), 0.2);">
                    <i data-lucide="settings-2" class="w-3 h-3 inline -mt-0.5 mr-1"></i>Assignment
                </button>
                <button type="button" data-modal-tab-btn="passport" onclick="switchModalTab('passport')" class="px-3 py-2 rounded-lg text-xs font-bold text-gray-500 hover:text-white transition-all" style="background: transparent; border: 1px solid transparent;">
                    <i data-lucide="id-card" class="w-3 h-3 inline -mt-0.5 mr-1"></i>Game Passport
                </button>
                <button type="button" data-modal-tab-btn="player-info" onclick="switchModalTab('player-info')" class="px-3 py-2 rounded-lg text-xs font-bold text-gray-500 hover:text-white transition-all" style="background: transparent; border: 1px solid transparent;">
                    <i data-lucide="user" class="w-3 h-3 inline -mt-0.5 mr-1"></i>Player Info
                </button>
                <button type="button" data-modal-tab-btn="stats" onclick="switchModalTab('stats')" class="px-3 py-2 rounded-lg text-xs font-bold text-gray-500 hover:text-white transition-all" style="background: transparent; border: 1px solid transparent;">
                    <i data-lucide="bar-chart-3" class="w-3 h-3 inline -mt-0.5 mr-1"></i>Stats
                </button>
            </div>

            {# ── Tab: Assignment (Edit) ── #}
            <div data-modal-tab="edit">
                <div class="space-y-4">
                    <div>
                        <label class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">Roster Position</label>
                        <select id="modal-roster-slot" class="input-premium text-sm w-full py-3">${slotOptions}</select>
                    </div>
                    <div>
                        <label class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">In-Game Role</label>
                        ${roles.length > 0 ? `
                        <select id="modal-player-role" class="input-premium text-sm w-full py-3">${roleOptions}</select>
                        <p class="text-[10px] text-gray-600 mt-1">Select the player's tactical role for this tournament.</p>
                        ` : `
                        <input type="text" id="modal-player-role" class="input-premium text-sm w-full py-3" placeholder="e.g. Duelist, IGL, Support" value="${playerRole || ''}">
                        <p class="text-[10px] text-gray-600 mt-1">Type the player's in-game role.</p>
                        `}
                    </div>
                    <div>
                        <label class="flex items-center gap-3 p-2.5 rounded-lg border border-white/5 bg-black/20 cursor-pointer hover:border-amber-500/20 transition-all has-[:checked]:border-amber-500/30 has-[:checked]:bg-amber-500/5">
                            <input type="checkbox" id="modal-is-igl" class="w-4 h-4 accent-[#f59e0b] cursor-pointer">
                            <span class="text-xs font-bold text-gray-400 flex items-center gap-1.5 has-[:checked]:text-amber-400">
                                <i data-lucide="crown" class="w-3 h-3 text-amber-500/60"></i> IGL / Shot Caller
                            </span>
                        </label>
                    </div>
                    ${runtimeConfig.formConfig.showMemberGameIds ? `
                    <div>
                        <label class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">${runtimeConfig.gameIdLabel}</label>
                        <input type="text" id="modal-game-id" class="input-premium text-sm w-full py-3" placeholder="${runtimeConfig.gameIdPlaceholder}" value="${passportDisplay !== '—' ? passportDisplay : ''}">
                        <p class="text-xs text-gray-600 mt-1">Used for match lobbies. ${hasPassport ? 'Auto-filled from game passport.' : 'Player has no game passport.'}</p>
                    </div>
                    ` : ''}
                </div>
            </div>

            {# ── Tab: Game Passport ── #}
            <div data-modal-tab="passport" class="hidden">
                ${hasPassport ? `
                <div class="space-y-3">
                    <div class="p-3 rounded-xl border border-white/5 bg-black/30">
                        <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Identity</div>
                        <div class="space-y-2">
                            <div class="flex justify-between items-center">
                                <span class="text-xs text-gray-400">${runtimeConfig.gameIdLabel}</span>
                                <span class="text-sm font-bold text-white font-mono">${passportDisplay}</span>
                            </div>
                            ${gpIGN ? `<div class="flex justify-between items-center">
                                <span class="text-xs text-gray-400">In-Game Name</span>
                                <span class="text-sm font-bold text-white">${gpIGN}</span>
                            </div>` : ''}
                            ${gpDisc ? `<div class="flex justify-between items-center">
                                <span class="text-xs text-gray-400">Tag</span>
                                <span class="text-sm font-bold text-white font-mono">${gpDisc}</span>
                            </div>` : ''}
                            ${gpPlatform ? `<div class="flex justify-between items-center">
                                <span class="text-xs text-gray-400">Platform</span>
                                <span class="text-sm font-bold text-white">${gpPlatform}</span>
                            </div>` : ''}
                            ${gpRegion ? `<div class="flex justify-between items-center">
                                <span class="text-xs text-gray-400">Region</span>
                                <span class="text-sm font-bold text-white">${gpRegion}</span>
                            </div>` : ''}
                        </div>
                    </div>
                    <div class="p-3 rounded-xl border border-white/5 bg-black/30">
                        <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Competitive</div>
                        <div class="space-y-2">
                            <div class="flex justify-between items-center">
                                <span class="text-xs text-gray-400">Rank</span>
                                <span class="flex items-center gap-1.5">
                                    ${gpRankImage ? `<img src="${gpRankImage}" class="w-5 h-5 object-contain" alt="">` : ''}
                                    <span class="text-sm font-bold text-yellow-400">${gpRank || '—'}</span>
                                </span>
                            </div>
                            ${gpMainRole ? `<div class="flex justify-between items-center">
                                <span class="text-xs text-gray-400">Main Role</span>
                                <span class="text-sm font-bold text-white">${gpMainRole}</span>
                            </div>` : ''}
                        </div>
                    </div>
                </div>
                ` : `
                <div class="text-center py-8">
                    <div class="w-14 h-14 rounded-full bg-orange-500/10 border border-orange-500/20 mx-auto mb-3 flex items-center justify-center">
                        <i data-lucide="alert-circle" class="w-7 h-7 text-orange-400"></i>
                    </div>
                    <p class="text-sm font-bold text-white mb-1">No Game Passport</p>
                    <p class="text-xs text-gray-500 max-w-[250px] mx-auto">This player hasn't set up a game passport for this game yet. Their game ID can still be entered manually in the Assignment tab.</p>
                </div>
                `}
            </div>

            {# ── Tab: Player Info ── #}
            <div data-modal-tab="player-info" class="hidden">
                <div class="space-y-3">
                    <div class="p-3 rounded-xl border border-white/5 bg-black/30">
                        <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Personal Details</div>
                        <p class="text-[10px] text-gray-600 mb-2">Fields provided by the player are shown as read-only. Missing mandatory fields can be filled by the coordinator.</p>
                        <div class="space-y-1">
                            ${detailRow('Full Name', profileFullName, !profileFullName ? 'full_name' : null, 'text')}
                            ${detailRow('Email', profileEmail, !profileEmail ? 'email' : null, 'email')}
                            ${detailRow('Discord', profileDiscord, !profileDiscord ? 'discord' : null, 'text')}
                            ${detailRow('Phone', profilePhone, !profilePhone ? 'phone' : null, 'tel')}
                            ${detailRow('Pronouns', profilePronouns, null)}
                            ${detailRow('Country', profileCountry, !profileCountry ? 'country' : null, 'text')}
                            ${detailRow('Gender', profileGender, null)}
                            ${profileAge ? detailRow('Age', profileAge, null) : detailRow('Date of Birth', profileDob, !profileDob ? 'dob' : null, 'date')}
                        </div>
                    </div>
                    <div class="p-2 rounded-lg bg-amber-500/5 border border-amber-500/10">
                        <p class="text-[10px] text-amber-400/80 flex items-start gap-1.5">
                            <i data-lucide="info" class="w-3 h-3 shrink-0 mt-0.5"></i>
                            Coordinator-provided info is saved for this tournament registration and the team record. Game passport data cannot be edited here.
                        </p>
                    </div>
                </div>
            </div>

            {# ── Tab: Stats ── #}
            <div data-modal-tab="stats" class="hidden">
                ${hasPassport && gpMatches > 0 ? `
                ${statsBar}
                <div class="mt-3 p-3 rounded-xl border border-white/5 bg-black/30">
                    <div class="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-2">Performance</div>
                    <div class="space-y-2">
                        <div>
                            <div class="flex justify-between text-xs mb-1">
                                <span class="text-gray-400">Win Rate</span>
                                <span class="font-bold ${gpWinrate >= 50 ? 'text-green-400' : 'text-red-400'}">${gpWinrate}%</span>
                            </div>
                            <div class="w-full h-1.5 rounded-full bg-black/50 overflow-hidden">
                                <div class="h-full rounded-full transition-all" style="width: ${gpWinrate}%; background: ${gpWinrate >= 50 ? '#4ade80' : '#f87171'};"></div>
                            </div>
                        </div>
                    </div>
                </div>
                ` : `
                <div class="text-center py-8">
                    <div class="w-14 h-14 rounded-full bg-white/5 border border-white/10 mx-auto mb-3 flex items-center justify-center">
                        <i data-lucide="bar-chart-3" class="w-7 h-7 text-gray-600"></i>
                    </div>
                    <p class="text-sm font-bold text-white mb-1">No Stats Available</p>
                    <p class="text-xs text-gray-500">Statistics will appear once the player has match data.</p>
                </div>
                `}
            </div>
        `;

        // Populate from existing hidden fields (override passport default)
        const existSlot = document.querySelector(`[name="member_${activeModalMemberId}_roster_slot"]`);
        const existRole = document.querySelector(`[name="member_${activeModalMemberId}_player_role"]`);
        const existGameId = document.querySelector(`[name="member_${activeModalMemberId}_game_id"]`);
        const existIgl = document.querySelector(`[name="member_${activeModalMemberId}_is_igl"]`);
        if (existSlot && document.getElementById('modal-roster-slot')) {
            document.getElementById('modal-roster-slot').value = existSlot.value;
        }
        if (existRole && document.getElementById('modal-player-role')) {
            document.getElementById('modal-player-role').value = existRole.value;
        }
        if (existGameId && document.getElementById('modal-game-id')) {
            document.getElementById('modal-game-id').value = existGameId.value;
        }
        const iglCheckbox = document.getElementById('modal-is-igl');
        if (iglCheckbox) {
            // Use saved value if exists, otherwise default captain to IGL only on first open
            if (existIgl) {
                iglCheckbox.checked = existIgl.value === 'true';
            } else {
                iglCheckbox.checked = isCaptain;
            }
        }

        // Show modal
        activeModalTab = 'edit';
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        lucide.createIcons();

        const panel = document.getElementById('member-modal-panel');
        if (panel) {
            panel.style.transform = 'scale(0.95)';
            panel.style.opacity = '0';
            requestAnimationFrame(() => {
                panel.style.transform = 'scale(1)';
                panel.style.opacity = '1';
            });
        }
    }
    window.openMemberModal = openMemberModal;

    function closeMemberModal(event) {
        if (event && event.target !== event.currentTarget) return;
        const modal = document.getElementById('member-modal-overlay');
        const panel = document.getElementById('member-modal-panel');
        if (panel) {
            panel.style.transform = 'scale(0.95)';
            panel.style.opacity = '0';
        }
        setTimeout(() => {
            if (modal) { modal.classList.add('hidden'); modal.style.display = ''; }
            document.body.style.overflow = '';
            activeModalMemberId = null;
        }, 200);
    }
    window.closeMemberModal = closeMemberModal;

    function saveMemberChanges() {
        if (!activeModalMemberId) return;
        const card = document.querySelector(`[data-member-id="${activeModalMemberId}"]`);
        if (!card) { closeMemberModal(); return; }

        const slotSelect = document.getElementById('modal-roster-slot');
        const roleSelect = document.getElementById('modal-player-role');
        const gameIdInput = document.getElementById('modal-game-id');

        let newSlot = null;

        if (slotSelect) {
            newSlot = slotSelect.value;
            const hiddenSlot = card.querySelector(`[name="member_${activeModalMemberId}_roster_slot"]`);
            if (hiddenSlot) hiddenSlot.value = newSlot;
            card.dataset.memberRosterSlot = newSlot;
            updateSlotBadge(card, newSlot);
            moveCardToSection(card, newSlot);
        }

        if (roleSelect) {
            const hiddenRole = card.querySelector(`[name="member_${activeModalMemberId}_player_role"]`);
            if (hiddenRole) hiddenRole.value = roleSelect.value;
            card.dataset.memberPlayerRole = roleSelect.value;
            updateRoleBadge(card, roleSelect.value);
        }

        if (gameIdInput) {
            let hiddenGameId = card.querySelector(`[name="member_${activeModalMemberId}_game_id"]`);
            if (!hiddenGameId) {
                hiddenGameId = document.createElement('input');
                hiddenGameId.type = 'hidden';
                hiddenGameId.name = `member_${activeModalMemberId}_game_id`;
                card.appendChild(hiddenGameId);
            }
            hiddenGameId.value = gameIdInput.value;
        }

        // Save IGL designation
        const iglCheckbox = document.getElementById('modal-is-igl');
        if (iglCheckbox) {
            const isIgl = iglCheckbox.checked;
            let hiddenIgl = card.querySelector(`[name="member_${activeModalMemberId}_is_igl"]`);
            if (!hiddenIgl) {
                hiddenIgl = document.createElement('input');
                hiddenIgl.type = 'hidden';
                hiddenIgl.name = `member_${activeModalMemberId}_is_igl`;
                card.appendChild(hiddenIgl);
            }
            hiddenIgl.value = isIgl ? 'true' : 'false';

            // If toggling ON, un-IGL everyone else
            if (isIgl) {
                document.querySelectorAll('[name$="_is_igl"]').forEach(inp => {
                    if (inp !== hiddenIgl) inp.value = 'false';
                });
                // Update visual badges on all cards
                document.querySelectorAll('.player-slot .igl-indicator').forEach(el => el.remove());
            }

            // Show/remove IGL badge on this card
            const nameEl = card.querySelector('.flex.items-center.gap-2.flex-wrap');
            if (nameEl) {
                const existBadge = nameEl.querySelector('.igl-indicator');
                if (isIgl && !existBadge) {
                    const badge = document.createElement('span');
                    badge.className = 'igl-indicator px-1.5 py-0.5 text-[10px] font-black uppercase rounded bg-amber-500/20 text-amber-400 border border-amber-500/30';
                    badge.innerHTML = '<i data-lucide="crown" class="w-2.5 h-2.5 inline -mt-0.5 mr-0.5"></i>IGL';
                    nameEl.appendChild(badge);
                } else if (!isIgl && existBadge) {
                    existBadge.remove();
                }
            }

            // Update the global IGL member ID hidden field
            const iglHidden = document.getElementById('igl-member-id');
            if (iglHidden) {
                if (isIgl) {
                    iglHidden.value = activeModalMemberId;
                } else if (iglHidden.value === activeModalMemberId) {
                    iglHidden.value = '';
                }
            }

            // Re-render Lucide icons for the newly created badge
            if (isIgl && typeof lucide !== 'undefined') lucide.createIcons();
        }

        // Save player info fields (coordinator-provided for missing data)
        const piFields = ['full_name', 'email', 'discord', 'phone', 'country', 'dob'];
        piFields.forEach(field => {
            const input = document.getElementById(`modal-pi-${field}`);
            if (input && input.value.trim()) {
                let hidden = card.querySelector(`[name="member_${activeModalMemberId}_pi_${field}"]`);
                if (!hidden) {
                    hidden = document.createElement('input');
                    hidden.type = 'hidden';
                    hidden.name = `member_${activeModalMemberId}_pi_${field}`;
                    card.appendChild(hidden);
                }
                hidden.value = input.value.trim();
            }
        });

        closeMemberModal();
        updateRosterCounts();
        checkStep('roster');
    }
    window.saveMemberChanges = saveMemberChanges;

    function moveCardToSection(card, slot) {
        const sectionMap = {
            'STARTER': 'roster-starters',
            'SUBSTITUTE': 'roster-subs',
            'COACH': 'roster-coaches',
        };
        const targetContainerId = sectionMap[slot];
        if (!targetContainerId) return;
        const target = document.getElementById(targetContainerId);
        if (!target) return;
        // Only move if not already there
        if (card.parentElement && card.parentElement.id === targetContainerId) return;
        // Animate out
        card.style.opacity = '0';
        card.style.transform = 'translateX(-10px)';
        setTimeout(() => {
            target.appendChild(card);
            // Animate in
            requestAnimationFrame(() => {
                card.style.opacity = '1';
                card.style.transform = 'translateX(0)';
            });
            // Show/hide empty state messages in sections
            updateSectionEmptyStates();
        }, 200);
    }

    function updateSectionEmptyStates() {
        ['roster-starters', 'roster-subs', 'roster-coaches'].forEach(id => {
            const container = document.getElementById(id);
            if (!container) return;
            const cards = container.querySelectorAll('[data-member-id]');
            let emptyMsg = container.querySelector('.section-empty-hint');
            if (cards.length === 0 && !emptyMsg) {
                emptyMsg = document.createElement('div');
                emptyMsg.className = 'section-empty-hint text-center py-3';
                emptyMsg.innerHTML = '<p class="text-xs text-gray-600 italic">No members in this section. Move players here using their modal.</p>';
                container.appendChild(emptyMsg);
            } else if (cards.length > 0 && emptyMsg) {
                emptyMsg.remove();
            }
        });
    }

    function updateSlotBadge(card, slot) {
        card.classList.remove('slot-starter', 'slot-sub', 'slot-coach');
        if (slot === 'SUBSTITUTE') card.classList.add('slot-sub');
        else if (slot === 'COACH') card.classList.add('slot-coach');
        else card.classList.add('slot-starter');

        // Find and update badge text
        const badges = card.querySelectorAll('.font-black.uppercase.rounded.tracking-wider');
        badges.forEach(badge => {
            const text = badge.textContent.trim().toLowerCase();
            if (['starter', 'sub', 'coach'].includes(text)) {
                if (slot === 'SUBSTITUTE') {
                    badge.textContent = 'Sub';
                    badge.className = 'px-2 py-1 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[9px] font-black uppercase rounded tracking-wider';
                } else if (slot === 'COACH') {
                    badge.textContent = 'Coach';
                    badge.className = 'px-2 py-1 bg-dc-purple/10 border border-dc-purple/20 text-dc-purple text-[9px] font-black uppercase rounded tracking-wider';
                } else {
                    badge.textContent = 'Starter';
                    badge.className = 'px-2 py-1 text-[9px] font-black uppercase rounded tracking-wider';
                    badge.style.background = 'rgba(var(--accent-rgb), 0.1)';
                    badge.style.border = '1px solid rgba(var(--accent-rgb), 0.2)';
                    badge.style.color = 'var(--accent)';
                }
            }
        });
    }

    function updateRoleBadge(card, roleCode) {
        const infoDiv = card.querySelector('.min-w-0');
        if (!infoDiv) return;

        let roleBadge = infoDiv.querySelector('.player-role-badge');
        if (roleCode) {
            const role = (runtimeConfig.rosterRoles || []).find(r => r.code === roleCode);
            const roleName = role?.name || roleCode;
            if (!roleBadge) {
                const badgeRow = infoDiv.querySelectorAll('.flex.items-center');
                const target = badgeRow.length > 1 ? badgeRow[1] : badgeRow[0];
                if (target) {
                    roleBadge = document.createElement('span');
                    roleBadge.className = 'player-role-badge text-[10px] px-1.5 py-0.5 rounded border border-white/10 bg-white/5 text-gray-400 font-bold';
                    target.appendChild(roleBadge);
                }
            }
            if (roleBadge) roleBadge.textContent = roleName;
        } else if (roleBadge) {
            roleBadge.remove();
        }
    }

    // ══════════════════════════════════════════════════════════
    //  FILE UPLOAD & PREVIEW
    // ══════════════════════════════════════════════════════════

    function previewUpload(input, type) {
        const file = input.files[0];
        if (!file) return;

        const maxSize = type === 'banner' ? 10 * 1024 * 1024 : 5 * 1024 * 1024;
        if (file.size > maxSize) {
            alert(`File too large. Maximum ${type === 'banner' ? '10MB' : '5MB'}.`);
            input.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            const previewContainer = document.getElementById(`${type}-preview-container`);
            const preview = document.getElementById(`${type}-preview`);
            const placeholder = document.getElementById(`${type}-placeholder`);

            if (preview) preview.src = e.target.result;
            if (previewContainer) previewContainer.classList.remove('hidden');
            if (placeholder) placeholder.classList.add('hidden');
        };
        reader.readAsDataURL(file);
    }
    window.previewUpload = previewUpload;

    function handleFileDrop(event, inputName) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        const input = document.querySelector(`[name="${inputName}"]`);
        if (input && event.dataTransfer.files.length) {
            input.files = event.dataTransfer.files;
            const type = inputName === 'team_banner' ? 'banner' : 'logo';
            previewUpload(input, type);
        }
    }
    window.handleFileDrop = handleFileDrop;

    // ══════════════════════════════════════════════════════════
    //  BIO COUNTER
    // ══════════════════════════════════════════════════════════

    function initBioCounter() {
        const bio = document.getElementById('team-bio');
        if (bio) updateBioCounter(bio);
    }

    function updateBioCounter(textarea) {
        const counter = document.getElementById('bio-counter');
        if (counter && textarea) {
            counter.textContent = `${textarea.value.length} / 500`;
        }
    }
    window.updateBioCounter = updateBioCounter;

    // ══════════════════════════════════════════════════════════
    //  TERMS & SUBMIT
    // ══════════════════════════════════════════════════════════

    function validateTerms() {
        const cb = document.getElementById('terms-checkbox');
        const submitBtn = document.getElementById('btn-submit');

        if (cb && submitBtn) {
            if (cb.checked) {
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                submitBtn.classList.add('hover:scale-105');
                submitBtn.style.boxShadow = '0 0 30px rgba(var(--accent-rgb), 0.6)';
            } else {
                submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
                submitBtn.classList.remove('hover:scale-105');
                submitBtn.style.boxShadow = '0 0 25px rgba(var(--accent-rgb), 0.4)';
            }
        }
        checkStep('review');
    }
    window.validateTerms = validateTerms;

    function toggleAccordion(id) {
        const el = document.getElementById(id);
        if (!el) return;
        const body = el.querySelector('.accordion-body');
        const chevron = el.querySelector('.accordion-chevron');
        if (!body) return;

        const isOpen = body.style.maxHeight && body.style.maxHeight !== '0px';
        if (isOpen) {
            body.style.maxHeight = '0px';
            if (chevron) chevron.style.transform = 'rotate(0deg)';
        } else {
            body.style.maxHeight = body.scrollHeight + 'px';
            if (chevron) chevron.style.transform = 'rotate(180deg)';
        }
    }
    window.toggleAccordion = toggleAccordion;

    function updateTermsCardStyle() {
        const cb = document.getElementById('terms-checkbox');
        const card = document.getElementById('terms-checkbox-card');
        if (!cb || !card) return;
        if (cb.checked) {
            card.style.background = 'rgba(74, 222, 128, 0.05)';
            card.style.borderColor = 'rgba(74, 222, 128, 0.2)';
        } else {
            card.style.background = 'rgba(255,255,255,0.01)';
            card.style.borderColor = 'rgba(255,255,255,0.05)';
        }
    }
    window.updateTermsCardStyle = updateTermsCardStyle;

    // ══════════════════════════════════════════════════════════
    //  REVIEW SYNC
    // ══════════════════════════════════════════════════════════

    function syncReview() {
        // Sync communication fields
        syncReviewField('phone', 'review-phone');
        syncReviewField('discord', 'review-discord');
        syncReviewField('captain_whatsapp', 'review-phone');  // fallback

        // Coordinator
        if (runtimeConfig.isTeam) {
            const isSelf = document.querySelector('input[name="coordinator_is_self"][value="true"]:checked');
            const reviewCoord = document.getElementById('review-coordinator');
            if (isSelf && reviewCoord) {
                reviewCoord.textContent = document.querySelector('[name="display_name"]')?.value || '{{ request.user.username }}';
            }
            // Role
            const coordRole = document.querySelector('input[name="coordinator_role"]:checked');
            const reviewCoordRole = document.getElementById('review-coord-role');
            if (coordRole && reviewCoordRole) {
                const label = coordRole.closest('label')?.querySelector('span')?.textContent || coordRole.value;
                reviewCoordRole.textContent = label;
            }
        }

        // Preferred contact
        const prefContact = document.querySelector('input[name="preferred_contact"]:checked');
        const reviewPrefContact = document.getElementById('review-preferred-contact');
        if (prefContact && reviewPrefContact) {
            reviewPrefContact.textContent = prefContact.value;
        }

        // Payment
        const paymentMethod = document.querySelector('input[name="payment_method"]:checked');
        const reviewGateway = document.getElementById('review-gateway');
        if (paymentMethod && reviewGateway) {
            if (paymentMethod.value === 'mobile') {
                const subInput = document.getElementById('payment-sub-method');
                const subVal = subInput ? subInput.value : '';
                const subMap = { bkash: 'bKash', nagad: 'Nagad', rocket: 'Rocket', bank_transfer: 'Bank Transfer' };
                reviewGateway.textContent = subMap[subVal] || 'Mobile Payment';
            } else {
                const map = { deltacoin: 'DeltaCoin' };
                reviewGateway.textContent = map[paymentMethod.value] || paymentMethod.value;
            }
        }

        const trxid = document.getElementById('trxid');
        const reviewTrxid = document.getElementById('review-trxid');
        if (trxid && reviewTrxid) reviewTrxid.textContent = trxid.value.trim() || '—';

        // Guest team name
        const guestName = document.querySelector('[name="guest_team_name"]');
        const reviewGuestName = document.getElementById('review-guest-name');
        if (guestName && reviewGuestName) reviewGuestName.textContent = guestName.value.trim() || '—';

        // Custom questions
        document.querySelectorAll('[data-review-q]').forEach(li => {
            const qId = li.getAttribute('data-review-q');
            const input = document.querySelector(`[name="custom_q_${qId}"]`);
            const display = document.getElementById(`review-q-${qId}`);
            if (input && display) {
                if (input.type === 'checkbox') {
                    display.textContent = input.checked ? 'Yes' : 'No';
                } else if (input.tagName === 'SELECT') {
                    display.textContent = input.options[input.selectedIndex]?.text || '—';
                } else {
                    display.textContent = input.value.trim() || '—';
                }
            }
        });

        // IGL designation in roster review
        const iglId = document.getElementById('igl-member-id')?.value;
        document.querySelectorAll('[data-review-member-slot]').forEach(el => {
            const row = el.closest('.flex.items-center.justify-between');
            if (!row) return;
            const existingIgl = row.querySelector('.review-igl-badge');
            if (existingIgl) existingIgl.remove();
        });
        if (iglId) {
            const iglSlot = document.querySelector(`[data-review-member-slot="${iglId}"]`);
            if (iglSlot) {
                const row = iglSlot.closest('.flex.items-center.justify-between');
                const nameCol = row?.querySelector('.flex.items-center.gap-1\\.5');
                if (nameCol && !nameCol.querySelector('.review-igl-badge')) {
                    const badge = document.createElement('span');
                    badge.className = 'review-igl-badge px-1 py-0.5 text-[8px] font-black uppercase rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 ml-1';
                    badge.textContent = 'IGL';
                    nameCol.appendChild(badge);
                }
            }
        }

        // Dynamic comm channels
        syncDynamicCommsToReview();

        // Guest roster
        if (runtimeConfig.isGuestTeam) syncGuestRosterToReview();

        // Extra fields
        syncReviewField('payment_mobile_number', 'review-payment-mobile');
        syncReviewField('payment_notes', 'review-payment-notes');

        // Validate all steps
        stepsConfig.forEach(s => checkStep(s.key));
    }

    function syncReviewField(inputName, reviewId) {
        const input = document.querySelector(`[name="${inputName}"]`);
        const reviewEl = document.getElementById(reviewId);
        if (input && reviewEl) {
            reviewEl.textContent = input.value.trim() || '—';
        }
    }

    function syncDynamicCommsToReview() {
        const reviewList = document.getElementById('review-comms-list');
        if (!reviewList) return;

        const commInputs = document.querySelectorAll('[data-channel-key]');
        if (commInputs.length === 0) return;

        reviewList.innerHTML = '';
        commInputs.forEach(input => {
            const key = input.getAttribute('data-channel-key');
            const val = input.value.trim() || '—';
            const label = key.charAt(0).toUpperCase() + key.slice(1);
            const li = document.createElement('li');
            li.className = 'flex justify-between';
            li.innerHTML = `<span class="text-gray-500">${label}:</span><strong class="text-white font-mono text-xs">${val}</strong>`;
            reviewList.appendChild(li);
        });
    }

    function syncGuestRosterToReview() {
        const container = document.getElementById('review-guest-roster');
        if (!container) return;

        const rows = document.querySelectorAll('[data-guest-row]');
        container.innerHTML = '';

        rows.forEach((row, i) => {
            const idx = row.getAttribute('data-guest-row');
            const gameId = row.querySelector(`[name="member_game_id_${idx}"]`);
            const displayName = row.querySelector(`[name="member_display_name_${idx}"]`);
            const role = row.querySelector(`[name="member_role_${idx}"]`);

            const li = document.createElement('div');
            li.className = 'flex justify-between items-center p-2 rounded-lg hover:bg-white/5 transition-colors';
            li.innerHTML = `
                <span class="text-sm text-gray-300">
                    ${displayName?.value || gameId?.value || `Member ${i + 1}`}
                    <span class="text-[8px] uppercase text-gray-500 ml-1">${role?.value || 'starter'}</span>
                </span>
                <span class="font-mono text-xs text-gray-500">${gameId?.value || '—'}</span>
            `;
            container.appendChild(li);
        });
    }

    // ── Copy Utility ──────────────────────────────────────────
    function copyNumber(el) {
        const number = el.querySelector('.select-all')?.textContent;
        if (number) {
            navigator.clipboard.writeText(number.replace(/[-\s]/g, '')).then(() => {
                const btn = el.querySelector('span:last-child');
                if (btn) {
                    btn.textContent = 'Copied!';
                    setTimeout(() => btn.textContent = 'Copy', 2000);
                }
            });
        }
    }
    window.copyNumber = copyNumber;

    // ══════════════════════════════════════════════════════════
    //  FORM SUBMISSION
    // ══════════════════════════════════════════════════════════

    function handleSubmit(event) {
        if (event) event.preventDefault();

        const terms = document.getElementById('terms-checkbox');
        if (!terms || !terms.checked) {
            alert('Please accept the rules and terms before submitting.');
            return false;
        }

        // Run all validations
        let allValid = true;
        for (let i = 0; i < TOTAL_STEPS; i++) {
            const valid = checkStep(stepsConfig[i].key);
            if (!valid) {
                allValid = false;
                showStep(i);
                const stepEl = document.querySelector(`[data-wizard-step="${stepsConfig[i].key}"]`);
                if (stepEl) {
                    const firstInvalid = stepEl.querySelector('input:invalid, select:invalid, textarea:invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                        firstInvalid.classList.add('input-error');
                    }
                }
                break;
            }
        }

        if (!allValid) return false;

        // Disable required on ALL hidden steps to prevent browser validation traps
        document.querySelectorAll('[data-wizard-step].step-hidden').forEach(function(hiddenStep) {
            hiddenStep.querySelectorAll('[required]').forEach(function(inp) {
                inp.removeAttribute('required');
                inp.dataset.wasRequired = 'true';
            });
        });

        // Show loading overlay
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
            if (typeof lucide !== 'undefined') lucide.createIcons();
        }

        // Submit via fetch to bypass native HTML5 validation entirely
        const form = document.getElementById('registration-form');
        if (!form) return false;
        const formData = new FormData(form);

        fetch(form.action || window.location.href, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            credentials: 'same-origin'
        }).then(function(response) {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            return response.text().then(function(html) {
                if (response.ok) {
                    // Server returned HTML (success page) — replace document
                    document.open();
                    document.write(html);
                    document.close();
                } else {
                    // Server returned error — hide overlay and show message
                    if (overlay) overlay.style.display = 'none';
                    try {
                        var data = JSON.parse(html);
                        alert(data.error || data.message || 'Registration failed. Please try again.');
                    } catch(e) {
                        alert('Registration failed. Please check your details and try again.');
                    }
                }
            });
        }).catch(function() {
            if (overlay) overlay.style.display = 'none';
            alert('Network error. Please check your connection and try again.');
        });

        return false;
    }
    window.handleSubmit = handleSubmit;

    // ══════════════════════════════════════════════════════════
    //  REAL-TIME VALIDATION — Live Field Feedback
    // ══════════════════════════════════════════════════════════

    function initLiveValidation() {
        const form = document.querySelector('form');
        if (!form) return;

        // Delegate input/change events to the form for all interactive fields
        form.addEventListener('input', debounce(handleLiveInput, 150));
        form.addEventListener('change', handleLiveChange);
    }

    function debounce(fn, delay) {
        let timer;
        return function(...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    }

    function handleLiveInput(e) {
        const el = e.target;
        if (!el || !el.closest('[data-wizard-step]')) return;
        const stepEl = el.closest('[data-wizard-step]');
        const stepKey = stepEl.dataset.wizardStep;

        // Field-level visual feedback
        applyFieldFeedback(el);

        // Re-validate the step
        const valid = checkStep(stepKey);
        if (!valid && stepEl === document.querySelector(`[data-wizard-step="${stepsConfig[currentStep].key}"]`)) {
            const invalid = getFirstVisibleInvalidInput(stepEl);
            if (invalid) invalid.classList.add('input-error');
        }
    }

    function handleLiveChange(e) {
        const el = e.target;
        if (!el || !el.closest('[data-wizard-step]')) return;
        const stepEl = el.closest('[data-wizard-step]');
        const stepKey = stepEl.dataset.wizardStep;

        applyFieldFeedback(el);
        const valid = checkStep(stepKey);
        if (!valid && stepEl === document.querySelector(`[data-wizard-step="${stepsConfig[currentStep].key}"]`)) {
            const invalid = getFirstVisibleInvalidInput(stepEl);
            if (invalid) invalid.classList.add('input-error');
        }
    }

    function applyFieldFeedback(el) {
        if (!el) return;
        // Only apply to visible text/select/textarea inputs with names
        const tag = el.tagName.toLowerCase();
        const type = (el.type || '').toLowerCase();

        if (tag === 'input' && ['checkbox', 'radio', 'hidden', 'file'].includes(type)) return;
        if (!['input', 'select', 'textarea'].includes(tag)) return;
        if (!el.name) return;

        // Skip if not visible
        if (el.offsetParent === null) return;

        const wrapper = el.closest('.relative') || el.parentElement;

        // Remove any existing feedback icon
        const existingBadge = wrapper?.querySelector('.live-feedback-icon');
        if (existingBadge) existingBadge.remove();

        const val = el.value.trim();
        const isRequired = el.hasAttribute('required') || el.closest('[data-required]');

        if (val.length > 0) {
            // Input has value — show check or validation state
            el.style.borderColor = 'rgba(74, 222, 128, 0.3)';
            el.style.boxShadow = '0 0 0 1px rgba(74, 222, 128, 0.08)';

            // Check HTML5 validity for pattern fields
            if (el.validity && !el.validity.valid) {
                el.style.borderColor = 'rgba(248, 113, 113, 0.4)';
                el.style.boxShadow = '0 0 0 1px rgba(248, 113, 113, 0.1)';
            }
        } else if (isRequired) {
            // Empty + required — subtle warning
            el.style.borderColor = 'rgba(255,255,255,0.08)';
            el.style.boxShadow = 'none';
        } else {
            // Empty + optional — neutral
            el.style.borderColor = '';
            el.style.boxShadow = '';
        }
    }

    // Toggle required on contact inputs based on preferred_contact selection.
    function initPreferredContactValidation() {
        var contactInputMap = {
            phone: 'input[name="phone"]',
            discord: 'input[name="discord"], input[name="socials_discord_handle"]',
            email: 'input[name="email"]',
            whatsapp: 'input[name="whatsapp"], input[name="captain_whatsapp"]',
            facebook: 'input[name="comm_facebook"]',
        };

        Object.values(contactInputMap).forEach(function(selector) {
            document.querySelectorAll(selector).forEach(function(el) {
                el.dataset.contactField = 'true';
            });
        });

        function applyContactRequired(selectedValue) {
            // Remove required from all contact inputs first
            Object.values(contactInputMap).forEach(function(selector) {
                document.querySelectorAll(selector).forEach(function(el) {
                    el.removeAttribute('required');
                    delete el.dataset.wasRequired;
                });
            });

            // Add required only to the matching input if it exists
            var selector = contactInputMap[selectedValue];
            if (selector) {
                document.querySelectorAll(selector).forEach(function(el) {
                    if (el.offsetParent !== null) { // only if visible
                        el.setAttribute('required', '');
                    }
                });
            }

            // Final pass: remove required from hidden-step fields to avoid native invalid focus traps
            clearHiddenRequiredAttributes();
        }

        document.querySelectorAll('input[name="preferred_contact"]').forEach(function(radio) {
            radio.addEventListener('change', function() {
                applyContactRequired(this.value);
            });
        });
        // Apply for any pre-selected value on load
        var preSelected = document.querySelector('input[name="preferred_contact"]:checked');
        if (preSelected) {
            applyContactRequired(preSelected.value);
        }
    }

    // Initialize live validation after DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        setTimeout(initLiveValidation, 200);
        setTimeout(initPreferredContactValidation, 250);
        setTimeout(clearHiddenRequiredAttributes, 300);
    });

})();
