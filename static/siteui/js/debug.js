(function(window){
    // Ensure global debug flag exists; default false if not set by server
    if (typeof window.DELTACROWN_DEBUG === 'undefined') {
        window.DELTACROWN_DEBUG = false;
    }

    window.dcLog = function() {
        if (!window.DELTACROWN_DEBUG) return;
        if (!console || !console.log) return;
        try { console.log.apply(console, arguments); } catch(e) { /* ignore */ }
    };

    // Small helper wrappers for console.debug/warn/error if needed
    window.dcDebug = function() { if (window.DELTACROWN_DEBUG && console && console.debug) try { console.debug.apply(console, arguments);} catch(e){} };
    window.dcWarn = function() { if (window.DELTACROWN_DEBUG && console && console.warn) try { console.warn.apply(console, arguments);} catch(e){} };
})(window);
