/**
 * vNext Hub - Dynamic Widget Loader
 * 
 * Fetches and populates hub page widgets with real data from API endpoints:
 * - Live ticker feed
 * - Scout radar (LFT players)
 * - Scrim finder
 * - Team search autocomplete
 * 
 * Features:
 * - Loading states with shimmer placeholders
 * - Error handling with safe fallbacks
 * - AbortController for clean fetch cancellation
 * - CSP-safe (no eval, no inline scripts)
 */

// API Configuration
const API_BASE = '/api/vnext/system';
const ENDPOINTS = {
    ticker: `${API_BASE}/ticker/`,
    lft: `${API_BASE}/players/lft/`,
    scrims: `${API_BASE}/scrims/active/`,
    teamSearch: `${API_BASE}/teams/search/`
};

// Abort controllers for fetch cancellation
let fetchControllers = {
    ticker: null,
    lft: null,
    scrims: null,
    teamSearch: null
};

/**
 * Fetch with timeout and abort controller
 */
async function fetchWithTimeout(url, options = {}, timeout = 10000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        throw error;
    }
}

/**
 * Populate live ticker with real events
 */
async function loadTicker() {
    const tickerContainer = document.querySelector('.animate-marquee');
    if (!tickerContainer) return;
    
    try {
        // Abort previous request if pending
        if (fetchControllers.ticker) {
            fetchControllers.ticker.abort();
        }
        fetchControllers.ticker = new AbortController();
        
        const response = await fetchWithTimeout(
            ENDPOINTS.ticker,
            { signal: fetchControllers.ticker.signal }
        );
        
        if (!response.ok) throw new Error('Ticker fetch failed');
        
        const data = await response.json();
        
        if (!data.ok || !data.data || !data.data.items || data.data.items.length === 0) {
            // No data available - keep placeholder or show message
            console.log('No ticker data available');
            return;
        }
        
        // Build ticker HTML from real data
        const tickerHTML = data.data.items.map(item => {
            switch (item.type) {
                case 'rank_change':
                    return `
                        <div class="flex items-center gap-3 border-l border-white/10 pl-6">
                            <span class="text-delta-violet font-bold"><i class="fas fa-chart-line mr-1"></i> RANKING:</span>
                            <span class="text-white font-medium">${item.title}</span>
                            <span class="text-slate-500 text-[10px] uppercase">${item.subtitle}</span>
                        </div>
                    `;
                case 'team_created':
                    return `
                        <div class="flex items-center gap-3 border-l border-white/10 pl-6">
                            <span class="text-delta-electric font-bold"><i class="fas fa-plus-circle mr-1"></i> NEW:</span>
                            <span class="text-white font-medium">${item.title}</span>
                            <span class="text-slate-500 text-[10px] uppercase">${item.subtitle}</span>
                        </div>
                    `;
                case 'member_joined':
                    return `
                        <div class="flex items-center gap-3 border-l border-white/10 pl-6">
                            <span class="text-delta-gold font-bold"><i class="fas fa-exchange-alt mr-1"></i> TRANSFER:</span>
                            <span class="text-white font-medium">${item.title}</span>
                            <span class="text-slate-500 text-[10px] uppercase">${item.subtitle}</span>
                        </div>
                    `;
                case 'match_result':
                    return `
                        <div class="flex items-center gap-3 border-l border-white/10 pl-6">
                            <span class="text-delta-danger font-bold flex items-center gap-2"><i class="fas fa-circle text-[6px] animate-pulse"></i> RESULT:</span>
                            <span class="text-white font-bold">${item.title}</span>
                            <span class="text-[9px] text-slate-400 border border-white/10 px-2 py-0.5 rounded bg-white/5 ml-2 font-bold uppercase">${item.subtitle}</span>
                        </div>
                    `;
                default:
                    return '';
            }
        }).join('');
        
        // Replace ticker content (duplicate for seamless loop)
        tickerContainer.innerHTML = tickerHTML + tickerHTML;
        
    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Ticker fetch aborted');
        } else {
            console.error('Ticker load error:', error);
            // Keep existing placeholder HTML
        }
    }
}

/**
 * Populate scout radar with LFT players
 */
