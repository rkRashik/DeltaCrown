/**
 * TOC Tournament Launch Guide — Onboarding System
 *
 * Activates when TOC_ONBOARDING.enabled is set by the template.
 * Shows a 11-step guided panel explaining the full tournament lifecycle.
 * Dismissal is persisted in localStorage keyed by tournament slug.
 * CSP-safe: no inline event handlers.
 */
(function () {
  "use strict";

  var cfg = window.TOC_ONBOARDING;
  if (!cfg) return;

  var STORAGE_KEY = "dc_toc_ob_done_" + cfg.slug;

  // Force-open on first redirect even if previously finished.
  var forceOpen = cfg.forceOpen;
  if (!forceOpen && localStorage.getItem(STORAGE_KEY) === "1") return;

  var STEPS = [
    {
      id: "welcome",
      icon: "layout-dashboard",
      title: "Welcome to the Tournament Control Center",
      body: "Your tournament has been created as a <strong>Draft</strong>. Before participants can join, you must complete setup and publish it. This guide walks you through every stage of the tournament lifecycle.",
      tab: null,
    },
    {
      id: "publish",
      icon: "send",
      title: "Step 1 — Publish & open registration",
      body: "A draft tournament is invisible to the public. Once you finish setup, publish it so players can discover and register. You can publish from the <strong>Overview tab → Launch Checklist → Publish</strong>, or from the Settings tab.",
      tab: "overview",
      highlight: "#overview-lifecycle",
    },
    {
      id: "branding",
      icon: "image",
      title: "Step 2 — Branding & public page",
      body: "Upload your tournament logo and banner, and review your description, rules, region, and community links. These appear on the public tournament page. Go to <strong>Settings → Branding</strong>.",
      tab: "settings",
    },
    {
      id: "registrations",
      icon: "users",
      title: "Step 3 — Review registrations",
      body: "Once published, participants register. Review each registration in the <strong>Participants tab</strong>. You can approve, reject, or waitlist entries. Confirmed participants are locked into the bracket when registration closes.",
      tab: "participants",
    },
    {
      id: "rules",
      icon: "book-open",
      title: "Step 4 — Rules, format & eligibility",
      body: "Double-check your game, format, roster size, platform, proof type, and rulebook in <strong>Settings → Rules & Info</strong>. Wrong format or roster settings break the bracket and match flow — verify before publishing.",
      tab: "rules",
    },
    {
      id: "bracket",
      icon: "git-branch",
      title: "Step 5 — Generate the bracket",
      body: "After registration closes and participants are confirmed, generate the bracket from the <strong>Brackets tab</strong>. The bracket uses confirmed participants and your chosen format. Review it before publishing to participants.",
      tab: "brackets",
    },
    {
      id: "matches",
      icon: "swords",
      title: "Step 6 — Match lobby & operations",
      body: "Each match has its own lobby where participants check in, set up credentials, and play. Monitor check-ins, no-shows, lobby status, and result submissions from the <strong>Matches tab</strong>. Intervene if a team is late or disputes arise.",
      tab: "matches",
    },
    {
      id: "evidence",
      icon: "shield-check",
      title: "Step 7 — Result verification & evidence",
      body: "After each match, the winner submits a screenshot or proof. Review evidence in the <strong>Matches</strong> or <strong>Disputes</strong> tab. Confirm or reject the result. A public match report is generated once the result is verified.",
      tab: "disputes",
    },
    {
      id: "announcements",
      icon: "megaphone",
      title: "Step 8 — Announcements & communication",
      body: "Post schedule updates, rule clarifications, and live commentary from the <strong>Announcements tab</strong>. Participants see these in their Hub. Pin your Discord/Telegram/WhatsApp link so participants can reach you instantly.",
      tab: "announcements",
    },
    {
      id: "liveops",
      icon: "activity",
      title: "Step 9 — Running the event (live ops)",
      body: "On tournament day: monitor check-ins, start matches on time, track result submissions, and resolve disputes within 15 minutes. Use the <strong>Overview health bar</strong> to spot issues. Keep the community updated on any delays.",
      tab: "overview",
    },
    {
      id: "completion",
      icon: "trophy",
      title: "Step 10 — Completion & wrap-up",
      body: "When all matches are resolved and the final winner is confirmed, the tournament transitions to <strong>Completed</strong>. Winners are announced on the public page, match reports are finalized, and prizes can be distributed from the <strong>Prizes & Awards tab</strong>.",
      tab: "prizes",
    },
  ];

  var currentStep = 0;

  function byId(id) { return document.getElementById(id); }

  function renderPanel() {
    var overlay = byId("dc-ob-overlay");
    var panel = byId("dc-ob-panel");
    if (!overlay || !panel) return;

    var step = STEPS[currentStep];
    var total = STEPS.length;
    var pct = Math.round(((currentStep + 1) / total) * 100);

    byId("dc-ob-step-label").textContent = (currentStep + 1) + " / " + total;
    byId("dc-ob-progress").style.width = pct + "%";
    byId("dc-ob-title").innerHTML = step.title;
    byId("dc-ob-body").innerHTML = step.body;

    // Dots
    var dotsEl = byId("dc-ob-dots");
    if (dotsEl) {
      dotsEl.innerHTML = STEPS.map(function (s, i) {
        var active = i === currentStep ? "background:var(--dc-accent,#06b6d4);" : "background:rgba(255,255,255,0.18);";
        return '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;' + active + '"></span>';
      }).join("");
    }

    // Back button
    var backBtn = byId("dc-ob-back");
    if (backBtn) backBtn.disabled = currentStep === 0;

    // Next vs Finish
    var nextBtn = byId("dc-ob-next");
    if (nextBtn) {
      nextBtn.textContent = currentStep === total - 1 ? "Finish guide" : "Next →";
    }

    // Tab jump button
    var jumpBtn = byId("dc-ob-jump");
    if (jumpBtn) {
      if (step.tab) {
        jumpBtn.style.display = "";
        jumpBtn.textContent = "Open " + step.tab + " tab";
        jumpBtn.setAttribute("data-jump-tab", step.tab);
      } else {
        jumpBtn.style.display = "none";
      }
    }
  }

  function jumpToTab(tabId) {
    var btns = document.querySelectorAll(".toc-nav-btn[data-tab]");
    for (var i = 0; i < btns.length; i++) {
      if (btns[i].getAttribute("data-tab") === tabId) {
        btns[i].click();
        return;
      }
    }
    // Fallback: search by text
    var allBtns = document.querySelectorAll(".toc-nav-btn");
    var needle = tabId.replace(/-/g, " ").toLowerCase();
    for (var j = 0; j < allBtns.length; j++) {
      if (allBtns[j].textContent.trim().toLowerCase().indexOf(needle) !== -1) {
        allBtns[j].click();
        return;
      }
    }
  }

  function closePanel() {
    var overlay = byId("dc-ob-overlay");
    if (overlay) {
      overlay.style.opacity = "0";
      setTimeout(function () { overlay.style.display = "none"; }, 280);
    }
    localStorage.setItem(STORAGE_KEY, "1");
  }

  function buildOverlay() {
    var el = document.createElement("div");
    el.id = "dc-ob-overlay";
    el.setAttribute("role", "dialog");
    el.setAttribute("aria-modal", "true");
    el.setAttribute("aria-label", "Tournament Launch Guide");
    el.style.cssText = [
      "position:fixed;inset:0;z-index:200;display:flex;align-items:center;",
      "justify-content:center;padding:16px;",
      "background:rgba(0,0,0,0.72);backdrop-filter:blur(8px);",
      "transition:opacity 0.28s ease;",
    ].join("");

    el.innerHTML = [
      '<div id="dc-ob-panel" style="',
        "position:relative;width:100%;max-width:580px;max-height:88vh;overflow-y:auto;",
        "background:#0d1117;border:1px solid rgba(255,255,255,0.10);",
        "border-radius:24px;box-shadow:0 32px 80px rgba(0,0,0,0.7);",
        "display:flex;flex-direction:column;",
      '">',

        // Header
        '<div style="padding:20px 24px 0;flex-shrink:0;">',
          '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;">',
            '<div style="display:flex;align-items:center;gap:10px;">',
              '<div style="width:32px;height:32px;border-radius:10px;background:rgba(6,182,212,0.15);display:flex;align-items:center;justify-content:center;">',
                '<i data-lucide="map" style="width:16px;height:16px;color:#06b6d4;"></i>',
              '</div>',
              '<div>',
                '<p style="font-size:10px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:rgba(255,255,255,0.35);margin:0;">Tournament Launch Guide</p>',
                '<p style="font-size:11px;color:rgba(255,255,255,0.5);margin:0;" id="dc-ob-step-label">1 / 11</p>',
              '</div>',
            '</div>',
            '<button id="dc-ob-close" style="width:30px;height:30px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.05);color:rgba(255,255,255,0.5);cursor:pointer;display:flex;align-items:center;justify-content:center;" title="Close guide">',
              '<i data-lucide="x" style="width:14px;height:14px;"></i>',
            '</button>',
          '</div>',
          // Progress bar
          '<div style="height:3px;border-radius:99px;background:rgba(255,255,255,0.08);overflow:hidden;margin-bottom:4px;">',
            '<div id="dc-ob-progress" style="height:100%;border-radius:99px;background:#06b6d4;transition:width 0.35s ease;width:9%;"></div>',
          '</div>',
          '<div id="dc-ob-dots" style="display:flex;gap:5px;justify-content:center;padding:6px 0 12px;"></div>',
        '</div>',

        // Body
        '<div style="padding:0 24px 20px;flex:1;overflow-y:auto;">',
          '<h2 id="dc-ob-title" style="font-family:Outfit,sans-serif;font-size:20px;font-weight:800;color:#fff;margin:0 0 12px;line-height:1.3;"></h2>',
          '<p id="dc-ob-body" style="font-size:13px;line-height:1.7;color:rgba(255,255,255,0.65);margin:0;"></p>',
        '</div>',

        // Footer
        '<div style="padding:16px 24px 20px;border-top:1px solid rgba(255,255,255,0.08);display:flex;align-items:center;gap:10px;flex-shrink:0;">',
          '<button id="dc-ob-jump" style="flex:1;padding:8px 12px;border-radius:10px;border:1px solid rgba(6,182,212,0.3);background:rgba(6,182,212,0.08);color:#06b6d4;font-size:11px;font-weight:700;cursor:pointer;letter-spacing:0.04em;display:none;"></button>',
          '<div style="display:flex;gap:8px;margin-left:auto;">',
            '<button id="dc-ob-back" style="padding:8px 16px;border-radius:10px;border:1px solid rgba(255,255,255,0.12);background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.6);font-size:12px;font-weight:600;cursor:pointer;">Back</button>',
            '<button id="dc-ob-next" style="padding:8px 20px;border-radius:10px;background:#06b6d4;color:#020a0f;font-size:12px;font-weight:800;cursor:pointer;border:none;">Next →</button>',
          '</div>',
        '</div>',

      '</div>',
    ].join("");

    return el;
  }

  function init() {
    var overlay = buildOverlay();
    document.body.appendChild(overlay);
    renderPanel();

    // Init Lucide icons for new elements
    if (window.lucide && typeof window.lucide.createIcons === "function") {
      window.lucide.createIcons({ nodes: [overlay] });
    }

    // Bind events (no inline handlers)
    var closeBtn = byId("dc-ob-close");
    if (closeBtn) closeBtn.addEventListener("click", closePanel);

    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) closePanel();
    });

    var backBtn = byId("dc-ob-back");
    if (backBtn) {
      backBtn.addEventListener("click", function () {
        if (currentStep > 0) { currentStep--; renderPanel(); }
      });
    }

    var nextBtn = byId("dc-ob-next");
    if (nextBtn) {
      nextBtn.addEventListener("click", function () {
        if (currentStep < STEPS.length - 1) {
          currentStep++;
          renderPanel();
        } else {
          closePanel();
        }
      });
    }

    var jumpBtn = byId("dc-ob-jump");
    if (jumpBtn) {
      jumpBtn.addEventListener("click", function () {
        var tab = jumpBtn.getAttribute("data-jump-tab");
        if (tab) jumpToTab(tab);
      });
    }

    document.addEventListener("keydown", function (e) {
      if (!byId("dc-ob-overlay") || byId("dc-ob-overlay").style.display === "none") return;
      if (e.key === "ArrowRight" || e.key === "Enter") {
        var nb = byId("dc-ob-next");
        if (nb) nb.click();
      }
      if (e.key === "ArrowLeft") {
        var bb = byId("dc-ob-back");
        if (bb && !bb.disabled) bb.click();
      }
      if (e.key === "Escape") closePanel();
    });
  }

  // Show guide button (always present in TOC for "Show guide again")
  function wireReopenButton() {
    var reopenBtns = document.querySelectorAll("[data-open-onboarding]");
    reopenBtns.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var overlay = byId("dc-ob-overlay");
        if (overlay) {
          currentStep = 0;
          overlay.style.display = "flex";
          overlay.style.opacity = "1";
          renderPanel();
        } else {
          init();
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { init(); wireReopenButton(); });
  } else {
    init();
    wireReopenButton();
  }
})();
