/**
 * Spectator WebSocket Client
 * 
 * Phase G: Spectator Live Views
 * 
 * Provides real-time updates for spectator pages via WebSocket connections.
 * Handles automatic reconnection, event logging, and htmx integration.
 * 
 * IDs-Only Discipline:
 * - All events contain only IDs (tournament_id, match_id, participant_id, team_id)
 * - No display names, usernames, or emails
 * - Client-side name resolution via external APIs (future enhancement)
 * 
 * Usage:
 *   const client = new SpectatorWSClient(wsUrl, options);
 *   client.connect();
 *   client.on('score_updated', (data) => { ... });
 */

class SpectatorWSClient {
    constructor(wsUrl, options = {}) {
        this.wsUrl = wsUrl;
        this.options = {
            reconnectDelay: 5000,
            maxReconnectAttempts: 10,
            debug: false,
            ...options
        };
        
        this.ws = null;
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        this.isConnected = false;
        this.eventHandlers = {};
        
        this.log('SpectatorWSClient initialized', { wsUrl });
    }
    
    /**
     * Connect to WebSocket server
     */
    connect() {
        // Get JWT token from localStorage (if available)
        const token = localStorage.getItem('access_token') || '';
        const wsUrlWithToken = token ? `${this.wsUrl}?token=${token}` : this.wsUrl;
        
        this.log('Connecting to WebSocket', { url: this.wsUrl });
        
        try {
            this.ws = new WebSocket(wsUrlWithToken);
            
            this.ws.onopen = this.handleOpen.bind(this);
            this.ws.onmessage = this.handleMessage.bind(this);
            this.ws.onerror = this.handleError.bind(this);
            this.ws.onclose = this.handleClose.bind(this);
        } catch (error) {
            this.log('Failed to create WebSocket', { error }, 'error');
            this.scheduleReconnect();
        }
    }
    
    /**
     * Handle WebSocket connection open
     */
    handleOpen() {
        this.log('WebSocket connected');
        this.isConnected = true;
        this.reconnectAttempts = 0;
        
        // Clear reconnect timer
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        // Trigger 'connected' event
        this.trigger('connected', { timestamp: new Date().toISOString() });
    }
    
    /**
     * Handle WebSocket message
     */
    handleMessage(event) {
        try {
            const data = JSON.parse(event.data);
            this.log('WebSocket message received', { type: data.type });
            
            // Trigger event-specific handlers
            if (data.type) {
                this.trigger(data.type, data.data || data);
            }
            
            // Trigger generic 'message' handler
            this.trigger('message', data);
            
        } catch (error) {
            this.log('Failed to parse WebSocket message', { error }, 'error');
        }
    }
    
    /**
     * Handle WebSocket error
     */
    handleError(error) {
        this.log('WebSocket error', { error }, 'error');
        this.isConnected = false;
        this.trigger('error', { error });
    }
    
