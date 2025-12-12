/**
 * Stellarium Web Engine Initialization
 * 
 * This script initializes the Stellarium Web Engine for interactive sky visualization.
 * It is loaded and called by the StellariumWidget Python component.
 */

(function() {
    console.log('[stellarium_init.js] Script loaded');

    // Pending initializations queue (for configs that arrive before script is ready)
    window._stellariumInitQueue = window._stellariumInitQueue || [];
    
    // Store the JS URL for loading (from first config that has it)
    window._stellariumJsUrl = window._stellariumJsUrl || null;

    /**
     * Initialize a Stellarium widget instance.
     * 
     * @param {Object} config - Configuration object
     * @param {string} config.widgetId - Unique identifier for this widget instance
     * @param {string} config.canvasId - ID of the canvas element to render to
     * @param {number} config.latitude - Initial observer latitude in degrees
     * @param {number} config.longitude - Initial observer longitude in degrees
     * @param {string} config.jsUrl - URL to stellarium-web-engine.js
     * @param {string} config.wasmUrl - URL to stellarium-web-engine.wasm
     * @param {string} config.dataUrl - Base URL for sky data
     */
    window.initStellariumWidget = function(config) {
        console.log('[stellarium_init.js] initStellariumWidget called', config);
        
        // Store JS URL if not already set
        if (!window._stellariumJsUrl && config.jsUrl) {
            window._stellariumJsUrl = config.jsUrl;
        }
        
        // If StelWebEngine isn't loaded yet, queue this and start loading
        if (!window.StelWebEngine) {
            window._stellariumInitQueue.push(config);
            loadStelWebEngine();
            return;
        }

        initEngine(config);
    };

    function loadStelWebEngine() {
        // Prevent multiple loads
        if (window._stellariumEngineLoading) return;
        window._stellariumEngineLoading = true;

        const jsUrl = window._stellariumJsUrl || '/swe/build/stellarium-web-engine.js';
        console.log('[stellarium_init.js] Loading StelWebEngine from:', jsUrl);
        
        const script = document.createElement('script');
        script.src = jsUrl;
        script.onload = function() {
            console.log('[stellarium_init.js] StelWebEngine loaded, processing queue:', window._stellariumInitQueue.length);
            // Process any queued initializations
            while (window._stellariumInitQueue.length > 0) {
                const config = window._stellariumInitQueue.shift();
                initEngine(config);
            }
        };
        document.head.appendChild(script);
    }

    function initEngine(config) {
        const { widgetId, canvasId, latitude, longitude, wasmUrl, dataUrl } = config;
        console.log(`[${widgetId}] initEngine called`);

        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`[${widgetId}] Canvas not found: ${canvasId}`);
            return;
        }

        // Resize canvas to match display size
        function resizeCanvas() {
            const rect = canvas.parentElement.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;
        }
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Use provided URLs or fall back to defaults
        const resolvedWasmUrl = wasmUrl || '/swe/build/stellarium-web-engine.wasm';
        const resolvedDataUrl = dataUrl || '/swe/data/';

        StelWebEngine({
            wasmFile: resolvedWasmUrl,
            canvas: canvas,
            onReady: function(stel) {
                console.log(`[${widgetId}] Stellarium engine ready`);

                // Store reference globally for later control
                window[`${widgetId}_stel`] = stel;

                // Load sky data
                const core = stel.core;

                core.stars.addDataSource({ url: resolvedDataUrl + 'stars' });
                core.skycultures.addDataSource({ url: resolvedDataUrl + 'skycultures/western', key: 'western' });
                core.dsos.addDataSource({ url: resolvedDataUrl + 'dso' });
                core.landscapes.addDataSource({ url: resolvedDataUrl + 'landscapes/guereins', key: 'guereins' });
                core.milkyway.addDataSource({ url: resolvedDataUrl + 'surveys/milkyway' });

                // Set initial observer location
                stel.observer.latitude = latitude * stel.D2R;
                stel.observer.longitude = longitude * stel.D2R;

                // Notify Python that we're ready
                window[`${widgetId}_ready`] = true;
            }
        });
    }

    // Process any configs that were queued before this script loaded
    console.log('[stellarium_init.js] Checking queue on load:', window._stellariumInitQueue.length);
    if (window._stellariumInitQueue.length > 0) {
        // Start loading StelWebEngine (it will process the queue when ready)
        loadStelWebEngine();
    }
})();