async function loadScoutRadar() {
    const radarContainer = document.querySelector('.scout-radar-players');
    if (!radarContainer) return;
    
    try {
        if (fetchControllers.lft) {
            fetchControllers.lft.abort();
        }
        fetchControllers.lft = new AbortController();
        
        const response = await fetchWithTimeout(
            ENDPOINTS.lft + '?limit=5',
            { signal: fetchControllers.lft.signal }
        );
        
        if (!response.ok) throw new Error('Scout radar fetch failed');
        
        const data = await response.json();
        
        if (!data.ok || !data.data || !data.data.players || data.data.players.length === 0) {
            // No players available - show placeholder message
            radarContainer.innerHTML = `
                <div class="text-center py-6 text-slate-500 text-xs">
                    <i class="fas fa-satellite-dish text-2xl mb-2 opacity-30"></i>
                    <div>No players currently LFT</div>
                </div>
            `;
            return;
        }
        
        // Build scout radar HTML from real data
        const playersHTML = data.data.players.slice(0, 5).map(player => `
            <div class="flex items-center gap-3 p-2.5 rounded-lg bg-white/5 border border-white/5 hover:border-delta-success/50 transition cursor-pointer group">
                <img src="${player.avatar_url || 'https://api.dicebear.com/7.x/avataaars/svg?seed=' + player.username}" class="w-9 h-9 rounded bg-delta-panel">
                <div class="flex-1">
                    <div class="text-xs font-bold text-white group-hover:text-delta-success transition-colors">${player.display_name || player.username}</div>
                    <div class="text-[9px] text-slate-400 font-ui uppercase">${player.role || 'Flex'} • ${player.region || 'Global'}</div>
                </div>
                <a href="${player.profile_url}" class="w-7 h-7 rounded-lg flex items-center justify-center bg-delta-success text-delta-base text-xs hover:scale-110 transition shadow-neon-blue">
                    <i class="fas fa-user"></i>
                </a>
            </div>
        `).join('');
        
        radarContainer.innerHTML = playersHTML;
        
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Scout radar load error:', error);
            // Keep existing placeholder HTML
        }
    }
}

/**
 * Populate scrim finder with active scrims
 */
async function loadScrimFinder() {
    const scrimContainer = document.querySelector('.scrim-finder-list');
    if (!scrimContainer) return;
    
    try:
        if (fetchControllers.scrims) {
            fetchControllers.scrims.abort();
        }
        fetchControllers.scrims = new AbortController();
        
        const response = await fetchWithTimeout(
            ENDPOINTS.scrims + '?limit=5',
            { signal: fetchControllers.scrims.signal }
        );
        
        if (!response.ok) throw new Error('Scrims fetch failed');
        
        const data = await response.json();
        
        if (!data.ok || !data.data || !data.data.scrims || data.data.scrims.length === 0) {
            // No scrims available - show placeholder message
            scrimContainer.innerHTML = `
                <div class="text-center py-6 text-slate-500 text-xs">
                    <i class="fas fa-handshake text-2xl mb-2 opacity-30"></i>
                    <div>No active scrims right now</div>
                </div>
            `;
            return;
        }
        
        // Build scrim finder HTML from real data
        const scrimsHTML = data.data.scrims.slice(0, 3).map(scrim => {
            const startTime = scrim.start_time ? new Date(scrim.start_time).toLocaleTimeString('en-US', {hour: '2-digit', minute: '2-digit'}) : 'TBD';
            const isLive = scrim.start_time && new Date(scrim.start_time) <= new Date();
            
            return `
                <div class="p-3 bg-delta-panel rounded-xl border border-white/5 hover:border-delta-gold transition cursor-pointer group">
                    <div class="flex justify-between items-center mb-1">
                        <span class="text-xs font-bold text-white group-hover:text-delta-gold transition">${scrim.title}</span>
                        <span class="text-[9px] ${isLive ? 'bg-delta-success/10 text-delta-success border-delta-success/20' : 'bg-delta-gold/10 text-delta-gold border-delta-gold/20'} border px-2 py-0.5 rounded font-bold">
                            ${isLive ? 'NOW' : startTime}
                        </span>
                    </div>
                    <div class="text-[10px] text-slate-500 font-ui uppercase tracking-wide">${scrim.format || 'Standard'} • ${scrim.region || 'Any'}</div>
                </div>
            `;
        }).join('');
        
        scrimContainer.innerHTML = scrimsHTML;
        
    } catch (error) {
        if (error.name !== 'AbortError') {
            console.error('Scrim finder load error:', error);
            // Keep existing placeholder HTML
        }
    }
}

/**
 * Setup team search autocomplete
 */
