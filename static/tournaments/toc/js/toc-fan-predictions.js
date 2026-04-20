/**
 * TOC Engagement Module — Fan Predictions Command Center
 *
 * Creates and manages live poll prompts from TOC and syncs them to
 * the public detail-page Live Poll widget via detail widgets save API.
 */
;(function () {
    'use strict';

    const NS = (window.TOC = window.TOC || {});
    const CFG = window.TOC_CONFIG || {};

    const $ = (sel, root) => (root || document).querySelector(sel);
    const $$ = (sel, root) => [...(root || document).querySelectorAll(sel)];

    const MAX_QUESTIONS = 8;
    const MAX_OPTIONS = 6;

    const THEME_DEFS = [
        { id: 'cyber', name: 'Liquid Cyber', icon: 'hexagon' },
        { id: 'tactical', name: 'Tactical HUD', icon: 'crosshair' },
        { id: 'glass', name: 'Cinematic Glass', icon: 'droplet' },
        { id: 'sport', name: 'Sport Mobile', icon: 'smartphone' },
        { id: 'native', name: 'DC Native', icon: 'layers' },
    ];
    const THEME_IDS = THEME_DEFS.map((theme) => theme.id);

    const PHASE_DEFS = [
        { id: 'registration', label: 'Pre-Event' },
        { id: 'group', label: 'Group Stages' },
        { id: 'playoffs', label: 'Playoffs' },
        { id: 'finals', label: 'Finals' },
    ];

    const SUGGESTION_MATRIX = {
        valorant: {
            registration: [
                { q: 'Which agent class will define the meta this season?', opts: ['Duelists', 'Initiators', 'Controllers', 'Sentinels'] },
                { q: 'Most banned map prediction?', opts: ['Ascent', 'Bind', 'Split', 'Lotus'] },
            ],
            group: [
                { q: 'First blood in the pistol round?', opts: ['Attacking Side', 'Defending Side'] },
                { q: 'Will this match go to Overtime?', opts: ['Yes, 13-13 incoming', 'No, clean finish'] },
                { q: 'Who wins the economy round buy?', opts: ['Full Buy Team', 'Eco/Thrifty Team'] },
            ],
            playoffs: [
                { q: 'Which map will be the decider?', opts: ['Ascent', 'Bind', 'Sunset', 'Breeze'] },
                { q: 'Highest ACS prediction for this series?', opts: ['Team A Star', 'Team B Star', 'A Flex Player'] },
            ],
            finals: [
                { q: 'Who will MVP the Grand Final?', opts: ['Team Alpha IGL', 'Team Alpha Duelist', 'Team Bravo Duelist'] },
                { q: 'Final scoreline prediction?', opts: ['3-0 Sweep', '3-1 Domination', '3-2 Thriller'] },
            ],
        },
        efootball: {
            registration: [
                { q: 'Which playstyle will rule the Genesis Cup?', opts: ['Possession Game', 'Quick Counter', 'Long Ball Counter', 'Out Wide'] },
            ],
            group: [
                { q: 'Who dominates ball possession in the first half?', opts: ['Home Player', 'Away Player', 'Dead Even (50/50)'] },
                { q: 'First to score?', opts: ['Before 30 mins', 'Right before Half-time', 'Second Half'] },
            ],
            playoffs: [
                { q: 'Will we see a penalty shootout tonight?', opts: ['Yes, taking it all the way', 'No, decided in 90 mins'] },
            ],
            finals: [
                { q: 'Who lifts the ultimate trophy?', opts: ['The Underdog', 'The Tournament Favorite'] },
            ],
        },
        pubgm: {
            registration: [
                { q: 'Which drop location will be the hottest?', opts: ['Pochinki', 'School', 'Military Base', 'Novorepnoye'] },
            ],
            group: [
                { q: 'Who secures the first Chicken Dinner?', opts: ['Group A Leaders', 'Group B Leaders', 'Dark Horse Squad'] },
                { q: 'First squad wipe location?', opts: ['Hot Drop Zone', 'Bridge Camp', 'Open Field Rotation'] },
            ],
            playoffs: [
                { q: 'Most elimination points in Sanhok?', opts: ['Aggressive Pushers', 'Zone Campers', 'Edge Players'] },
            ],
            finals: [
                { q: 'How many points to win it all?', opts: ['Under 150 pts', '150-180 pts', '180+ pts'] },
            ],
        },
        cs2: {
            registration: [
                { q: 'Which weapon will get the most impact kills?', opts: ['AWP', 'AK-47', 'M4A1-S', 'Desert Eagle'] },
            ],
            group: [
                { q: 'Who wins the opening AWP duel?', opts: ['T-Side Sniper', 'CT-Side Sniper'] },
                { q: 'Will the bomb be planted in Round 1?', opts: ['Yes', 'No, team wipe'] },
            ],
            playoffs: [
                { q: 'Will we see a ninja defuse today?', opts: ['Absolutely', 'Not a chance'] },
            ],
            finals: [
                { q: 'Grand Final MVP prediction?', opts: ['Star Rifler', 'Primary AWPer', 'Support / IGL'] },
            ],
        },
    };

    const state = {
        initialized: false,
        activeTheme: 'cyber',
        selectedGame: 'valorant',
        selectedPhase: 'group',
        detailWidgets: {},
        poll: {
            enabled: true,
            isPublished: false,
            activeQuestionIndex: 0,
            questions: [],
        },
    };

    function esc(value) {
        const div = document.createElement('div');
        div.textContent = value == null ? '' : String(value);
        return div.innerHTML;
    }

    function refreshIcons() {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    function toast(message, type) {
        if (NS.toast) {
            NS.toast(message, type || 'info');
        }
    }

    function deepClone(payload) {
        try {
            return JSON.parse(JSON.stringify(payload || {}));
        } catch (_err) {
            return {};
        }
    }

    function slugToken(value, fallback) {
        let token = String(value || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
        if (!token) {
            token = String(fallback || 'token').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
        }
        return token || 'token';
    }

    function normalizeVotes(value) {
        const n = Number(value);
        if (!Number.isFinite(n)) return 0;
        return Math.max(0, Math.round(n));
    }

    function normalizeTheme(value, fallback) {
        const fallbackTheme = THEME_IDS.includes(String(fallback || '').trim().toLowerCase())
            ? String(fallback || '').trim().toLowerCase()
            : 'cyber';
        const nextTheme = String(value || '').trim().toLowerCase();
        return THEME_IDS.includes(nextTheme) ? nextTheme : fallbackTheme;
    }

    function inferGameKey(raw) {
        const token = String(raw || '').toLowerCase();
        if (token.includes('valorant')) return 'valorant';
        if (token.includes('efootball') || token === 'pes') return 'efootball';
        if (token.includes('pubg')) return 'pubgm';
        if (token.includes('cs2') || token.includes('counter')) return 'cs2';
        return 'valorant';
    }

    function inferPhase(rawStage) {
        const stage = String(rawStage || '').toLowerCase();
        if (!stage) return 'group';
        if (stage.includes('final')) return 'finals';
        if (stage.includes('playoff') || stage.includes('knockout') || stage.includes('elimination')) return 'playoffs';
        if (stage.includes('group') || stage.includes('swiss') || stage.includes('round_robin') || stage.includes('round-robin')) return 'group';
        return 'registration';
    }

    function defaultQuestion(questionIndex) {
        return {
            id: 'poll-' + (questionIndex + 1),
            question: questionIndex === 0 ? 'Who will win?' : 'Prediction ' + (questionIndex + 1),
            options: [
                { id: 'option-a', name: 'Option A', votes: 0, percent: 0 },
                { id: 'option-b', name: 'Option B', votes: 0, percent: 0 },
            ],
            total_votes: 0,
        };
    }

    function normalizeQuestion(rawQuestion, questionIndex) {
        const source = rawQuestion && typeof rawQuestion === 'object' ? rawQuestion : {};
        const fallback = defaultQuestion(questionIndex);
        const normalized = {
            id: slugToken(source.id || fallback.id, fallback.id),
            question: String(source.question || fallback.question).trim() || fallback.question,
            options: [],
            total_votes: normalizeVotes(source.total_votes),
        };

        let options = Array.isArray(source.options) ? source.options : [];
        if (!options.length && questionIndex === 0 && Array.isArray(source.preview_options)) {
            options = source.preview_options;
        }

        normalized.options = options
            .map((option, optionIndex) => {
                const opt = option && typeof option === 'object' ? option : { name: option };
                return {
                    id: slugToken(opt.id || ('option-' + (optionIndex + 1)), 'option-' + (optionIndex + 1)),
                    name: String(opt.name || ('Option ' + String.fromCharCode(65 + optionIndex))).trim() || ('Option ' + String.fromCharCode(65 + optionIndex)),
                    votes: normalizeVotes(opt.votes),
                    percent: normalizeVotes(opt.percent),
                };
            })
            .slice(0, MAX_OPTIONS);

        while (normalized.options.length < 2) {
            const optionIndex = normalized.options.length;
            normalized.options.push({
                id: slugToken('option-' + (optionIndex + 1), 'option-' + (optionIndex + 1)),
                name: 'Option ' + String.fromCharCode(65 + optionIndex),
                votes: 0,
                percent: 0,
            });
        }

        recalcQuestion(normalized);
        return normalized;
    }

    function normalizePoll(rawPoll) {
        const source = rawPoll && typeof rawPoll === 'object' ? rawPoll : {};
        let rawQuestions = Array.isArray(source.questions) ? source.questions : [];

        if (!rawQuestions.length) {
            rawQuestions = [{
                id: source.id || 'poll-1',
                question: source.question || 'Who will win?',
                options: Array.isArray(source.options) ? source.options : [],
            }];
        }

        let questions = rawQuestions
            .slice(0, MAX_QUESTIONS)
            .map((question, index) => normalizeQuestion(question, index));

        if (!questions.length) {
            questions = [defaultQuestion(0)];
        }

        return {
            enabled: source.enabled !== undefined ? Boolean(source.enabled) : Boolean(source.active),
            isPublished: source.active !== undefined ? Boolean(source.active) : false,
            theme: normalizeTheme(source.theme, 'cyber'),
            activeQuestionIndex: 0,
            questions,
        };
    }

    function recalcQuestion(question) {
        if (!question || !Array.isArray(question.options)) return;

        question.options = question.options.map((option, optionIndex) => ({
            id: slugToken(option.id || ('option-' + (optionIndex + 1)), 'option-' + (optionIndex + 1)),
            name: String(option.name || ('Option ' + String.fromCharCode(65 + optionIndex))).trim() || ('Option ' + String.fromCharCode(65 + optionIndex)),
            votes: normalizeVotes(option.votes),
            percent: normalizeVotes(option.percent),
        }));

        const total = question.options.reduce((sum, option) => sum + normalizeVotes(option.votes), 0);
        question.total_votes = total;

        if (total <= 0) {
            question.options.forEach((option) => {
                option.percent = 0;
            });
            return;
        }

        let running = 0;
        question.options.forEach((option, index) => {
            if (index === question.options.length - 1) {
                option.percent = Math.max(0, 100 - running);
            } else {
                option.percent = Math.max(0, Math.min(100, Math.round((option.votes / total) * 100)));
                running += option.percent;
            }
        });
    }

    function recalcAllQuestions() {
        if (!state.poll || !Array.isArray(state.poll.questions)) return;
        state.poll.questions.forEach((question) => recalcQuestion(question));
    }

    function totalVotes() {
        if (!state.poll || !Array.isArray(state.poll.questions)) return 0;
        return state.poll.questions.reduce((sum, question) => sum + normalizeVotes(question.total_votes), 0);
    }

    function activeQuestion() {
        if (!state.poll || !Array.isArray(state.poll.questions) || !state.poll.questions.length) {
            return null;
        }
        const idx = Math.max(0, Math.min(state.poll.activeQuestionIndex || 0, state.poll.questions.length - 1));
        state.poll.activeQuestionIndex = idx;
        return state.poll.questions[idx];
    }

    function setSyncStatus(message, tone) {
        const el = $('#fanpred-sync-status');
        if (!el) return;

        if (tone === 'loading') {
            el.className = 'text-[10px] font-mono text-dc-warning mt-2';
            el.textContent = message || 'Syncing fan predictions...';
            return;
        }
        if (tone === 'error') {
            el.className = 'text-[10px] font-mono text-dc-danger mt-2';
            el.textContent = message || 'Sync failed';
            return;
        }
        if (tone === 'success') {
            el.className = 'text-[10px] font-mono text-dc-success mt-2';
            el.textContent = message || 'Synced';
            return;
        }

        el.className = 'text-[10px] font-mono text-dc-text mt-2';
        el.textContent = message || 'Not synced yet';
    }

    function setErrorBanner(message) {
        const el = $('#fanpred-error-banner');
        if (!el) return;

        if (!message) {
            el.classList.add('hidden');
            el.innerHTML = '';
            return;
        }

        el.classList.remove('hidden');
        el.innerHTML = ''
            + '<div class="flex items-start gap-3">'
            + '<i data-lucide="triangle-alert" class="w-4 h-4 text-dc-danger shrink-0 mt-0.5"></i>'
            + '<div class="min-w-0 flex-1">'
            + '<p class="text-xs font-bold text-white">Fan Predictions sync failed</p>'
            + '<p class="text-[11px] text-dc-text mt-1">' + esc(message) + '</p>'
            + '</div></div>';
        refreshIcons();
    }

    function normalizeState() {
        if (!state.poll || typeof state.poll !== 'object') {
            state.poll = normalizePoll({});
            return;
        }

        state.poll.theme = normalizeTheme(state.poll.theme, state.activeTheme || 'cyber');
        state.activeTheme = state.poll.theme;

        if (!Array.isArray(state.poll.questions) || !state.poll.questions.length) {
            state.poll.questions = [defaultQuestion(0)];
        }

        state.poll.questions = state.poll.questions
            .slice(0, MAX_QUESTIONS)
            .map((question, index) => normalizeQuestion(question, index));

        if (!state.poll.questions.length) {
            state.poll.questions = [defaultQuestion(0)];
        }

        const nextIndex = Math.max(0, Math.min(state.poll.activeQuestionIndex || 0, state.poll.questions.length - 1));
        state.poll.activeQuestionIndex = nextIndex;
    }

    function bootstrapState() {
        const initialWidgets = window.TOC_INITIAL_DETAIL_WIDGETS && typeof window.TOC_INITIAL_DETAIL_WIDGETS === 'object'
            ? deepClone(window.TOC_INITIAL_DETAIL_WIDGETS)
            : {};

        state.detailWidgets = initialWidgets;
        const rawPoll = initialWidgets.poll && typeof initialWidgets.poll === 'object' ? initialWidgets.poll : {};
        state.poll = normalizePoll(rawPoll);
        state.activeTheme = state.poll.theme;
        state.selectedGame = inferGameKey(CFG.gameSlug);
        state.selectedPhase = inferPhase(CFG.currentStage);

        normalizeState();
    }

    function applyStatusPill() {
        const pill = $('#fanpred-status-pill');
        if (!pill) return;

        let text = 'Draft Mode';
        let classes = 'inline-flex items-center mt-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-widest bg-amber-500/20 text-amber-400 border-amber-500/30';

        if (!state.poll.enabled) {
            text = 'Hidden';
            classes = 'inline-flex items-center mt-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-widest bg-gray-500/20 text-gray-300 border-gray-400/30';
        } else if (state.poll.isPublished) {
            text = 'Live on Hub';
            classes = 'inline-flex items-center mt-1 px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-widest bg-green-500/20 text-green-400 border-green-500/30';
        }

        pill.className = classes;
        pill.textContent = text;
    }

    function renderThemeButtons() {
        const grid = $('#fanpred-theme-grid');
        if (!grid) return;

        grid.innerHTML = THEME_DEFS.map((theme) => {
            const active = state.activeTheme === theme.id;
            return ''
                + '<button type="button" data-fanpred-theme="' + esc(theme.id) + '" class="fanpred-theme-btn p-3 rounded-xl border flex flex-col items-center justify-center gap-2 transition-all '
                + (active
                    ? 'bg-theme/10 border-theme text-white shadow-[0_0_15px_var(--color-primary-muted)]'
                    : 'bg-black/50 border-dc-border text-dc-text hover:border-dc-borderLight')
                + '">'
                + '<i data-lucide="' + esc(theme.icon) + '" class="w-5 h-5"></i>'
                + '<span class="text-[10px] font-bold uppercase tracking-wider text-center leading-tight">' + esc(theme.name) + '</span>'
                + '</button>';
        }).join('');

        refreshIcons();
    }

    function renderGamePhaseOptions() {
        const gameSelect = $('#fanpred-game-select');
        const phaseSelect = $('#fanpred-phase-select');
        if (!gameSelect || !phaseSelect) return;

        const gameKeys = Object.keys(SUGGESTION_MATRIX);
        gameSelect.innerHTML = gameKeys.map((key) => {
            let label = key;
            if (key === 'pubgm') label = 'PUBG Mobile';
            if (key === 'cs2') label = 'Counter-Strike 2';
            if (key === 'efootball') label = 'eFootball';
            if (key === 'valorant') label = 'Valorant';
            return '<option value="' + esc(key) + '">' + esc(label) + '</option>';
        }).join('');

        phaseSelect.innerHTML = PHASE_DEFS.map((phase) => {
            return '<option value="' + esc(phase.id) + '">' + esc(phase.label) + '</option>';
        }).join('');

        gameSelect.value = gameKeys.includes(state.selectedGame) ? state.selectedGame : 'valorant';
        phaseSelect.value = PHASE_DEFS.some((phase) => phase.id === state.selectedPhase) ? state.selectedPhase : 'group';
    }

    function renderQuestionTabs() {
        const tabs = $('#fanpred-question-tabs');
        if (!tabs) return;

        tabs.innerHTML = state.poll.questions.map((question, index) => {
            const active = index === state.poll.activeQuestionIndex;
            return ''
                + '<button type="button" data-fanpred-question-index="' + index + '" class="px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest transition-colors border '
                + (active
                    ? 'bg-theme/20 text-theme border-theme/40 shadow-[0_0_12px_var(--color-primary-muted)]'
                    : 'bg-dc-surface text-dc-text border-dc-border hover:text-white hover:border-dc-borderLight')
                + '">' + esc(question.question || ('Prompt ' + (index + 1))) + '</button>';
        }).join('');
    }

    function renderOptionRows() {
        const list = $('#fanpred-options-list');
        const question = activeQuestion();
        if (!list || !question) return;

        list.innerHTML = question.options.map((option, index) => {
            return ''
                + '<div class="flex items-center gap-3" data-fanpred-option-row="' + index + '">'
                + '<div class="w-6 h-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-[10px] font-bold text-dc-text">' + esc(String.fromCharCode(65 + index)) + '</div>'
                + '<input type="text" data-fanpred-option-name="' + index + '" value="' + esc(option.name) + '" class="w-full bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-theme/50">'
                + '<input type="number" min="0" step="1" data-fanpred-option-votes="' + index + '" value="' + esc(option.votes) + '" class="w-24 bg-dc-surface border border-dc-border rounded-lg px-3 py-2 text-sm text-center text-white focus:outline-none focus:border-theme/50" title="Override Votes">'
                + '<button type="button" data-fanpred-option-remove="' + index + '" class="p-2.5 text-dc-text hover:text-dc-danger bg-white/5 rounded-lg transition-colors border border-transparent hover:border-dc-danger/30">'
                + '<i data-lucide="trash-2" class="w-4 h-4"></i>'
                + '</button>'
                + '</div>';
        }).join('');

        refreshIcons();
    }

    function renderEditor() {
        normalizeState();

        const question = activeQuestion();
        const questionInput = $('#fanpred-question-input');
        const publishedToggle = $('#fanpred-published-toggle');
        const enabledToggle = $('#fanpred-enabled-toggle');
        const totalVotesEl = $('#fanpred-total-votes');

        if (questionInput && question) questionInput.value = question.question || '';
        if (publishedToggle) publishedToggle.checked = Boolean(state.poll.isPublished);
        if (enabledToggle) enabledToggle.checked = Boolean(state.poll.enabled);
        if (totalVotesEl) totalVotesEl.textContent = String(totalVotes());

        applyStatusPill();
        renderQuestionTabs();
        renderOptionRows();
        renderPreview();
    }

    function renderPreviewOptions(themeId, options) {
        if (themeId === 'cyber') {
            return options.map((option) => {
                return ''
                    + '<div class="w-full relative block">'
                    + '<div class="bg-white/5 border border-white/10 p-3 relative overflow-hidden">'
                    + '<div class="absolute top-0 left-0 bottom-0 bg-gradient-to-r from-theme/80 to-blue-500/80 transition-all duration-700 ease-out" style="width:' + option.percent + '%"></div>'
                    + '<div class="relative flex justify-between items-center text-sm font-medium">'
                    + '<span class="text-white drop-shadow-md">' + esc(option.name) + '</span>'
                    + '<span class="font-display text-white font-black text-lg">' + esc(option.percent) + '%</span>'
                    + '</div></div></div>';
            }).join('');
        }

        if (themeId === 'tactical') {
            return options.map((option) => {
                return ''
                    + '<div class="w-full relative bg-black/60 border border-white/10 p-3 text-left">'
                    + '<div class="flex justify-between items-center text-sm uppercase">'
                    + '<span class="text-[#ece8e1]/80 font-semibold">' + esc(option.name) + '</span>'
                    + '<span class="text-[#ff4655] font-bold">' + esc(option.percent) + '%</span>'
                    + '</div>'
                    + '<div class="mt-2 h-1 w-full bg-white/5 relative overflow-hidden">'
                    + '<div class="absolute left-0 top-0 bottom-0 bg-[#ff4655] transition-all duration-700" style="width:' + option.percent + '%"></div>'
                    + '</div></div>';
            }).join('');
        }

        if (themeId === 'glass') {
            return options.map((option) => {
                return ''
                    + '<div class="w-full relative rounded-xl overflow-hidden border border-white/10 bg-black/20 p-3">'
                    + '<div class="absolute left-0 top-0 bottom-0 bg-white/10 transition-all duration-700 z-0" style="width:' + option.percent + '%"></div>'
                    + '<div class="relative z-10 flex justify-between items-center">'
                    + '<span class="font-medium text-gray-200 text-sm">' + esc(option.name) + '</span>'
                    + '<span class="font-bold text-white text-sm">' + esc(option.percent) + '%</span>'
                    + '</div></div>';
            }).join('');
        }

        if (themeId === 'sport') {
            return options.map((option) => {
                return ''
                    + '<div class="w-full relative rounded-lg bg-black border border-gray-700 p-1">'
                    + '<div class="absolute inset-y-0 left-0 bg-gradient-to-r from-yellow-500 to-yellow-400 transition-all duration-700" style="width:' + option.percent + '%"></div>'
                    + '<div class="relative z-10 flex justify-between items-center p-2">'
                    + '<span class="font-bold text-sm text-white drop-shadow-md mix-blend-difference">' + esc(option.name) + '</span>'
                    + '<span class="text-yellow-400 font-black text-sm mix-blend-difference">' + esc(option.percent) + '%</span>'
                    + '</div></div>';
            }).join('');
        }

        return options.map((option, idx) => {
            const colorClass = idx % 2 === 0 ? 'bg-theme' : 'bg-blue-500';
            return ''
                + '<div class="w-full text-left">'
                + '<div class="flex justify-between text-sm mb-2">'
                + '<span class="text-dc-textBright font-medium">' + esc(option.name) + '</span>'
                + '<span class="text-white font-bold text-xs">' + esc(option.percent) + '%</span>'
                + '</div>'
                + '<div class="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">'
                + '<div class="h-full rounded-full transition-all duration-700 ' + colorClass + '" style="width:' + option.percent + '%"></div>'
                + '</div></div>';
        }).join('');
    }

    function renderPreview() {
        const question = activeQuestion();
        if (!question) return;

        const wrappers = {
            cyber: $('#fanpred-preview-cyber'),
            tactical: $('#fanpred-preview-tactical'),
            glass: $('#fanpred-preview-glass'),
            sport: $('#fanpred-preview-sport'),
            native: $('#fanpred-preview-native'),
        };

        Object.keys(wrappers).forEach((themeId) => {
            const el = wrappers[themeId];
            if (!el) return;
            if (themeId === state.activeTheme) {
                el.classList.remove('hidden');
            } else {
                el.classList.add('hidden');
            }
        });

        const targets = [
            ['cyber', '#fanpred-preview-question-cyber', '#fanpred-preview-options-cyber'],
            ['tactical', '#fanpred-preview-question-tactical', '#fanpred-preview-options-tactical'],
            ['glass', '#fanpred-preview-question-glass', '#fanpred-preview-options-glass'],
            ['sport', '#fanpred-preview-question-sport', '#fanpred-preview-options-sport'],
            ['native', '#fanpred-preview-question-native', '#fanpred-preview-options-native'],
        ];

        targets.forEach((entry) => {
            const themeId = entry[0];
            const qEl = $(entry[1]);
            const oEl = $(entry[2]);
            if (!qEl || !oEl) return;
            qEl.textContent = question.question;
            oEl.innerHTML = renderPreviewOptions(themeId, question.options);
        });

        refreshIcons();
    }

    function renderEverything() {
        renderThemeButtons();
        renderGamePhaseOptions();
        renderEditor();
    }

    function addQuestion() {
        if (state.poll.questions.length >= MAX_QUESTIONS) {
            toast('Max ' + MAX_QUESTIONS + ' prompts allowed.', 'warning');
            return;
        }

        const nextIndex = state.poll.questions.length;
        const question = defaultQuestion(nextIndex);
        question.id = slugToken('poll-' + (nextIndex + 1), 'poll-' + (nextIndex + 1));
        question.question = 'Prediction ' + (nextIndex + 1);

        state.poll.questions.push(question);
        state.poll.activeQuestionIndex = state.poll.questions.length - 1;
        renderEditor();
    }

    function removeQuestion() {
        if (state.poll.questions.length <= 1) {
            toast('Minimum one prompt is required.', 'warning');
            return;
        }

        state.poll.questions.splice(state.poll.activeQuestionIndex, 1);
        state.poll.activeQuestionIndex = Math.max(0, state.poll.activeQuestionIndex - 1);
        renderEditor();
    }

    function addOption() {
        const question = activeQuestion();
        if (!question) return;
        if (question.options.length >= MAX_OPTIONS) {
            toast('Max ' + MAX_OPTIONS + ' options allowed.', 'warning');
            return;
        }

        const optionIndex = question.options.length;
        question.options.push({
            id: slugToken('option-' + (optionIndex + 1), 'option-' + (optionIndex + 1)),
            name: 'Option ' + String.fromCharCode(65 + optionIndex),
            votes: 0,
            percent: 0,
        });
        recalcQuestion(question);
        renderEditor();
    }

    function removeOption(optionIndex) {
        const question = activeQuestion();
        if (!question) return;
        if (question.options.length <= 2) {
            toast('Minimum 2 options required.', 'warning');
            return;
        }

        if (optionIndex < 0 || optionIndex >= question.options.length) return;
        question.options.splice(optionIndex, 1);
        recalcQuestion(question);
        renderEditor();
    }

    function applySmartSuggestion() {
        const pool = SUGGESTION_MATRIX[state.selectedGame] && SUGGESTION_MATRIX[state.selectedGame][state.selectedPhase]
            ? SUGGESTION_MATRIX[state.selectedGame][state.selectedPhase]
            : [];

        if (!pool.length) {
            toast('No smart suggestions available for this context yet.', 'warning');
            return;
        }

        const pick = pool[Math.floor(Math.random() * pool.length)];
        const question = activeQuestion();
        if (!question) return;

        question.question = String(pick.q || 'Who will win?');
        question.options = (pick.opts || []).slice(0, MAX_OPTIONS).map((optName, index) => {
            return {
                id: slugToken('opt-' + Date.now() + '-' + index, 'option-' + (index + 1)),
                name: String(optName || ('Option ' + String.fromCharCode(65 + index))),
                votes: Math.floor(Math.random() * 800) + 50,
                percent: 0,
            };
        });

        while (question.options.length < 2) {
            const idx = question.options.length;
            question.options.push({
                id: slugToken('option-' + (idx + 1), 'option-' + (idx + 1)),
                name: 'Option ' + String.fromCharCode(65 + idx),
                votes: 0,
                percent: 0,
            });
        }

        state.poll.isPublished = false;
        recalcQuestion(question);
        renderEditor();
        toast('Smart prompt generated. Review and sync when ready.', 'success');
    }

    function computePrimaryPreviewOptions(primaryQuestion) {
        const question = primaryQuestion || defaultQuestion(0);
        const opts = Array.isArray(question.options) ? question.options : [];

        const first = opts[0] || { name: 'Option A', percent: 50 };
        const second = opts[1] || { name: 'Option B', percent: 50 };

        let firstPct = normalizeVotes(first.percent);
        let secondPct = normalizeVotes(second.percent);
        const sum = firstPct + secondPct;

        if (sum <= 0) {
            firstPct = 50;
            secondPct = 50;
        } else if (sum !== 100) {
            firstPct = Math.max(0, Math.min(100, Math.round((firstPct / sum) * 100)));
            secondPct = Math.max(0, 100 - firstPct);
        }

        return [
            { id: slugToken(first.id || 'option-a', 'option-a'), name: String(first.name || 'Option A'), percent: firstPct },
            { id: slugToken(second.id || 'option-b', 'option-b'), name: String(second.name || 'Option B'), percent: secondPct },
        ];
    }

    function buildPollPayloadForSave() {
        normalizeState();
        recalcAllQuestions();

        const questions = state.poll.questions.map((question, questionIndex) => {
            return {
                id: slugToken(question.id || ('poll-' + (questionIndex + 1)), 'poll-' + (questionIndex + 1)),
                question: String(question.question || ('Prediction ' + (questionIndex + 1))).trim() || ('Prediction ' + (questionIndex + 1)),
                options: question.options.slice(0, MAX_OPTIONS).map((option, optionIndex) => {
                    return {
                        id: slugToken(option.id || ('option-' + (optionIndex + 1)), 'option-' + (optionIndex + 1)),
                        name: String(option.name || ('Option ' + String.fromCharCode(65 + optionIndex))).trim() || ('Option ' + String.fromCharCode(65 + optionIndex)),
                    };
                }),
            };
        });

        const primary = questions[0] || defaultQuestion(0);
        const primaryPreviewOptions = computePrimaryPreviewOptions(activeQuestion());

        return {
            enabled: Boolean(state.poll.enabled),
            active: Boolean(state.poll.isPublished),
            theme: normalizeTheme(state.activeTheme, state.poll.theme || 'cyber'),
            question: String(primary.question || 'Who will win?'),
            options: primaryPreviewOptions.map((option) => ({ name: option.name, percent: option.percent })),
            questions,
        };
    }

    function withButtonSpinner(button) {
        if (!button) return function () {};
        const original = button.innerHTML;
        button.disabled = true;
        button.classList.add('opacity-60', 'pointer-events-none');
        button.innerHTML = '<span class="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></span><span>Saving...</span>';
        return function restore() {
            button.disabled = false;
            button.classList.remove('opacity-60', 'pointer-events-none');
            button.innerHTML = original;
        };
    }

    async function saveAndSync() {
        const saveUrl = CFG.detailWidgetsSaveUrl || '';
        if (!saveUrl) {
            toast('Detail widget save URL missing from TOC config.', 'error');
            return;
        }

        const saveBtn = $('#fanpred-save-btn');
        const restore = withButtonSpinner(saveBtn);
        setErrorBanner('');
        setSyncStatus('Syncing fan predictions to public detail widget...', 'loading');

        try {
            if (!state.detailWidgets || typeof state.detailWidgets !== 'object') {
                state.detailWidgets = {};
            }

            state.detailWidgets.poll = buildPollPayloadForSave();

            const response = await fetch(saveUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': typeof NS.getCsrfToken === 'function' ? NS.getCsrfToken() : '',
                },
                body: JSON.stringify({ detail_widgets: state.detailWidgets }),
            });

            let payload = {};
            try {
                payload = await response.json();
            } catch (_err) {
                payload = {};
            }

            if (!response.ok || !payload.success) {
                throw new Error(payload.error || 'Unable to save fan predictions right now.');
            }

            if (payload.detail_widgets && typeof payload.detail_widgets === 'object') {
                state.detailWidgets = deepClone(payload.detail_widgets);
                state.poll = normalizePoll(state.detailWidgets.poll || {});
                state.activeTheme = state.poll.theme;
            }

            renderEditor();
            setSyncStatus('Last synced ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }), 'success');
            toast('Fan Predictions synced to the public Live Poll widget.', 'success');
        } catch (error) {
            const message = error && error.message ? String(error.message) : 'Fan predictions sync failed.';
            setErrorBanner(message);
            setSyncStatus(message, 'error');
            toast(message, 'error');
        } finally {
            restore();
        }
    }

    function bindEvents() {
        const themeGrid = $('#fanpred-theme-grid');
        const gameSelect = $('#fanpred-game-select');
        const phaseSelect = $('#fanpred-phase-select');
        const generateBtn = $('#fanpred-generate-btn');
        const addQuestionBtn = $('#fanpred-add-question-btn');
        const removeQuestionBtn = $('#fanpred-remove-question-btn');
        const questionInput = $('#fanpred-question-input');
        const optionsList = $('#fanpred-options-list');
        const addOptionBtn = $('#fanpred-add-option-btn');
        const publishToggle = $('#fanpred-published-toggle');
        const enabledToggle = $('#fanpred-enabled-toggle');
        const saveBtn = $('#fanpred-save-btn');
        const questionTabs = $('#fanpred-question-tabs');

        if (themeGrid) {
            themeGrid.addEventListener('click', function (event) {
                const button = event.target.closest('[data-fanpred-theme]');
                if (!button) return;
                const nextTheme = normalizeTheme(button.getAttribute('data-fanpred-theme'), state.activeTheme || 'cyber');
                if (!nextTheme) return;
                state.activeTheme = nextTheme;
                state.poll.theme = nextTheme;
                renderThemeButtons();
                renderPreview();
            });
        }

        if (gameSelect) {
            gameSelect.addEventListener('change', function () {
                state.selectedGame = String(gameSelect.value || 'valorant');
            });
        }

        if (phaseSelect) {
            phaseSelect.addEventListener('change', function () {
                state.selectedPhase = String(phaseSelect.value || 'group');
            });
        }

        if (generateBtn) {
            generateBtn.addEventListener('click', function () {
                applySmartSuggestion();
            });
        }

        if (addQuestionBtn) {
            addQuestionBtn.addEventListener('click', function () {
                addQuestion();
            });
        }

        if (removeQuestionBtn) {
            removeQuestionBtn.addEventListener('click', function () {
                removeQuestion();
            });
        }

        if (questionInput) {
            questionInput.addEventListener('input', function () {
                const question = activeQuestion();
                if (!question) return;
                question.question = String(questionInput.value || '').trim();
                if (!question.question) {
                    question.question = 'Prediction ' + (state.poll.activeQuestionIndex + 1);
                }
                renderQuestionTabs();
                renderPreview();
            });
        }

        if (questionTabs) {
            questionTabs.addEventListener('click', function (event) {
                const button = event.target.closest('[data-fanpred-question-index]');
                if (!button) return;
                const index = Number(button.getAttribute('data-fanpred-question-index'));
                if (!Number.isFinite(index)) return;
                state.poll.activeQuestionIndex = Math.max(0, Math.min(index, state.poll.questions.length - 1));
                renderEditor();
            });
        }

        if (optionsList) {
            optionsList.addEventListener('input', function (event) {
                const nameInput = event.target.closest('[data-fanpred-option-name]');
                const votesInput = event.target.closest('[data-fanpred-option-votes]');
                const question = activeQuestion();
                if (!question) return;

                if (nameInput) {
                    const idx = Number(nameInput.getAttribute('data-fanpred-option-name'));
                    if (!Number.isFinite(idx) || idx < 0 || idx >= question.options.length) return;
                    question.options[idx].name = String(nameInput.value || '').trim() || ('Option ' + String.fromCharCode(65 + idx));
                    renderPreview();
                    return;
                }

                if (votesInput) {
                    const idx = Number(votesInput.getAttribute('data-fanpred-option-votes'));
                    if (!Number.isFinite(idx) || idx < 0 || idx >= question.options.length) return;
                    question.options[idx].votes = normalizeVotes(votesInput.value);
                    recalcQuestion(question);
                    renderEditor();
                }
            });

            optionsList.addEventListener('click', function (event) {
                const removeBtn = event.target.closest('[data-fanpred-option-remove]');
                if (!removeBtn) return;
                const idx = Number(removeBtn.getAttribute('data-fanpred-option-remove'));
                if (!Number.isFinite(idx)) return;
                removeOption(idx);
            });
        }

        if (addOptionBtn) {
            addOptionBtn.addEventListener('click', function () {
                addOption();
            });
        }

        if (publishToggle) {
            publishToggle.addEventListener('change', function () {
                state.poll.isPublished = Boolean(publishToggle.checked);
                applyStatusPill();
            });
        }

        if (enabledToggle) {
            enabledToggle.addEventListener('change', function () {
                state.poll.enabled = Boolean(enabledToggle.checked);
                applyStatusPill();
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', function () {
                saveAndSync();
            });
        }
    }

    function initOnce() {
        if (state.initialized) return;
        state.initialized = true;

        bootstrapState();
        bindEvents();
        renderEverything();
        setSyncStatus('Ready. Update prompts and click Save & Sync.', 'neutral');
    }

    function onTabChanged(event) {
        const tab = event && event.detail ? event.detail.tab : '';
        if (tab !== 'fan-predictions') return;
        initOnce();
        renderEverything();
    }

    document.addEventListener('toc:tab-changed', onTabChanged);

    if ((window.location.hash || '').replace('#', '') === 'fan-predictions') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initOnce);
        } else {
            initOnce();
        }
    }

    NS.fanPredictions = {
        init: initOnce,
        refresh: function () {
            bootstrapState();
            renderEverything();
        },
        saveAndSync,
        generateSmartPoll: applySmartSuggestion,
    };
})();
