/* ═══════════════════════════════════════════════════════════════
   DeltaCrown — Smart Registration Wizard Engine v2
   Full wizard logic: step navigation, validation, auto-save,
   review sync, roster management, payment switching.
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
        showStep(0);
        updateRosterCounts();
        initBioCounter();
        lucide.createIcons();

        // Auto-validate first step
        setTimeout(() => checkStep(stepsConfig[0].key), 100);
    });

    // ── Sidebar Builder ───────────────────────────────────────
    function buildSidebar() {
        const container = document.getElementById('sidebar-steps');
        if (!container) return;
        container.innerHTML = '';

        stepsConfig.forEach((step, idx) => {
            const el = document.createElement('div');
            el.className = 'flex items-start gap-4 cursor-pointer group';
            el.setAttribute('data-sidebar-step', idx);
            el.onclick = () => { if (canGoTo(idx)) goToStep(idx); };

            el.innerHTML = `
                <div class="w-[30px] h-[30px] rounded-full border-2 flex items-center justify-center shrink-0 transition-all duration-500 step-indicator"
                     style="border-color: rgba(255,255,255,0.15); background: transparent;" data-step-indicator="${idx}">
                    <i data-lucide="${step.icon}" class="w-3.5 h-3.5 text-gray-500 step-icon"></i>
                </div>
                <div class="pt-0.5">
                    <p class="text-sm font-bold text-gray-400 group-hover:text-white transition-colors step-label">${step.label}</p>
                    <p class="text-[10px] text-gray-600 mt-0.5">${step.subtitle}</p>
                </div>
            `;
            container.appendChild(el);
        });

        lucide.createIcons({ attrs: { class: '' }, nameAttr: 'data-lucide' });
    }

    // ── Step Navigation ───────────────────────────────────────
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
            stepEl.style.animation = 'none';
            stepEl.offsetHeight; // trigger reflow
            stepEl.style.animation = '';
        }

        // Update sidebar indicators
        updateSidebarIndicators();

        // Update footer buttons
        updateFooterButtons();

        // Update progress
        updateProgress();

        // Re-init icons
        lucide.createIcons();

        // Scroll content to top
        const content = document.getElementById('wizard-content');
        if (content) content.scrollTop = 0;

        // Sync review step
        if (key === 'review') syncReview();
    }

    function nextStep() {
        if (currentStep < TOTAL_STEPS - 1) {
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
        showStep(idx);
    }
    window.goToStep = goToStep;

    function goToStepByKey(key) {
        const idx = stepsConfig.findIndex(s => s.key === key);
        if (idx >= 0) showStep(idx);
    }
    window.goToStepByKey = goToStepByKey;

    function canGoTo(idx) {
        // Can always go backwards or to current step
        if (idx <= currentStep) return true;
        // Can go forward only if current is valid
        return true; // Allow free navigation — validation happens on submit
    }

    // ── Sidebar Indicator Updates ─────────────────────────────
    function updateSidebarIndicators() {
        stepsConfig.forEach((step, idx) => {
            const indicator = document.querySelector(`[data-step-indicator="${idx}"]`);
            const sidebarItem = document.querySelector(`[data-sidebar-step="${idx}"]`);
            if (!indicator || !sidebarItem) return;

            const icon = indicator.querySelector('.step-icon');
            const label = sidebarItem.querySelector('.step-label');

            if (idx === currentStep) {
                // Active
                indicator.style.borderColor = 'var(--accent)';
                indicator.style.background = 'rgba(var(--accent-rgb), 0.2)';
                indicator.style.boxShadow = '0 0 15px rgba(var(--accent-rgb), 0.4)';
                if (icon) icon.style.color = 'var(--accent)';
                if (label) label.style.color = 'white';
            } else if (idx < currentStep || stepValidity[idx]) {
                // Completed
                indicator.style.borderColor = '#4ade80';
                indicator.style.background = 'rgba(74, 222, 128, 0.15)';
                indicator.style.boxShadow = 'none';
                if (icon) icon.style.color = '#4ade80';
                if (label) label.style.color = 'rgba(255,255,255,0.6)';
            } else {
                // Inactive
                indicator.style.borderColor = 'rgba(255,255,255,0.15)';
                indicator.style.background = 'transparent';
                indicator.style.boxShadow = 'none';
                if (icon) icon.style.color = 'rgba(255,255,255,0.3)';
                if (label) label.style.color = 'rgba(255,255,255,0.4)';
            }
        });

        // Update vertical progress line
        const vProgress = document.getElementById('vertical-progress');
        if (vProgress) {
            const pct = TOTAL_STEPS > 1 ? (currentStep / (TOTAL_STEPS - 1)) * 100 : 0;
            vProgress.style.height = pct + '%';
        }
    }

    // ── Footer Button Updates ─────────────────────────────────
    function updateFooterButtons() {
        const btnBack = document.getElementById('btn-back');
        const btnNext = document.getElementById('btn-next');
        const btnSubmit = document.getElementById('btn-submit');

        if (btnBack) {
            if (currentStep === 0) {
                btnBack.style.opacity = '0';
                btnBack.style.pointerEvents = 'none';
            } else {
                btnBack.style.opacity = '1';
                btnBack.style.pointerEvents = 'auto';
            }
        }

        const isLastStep = currentStep === TOTAL_STEPS - 1;

        if (btnNext) {
            btnNext.style.display = isLastStep ? 'none' : 'flex';
        }

        if (btnSubmit) {
            btnSubmit.style.display = isLastStep ? 'flex' : 'none';
        }
    }

    // ── Progress Calculation ──────────────────────────────────
    function updateProgress() {
        const completedSteps = stepValidity.filter(v => v).length;
        const pct = Math.round((completedSteps / TOTAL_STEPS) * 100);

        const bar = document.getElementById('readiness-bar');
        const pctEl = document.getElementById('readiness-pct');

        if (bar) bar.style.width = pct + '%';
        if (pctEl) pctEl.textContent = pct + '%';
    }

    // ── Step Validation ───────────────────────────────────────
    function checkStep(stepKey) {
        const idx = stepsConfig.findIndex(s => s.key === stepKey);
        if (idx < 0) return;

        let valid = true;

        switch(stepKey) {
            case 'coordinator':
                valid = validateCoordinator();
                break;
            case 'comms':
                valid = validateComms();
                break;
            case 'team_info':
                valid = true; // All optional
                break;
            case 'roster':
                valid = validateRoster();
                break;
            case 'questions':
                valid = validateQuestions();
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
        updateSidebarIndicators();
        updateProgress();
        return valid;
    }
    window.checkStep = checkStep;

    function validateCoordinator() {
        const stepEl = document.querySelector('[data-wizard-step="coordinator"]');
        if (!stepEl) return true;

        // Check required inputs
        const requiredInputs = stepEl.querySelectorAll('input[required], select[required]');
        for (const input of requiredInputs) {
            if (!input.value.trim()) return false;
        }

        // For guest team: need name and tag
        if (runtimeConfig.isGuestTeam) {
            const name = stepEl.querySelector('[name="guest_team_name"]');
            const tag = stepEl.querySelector('[name="guest_team_tag"]');
            if (name && !name.value.trim()) return false;
            if (tag && !tag.value.trim()) return false;
        }

        return true;
    }

    function validateComms() {
        const stepEl = document.querySelector('[data-wizard-step="comms"]');
        if (!stepEl) return true;

        const requiredInputs = stepEl.querySelectorAll('input[required]');
        for (const input of requiredInputs) {
            if (!input.value.trim()) return false;
            // Live validation styling
            applyInputValidation(input);
        }
        return true;
    }

    function validateRoster() {
        if (!runtimeConfig.isTeam) return true;

        if (runtimeConfig.isGuestTeam) {
            // Check each guest member has game_id and display_name
            const rows = document.querySelectorAll('[data-guest-row]');
            if (rows.length < runtimeConfig.rosterConfig.minTeamSize) return false;
            for (const row of rows) {
                const gameId = row.querySelector('[name^="member_game_id_"]');
                if (gameId && !gameId.value.trim()) return false;
                const displayName = row.querySelector('[name^="member_display_name_"]');
                if (displayName && displayName.hasAttribute('required') && !displayName.value.trim()) return false;
            }
        } else {
            // Verified team — check minimum roster size
            const rosterCards = document.querySelectorAll('[data-member-id]');
            if (rosterCards.length < runtimeConfig.rosterConfig.minTeamSize) return false;
        }
        return true;
    }

    function validateQuestions() {
        const stepEl = document.querySelector('[data-wizard-step="questions"]');
        if (!stepEl) return true;

        const requiredInputs = stepEl.querySelectorAll('input[required], select[required], textarea[required]');
        for (const input of requiredInputs) {
            if (!input.value.trim()) return false;
        }
        return true;
    }

    function validatePayment() {
        if (!runtimeConfig.hasEntryFee) return true;

        const method = document.querySelector('input[name="payment_method"]:checked');
        if (!method) return false;

        if (method.value === 'deltacoin') return true;

        // Mobile payment — need TrxID
        const trxid = document.getElementById('trxid');
        if (!trxid || !/^[A-Za-z0-9]{10}$/.test(trxid.value.trim())) return false;

        // Check payment_mobile_number if the field exists and is visible
        const mobileNum = document.getElementById('payment_mobile');
        if (mobileNum && mobileNum.offsetParent !== null && !mobileNum.value.trim()) return false;

        return true;
    }

    function validateReview() {
        const terms = document.getElementById('terms-checkbox');
        return terms && terms.checked;
    }

    // ── Input Validation Styling ──────────────────────────────
    function applyInputValidation(input) {
        if (!input) return;
        const val = input.value.trim();

        if (input.type === 'email' && val) {
            const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
            input.classList.toggle('input-valid', emailValid);
            input.classList.toggle('input-error', !emailValid);
        } else if (input.type === 'tel' && val) {
            const phoneValid = /^[\d+\-() ]{7,20}$/.test(val);
            input.classList.toggle('input-valid', phoneValid);
            input.classList.toggle('input-error', !phoneValid);
        } else if (val) {
            input.classList.add('input-valid');
            input.classList.remove('input-error');
        } else {
            input.classList.remove('input-valid', 'input-error');
        }
    }

    // ── Payment Method Logic ──────────────────────────────────
    function selectPaymentMethod(method) {
        const dcPanel = document.getElementById('panel-deltacoin');
        const mobilePanel = document.getElementById('panel-mobile');

        if (method === 'deltacoin') {
            if (dcPanel) dcPanel.classList.remove('step-hidden');
            if (mobilePanel) mobilePanel.classList.add('step-hidden');
        } else {
            if (dcPanel) dcPanel.classList.add('step-hidden');
            if (mobilePanel) mobilePanel.classList.remove('step-hidden');
        }

        checkStep('payment');
    }
    window.selectPaymentMethod = selectPaymentMethod;

    function selectMobileMethod(method) {
        document.querySelectorAll('.mobile-tab').forEach(tab => {
            const isActive = tab.getAttribute('data-mobile-method') === method;
            tab.className = `mobile-tab px-4 py-2 rounded-xl text-xs font-bold border transition-all ${
                isActive
                    ? 'bg-bkash-pink/10 border-bkash-pink/30 text-bkash-pink'
                    : 'bg-white/5 border-white/10 text-gray-400 hover:text-white'
            }`;
        });

        // Update radio — check the matching radio or set the bkash radio value
        const matchingRadio = document.querySelector(`input[name="payment_method"][value="${method}"]`);
        if (matchingRadio) {
            matchingRadio.checked = true;
        } else {
            // Fallback: update the bkash radio value for non-standard methods
            const bkashRadio = document.querySelector('input[name="payment_method"][value="bkash"]');
            if (bkashRadio) bkashRadio.value = method;
        }
    }
    window.selectMobileMethod = selectMobileMethod;

    // ── Transaction ID Validation ─────────────────────────────
    function validateTrxId() {
        const input = document.getElementById('trxid');
        const status = document.getElementById('trx-status');
        const icon = document.getElementById('trx-icon');
        if (!input || !status) return;

        const val = input.value.trim().toUpperCase();
        input.value = val;

        if (val.length === 0) {
            status.innerHTML = 'Awaiting 10-character alphanumeric ID';
            status.className = 'mt-3 flex items-center justify-center gap-2 text-xs font-medium text-gray-500 h-5';
            input.classList.remove('input-valid', 'input-error');
        } else if (/^[A-Z0-9]{10}$/.test(val)) {
            status.innerHTML = '<i data-lucide="check-circle-2" class="w-4 h-4"></i> Valid Transaction ID';
            status.className = 'mt-3 flex items-center justify-center gap-2 text-xs font-medium text-green-400 h-5';
            input.classList.add('input-valid');
            input.classList.remove('input-error');
        } else {
            const remaining = 10 - val.length;
            status.innerHTML = remaining > 0 ? `${remaining} more character${remaining !== 1 ? 's' : ''} needed` : 'Must be exactly 10 alphanumeric characters';
            status.className = 'mt-3 flex items-center justify-center gap-2 text-xs font-medium text-yellow-400 h-5';
            input.classList.remove('input-valid');
            if (val.length === 10) input.classList.add('input-error');
        }

        lucide.createIcons();
        checkStep('payment');
    }
    window.validateTrxId = validateTrxId;

    // ── Guest Member Management ───────────────────────────────
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
        const hasDetailFields = runtimeConfig.formConfig.requireMemberRealName ||
                               runtimeConfig.formConfig.requireMemberEmail ||
                               runtimeConfig.formConfig.requireMemberPhoto;

        // Build coach option only if game allows coaches
        const coachOption = rc.allowCoaches ? `<option value="coach">Coach</option>` : '';

        let detailPanel = '';
        if (hasDetailFields) {
            detailPanel = `
                <button type="button" class="mt-3 text-[10px] font-bold text-gray-500 hover:text-white flex items-center gap-1 transition-colors" onclick="toggleMemberDetail(this)">
                    <i data-lucide="chevron-down" class="w-3 h-3 transition-transform"></i> Additional Details
                </button>
                <div class="member-detail-panel mt-3">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-3 border-t border-white/5">
                        ${runtimeConfig.formConfig.requireMemberRealName ? `<input type="text" name="member_real_name_${idx}" class="input-premium text-sm" placeholder="Real Name *">` : ''}
                        ${runtimeConfig.formConfig.requireMemberEmail ? `<input type="email" name="member_email_${idx}" class="input-premium text-sm" placeholder="Email *">` : ''}
                        ${runtimeConfig.formConfig.requireMemberPhoto ? `
                        <div class="sm:col-span-2">
                            <label class="flex items-center gap-3 p-3 rounded-xl border border-dashed border-white/10 bg-black/30 cursor-pointer hover:border-white/20 transition-all text-sm">
                                <i data-lucide="camera" class="w-4 h-4 text-gray-500 shrink-0"></i>
                                <span class="text-gray-400 text-xs">Upload photo</span>
                                <input type="file" name="member_photo_${idx}" accept="image/*" class="sr-only" onchange="this.previousElementSibling.textContent = this.files[0]?.name || 'Upload photo'">
                            </label>
                        </div>` : ''}
                    </div>
                </div>
            `;
        }

        // Build in-game role selector if game defines roles
        let gameRoleSelector = '';
        const roles = runtimeConfig.rosterRoles || [];
        if (roles.length > 0) {
            const opts = roles.map(r => `<option value="${r.code}">${r.name}</option>`).join('');
            gameRoleSelector = `
                <div class="mt-3 pt-3 border-t border-white/5">
                    <label class="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-1.5 block">In-Game Role</label>
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
                    <input type="text" name="member_game_id_${idx}" class="input-premium text-sm" placeholder="${runtimeConfig.gameIdLabel}" required oninput="checkStep('roster')">
                    <input type="text" name="member_display_name_${idx}" class="input-premium text-sm" placeholder="Display Name" required oninput="checkStep('roster')">
                </div>
                <button type="button" class="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-gray-500 hover:text-red-400 hover:border-red-400/30 transition-all shrink-0" onclick="removeGuestMember(this)" title="Remove">
                    <i data-lucide="x" class="w-4 h-4"></i>
                </button>
            </div>
            ${detailPanel}
            ${gameRoleSelector}
        `;

        list.appendChild(row);
        guestMemberCount++;
        updateRosterCounts();
        lucide.createIcons();
        checkStep('roster');
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
                checkStep('roster');
            }, 300);
        }
    }
    window.removeGuestMember = removeGuestMember;

    function renumberGuestMembers() {
        const rows = document.querySelectorAll('[data-guest-row]');
        rows.forEach((row, i) => {
            row.setAttribute('data-guest-row', i);
            const num = row.querySelector('.rounded-full');
            if (num && !num.querySelector('i')) num.textContent = i + 1;
        });
        guestMemberCount = rows.length;
    }

    // ── Member Detail Panel Toggle ────────────────────────────
    function toggleMemberDetail(btn) {
        const panel = btn.nextElementSibling;
        if (!panel) return;

        const icon = btn.querySelector('i, svg');
        if (panel.classList.contains('expanded')) {
            panel.classList.remove('expanded');
            if (icon) icon.style.transform = 'rotate(0deg)';
        } else {
            panel.classList.add('expanded');
            if (icon) icon.style.transform = 'rotate(180deg)';
        }
    }
    window.toggleMemberDetail = toggleMemberDetail;

    // ── Roster Counts ─────────────────────────────────────────
    function updateRosterCounts() {
        const countText = document.getElementById('roster-count-text');
        if (!countText) return;

        if (runtimeConfig.isGuestTeam) {
            const rows = document.querySelectorAll('[data-guest-row]');
            countText.textContent = rows.length;
        } else {
            const members = document.querySelectorAll('[data-member-id]');
            countText.textContent = members.length;
        }
    }
    window.updateRosterCounts = updateRosterCounts;

    // ── File Upload Preview ───────────────────────────────────
    function previewUpload(input, type) {
        const file = input.files[0];
        if (!file) return;

        const maxSize = type === 'banner' ? 5 * 1024 * 1024 : 2 * 1024 * 1024;
        if (file.size > maxSize) {
            alert(`File too large. Maximum ${type === 'banner' ? '5MB' : '2MB'}.`);
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

    // ── Bio Counter ───────────────────────────────────────────
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

    // ── Terms Validation ──────────────────────────────────────
    function validateTerms() {
        const cb = document.getElementById('terms-checkbox');
        const submitBtn = document.getElementById('btn-submit');

        if (cb && submitBtn) {
            if (cb.checked) {
                submitBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                submitBtn.classList.add('hover:scale-105');
                submitBtn.style.boxShadow = '0 0 30px rgba(var(--accent-rgb), 0.6)';
                cb.style.borderColor = 'var(--accent)';
                cb.style.background = 'var(--accent)';
            } else {
                submitBtn.classList.add('opacity-50', 'cursor-not-allowed');
                submitBtn.classList.remove('hover:scale-105');
                submitBtn.style.boxShadow = '0 0 25px rgba(var(--accent-rgb), 0.4)';
                cb.style.borderColor = '';
                cb.style.background = '';
            }
        }

        checkStep('review');
    }
    window.validateTerms = validateTerms;

    // ── Review Sync ───────────────────────────────────────────
    function syncReview() {
        // Sync communication fields
        syncReviewField('comm_phone', 'review-phone');
        syncReviewField('phone', 'review-phone');
        syncReviewField('comm_discord', 'review-discord');
        syncReviewField('discord', 'review-discord');

        // Sync coordinator role
        const coordRole = document.querySelector('input[name="coordinator_role"]:checked');
        const reviewCoordRole = document.getElementById('review-coord-role');
        if (coordRole && reviewCoordRole) {
            reviewCoordRole.textContent = coordRole.closest('label')?.querySelector('p.text-sm')?.textContent || coordRole.value;
        }

        // Sync payment
        const paymentMethod = document.querySelector('input[name="payment_method"]:checked');
        const reviewGateway = document.getElementById('review-gateway');
        if (paymentMethod && reviewGateway) {
            const methodMap = { deltacoin: 'DeltaCoin', bkash: 'bKash', nagad: 'Nagad', rocket: 'Rocket' };
            reviewGateway.textContent = methodMap[paymentMethod.value] || paymentMethod.value;
        }

        const trxid = document.getElementById('trxid');
        const reviewTrxid = document.getElementById('review-trxid');
        if (trxid && reviewTrxid) {
            reviewTrxid.textContent = trxid.value.trim() || '—';
        }

        // Sync guest team name
        const guestName = document.querySelector('[name="guest_team_name"]');
        const reviewGuestName = document.getElementById('review-guest-name');
        if (guestName && reviewGuestName) {
            reviewGuestName.textContent = guestName.value.trim() || '—';
        }

        // Sync custom questions
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

        // Sync dynamic comm channels to review
        syncDynamicCommsToReview();

        // Sync guest roster to review
        if (runtimeConfig.isGuestTeam) {
            syncGuestRosterToReview();
        }

        // Sync organizer-enabled fields
        syncReviewField('age', 'review-age');
        syncReviewField('country', 'review-country');
        syncReviewField('platform_server', 'review-platform');
        syncReviewField('captain_display_name', 'review-captain-display');
        syncReviewField('captain_whatsapp', 'review-captain-whatsapp');
        syncReviewField('captain_phone', 'review-captain-phone');
        syncReviewField('captain_discord', 'review-captain-discord');
        syncReviewField('team_region', 'review-team-region');
        syncReviewField('payment_mobile_number', 'review-payment-mobile');
        syncReviewField('payment_notes', 'review-payment-notes');
        syncReviewField('team_bio', 'review-team-bio');

        // Sync preferred contact display
        const prefContact = document.querySelector('input[name="preferred_contact"]:checked');
        const reviewPrefContact = document.getElementById('review-preferred-contact');
        if (prefContact && reviewPrefContact) {
            reviewPrefContact.textContent = prefContact.value || '—';
        }

        // Validate all steps to update sidebar
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

        // Gather all comm_ inputs
        const commInputs = document.querySelectorAll('[data-channel-key]');
        if (commInputs.length === 0) return;

        reviewList.innerHTML = '';
        commInputs.forEach(input => {
            const key = input.getAttribute('data-channel-key');
            const val = input.value.trim() || '—';
            const label = key.charAt(0).toUpperCase() + key.slice(1);
            const li = document.createElement('li');
            li.className = 'flex justify-between';
            li.innerHTML = `
                <span class="text-gray-500">${label}:</span>
                <strong class="text-white font-mono text-xs">${val}</strong>
            `;
            reviewList.appendChild(li);
        });
    }

    function syncGuestRosterToReview() {
        const container = document.getElementById('review-guest-roster');
        if (!container) return;

        const rows = document.querySelectorAll('[data-guest-row]');
        container.innerHTML = '';

        rows.forEach((row, idx) => {
            const gameId = row.querySelector(`[name="member_game_id_${row.getAttribute('data-guest-row')}"]`);
            const displayName = row.querySelector(`[name="member_display_name_${row.getAttribute('data-guest-row')}"]`);
            const role = row.querySelector(`[name="member_role_${row.getAttribute('data-guest-row')}"]`);

            const li = document.createElement('div');
            li.className = 'flex justify-between items-center p-2 rounded-lg hover:bg-white/5 transition-colors';
            li.innerHTML = `
                <span class="text-sm text-gray-300">
                    ${displayName?.value || gameId?.value || `Member ${idx+1}`}
                    <span class="text-[8px] uppercase text-gray-500 ml-1">${role?.value || 'starter'}</span>
                </span>
                <span class="font-mono text-xs text-gray-500">${gameId?.value || '—'}</span>
            `;
            container.appendChild(li);
        });
    }

    // ── Copy Number Utility ───────────────────────────────────
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

    // ── Member Detail Modal (Verified Roster) ───────────────
    let activeModalMemberId = null;

    function openMemberModal(cardEl) {
        const modal = document.getElementById('member-modal-overlay');
        const body = document.getElementById('member-modal-body');
        if (!modal || !body) return;

        activeModalMemberId = cardEl.dataset.memberId;
        const d = cardEl.dataset;
        const displayName = d.memberDisplayName || d.memberUsername;
        const username = d.memberUsername || '';
        const rosterSlot = d.memberRosterSlot || 'STARTER';
        const playerRole = d.memberPlayerRole || '';
        const isCaptain = d.memberIsCaptain === 'true';

        // Build avatar
        const avatarImg = cardEl.querySelector('img');
        const avatarSrc = avatarImg ? avatarImg.src : `https://ui-avatars.com/api/?name=${encodeURIComponent(username)}&background=111&color=fff&size=96`;

        // Build role options
        const roles = runtimeConfig.rosterRoles || [];
        let roleOptions = '<option value="">— None —</option>';
        roles.forEach(r => {
            const selected = r.code === playerRole ? 'selected' : '';
            roleOptions += `<option value="${r.code}" ${selected}>${r.name}</option>`;
        });

        // Build slot options
        const rc = runtimeConfig.rosterConfig;
        let slotOptions = `
            <option value="STARTER" ${rosterSlot === 'STARTER' ? 'selected' : ''}>Starter</option>
            <option value="SUBSTITUTE" ${rosterSlot === 'SUBSTITUTE' ? 'selected' : ''}>Substitute</option>
        `;
        if (rc.allowCoaches) {
            slotOptions += `<option value="COACH" ${rosterSlot === 'COACH' ? 'selected' : ''}>Coach</option>`;
        }

        body.innerHTML = `
            <div class="flex items-center gap-5 mb-2">
                <div class="w-20 h-20 rounded-full overflow-hidden border-2 ${isCaptain ? 'border-dc-gold' : 'border-white/10'} shadow-xl shrink-0">
                    <img src="${avatarSrc}" class="w-full h-full object-cover" alt="${displayName}">
                </div>
                <div>
                    <h4 class="text-xl font-black text-white">${displayName}</h4>
                    <p class="text-xs text-gray-500 font-mono">@${username}</p>
                    ${isCaptain ? '<span class="inline-flex items-center gap-1 mt-1 px-2 py-0.5 rounded bg-dc-gold text-black text-[9px] font-black uppercase"><i data-lucide="crown" class="w-3 h-3"></i> Captain</span>' : ''}
                </div>
            </div>

            <div class="space-y-5">
                <div>
                    <label class="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">Roster Position</label>
                    <select id="modal-roster-slot" class="input-premium text-sm w-full py-3">${slotOptions}</select>
                </div>

                ${roles.length > 0 ? `
                <div>
                    <label class="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">In-Game Role</label>
                    <select id="modal-player-role" class="input-premium text-sm w-full py-3">${roleOptions}</select>
                    <p class="text-[10px] text-gray-600 mt-1">Tactical role for this game (e.g., Duelist, Controller)</p>
                </div>
                ` : ''}

                ${runtimeConfig.formConfig.showMemberGameIds ? `
                <div>
                    <label class="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">${runtimeConfig.gameIdLabel}</label>
                    <input type="text" id="modal-game-id" class="input-premium text-sm w-full py-3" placeholder="${runtimeConfig.gameIdPlaceholder}" value="">
                    <p class="text-[10px] text-gray-600 mt-1">The in-game identifier used for match lobbies</p>
                </div>
                ` : ''}

                ${runtimeConfig.formConfig.requireMemberRealName ? `
                <div>
                    <label class="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">Real Name</label>
                    <input type="text" id="modal-real-name" class="input-premium text-sm w-full py-3" placeholder="Full legal name">
                </div>
                ` : ''}

                ${runtimeConfig.formConfig.requireMemberEmail ? `
                <div>
                    <label class="text-[9px] font-bold text-gray-500 uppercase tracking-widest mb-2 block">Email</label>
                    <input type="email" id="modal-email" class="input-premium text-sm w-full py-3" placeholder="member@email.com">
                </div>
                ` : ''}
            </div>
        `;

        // Populate existing hidden field values if any
        const existingSlot = document.querySelector(`[name="member_${activeModalMemberId}_roster_slot"]`);
        const existingRole = document.querySelector(`[name="member_${activeModalMemberId}_player_role"]`);
        const existingGameId = document.querySelector(`[name="member_${activeModalMemberId}_game_id"]`);
        const existingRealName = document.querySelector(`[name="member_${activeModalMemberId}_real_name"]`);
        const existingEmail = document.querySelector(`[name="member_${activeModalMemberId}_email"]`);
        if (existingSlot && document.getElementById('modal-roster-slot')) {
            document.getElementById('modal-roster-slot').value = existingSlot.value;
        }
        if (existingRole && document.getElementById('modal-player-role')) {
            document.getElementById('modal-player-role').value = existingRole.value;
        }
        if (existingGameId && document.getElementById('modal-game-id')) {
            document.getElementById('modal-game-id').value = existingGameId.value;
        }
        if (existingRealName && document.getElementById('modal-real-name')) {
            document.getElementById('modal-real-name').value = existingRealName.value;
        }
        if (existingEmail && document.getElementById('modal-email')) {
            document.getElementById('modal-email').value = existingEmail.value;
        }

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        lucide.createIcons();

        // Animate panel in
        const panel = document.getElementById('member-modal-panel');
        if (panel) {
            panel.style.transform = 'translateX(100%)';
            requestAnimationFrame(() => { panel.style.transform = 'translateX(0)'; });
        }
    }
    window.openMemberModal = openMemberModal;

    function closeMemberModal(event) {
        if (event && event.target !== event.currentTarget) return;
        const modal = document.getElementById('member-modal-overlay');
        const panel = document.getElementById('member-modal-panel');
        if (panel) {
            panel.style.transform = 'translateX(100%)';
        }
        setTimeout(() => {
            if (modal) modal.classList.add('hidden');
            document.body.style.overflow = '';
            activeModalMemberId = null;
        }, 300);
    }
    window.closeMemberModal = closeMemberModal;

    function saveMemberChanges() {
        if (!activeModalMemberId) return;

        const card = document.querySelector(`[data-member-id="${activeModalMemberId}"]`);
        if (!card) { closeMemberModal(); return; }

        // Read modal values
        const slotSelect = document.getElementById('modal-roster-slot');
        const roleSelect = document.getElementById('modal-player-role');
        const gameIdInput = document.getElementById('modal-game-id');
        const realNameInput = document.getElementById('modal-real-name');
        const emailInput = document.getElementById('modal-email');

        // Update hidden fields on the card
        if (slotSelect) {
            const hiddenSlot = card.querySelector(`[name="member_${activeModalMemberId}_roster_slot"]`);
            if (hiddenSlot) hiddenSlot.value = slotSelect.value;
            card.dataset.memberRosterSlot = slotSelect.value;
            updateSlotBadge(card, slotSelect.value);
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

        if (realNameInput) {
            let hiddenRealName = card.querySelector(`[name="member_${activeModalMemberId}_real_name"]`);
            if (!hiddenRealName) {
                hiddenRealName = document.createElement('input');
                hiddenRealName.type = 'hidden';
                hiddenRealName.name = `member_${activeModalMemberId}_real_name`;
                card.appendChild(hiddenRealName);
            }
            hiddenRealName.value = realNameInput.value;
        }

        if (emailInput) {
            let hiddenEmail = card.querySelector(`[name="member_${activeModalMemberId}_email"]`);
            if (!hiddenEmail) {
                hiddenEmail = document.createElement('input');
                hiddenEmail.type = 'hidden';
                hiddenEmail.name = `member_${activeModalMemberId}_email`;
                card.appendChild(hiddenEmail);
            }
            hiddenEmail.value = emailInput.value;
        }

        closeMemberModal();
        checkStep('roster');
    }
    window.saveMemberChanges = saveMemberChanges;

    function updateSlotBadge(card, slot) {
        // Update the player-slot class
        card.classList.remove('slot-starter', 'slot-sub', 'slot-coach');
        if (slot === 'SUBSTITUTE') {
            card.classList.add('slot-sub');
        } else if (slot === 'COACH') {
            card.classList.add('slot-coach');
        } else {
            card.classList.add('slot-starter');
        }

        // Find and update the slot badge text
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
        // Find player_role badge or create one
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

    // ── Form Submission ───────────────────────────────────────
    function handleSubmit(event) {
        const terms = document.getElementById('terms-checkbox');
        if (!terms || !terms.checked) {
            event.preventDefault();
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
                break;
            }
        }

        if (!allValid) {
            event.preventDefault();
            return false;
        }

        // Show loading overlay
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
            lucide.createIcons();
        }

        return true;
    }
    window.handleSubmit = handleSubmit;

})();