    /**
     * Handle WebSocket connection close
     */
    handleClose(event) {
        this.log('WebSocket closed', { code: event.code, reason: event.reason });
        this.isConnected = false;
        
        this.trigger('disconnected', {
            code: event.code,
            reason: event.reason,
            timestamp: new Date().toISOString()
        });
        
        // Schedule reconnect
        this.scheduleReconnect();
    }
    
    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
            this.log('Max reconnect attempts reached', {}, 'error');
            this.trigger('max_reconnect_attempts');
            return;
        }
        
        if (this.reconnectTimer) {
            return; // Already scheduled
        }
        
        this.reconnectAttempts++;
        this.log('Scheduling reconnect', {
            attempt: this.reconnectAttempts,
            delay: this.options.reconnectDelay
        });
        
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, this.options.reconnectDelay);
    }
    
    /**
     * Send message to WebSocket server
     */
    send(type, data = {}) {
        if (!this.isConnected || !this.ws) {
            this.log('Cannot send message: not connected', {}, 'warn');
            return false;
        }
        
        const message = { type, ...data };
        
        try {
            this.ws.send(JSON.stringify(message));
            this.log('Message sent', { type });
            return true;
        } catch (error) {
            this.log('Failed to send message', { error }, 'error');
            return false;
        }
    }
    
    /**
     * Register event handler
     */
    on(eventType, handler) {
        if (!this.eventHandlers[eventType]) {
            this.eventHandlers[eventType] = [];
        }
        this.eventHandlers[eventType].push(handler);
    }
    
    /**
     * Unregister event handler
     */
    off(eventType, handler) {
        if (!this.eventHandlers[eventType]) {
            return;
        }
        
        if (handler) {
            this.eventHandlers[eventType] = this.eventHandlers[eventType].filter(h => h !== handler);
        } else {
            delete this.eventHandlers[eventType];
        }
    }
    
    /**
     * Trigger event handlers
     */
    trigger(eventType, data) {
        const handlers = this.eventHandlers[eventType] || [];
        handlers.forEach(handler => {
            try {
                handler(data);
            } catch (error) {
                this.log('Error in event handler', { eventType, error }, 'error');
            }
        });
    }
    
    /**
     * Disconnect from WebSocket
     */
    disconnect() {
        this.log('Disconnecting WebSocket');
        
        // Clear reconnect timer
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        // Close WebSocket
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.isConnected = false;
    }
    
    /**
     * Log message (respects debug option)
     */
    log(message, data = {}, level = 'info') {
        if (!this.options.debug && level === 'info') {
            return;
        }
        
        const logFn = console[level] || console.log;
        logFn(`[SpectatorWS] ${message}`, data);
    }
}

/**
 * Helper: Integrate SpectatorWSClient with htmx auto-refresh
 * 
 * When WebSocket receives specific events, trigger htmx refresh on matching elements.
 * 
 * Usage:
 *   SpectatorWSHelper.autoRefreshOnEvent(client, {
 *       'score_updated': '[hx-get*="scoreboard/fragment"]',
 *       'bracket_updated': '[hx-get*="leaderboard/fragment"]'
 *   });
 */
class SpectatorWSHelper {
    static autoRefreshOnEvent(client, eventSelectors) {
        Object.entries(eventSelectors).forEach(([eventType, selector]) => {
            client.on(eventType, () => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    if (typeof htmx !== 'undefined') {
                        htmx.trigger(el, 'refresh');
                    }
                });
            });
        });
    }
    
    /**
     * Update connection status indicator
     * 
     * Usage:
     *   SpectatorWSHelper.bindConnectionStatus(client, statusElement);
     */
    static bindConnectionStatus(client, statusElement) {
        if (!statusElement) return;
        
        const updateStatus = (connected) => {
            statusElement.textContent = connected ? 'Connected' : 'Disconnected';
            statusElement.className = connected
                ? 'text-dc-success'
                : 'text-gray-400';
        };
        
        client.on('connected', () => updateStatus(true));
        client.on('disconnected', () => updateStatus(false));
    }
    
    /**
     * Append event to live feed
     * 
     * Usage:
     *   SpectatorWSHelper.bindLiveFeed(client, feedElement);
     */
    static bindLiveFeed(client, feedElement, maxEvents = 20) {
        if (!feedElement) return;
        
        const events = [];
        
        client.on('message', (data) => {
            const event = {
                type: data.type || 'EVENT',
                message: data.message || JSON.stringify(data),
                time: new Date().toLocaleTimeString()
            };
            
            events.unshift(event);
            if (events.length > maxEvents) {
                events.pop();
            }
            
            // Re-render feed
            feedElement.innerHTML = events.map(e => `
                <div class="bg-gradient-card rounded p-3 border border-gray-700 text-sm">
                    <div class="flex items-start justify-between mb-1">
                        <span class="font-semibold text-dc-primary">${e.type}</span>
                        <span class="text-xs text-gray-500">${e.time}</span>
                    </div>
                    <p class="text-gray-300 text-xs">${e.message}</p>
                </div>
            `).join('');
        });
    }
}

// Export for use in modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SpectatorWSClient, SpectatorWSHelper };
}