function setupTeamSearch() {
    const searchInput = document.querySelector('input[type="text"][placeholder*="Search team"]');
    if (!searchInput) return;
    
    let searchTimeout = null;
    let resultsContainer = null;
    
    // Create results dropdown
    const createResultsContainer = () => {
        if (resultsContainer) return resultsContainer;
        
        resultsContainer = document.createElement('div');
        resultsContainer.className = 'absolute top-full left-0 right-0 mt-2 bg-delta-panel border border-white/10 rounded-xl shadow-2xl max-h-96 overflow-y-auto z-50 hidden';
        searchInput.parentElement.appendChild(resultsContainer);
        searchInput.parentElement.style.position = 'relative';
        
        return resultsContainer;
    };
    
    // Perform search
    const performSearch = async (query) => {
        if (query.length < 2) {
            resultsContainer.classList.add('hidden');
            return;
        }
        
        try {
            if (fetchControllers.teamSearch) {
                fetchControllers.teamSearch.abort();
            }
            fetchControllers.teamSearch = new AbortController();
            
            const response = await fetchWithTimeout(
                `${ENDPOINTS.teamSearch}?q=${encodeURIComponent(query)}&limit=10`,
                { signal: fetchControllers.teamSearch.signal }
            );
            
            const data = await response.json();
            
            if (!data.ok || !data.data || !data.data.teams) {
                resultsContainer.innerHTML = `
                    <div class="p-4 text-center text-slate-500 text-sm">
                        ${data.safe_message || 'No results found'}
                    </div>
                `;
                resultsContainer.classList.remove('hidden');
                return;
            }
            
            if (data.data.teams.length === 0) {
                resultsContainer.innerHTML = `
                    <div class="p-4 text-center text-slate-500 text-sm">
                        <i class="fas fa-search text-2xl mb-2 opacity-30"></i>
                        <div>No teams match "${query}"</div>
                    </div>
                `;
                resultsContainer.classList.remove('hidden');
                return;
            }
            
            // Build results HTML
            const resultsHTML = data.data.teams.map(team => `
                <a href="${team.url}" class="flex items-center gap-4 p-4 hover:bg-white/5 border-b border-white/5 last:border-b-0 transition group">
                    ${team.logo ? 
                        `<img src="${team.logo}" class="w-10 h-10 rounded-lg object-cover">` :
                        `<div class="w-10 h-10 rounded-lg bg-gradient-to-br from-delta-electric to-delta-violet flex items-center justify-center text-xs font-cyber font-bold text-white">${team.name.substring(0, 3).toUpperCase()}</div>`
                    }
                    <div class="flex-1">
                        <div class="text-sm font-bold text-white group-hover:text-delta-electric">${team.name}</div>
                        <div class="text-xs text-slate-400">${team.tier} • ${team.cp.toLocaleString()} CP</div>
                    </div>
                    <i class="fas fa-arrow-right text-slate-600 group-hover:text-delta-electric transition"></i>
                </a>
            `).join('');
            
            resultsContainer.innerHTML = resultsHTML;
            resultsContainer.classList.remove('hidden');
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Team search error:', error);
            }
        }
    };
    
    // Setup event listeners
    createResultsContainer();
    
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        const query = e.target.value.trim();
        
        if (query.length < 2) {
            resultsContainer.classList.add('hidden');
            return;
        }
        
        searchTimeout = setTimeout(() => {
            performSearch(query);
        }, 300); // Debounce 300ms
    });
    
    searchInput.addEventListener('blur', () => {
        // Delay hiding to allow clicking results
        setTimeout(() => {
            resultsContainer.classList.add('hidden');
        }, 200);
    });
    
    searchInput.addEventListener('focus', (e) => {
        if (e.target.value.trim().length >= 2) {
            resultsContainer.classList.remove('hidden');
        }
    });
}

/**
 * Initialize all widgets on page load
 */
document.addEventListener('DOMContentLoaded', () => {
    console.log('vNext Hub: Initializing dynamic widgets...');
    
    // Load widgets in parallel
    Promise.all([
        loadTicker(),
        loadScoutRadar(),
        loadScrimFinder()
    ]).then(() => {
        console.log('vNext Hub: Widgets loaded');
    }).catch(error => {
        console.error('vNext Hub: Widget load error:', error);
    });
    
    // Setup interactive features
    setupTeamSearch();
});

/**
 * Cleanup on page unload
 */
window.addEventListener('beforeunload', () => {
    // Abort all pending requests
    Object.values(fetchControllers).forEach(controller => {
        if (controller) controller.abort();
    });
});
