/**
 * Custom PDF Viewer for Tournament Rules
 * 
 * Features:
 * - Renders PDF pages as canvas elements using PDF.js
 * - Privacy protections: no download UI, no text selection, no right-click
 * - Intercepts copy/save/print shortcuts
 * - Responsive page rendering
 * 
 * Dependencies: PDF.js (loaded via CDN or local)
 */

(function() {
    'use strict';
    
    // PDF.js configuration
    const PDFJS_CDN_BASE = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174';
    const PDFJS_SCRIPT_URL = `${PDFJS_CDN_BASE}/pdf.min.js`;
    const PDFJS_WORKER_URL = `${PDFJS_CDN_BASE}/pdf.worker.min.js`;
    
    // Viewer state
    let pdfjsLib = null;
    let isInitialized = false;
    let activeViewers = new Set();
    
    /**
     * Load PDF.js library dynamically
     */
    function loadPdfJs() {
        return new Promise((resolve, reject) => {
            if (window.pdfjsLib) {
                pdfjsLib = window.pdfjsLib;
                configurePdfJs();
                resolve(pdfjsLib);
                return;
            }
            
            const script = document.createElement('script');
            script.src = PDFJS_SCRIPT_URL;
            script.onload = () => {
                pdfjsLib = window.pdfjsLib;
                configurePdfJs();
                resolve(pdfjsLib);
            };
            script.onerror = () => {
                reject(new Error('Failed to load PDF.js library'));
            };
            document.head.appendChild(script);
        });
    }
    
    /**
     * Configure PDF.js worker
     */
    function configurePdfJs() {
        if (pdfjsLib && pdfjsLib.GlobalWorkerOptions) {
            pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER_URL;
        }
    }
    
    /**
     * Apply privacy protections to viewer container
     */
    function applyPrivacyProtections(container) {
        if (!container) return;
        
        // Prevent context menu (right-click)
        container.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            return false;
        });
        
        // Prevent text selection via drag
        container.addEventListener('selectstart', (e) => {
            e.preventDefault();
            return false;
        });
        
        // Prevent keyboard shortcuts for copy/save/print
        container.addEventListener('keydown', (e) => {
            const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
            const modKey = isMac ? e.metaKey : e.ctrlKey;
            
            if (modKey) {
                // Prevent: Ctrl/Cmd+C (copy), Ctrl/Cmd+S (save), Ctrl/Cmd+P (print)
                if (e.key === 'c' || e.key === 's' || e.key === 'p') {
                    e.preventDefault();
                    return false;
                }
            }
        });
        
        // Mark as protected
        container.setAttribute('data-protected', 'true');
    }
    
    /**
     * Render a single PDF page to canvas
     */
    async function renderPage(page, canvas, scale) {
        const viewport = page.getViewport({ scale });
        const context = canvas.getContext('2d');
        
        // Set canvas dimensions
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        
        // Render the page
        const renderContext = {
            canvasContext: context,
            viewport: viewport
        };
        
        await page.render(renderContext).promise;
    }
    
    /**
     * Calculate optimal scale for container width
     */
    function calculateScale(page, containerWidth) {
        const viewport = page.getViewport({ scale: 1.0 });
        const pageWidth = viewport.width;
        
        // Target 90% of container width for padding
        const targetWidth = containerWidth * 0.9;
        return targetWidth / pageWidth;
    }
    
    /**
     * Initialize PDF viewer for a given container
     * 
     * @param {string} pdfUrl - URL to the PDF file
     * @param {string} containerSelector - CSS selector for the pages container
     * @returns {Promise<void>}
     */
    async function initializeRulesPdfViewer(pdfUrl, containerSelector) {
        try {
            // Validate pdfUrl
            if (!pdfUrl || pdfUrl.trim() === '') {
                console.warn('[Rules PDF] No PDF URL provided, skipping initialization');
                return;
            }
            
            console.log('[Rules PDF] Initializing PDF.js with URL:', pdfUrl);
            
            // Find container
            const container = document.querySelector(containerSelector);
            if (!container) {
                console.error(`[Rules PDF] Container not found: ${containerSelector}`);
                return;
            }
            
            // Show loading state
            container.innerHTML = `
                <div class="td-pdf-loading">
                    <div class="td-pdf-spinner"></div>
                    <p>Loading rulebook...</p>
                </div>
            `;
            
            // Load PDF.js if needed
            if (!pdfjsLib) {
                console.log('[Rules PDF] Loading PDF.js library...');
                await loadPdfJs();
            }
            
            // Fetch PDF manually to avoid IDM interception and direct downloads
            console.log('[Rules PDF] Fetching PDF via fetch()...');
            const response = await fetch(pdfUrl, { 
                credentials: 'same-origin',
                headers: {
                    'Accept': 'application/pdf'
                }
            });
            
            console.log('[Rules PDF] Fetch response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status} when fetching PDF`);
            }
            
            // Get PDF as ArrayBuffer
            const arrayBuffer = await response.arrayBuffer();
            console.log('[Rules PDF] PDF downloaded, size:', arrayBuffer.byteLength, 'bytes');
            
            // Load PDF from data (not URL) to prevent direct navigation
            console.log('[Rules PDF] Loading PDF from ArrayBuffer...');
            const loadingTask = pdfjsLib.getDocument({
                data: arrayBuffer,
                isEvalSupported: false,
                cMapUrl: `${PDFJS_CDN_BASE}/cmaps/`,
                cMapPacked: true
            });
            const pdf = await loadingTask.promise;
            
            console.log('[Rules PDF] PDF loaded successfully, numPages:', pdf.numPages);
            
            // Clear loading state
            container.innerHTML = '';
            
            // Get container width for scale calculation
            const containerWidth = container.offsetWidth || 800;
            
            // Render all pages
            for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
                const page = await pdf.getPage(pageNum);
                
                // Create canvas wrapper
                const pageWrapper = document.createElement('div');
                pageWrapper.className = 'td-pdf-page';
                pageWrapper.setAttribute('data-page', pageNum);
                
                // Create canvas
                const canvas = document.createElement('canvas');
                canvas.className = 'td-pdf-canvas';
                
                // Calculate and render
                const scale = calculateScale(page, containerWidth);
                await renderPage(page, canvas, scale);
                
                pageWrapper.appendChild(canvas);
                container.appendChild(pageWrapper);
            }
            
            // Apply privacy protections
            applyPrivacyProtections(container);
            
            // Track active viewer
            activeViewers.add(container);
            
            console.log(`[Rules PDF] Viewer initialized: ${pdf.numPages} pages rendered`);
            
        } catch (error) {
            console.error('[Rules PDF] Error initializing PDF viewer:', error);
            
            // Detailed error logging
            if (error && error.name === 'UnexpectedResponseException') {
                console.error('[Rules PDF] UnexpectedResponseException details:', {
                    name: error.name,
                    message: error.message,
                    status: error.status || 'unknown',
                    url: pdfUrl
                });
            } else if (error.message && error.message.includes('HTTP')) {
                console.error('[Rules PDF] HTTP error:', error.message);
            }
            
            // Show error state
            const container = document.querySelector(containerSelector);
            if (container) {
                container.innerHTML = `
                    <div class="td-pdf-error">
                        <div class="td-pdf-error-icon">⚠️</div>
                        <p class="td-pdf-error-message">Failed to load PDF document.</p>
                        <p class="td-pdf-error-detail">${error.message || 'Please try refreshing the page or contact support.'}</p>
                    </div>
                `;
            }
        }
    }
    
    /**
     * Check if PDF viewer is already initialized
     */
    function isViewerInitialized(containerSelector) {
        const container = document.querySelector(containerSelector);
        return container && activeViewers.has(container);
    }
    
    /**
     * Destroy viewer and cleanup
     */
    function destroyViewer(containerSelector) {
        const container = document.querySelector(containerSelector);
        if (container) {
            container.innerHTML = '';
            activeViewers.delete(container);
        }
    }
    
    // Export to global scope
    window.TournamentPdfViewer = {
        initialize: initializeRulesPdfViewer,
        isInitialized: isViewerInitialized,
        destroy: destroyViewer
    };
    
})();
