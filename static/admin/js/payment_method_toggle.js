/**
 * Tournament Payment Method — Admin Dynamic Fieldset Toggle + Default Instructions
 * 
 * When a payment method is selected (bKash, Nagad, etc.), only the relevant
 * configuration fieldset is shown. All others are hidden.
 * Additionally, auto-fills realistic default instructions when the instructions
 * textarea is empty — the organizer can then edit as needed.
 * 
 * Works with Django Unfold admin theme.
 * DOM: .inline-related > ... > fieldset.module.pm-section.pm-{method}
 */
(function() {
    'use strict';

    const METHODS = ['bkash', 'nagad', 'rocket', 'bank_transfer', 'deltacoin'];

    // ── Default instruction templates (real-world Bangladesh MFS flow) ──
    const DEFAULT_INSTRUCTIONS = {
        bkash: [
            '1. Open your bKash app or dial *247#',
            '2. Select "Send Money"',
            '3. Enter the account number shown above',
            '4. Enter the exact entry fee amount: {{amount}}',
            '5. Enter your bKash PIN to confirm',
            '6. Copy the Transaction ID (TrxID) from the confirmation SMS',
            '7. Paste the TrxID in the field below',
            '',
            '⚠️ Important:',
            '• Send the exact amount — do not add or deduct any extra.',
            '• Use "Send Money" (not "Payment" or "Cash Out").',
            '• Keep the confirmation SMS until your registration is approved.',
        ].join('\n'),

        nagad: [
            '1. Open your Nagad app or dial *167#',
            '2. Select "Send Money"',
            '3. Enter the account number shown above',
            '4. Enter the exact entry fee amount: {{amount}}',
            '5. Enter your Nagad PIN to confirm',
            '6. Copy the Transaction ID (TrxID) from the confirmation SMS',
            '7. Paste the TrxID in the field below',
            '',
            '⚠️ Important:',
            '• Send the exact amount — do not add or deduct any extra.',
            '• Use "Send Money" (not "Cash Out").',
            '• Keep the confirmation SMS until your registration is approved.',
        ].join('\n'),

        rocket: [
            '1. Open your Rocket app or dial *322#',
            '2. Select "Send Money"',
            '3. Enter the account number shown above',
            '4. Enter the exact entry fee amount: {{amount}}',
            '5. Enter your Rocket PIN to confirm',
            '6. Copy the Transaction ID (TrxID) from the confirmation SMS',
            '7. Paste the TrxID in the field below',
            '',
            '⚠️ Important:',
            '• Send the exact amount — do not add or deduct any extra.',
            '• Keep the confirmation SMS until your registration is approved.',
        ].join('\n'),

        bank_transfer: [
            '1. Log in to your bank\'s online/mobile banking app',
            '2. Select "Fund Transfer" or "Send Money"',
            '3. Enter the bank account details shown above',
            '4. Enter the exact entry fee amount: {{amount}}',
            '5. Add your Team Name in the reference/remarks field',
            '6. Confirm the transfer',
            '7. Copy the Transaction Reference / UTR number',
            '8. Paste the reference in the field below',
            '',
            '⚠️ Important:',
            '• Double-check the account number and bank name before sending.',
            '• Transfers may take 1-2 business days to clear.',
            '• Keep the transaction receipt until your registration is approved.',
        ].join('\n'),

        deltacoin: [
            'Your DeltaCoin balance will be automatically deducted upon registration.',
            'Make sure you have sufficient DeltaCoin balance before proceeding.',
            'No manual transaction is required.',
        ].join('\n'),
    };

    function toggleFieldsets(methodSelect) {
        // Find the parent inline form (.inline-related or .inline-stacked)
        const inlineForm = methodSelect.closest('.inline-related') || methodSelect.closest('.djn-inline-form');
        if (!inlineForm) return;

        const selectedMethod = methodSelect.value;

        // Find all pm-section fieldsets within this inline form
        METHODS.forEach(method => {
            const section = inlineForm.querySelector(`fieldset.pm-${method}`);
            if (!section) return;

            if (method === selectedMethod) {
                section.style.display = '';
                // Auto-expand if Unfold collapsed it
                section.classList.remove('collapsed');
            } else {
                section.style.display = 'none';
            }
        });
    }

    /**
     * Auto-fill the instruction textarea with a sensible default
     * when the user picks a method and the textarea is still empty.
     */
    function prefillInstructions(methodSelect) {
        const selectedMethod = methodSelect.value;
        if (!selectedMethod || !DEFAULT_INSTRUCTIONS[selectedMethod]) return;

        const inlineForm = methodSelect.closest('.inline-related') || methodSelect.closest('.djn-inline-form');
        if (!inlineForm) return;

        // Instructions textarea id pattern: id_payment_configurations-N-{method}_instructions
        const textarea = inlineForm.querySelector(
            `textarea[id$="-${selectedMethod}_instructions"]`
        );
        if (!textarea) return;

        // Only prefill if currently empty (don't overwrite organizer edits)
        if (textarea.value.trim() === '') {
            textarea.value = DEFAULT_INSTRUCTIONS[selectedMethod];
            // Trigger input event so Django/Unfold knows the field changed
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }

    function bindSelect(select) {
        toggleFieldsets(select);
        select.addEventListener('change', function() {
            toggleFieldsets(this);
            prefillInstructions(this);
        });
    }

    function initPaymentMethodToggles() {
        // Find all method select dropdowns in payment method inlines
        // Unfold generates ids like: id_payment_configurations-0-method
        document.querySelectorAll('select[id$="-method"]').forEach(select => {
            // Verify this belongs to a payment method inline (not some other model)
            if (select.closest('.inline-related') && select.name && select.name.includes('payment_configurations')) {
                bindSelect(select);
            }
        });
    }

    // Handle dynamically added inlines ("Add another" button)
    function observeNewInlines() {
        const groups = document.querySelectorAll('.inline-group');
        groups.forEach(group => {
            const observer = new MutationObserver(mutations => {
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType !== 1) return;
                        const selects = node.querySelectorAll('select[id$="-method"]');
                        selects.forEach(sel => {
                            if (sel.name && sel.name.includes('payment_configurations')) {
                                bindSelect(sel);
                            }
                        });
                    });
                });
            });
            observer.observe(group, { childList: true, subtree: true });
        });
    }

    // Run when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initPaymentMethodToggles();
            observeNewInlines();
        });
    } else {
        // Delay slightly for Unfold JS to finish rendering
        setTimeout(() => {
            initPaymentMethodToggles();
            observeNewInlines();
        }, 300);
    }
})();
