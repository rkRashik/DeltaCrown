/*
 * Linked OAuth Passports UI controller (Phase 7)
 * Vanilla JS only - syncs card states from GamePassport API payloads.
 */

(function () {
    'use strict';

    const SECTION_ID = 'oauth-linked-passports';

    const GAME_CONFIG = {
        valorant: {
            slugs: ['valorant'],
            label: 'Valorant',
        },
        cs2: {
            slugs: ['cs2', 'counter-strike-2', 'counterstrike2'],
            label: 'Counter-Strike 2',
        },
        dota2: {
            slugs: ['dota2', 'dota-2'],
            label: 'Dota 2',
        },
        rocketleague: {
            slugs: ['rocketleague', 'rocket-league'],
            label: 'Rocket League',
        },
    };

    function normalize(value) {
        return String(value || '').trim().toLowerCase().replace(/\s+/g, '').replace(/_/g, '-');
    }

    function getPassportsFromResponse(payload) {
        if (!payload) return [];
        if (Array.isArray(payload?.data?.passports)) return payload.data.passports;
        if (Array.isArray(payload?.passports)) return payload.passports;
        if (Array.isArray(payload)) return payload;
        return [];
    }

    function getSlug(passport) {
        return normalize(
            passport?.game?.slug ||
            passport?.game_slug ||
            passport?.game?.name ||
            passport?.game_display_name ||
            ''
        );
    }

    function findPassportForCard(passports, cardKey) {
        const cfg = GAME_CONFIG[cardKey];
        if (!cfg) return null;
        return passports.find((passport) => cfg.slugs.includes(getSlug(passport))) || null;
    }

    function getIdentityLabel(passport) {
        if (!passport) return 'Not connected';
        const identity = passport.identity_key || passport.ign || passport.in_game_name || '';
        if (!identity) return 'Connected';
        return identity;
    }

    function getLocalLockState(passport) {
        if (!passport) {
            return {
                kind: 'open',
                isDeleteBlocked: false,
                shortLabel: '',
                title: '',
                message: '',
            };
        }

        if (passport.verification_status === 'VERIFIED') {
            return {
                kind: 'verified',
                isDeleteBlocked: true,
                shortLabel: 'Verified lock',
                title: 'Verified Passport',
                message: 'Verified passports cannot be deleted. Contact support if needed.',
            };
        }

        if (passport.cooldown && passport.cooldown.is_active) {
            const days = passport.cooldown.days_remaining || 0;
            return {
                kind: 'cooldown',
                isDeleteBlocked: true,
                shortLabel: days > 0 ? 'Cooldown ' + days + 'd' : 'Cooldown',
                title: 'Deletion Locked',
                message: 'This passport is currently in cooldown and cannot be deleted.',
            };
        }

        if (passport.is_locked) {
            const days = passport.days_locked || 0;
            return {
                kind: 'locked',
                isDeleteBlocked: true,
                shortLabel: days > 0 ? 'Locked ' + days + 'd' : 'Locked',
                title: 'Deletion Locked',
                message: 'This passport is currently locked and cannot be deleted.',
            };
        }

        return {
            kind: 'open',
            isDeleteBlocked: false,
            shortLabel: '',
            title: '',
            message: '',
        };
    }

    function getSharedLockState(passport) {
        if (window.gamePassports && typeof window.gamePassports.getPassportLockState === 'function') {
            return window.gamePassports.getPassportLockState(passport);
        }
        return getLocalLockState(passport);
    }

    function showBlockedToast(title, message) {
        if (window.gamePassports && typeof window.gamePassports.showDeletionBlockedMessage === 'function') {
            window.gamePassports.showDeletionBlockedMessage(title, message, 'locked');
            return;
        }

        if (typeof window.showToast === 'function') {
            window.showToast(message || title, 'warning');
            return;
        }

        if (window.Toast && typeof window.Toast.warning === 'function') {
            window.Toast.warning(message || title);
            return;
        }

        alert(message || title);
    }

    function updateCard(cardEl, passport) {
        const accountEl = cardEl.querySelector('[data-oauth-account]');
        const badgeEl = cardEl.querySelector('[data-oauth-state-badge]');
        const actionBtn = cardEl.querySelector('[data-oauth-action]');

        if (!accountEl || !badgeEl || !actionBtn) return;

        if (!passport) {
            accountEl.textContent = 'Not connected';
            badgeEl.textContent = 'Not Connected';
            badgeEl.className = 'rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-bold text-gray-300';
            actionBtn.textContent = 'Connect';
            actionBtn.dataset.oauthAction = 'connect';
            actionBtn.disabled = false;
            actionBtn.className = 'rounded-lg bg-cyan-400 px-3 py-2 text-xs font-black uppercase tracking-wider text-black transition hover:bg-white';
            delete actionBtn.dataset.oauthPassportId;
            delete actionBtn.dataset.oauthLockTitle;
            delete actionBtn.dataset.oauthLockMessage;
            return;
        }

        accountEl.textContent = getIdentityLabel(passport);
        const lockState = getSharedLockState(passport);

        if (lockState.isDeleteBlocked) {
            badgeEl.textContent = 'Connected';
            badgeEl.className = 'rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-bold text-emerald-200';
            actionBtn.textContent = lockState.shortLabel || 'Locked';
            actionBtn.dataset.oauthAction = 'locked';
            actionBtn.dataset.oauthLockTitle = lockState.title || 'Deletion Locked';
            actionBtn.dataset.oauthLockMessage = lockState.message || 'This passport is currently locked.';
            actionBtn.dataset.oauthLockKind = lockState.kind || 'locked';
            actionBtn.disabled = false;
            actionBtn.className = 'inline-flex items-center gap-2 rounded-lg border border-amber-300/30 bg-amber-400/10 px-3 py-2 text-xs font-black uppercase tracking-wider text-amber-200 cursor-not-allowed';
            actionBtn.innerHTML = '<i class="fa-solid fa-lock"></i><span>' + (lockState.shortLabel || 'Locked') + '</span>';
            delete actionBtn.dataset.oauthPassportId;
            return;
        }

        badgeEl.textContent = 'Connected';
        badgeEl.className = 'rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-bold text-emerald-200';
        actionBtn.textContent = 'Disconnect';
        actionBtn.dataset.oauthAction = 'disconnect';
        actionBtn.dataset.oauthPassportId = String(passport.id);
        actionBtn.disabled = false;
        actionBtn.className = 'rounded-lg border border-red-400/40 bg-red-500/10 px-3 py-2 text-xs font-black uppercase tracking-wider text-red-300 transition hover:bg-red-500/20';
        delete actionBtn.dataset.oauthLockTitle;
        delete actionBtn.dataset.oauthLockMessage;
        delete actionBtn.dataset.oauthLockKind;
    }

    function render(passports) {
        const root = document.getElementById(SECTION_ID);
        if (!root) return;

        const cards = root.querySelectorAll('[data-oauth-game]');
        cards.forEach((cardEl) => {
            const cardKey = cardEl.dataset.oauthGame;
            const match = findPassportForCard(passports, cardKey);
            updateCard(cardEl, match);
        });
    }

    function handleActionClick(event) {
        const btn = event.target.closest('[data-oauth-action]');
        if (!btn) return;

        const action = btn.dataset.oauthAction;
        if (action === 'connect') {
            const route = btn.dataset.oauthRoute;
            if (route) {
                window.location.href = route;
            }
            return;
        }

        if (action === 'disconnect') {
            const passportId = Number(btn.dataset.oauthPassportId || '0');
            if (!passportId) return;

            if (window.gamePassports && typeof window.gamePassports.initiateOTPDelete === 'function') {
                window.gamePassports.initiateOTPDelete(passportId);
            }
            return;
        }

        if (action === 'locked') {
            if (window.gamePassports && typeof window.gamePassports.showDeletionBlockedMessage === 'function') {
                window.gamePassports.showDeletionBlockedMessage(
                    btn.dataset.oauthLockTitle || 'Deletion Locked',
                    btn.dataset.oauthLockMessage || 'This passport is currently locked.',
                    btn.dataset.oauthLockKind || 'locked'
                );
                return;
            }

            showBlockedToast(
                btn.dataset.oauthLockTitle || 'Deletion Locked',
                btn.dataset.oauthLockMessage || 'This passport is currently locked.'
            );
        }
    }

    function init() {
        const root = document.getElementById(SECTION_ID);
        if (!root) return;

        root.addEventListener('click', handleActionClick);

        window.addEventListener('game-passports:data-updated', (event) => {
            const passports = getPassportsFromResponse(event?.detail?.passports || event?.detail);
            render(passports);
        });

        if (window.gamePassports && typeof window.gamePassports.getCurrentPassports === 'function') {
            render(window.gamePassports.getCurrentPassports());
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
