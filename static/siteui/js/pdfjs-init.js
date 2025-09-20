/* DeltaCrown — Inline PDF.js bootstrap
 * Requirements:
 *   <script src="{% static 'siteui/pdfjs/pdf.js' %}"></script>
 *   <script>pdfjsLib.GlobalWorkerOptions.workerSrc = "{% static 'siteui/pdfjs/pdf.worker.js' %}";</script>
 *
 * Markup (minimal expected by this script):
 *   <div class="pdfjs-viewer"
 *        data-pdf-url="/media/rules.pdf"
 *        data-start-page="1"
 *        data-title="Tournament Rules">
 *     <div class="pdfjs-toolbar">
 *       <button data-pdf-prev aria-label="Previous page">Prev</button>
 *       <span class="small">Page <span data-pdf-page>1</span>/<span data-pdf-pages>?</span></span>
 *       <button data-pdf-next aria-label="Next page">Next</button>
 *       <button data-pdf-zoomout aria-label="Zoom out">-</button>
 *       <button data-pdf-zoomin aria-label="Zoom in">+</button>
 *       <a data-pdf-download rel="noopener" target="_blank">Download</a>
 *     </div>
 *     <canvas class="pdfjs-canvas"></canvas>
 *     <div class="pdfjs-error" hidden></div>
 *   </div>
 *
 * Notes:
 * - Supports multiple viewers per page.
 * - Lazy-initializes on first intersection (50% visible) to save work.
 * - Theme-agnostic; the PDF page is rendered with transparent background.
 */
(function () {
  const hasPDFJS = () => !!(window.pdfjsLib && window.pdfjsLib.getDocument);

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.from((root || document).querySelectorAll(sel)); }

  function initAll() {
    const viewers = $all('.pdfjs-viewer[data-pdf-url]');
    if (!viewers.length) return;

    const io = ('IntersectionObserver' in window) ? new IntersectionObserver(onIntersect, { threshold: 0.5 }) : null;

    viewers.forEach((v) => {
      v.__dcPdf = { booted: false }; // guard
      if (io) {
        io.observe(v);
      } else {
        // Fallback: init immediately
        bootViewer(v);
      }
    });

    function onIntersect(entries) {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          bootViewer(entry.target);
          io && io.unobserve(entry.target);
        }
      });
    }
  }

  async function bootViewer(root) {
    if (root.__dcPdf && root.__dcPdf.booted) return;
    root.__dcPdf = { booted: true };

    const url = root.getAttribute('data-pdf-url');
    const startPage = parseInt(root.getAttribute('data-start-page') || '1', 10);
    const title = root.getAttribute('data-title') || 'PDF';

    const canvas = $('.pdfjs-canvas', root) || document.createElement('canvas');
    if (!canvas.parentNode) root.appendChild(canvas);
    const errorBox = $('.pdfjs-error', root) || makeErrorBox(root);
    const pageNumEl = $('[data-pdf-page]', root);
    const pagesEl = $('[data-pdf-pages]', root);
    const btnPrev = $('[data-pdf-prev]', root);
    const btnNext = $('[data-pdf-next]', root);
    const btnZoomIn = $('[data-pdf-zoomin]', root);
    const btnZoomOut = $('[data-pdf-zoomout]', root);
    const linkDownload = $('[data-pdf-download]', root);
    if (linkDownload) {
      linkDownload.href = url;
      linkDownload.setAttribute('download', '');
      linkDownload.textContent = linkDownload.textContent || 'Download';
    }

    if (!hasPDFJS()) {
      showError('PDF viewer library is not loaded.', root, errorBox);
      return;
    }

    let pdf, pageNum = Math.max(1, startPage), pageCount = 0, scale = 1.0;
    const ctx = canvas.getContext('2d');

    try {
      pdf = await window.pdfjsLib.getDocument({ url }).promise;
      pageCount = pdf.numPages;
      if (pagesEl) pagesEl.textContent = String(pageCount);
      await renderPage();

      // Wire controls
      btnPrev && btnPrev.addEventListener('click', () => {
        if (pageNum > 1) { pageNum--; renderPage(); }
      });
      btnNext && btnNext.addEventListener('click', () => {
        if (pageNum < pageCount) { pageNum++; renderPage(); }
      });
      btnZoomIn && btnZoomIn.addEventListener('click', () => {
        scale = Math.min(3.0, scale + 0.1);
        renderPage(true);
      });
      btnZoomOut && btnZoomOut.addEventListener('click', () => {
        scale = Math.max(0.5, scale - 0.1);
        renderPage(true);
      });
    } catch (err) {
      showError('Could not open PDF. Please try downloading instead.', root, errorBox, err);
      return;
    }

    async function renderPage(keepScroll) {
      try {
        const page = await pdf.getPage(pageNum);
        const viewport = page.getViewport({ scale });
        const ratio = window.devicePixelRatio || 1;

        canvas.width = Math.floor(viewport.width * ratio);
        canvas.height = Math.floor(viewport.height * ratio);
        canvas.style.width = Math.floor(viewport.width) + 'px';
        canvas.style.height = Math.floor(viewport.height) + 'px';

        const renderContext = {
          canvasContext: ctx,
          viewport,
          background: 'rgba(0,0,0,0)' // transparent to let theme show through
        };

        if (!keepScroll) {
          try { canvas.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (_) {}
        }

        await page.render(renderContext).promise;
        if (pageNumEl) pageNumEl.textContent = String(pageNum);
        root.setAttribute('data-pdf-ready', '1');
      } catch (err) {
        showError('Failed to render this page.', root, errorBox, err);
      }
    }
  }

  function makeErrorBox(root) {
    const el = document.createElement('div');
    el.className = 'pdfjs-error';
    el.hidden = true;
    root.appendChild(el);
    return el;
  }

  function showError(message, root, box, err) {
    if (!box) box = makeErrorBox(root);
    box.hidden = false;
    box.textContent = message;
    if (err && window.console) console.warn('[PDF]', err);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }
})();
