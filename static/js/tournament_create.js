(function () {
  "use strict";

  var createApp = document.getElementById("createApp");
  if (!createApp) {
    return;
  }

  function parseJsonById(id, fallback) {
    var node = document.getElementById(id);
    if (!node) {
      return fallback;
    }
    try {
      return JSON.parse(node.textContent || "");
    } catch (error) {
      return fallback;
    }
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function toArray(nodeList) {
    return Array.prototype.slice.call(nodeList || []);
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function slugify(value) {
    return String(value || "")
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 80);
  }

  function toMoney(value) {
    var number = Number(value || 0);
    if (Number.isNaN(number)) {
      return "0.00";
    }
    return number.toFixed(2);
  }

  function toInt(value, fallback) {
    var parsed = parseInt(String(value || ""), 10);
    if (Number.isNaN(parsed)) {
      return fallback;
    }
    return parsed;
  }

  function hexToRgbString(hexColor) {
    var value = String(hexColor || "").trim();
    var shortHexMatch = /^#([a-f\d])([a-f\d])([a-f\d])$/i.exec(value);
    var normalized = shortHexMatch
      ? "#" +
        shortHexMatch[1] + shortHexMatch[1] +
        shortHexMatch[2] + shortHexMatch[2] +
        shortHexMatch[3] + shortHexMatch[3]
      : value;
    var fullHexMatch = /^#([a-f\d]{6})$/i.exec(normalized);
    if (!fullHexMatch) {
      return "6,182,212";
    }
    var intValue = parseInt(fullHexMatch[1], 16);
    var r = (intValue >> 16) & 255;
    var g = (intValue >> 8) & 255;
    var b = intValue & 255;
    return r + "," + g + "," + b;
  }

  function relativeLuminance(r, g, b) {
    function ch(v) { v = v / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b);
  }

  function safeAccentColor(hexColor) {
    var value = String(hexColor || "").trim();
    var shortMatch = /^#([a-f\d])([a-f\d])([a-f\d])$/i.exec(value);
    var norm = shortMatch ? "#" + shortMatch[1]+shortMatch[1]+shortMatch[2]+shortMatch[2]+shortMatch[3]+shortMatch[3] : value;
    var fullMatch = /^#([a-f\d]{6})$/i.exec(norm);
    if (!fullMatch) return "#06b6d4";
    var iv = parseInt(fullMatch[1], 16);
    var r = (iv >> 16) & 255, g = (iv >> 8) & 255, b = iv & 255;
    var lum = relativeLuminance(r, g, b);
    if (lum >= 0.12) return norm;
    var factor = 1.8;
    r = Math.min(255, Math.round(r * factor + 60));
    g = Math.min(255, Math.round(g * factor + 60));
    b = Math.min(255, Math.round(b * factor + 60));
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
  }

  function getCookie(name) {
    var parts = document.cookie.split(";");
    for (var i = 0; i < parts.length; i += 1) {
      var part = parts[i].trim();
      if (part.indexOf(name + "=") === 0) {
        return decodeURIComponent(part.slice(name.length + 1));
      }
    }
    return "";
  }

  function formatLabel(value) {
    return String(value || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, function (letter) {
        return letter.toUpperCase();
      });
  }

  function safeDateLabel(value) {
    if (!value) {
      return "-";
    }
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "-";
    }
    return date.toLocaleString();
  }

  function platformLabel(value) {
    var found = platformChoices.find(function (item) {
      return item.value === value;
    });
    if (found) {
      return found.label;
    }
    return formatLabel(value);
  }

  function gameCategory(game) {
    return game && (game.category_label || game.category || "General");
  }

  function gameDisplayName(game) {
    return (game && (game.display_name || game.name)) || "Unknown";
  }

  function gameFallbackLetters(game) {
    if (!game) {
      return "GM";
    }
    if (game.short_code) {
      return String(game.short_code).slice(0, 2).toUpperCase();
    }
    var name = gameDisplayName(game);
    var words = name.trim().split(/\s+/).filter(Boolean);
    if (words.length === 1) {
      return words[0].slice(0, 2).toUpperCase();
    }
    return ((words[0][0] || "") + (words[1][0] || "")).toUpperCase() || "GM";
  }

  function getRecommendedSizes(game) {
    var list = game && Array.isArray(game.recommended_sizes) ? game.recommended_sizes : [];
    var parsed = list
      .map(function (value) {
        return toInt(value, 0);
      })
      .filter(function (value) {
        return value > 1 && value <= 256;
      });

    if (!parsed.length) {
      return [8, 16, 32, 64];
    }

    var unique = [];
    parsed.forEach(function (value) {
      if (unique.indexOf(value) === -1) {
        unique.push(value);
      }
    });

    return unique;
  }

  function defaultRosterMin(game) {
    if (!game) {
      return 1;
    }
    if (toInt(game.min_roster_size, 0) > 0) {
      return toInt(game.min_roster_size, 1);
    }
    if (toInt(game.team_size, 0) > 0) {
      return toInt(game.team_size, 1);
    }
    var display = String(game.team_size_display || "");
    var match = display.match(/(\d+)/);
    if (match) {
      return toInt(match[1], 1);
    }
    return state.participationUi === "solo" ? 1 : 5;
  }

  function defaultRosterMax(game) {
    var min = defaultRosterMin(game);
    if (!game) {
      return min;
    }
    if (toInt(game.max_roster_size, 0) > 0) {
      return toInt(game.max_roster_size, min);
    }
    if (toInt(game.team_size, 0) > 0) {
      return toInt(game.team_size, min) + 2;
    }
    return state.participationUi === "solo" ? 1 : Math.max(min + 2, min);
  }

  function defaultRosterSubs(game) {
    if (!game) {
      return state.participationUi === "solo" ? 0 : 2;
    }
    if (toInt(game.max_subs, -1) >= 0) {
      return toInt(game.max_subs, 0);
    }
    if (state.participationUi === "solo") {
      return 0;
    }
    return 2;
  }

  function getDefaultServer(game) {
    if (!game) {
      return "Global";
    }
    return game.recommended_server || game.server_region || game.default_region || "Global";
  }

  function getDefaultParticipation(game) {
    var value = String((game && game.recommended_participation) || "team").toLowerCase();
    if (value === "solo") {
      return "solo";
    }
    if (value === "squad") {
      return "squad";
    }
    return "team";
  }

  function setAccent(accentHex) {
    var accent = safeAccentColor(accentHex || "#06b6d4");
    var rgb = hexToRgbString(accent);
    createApp.style.setProperty("--accent", accent);
    createApp.style.setProperty("--accent-rgb", rgb);
  }

  var games = parseJsonById("gamesData", []);
  var formatChoices = parseJsonById("formatChoicesData", []);
  var platformChoices = parseJsonById("platformChoicesData", []);

  var isStaff = createApp.dataset.isStaff === "true";
  var canAfford = createApp.dataset.canAfford === "true";
  var apiCreateUrl = createApp.dataset.apiCreateUrl || "/api/tournaments/";

  var steps = [
    { id: 1, title: "Game", sub: "Select game" },
    { id: 2, title: "Details", sub: "Name & info" },
    { id: 3, title: "Format", sub: "Bracket & roster" },
    { id: 4, title: "Schedule & Payment", sub: "Dates & fees" },
    { id: 5, title: "Rules", sub: "Eligibility & rulebook" },
    { id: 6, title: "Review", sub: "Summary" },
    { id: 7, title: "Launch", sub: "Hosting fee & deploy" }
  ];

  var currentStep = 1;
  var selectedGame = games.length ? games[0] : null;
  var activeCategory = "All";

  var state = {
    name: "",
    slug: "",
    tournamentBrief: "",
    description: "",
    region: "Bangladesh",
    visibility: "public",
    timezone: "Asia/Dhaka",
    communityLinks: [],
    supportContact: "",

    format: "single_elimination",
    maxParticipants: 16,
    minParticipants: 2,
    participationUi: "team",
    platform: platformChoices.length ? platformChoices[0].value : "pc",
    rosterMin: 5,
    rosterMax: 7,
    rosterSubs: 2,
    resultProof: "screenshot",
    serverRegion: "Global",

    registrationStart: "",
    registrationEnd: "",
    checkInOpen: "",
    tournamentStart: "",
    tournamentEnd: "",

    venueMode: "online",
    isOfficial: false,

    hasEntryFee: false,
    entryFeeAmount: 0,
    entryFeeCurrency: "BDT",
    paymentMethods: ["bkash"],
    receiverNumber: "",
    paymentInstruction: "",
    verificationNote: "",

    prizePool: 0,
    prizeCurrency: "BDT",
    prizeFirst: 50,
    prizeSecond: 30,
    prizeThird: 20,
    mvpBonus: "",

    minAge: "none",
    countryRestriction: "",
    rankRestriction: "",
    rulesText: "",

    enableDynamicSeeding: false,
    enableLiveUpdates: true,
    enableCertificates: true,
    enableChallenges: false,
    enableFanVoting: false,
    checkInMinutes: 15
  };

  var paymentMethodWhitelist = ["bkash", "nagad", "rocket", "bank_transfer", "deltacoin"];

  function elValue(id, fallback) {
    var node = byId(id);
    if (!node) {
      return fallback;
    }
    return node.value;
  }

  function setText(id, value) {
    var node = byId(id);
    if (node) {
      node.textContent = String(value || "");
    }
  }

  function setHtml(id, html) {
    var node = byId(id);
    if (node) {
      node.innerHTML = html;
    }
  }

  function showToast(message) {
    var toast = byId("toast");
    if (!toast) {
      return;
    }
    toast.textContent = message;
    toast.classList.remove("hidden");
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(function () {
      toast.classList.add("hidden");
    }, 1800);
  }

  function openGuideModal() {
    var modal = byId("guideModal");
    if (!modal) {
      return;
    }
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }

  function closeGuideModal() {
    var modal = byId("guideModal");
    if (!modal) {
      return;
    }
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }

  function setLoading(isLoading) {
    var overlay = byId("loadingOverlay");
    if (!overlay) {
      return;
    }
    overlay.classList.toggle("hidden", !isLoading);
    overlay.classList.toggle("flex", isLoading);
  }

  function setDeployOverlay(visible, title, text) {
    var overlay = byId("deployOverlay");
    if (!overlay) {
      return;
    }
    overlay.classList.toggle("hidden", !visible);
    overlay.classList.toggle("flex", visible);
    if (title) {
      setText("deployTitle", title);
    }
    if (text) {
      setText("deployText", text);
    }
  }

  function selectedVenueMode() {
    var radios = document.querySelectorAll('input[name="venueMode"]');
    for (var i = 0; i < radios.length; i += 1) {
      if (radios[i].checked) {
        return radios[i].value;
      }
    }
    return "online";
  }

  function updateExpandPanel(panelId, open) {
    var panel = byId(panelId);
    if (!panel) {
      return;
    }
    panel.classList.toggle("open", !!open);
  }

  function collectCommunityLinks() {
    var links = [];
    var rows = document.querySelectorAll(".community-link-row");
    for (var i = 0; i < rows.length; i++) {
      var platform = rows[i].querySelector(".community-link-platform");
      var url = rows[i].querySelector(".community-link-url");
      if (platform && url && url.value.trim()) {
        links.push({ platform: platform.value, url: url.value.trim() });
      }
    }
    return links;
  }

  function syncIdentityState() {
    state.name = String(elValue("tournamentName", "")).trim();
    state.slug = slugify(state.name) || "untitled";
    state.tournamentBrief = String(elValue("tournamentBrief", "")).trim();
    state.description = String(elValue("description", "")).trim();
    state.region = String(elValue("regionSelect", "Bangladesh"));
    state.visibility = String(elValue("visibilitySelect", "public"));
    state.timezone = String(elValue("timezoneSelect", "Asia/Dhaka"));
    state.communityLinks = collectCommunityLinks();
    state.supportContact = String(elValue("supportContact", "")).trim();
  }

  function syncArchitectureState() {
    state.maxParticipants = Math.max(2, Math.min(256, toInt(elValue("capacitySlider", state.maxParticipants), state.maxParticipants)));
    state.rosterMin = Math.max(1, toInt(elValue("rosterMin", state.rosterMin), state.rosterMin));
    state.rosterMax = Math.max(state.rosterMin, toInt(elValue("rosterMax", state.rosterMax), state.rosterMax));
    state.rosterSubs = Math.max(0, toInt(elValue("rosterSubs", state.rosterSubs), state.rosterSubs));
    state.resultProof = String(elValue("resultProof", "screenshot"));
    state.serverRegion = String(elValue("serverRegion", "Global")).trim() || "Global";

    var dynamicSeeding = byId("enableDynamicSeeding");
    if (dynamicSeeding) {
      state.enableDynamicSeeding = !!dynamicSeeding.checked;
    }
    var liveUpdates = byId("enableLiveUpdates");
    if (liveUpdates) {
      state.enableLiveUpdates = !!liveUpdates.checked;
    }
    var certificates = byId("enableCertificates");
    if (certificates) {
      state.enableCertificates = !!certificates.checked;
    }
    var challenges = byId("enableChallenges");
    if (challenges) {
      state.enableChallenges = !!challenges.checked;
    }
    var fanVoting = byId("enableFanVoting");
    if (fanVoting) {
      state.enableFanVoting = !!fanVoting.checked;
    }
    var checkInMin = byId("checkInMinutes");
    if (checkInMin) {
      state.checkInMinutes = Math.max(5, Math.min(120, toInt(checkInMin.value, 15)));
    }
  }

  function syncEconomyState() {
    state.registrationStart = String(elValue("regStart", ""));
    state.registrationEnd = String(elValue("regEnd", ""));
    state.checkInOpen = String(elValue("checkInOpen", ""));
    state.tournamentStart = String(elValue("tourStart", ""));
    state.tournamentEnd = String(elValue("tourEnd", ""));

    state.venueMode = selectedVenueMode();
    if (!isStaff) {
      state.venueMode = "online";
    }

    var officialToggle = byId("officialToggle");
    state.isOfficial = isStaff && officialToggle ? !!officialToggle.checked : false;

    var feeToggle = byId("entryFeeToggle");
    state.hasEntryFee = !!(feeToggle && feeToggle.checked);
    state.entryFeeAmount = Math.max(0, Number(elValue("entryFeeAmount", 0)) || 0);
    state.entryFeeCurrency = String(elValue("entryFeeCurrency", "BDT"));

    state.receiverNumber = String(elValue("receiverNumber", "")).trim();
    state.paymentInstruction = String(elValue("paymentInstruction", "")).trim();
    state.verificationNote = String(elValue("verificationNote", "")).trim();

    state.prizePool = Math.max(0, Number(elValue("prizePool", 0)) || 0);
    state.prizeCurrency = String(elValue("prizeCurrency", "BDT"));
    state.prizeFirst = Math.max(0, Math.min(100, toInt(elValue("prizeFirst", 50), 50)));
    state.prizeSecond = Math.max(0, Math.min(100, toInt(elValue("prizeSecond", 30), 30)));
    state.prizeThird = Math.max(0, Math.min(100, toInt(elValue("prizeThird", 20), 20)));
    state.mvpBonus = String(elValue("mvpBonus", "")).trim();

    state.paymentMethods = collectPaymentMethods();
  }

  function syncRulesState() {
    state.minAge = String(elValue("minAge", "none"));
    state.countryRestriction = String(elValue("countryRestriction", "")).trim();
    state.rankRestriction = String(elValue("rankRestriction", "")).trim();
    state.rulesText = String(elValue("rulesText", "")).trim();
  }

  function collectPaymentMethods() {
    var checkboxes = document.querySelectorAll(".payment-method-checkbox");
    var selected = [];
    for (var i = 0; i < checkboxes.length; i += 1) {
      var box = checkboxes[i];
      if (box.checked) {
        selected.push(String(box.value));
      }
    }

    selected = selected.filter(function (method) {
      return paymentMethodWhitelist.indexOf(method) >= 0;
    });

    if (!state.hasEntryFee) {
      return [];
    }

    if (state.entryFeeCurrency === "DC") {
      return ["deltacoin"];
    }

    if (!selected.length) {
      if (state.entryFeeCurrency === "USD") {
        return ["bank_transfer"];
      }
      return ["bkash"];
    }

    return selected;
  }

  function normalizeParticipationType() {
    if (state.participationUi === "solo") {
      return "solo";
    }
    return "team";
  }

  function renderSteppers() {
    var desktop = byId("desktopStepper");
    var mobile = byId("mobileStepper");

    if (desktop) {
      desktop.innerHTML = steps
        .map(function (step) {
          return (
            '<button type="button" data-step-jump="' + step.id + '" class="group flex w-full items-center gap-4 rounded-2xl p-3 text-left transition hover:bg-white/5">' +
              '<span data-step-dot="' + step.id + '" class="step-dot relative z-10 flex h-9 w-9 items-center justify-center rounded-2xl border border-white/15 bg-black/45 text-xs font-extrabold text-white/50">' +
                step.id +
              "</span>" +
              '<span class="min-w-0">' +
                '<span data-step-title="' + step.id + '" class="block font-space text-sm font-bold text-white/55">' + escapeHtml(step.title) + "</span>" +
                '<span class="mt-1 block text-[10px] font-bold uppercase tracking-[0.18em] text-white/30">' + escapeHtml(step.sub) + "</span>" +
              "</span>" +
            "</button>"
          );
        })
        .join("");
    }

    if (mobile) {
      mobile.innerHTML = steps
        .map(function (step) {
          return (
            '<button type="button" data-step-jump="' + step.id + '" class="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-[11px] font-bold text-white/55">' +
              '<span data-mobile-step-dot="' + step.id + '" class="mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full bg-black/45 text-[10px]">' +
                step.id +
              "</span>" +
              escapeHtml(step.title) +
            "</button>"
          );
        })
        .join("");
    }

    toArray(document.querySelectorAll("[data-step-jump]")).forEach(function (button) {
      button.addEventListener("click", function () {
        var target = toInt(button.getAttribute("data-step-jump"), 1);
        goToStep(target);
      });
    });
  }

  function updateStepperUi() {
    var ratio = ((currentStep - 1) / (steps.length - 1)) * 100;
    setText("desktopStepCount", String(currentStep).padStart(2, "0") + " / " + String(steps.length).padStart(2, "0"));

    var timelineBar = byId("timelineBar");
    if (timelineBar) {
      timelineBar.style.height = "calc(" + ratio + "% - 6px)";
    }

    var bottomProgress = byId("bottomProgress");
    if (bottomProgress) {
      bottomProgress.style.width = ((currentStep / steps.length) * 100) + "%";
    }

    var bottomStepLabel = byId("bottomStepLabel");
    if (bottomStepLabel) {
      bottomStepLabel.textContent = currentStep + " / " + steps.length;
    }

    steps.forEach(function (step) {
      var done = step.id < currentStep;
      var active = step.id === currentStep;

      var dot = document.querySelector('[data-step-dot="' + step.id + '"]');
      if (dot) {
        dot.classList.remove("active", "done");
        if (done) {
          dot.classList.add("done");
          dot.textContent = "OK";
        } else if (active) {
          dot.classList.add("active");
          dot.textContent = String(step.id);
        } else {
          dot.textContent = String(step.id);
        }
      }

      var mobileDot = document.querySelector('[data-mobile-step-dot="' + step.id + '"]');
      if (mobileDot) {
        mobileDot.classList.remove("active", "done");
        if (done) {
          mobileDot.classList.add("done");
          mobileDot.textContent = "OK";
        } else if (active) {
          mobileDot.classList.add("active");
          mobileDot.textContent = String(step.id);
        } else {
          mobileDot.textContent = String(step.id);
        }
      }
    });

    toArray(document.querySelectorAll("[data-panel]")).forEach(function (panel) {
      var id = panel.id || "";
      var stepNumber = toInt(id.replace("step-", ""), 1);
      panel.classList.toggle("hidden", stepNumber !== currentStep);
    });

    var prevBtn = byId("prevBtn");
    if (prevBtn) {
      prevBtn.classList.toggle("hidden", currentStep === 1);
      prevBtn.classList.toggle("inline-flex", currentStep !== 1);
    }

    var nextBtn = byId("nextBtn");
    if (nextBtn) {
      nextBtn.classList.toggle("hidden", currentStep === steps.length);
      nextBtn.textContent = currentStep === steps.length - 1 ? "Proceed to Launch →" : "Continue";
    }
  }

  function validateStep(stepNumber) {
    syncIdentityState();
    syncArchitectureState();
    syncEconomyState();
    syncRulesState();

    if (stepNumber === 1) {
      if (!selectedGame) {
        alert("Please select a game before continuing.");
        return false;
      }
      return true;
    }

    if (stepNumber === 2) {
      if (!state.name) {
        alert("Please enter a tournament name.");
        return false;
      }
      if (!state.description) {
        alert("Please provide a full description.");
        return false;
      }
      return true;
    }

    if (stepNumber === 3) {
      if (!state.format) {
        alert("Please choose a tournament format.");
        return false;
      }
      if (state.maxParticipants < 2) {
        alert("Max participants must be at least 2.");
        return false;
      }
      if (state.rosterMax < state.rosterMin) {
        alert("Roster max cannot be lower than roster min.");
        return false;
      }
      return true;
    }

    if (stepNumber === 4) {
      if (!state.registrationStart || !state.registrationEnd || !state.tournamentStart) {
        alert("Please fill registration and tournament start timeline fields.");
        return false;
      }

      var regStart = new Date(state.registrationStart);
      var regEnd = new Date(state.registrationEnd);
      var tourStart = new Date(state.tournamentStart);

      if (!(regStart < regEnd && regEnd < tourStart)) {
        alert("Schedule must satisfy: registration start < registration end < tournament start.");
        return false;
      }

      if (state.hasEntryFee && state.entryFeeAmount <= 0) {
        alert("Entry fee must be greater than 0 for paid tournaments.");
        return false;
      }

      return true;
    }

    return true;
  }

  function goToStep(targetStep) {
    var target = Math.max(1, Math.min(steps.length, toInt(targetStep, 1)));

    if (target > currentStep) {
      for (var step = currentStep; step < target; step += 1) {
        if (!validateStep(step)) {
          return;
        }
      }
    }

    currentStep = target;
    updateStepperUi();
    updateReviewSummary();

    var mainScroll = byId("mainScroll");
    if (mainScroll) {
      mainScroll.scrollTo({ top: 0, behavior: "smooth" });
    }
  }

  function nextStep() {
    if (currentStep >= steps.length) {
      return;
    }
    if (!validateStep(currentStep)) {
      return;
    }
    currentStep += 1;
    updateStepperUi();
    updateReviewSummary();
  }

  function prevStep() {
    if (currentStep <= 1) {
      return;
    }
    currentStep -= 1;
    updateStepperUi();
    updateReviewSummary();
  }

  function renderCategoryFilters() {
    var categories = ["All"];
    games.forEach(function (game) {
      var category = gameCategory(game);
      if (categories.indexOf(category) === -1) {
        categories.push(category);
      }
    });

    setHtml(
      "categoryFilters",
      categories
        .map(function (category) {
          var activeClass = category === activeCategory
            ? "border-[var(--accent)] bg-[rgba(var(--accent-rgb),0.14)] text-white"
            : "border-white/10 bg-white/5 text-white/60";
          return (
            '<button type="button" class="rounded-full border px-4 py-2 text-xs font-bold transition ' + activeClass + '" data-category-filter="' + escapeHtml(category) + '">' +
              escapeHtml(category) +
            "</button>"
          );
        })
        .join("")
    );

    toArray(document.querySelectorAll("[data-category-filter]")).forEach(function (button) {
      button.addEventListener("click", function () {
        activeCategory = button.getAttribute("data-category-filter") || "All";
        renderCategoryFilters();
        filterGameCards();
      });
    });
  }

  function renderGameCards() {
    var html = games
      .map(function (game) {
        var gameId = String(game.id);
        var selected = selectedGame && String(selectedGame.id) === gameId;
        var rawColor = game.primary_color || "#06b6d4";
        var safeColor = safeAccentColor(rawColor);
        var rgb = hexToRgbString(safeColor);
        var name = gameDisplayName(game);
        var category = gameCategory(game);
        var hasCardImg = !!game.card_image_url;
        var hasIcon = !!game.icon_url;

        var bgStyle = hasCardImg
          ? "background-image:url(" + escapeHtml(game.card_image_url) + ");background-size:cover;background-position:center;"
          : "background:linear-gradient(145deg,rgba(" + rgb + ",0.18),rgba(0,0,0,0.55));";

        var selectedStyle = selected
          ? "border-color:" + safeColor + ";box-shadow:0 0 0 2px " + safeColor + ",0 12px 36px rgba(" + rgb + ",0.4);"
          : "";

        var iconEl = hasIcon
          ? '<img src="' + escapeHtml(game.icon_url) + '" alt="" class="h-8 w-8 rounded-lg object-cover shadow-lg">'
          : '<span class="font-space text-[11px] font-extrabold text-white/90">' + escapeHtml(gameFallbackLetters(game)) + '</span>';

        return (
          '<button type="button" class="game-card-portrait focus:outline-none" style="' + bgStyle + selectedStyle + '" data-game-id="' + escapeHtml(gameId) + '" data-game-name="' + escapeHtml(name.toLowerCase()) + '" data-game-category="' + escapeHtml(category) + '">' +
            '<span class="card-overlay pointer-events-none"></span>' +
            '<span class="card-info z-10">' +
              '<span class="flex h-10 w-10 items-center justify-center rounded-xl border border-white/20 bg-black/60 backdrop-blur-sm">' + iconEl + '</span>' +
              '<strong class="font-space text-xs font-extrabold leading-tight text-white drop-shadow-lg">' + escapeHtml(name) + '</strong>' +
            '</span>' +
            (selected ? '<span class="card-selected-badge text-[var(--accent)]">✓</span>' : '') +
          '</button>'
        );
      })
      .join("");

    setHtml("gameGrid", html);

    toArray(document.querySelectorAll("[data-game-id]")).forEach(function (button) {
      button.addEventListener("click", function () {
        var gameId = button.getAttribute("data-game-id");
        var found = games.find(function (game) {
          return String(game.id) === String(gameId);
        });
        if (!found) {
          return;
        }
        selectedGame = found;
        applyGameDefaults(found);
        renderGameCards();
        filterGameCards();
      });
    });

    filterGameCards();
  }

  function filterGameCards() {
    var query = String(elValue("gameSearch", "")).trim().toLowerCase();
    var cards = toArray(document.querySelectorAll("[data-game-id]"));
    var visible = 0;

    cards.forEach(function (card) {
      var name = String(card.getAttribute("data-game-name") || "").toLowerCase();
      var category = String(card.getAttribute("data-game-category") || "");

      var matchesName = !query || name.indexOf(query) >= 0;
      var matchesCategory = activeCategory === "All" || activeCategory === category;
      var show = matchesName && matchesCategory;
      card.classList.toggle("hidden", !show);
      if (show) {
        visible += 1;
      }
    });

    setText("gameCount", visible + " game" + (visible === 1 ? "" : "s"));
  }

  function ensureSupportedFormat(formatValue) {
    var supportedMap = selectedGame && selectedGame.supported_formats ? selectedGame.supported_formats : {};
    if (supportedMap[formatValue] !== false) {
      return formatValue;
    }

    var recommended = selectedGame && selectedGame.recommended_format;
    if (recommended && supportedMap[recommended] !== false) {
      return recommended;
    }

    var firstAllowed = formatChoices.find(function (choice) {
      return supportedMap[choice.value] !== false;
    });

    return firstAllowed ? firstAllowed.value : "single_elimination";
  }

  function renderFormatCards() {
    var supportedMap = selectedGame && selectedGame.supported_formats ? selectedGame.supported_formats : {};
    var recommended = selectedGame && selectedGame.recommended_format;

    setHtml(
      "formatGrid",
      formatChoices
        .map(function (choice) {
          var supported = supportedMap[choice.value] !== false;
          var selected = state.format === choice.value;
          var classes = "choice-card rounded-2xl p-4 text-left" +
            (selected ? " selected" : "") +
            (supported ? "" : " disabled");
          var recommendedBadge = recommended === choice.value
            ? '<span class="rounded-full border border-[var(--accent)]/35 bg-[rgba(var(--accent-rgb),0.12)] px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--accent)]">Recommended</span>'
            : "";
          var unsupportedBadge = !supported
            ? '<span class="rounded-full border border-red-500/30 bg-red-500/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.12em] text-red-300">Unsupported</span>'
            : "";

          return (
            '<button type="button" class="' + classes + '" data-format-value="' + escapeHtml(choice.value) + '" ' + (supported ? "" : "disabled") + '>' +
              '<div class="flex items-start justify-between gap-3">' +
                '<div>' +
                  '<strong class="block text-sm font-bold">' + escapeHtml(choice.label) + "</strong>" +
                  '<p class="mt-1 text-xs text-white/55">' + escapeHtml(choice.description || "") + "</p>" +
                  '<p class="mt-1 text-[11px] text-white/40">Best for: ' + escapeHtml(choice.best_for || "") + "</p>" +
                "</div>" +
              "</div>" +
              '<div class="mt-2 flex flex-wrap gap-2">' + recommendedBadge + unsupportedBadge + "</div>" +
            "</button>"
          );
        })
        .join("")
    );

    toArray(document.querySelectorAll("[data-format-value]")).forEach(function (button) {
      button.addEventListener("click", function () {
        var value = button.getAttribute("data-format-value");
        state.format = ensureSupportedFormat(value);
        renderFormatCards();
        updateArchitectureSummary();
      });
    });
  }

  function renderPlatformCards() {
    setHtml(
      "platformGrid",
      platformChoices
        .map(function (choice) {
          var selected = state.platform === choice.value;
          return (
            '<button type="button" class="choice-card rounded-xl px-3 py-3 text-xs font-bold ' + (selected ? "selected" : "") + '" data-platform-value="' + escapeHtml(choice.value) + '">' +
              escapeHtml(choice.label) +
            "</button>"
          );
        })
        .join("")
    );

    toArray(document.querySelectorAll("[data-platform-value]")).forEach(function (button) {
      button.addEventListener("click", function () {
        var value = button.getAttribute("data-platform-value");
        state.platform = value || "pc";
        renderPlatformCards();
        updateArchitectureSummary();
      });
    });
  }

  function renderSizeChips() {
    var sizes = getRecommendedSizes(selectedGame);
    setHtml(
      "sizeChips",
      sizes
        .map(function (size) {
          var selected = Number(size) === Number(state.maxParticipants);
          var cls = selected
            ? "border-[var(--accent)] bg-[rgba(var(--accent-rgb),0.14)] text-white"
            : "border-white/10 bg-white/5 text-white/70";
          return '<button type="button" class="rounded-xl border px-3 py-1.5 text-xs font-bold ' + cls + '" data-size-choice="' + size + '">' + size + "</button>";
        })
        .join("")
    );

    toArray(document.querySelectorAll("[data-size-choice]")).forEach(function (button) {
      button.addEventListener("click", function () {
        var size = Math.max(2, Math.min(256, toInt(button.getAttribute("data-size-choice"), 16)));
        state.maxParticipants = size;
        var slider = byId("capacitySlider");
        if (slider) {
          slider.value = String(size);
        }
        setText("capacityLabel", String(size));
        renderSizeChips();
        updateArchitectureSummary();
      });
    });
  }

  function setParticipationUi(participation) {
    var value = String(participation || "team").toLowerCase();
    if (value !== "solo" && value !== "squad") {
      value = "team";
    }
    state.participationUi = value;

    var teamBtn = byId("btnTeam");
    var soloBtn = byId("btnSolo");
    var squadBtn = byId("btnSquad");

    if (teamBtn) {
      teamBtn.classList.toggle("selected", value === "team");
    }
    if (soloBtn) {
      soloBtn.classList.toggle("selected", value === "solo");
    }
    if (squadBtn) {
      squadBtn.classList.toggle("selected", value === "squad");
    }

    if (value === "solo") {
      state.rosterMin = 1;
      state.rosterMax = 1;
      state.rosterSubs = 0;
      if (byId("rosterMin")) byId("rosterMin").value = "1";
      if (byId("rosterMax")) byId("rosterMax").value = "1";
      if (byId("rosterSubs")) byId("rosterSubs").value = "0";
    }

    updateArchitectureSummary();
  }

  function updateIdentityPreview() {
    syncIdentityState();
    setText("slugPreview", state.slug || "untitled");
    setText("previewName", state.name || "Untitled Tournament");
    setText("previewSlug", state.slug || "untitled");
    setText("launchName", state.name || "Untitled Tournament");
    setText("launchNameFinal", state.name || "Untitled Tournament");
    setText("previewRegion", state.region || "Bangladesh");
  }

  function updateArchitectureSummary() {
    syncArchitectureState();

    state.minParticipants = state.participationUi === "solo" ? 2 : Math.max(2, Math.min(state.maxParticipants, state.rosterMin));

    setText("capacityLabel", String(state.maxParticipants));

    var slider = byId("capacitySlider");
    if (slider && String(slider.value) !== String(state.maxParticipants)) {
      slider.value = String(state.maxParticipants);
    }

    setText("sumSlots", String(state.maxParticipants));
    setText("sumRoster", state.rosterMin + "-" + state.rosterMax + " (+" + state.rosterSubs + " subs)");
    setText("sumPlatform", platformLabel(state.platform));
    setText("sumServer", state.serverRegion || "Global");
    setText("launchSlots", String(state.maxParticipants));
    setText("launchSlotsFinal", String(state.maxParticipants));

    var gameName = gameDisplayName(selectedGame);
    var participationLabel = state.participationUi === "solo" ? "Solo" : (state.participationUi === "squad" ? "Squad" : "Team");

    setHtml(
      "configPreview",
      [
        ["Game", gameName],
        ["Format", formatLabel(state.format)],
        ["Participation", participationLabel],
        ["Capacity", String(state.maxParticipants)],
        ["Platform", platformLabel(state.platform)],
        ["Server", state.serverRegion || "Global"]
      ]
        .map(function (row) {
          return '<div class="flex items-center justify-between gap-3 border-b border-white/10 py-2 last:border-0"><span class="text-white/45">' + escapeHtml(row[0]) + '</span><span class="text-right font-semibold text-white/90">' + escapeHtml(row[1]) + "</span></div>";
        })
        .join("")
    );
  }

  function updateEconomySummary() {
    syncEconomyState();

    var entrySummary = state.hasEntryFee
      ? (state.entryFeeCurrency === "DC"
          ? String(Math.max(0, toInt(state.entryFeeAmount, 0))) + " DC"
          : toMoney(state.entryFeeAmount) + " " + state.entryFeeCurrency)
      : "Free";

    var prizeSummary = state.prizeCurrency === "DC"
      ? String(Math.max(0, toInt(state.prizePool, 0))) + " DC"
      : toMoney(state.prizePool) + " " + state.prizeCurrency;

    setText("sumEntry", entrySummary);
    setText("sumCurrency", state.entryFeeCurrency || "BDT");
    setText("sumPrize", prizeSummary);
    setText("launchEntry", entrySummary);
    setText("launchEntryFinal", entrySummary);

    updateExpandPanel("feePanel", state.hasEntryFee);

    var showLan = isStaff && (state.venueMode === "lan" || state.venueMode === "hybrid");
    updateExpandPanel("lanFields", showLan);

    if (!isStaff) {
      updateExpandPanel("lanFields", false);
      var onlineRadio = document.querySelector('input[name="venueMode"][value="online"]');
      if (onlineRadio) {
        onlineRadio.checked = true;
      }
      state.venueMode = "online";
    }
  }

  function updateReviewSummary() {
    syncIdentityState();
    syncArchitectureState();
    syncEconomyState();
    syncRulesState();

    var paymentMethods = state.paymentMethods.length
      ? state.paymentMethods.map(formatLabel).join(", ")
      : "None";

    var entrySummary = state.hasEntryFee
      ? (state.entryFeeCurrency === "DC"
          ? String(Math.max(0, toInt(state.entryFeeAmount, 0))) + " DC"
          : toMoney(state.entryFeeAmount) + " " + state.entryFeeCurrency)
      : "Free";

    var prizeSummary = state.prizeCurrency === "DC"
      ? String(Math.max(0, toInt(state.prizePool, 0))) + " DC"
      : toMoney(state.prizePool) + " " + state.prizeCurrency;

    var rows = [
      ["Game", gameDisplayName(selectedGame)],
      ["Tournament", state.name || "-"],
      ["Brief", state.tournamentBrief || "-"],
      ["Description", state.description ? state.description.slice(0, 120) + (state.description.length > 120 ? "..." : "") : "-"],
      ["Format", formatLabel(state.format)],
      ["Capacity", String(state.maxParticipants)],
      ["Participation", state.participationUi === "solo" ? "Solo" : (state.participationUi === "squad" ? "Squad" : "Team")],
      ["Platform", platformLabel(state.platform)],
      ["Registration", safeDateLabel(state.registrationStart) + " -> " + safeDateLabel(state.registrationEnd)],
      ["Tournament Start", safeDateLabel(state.tournamentStart)],
      ["Entry Fee", entrySummary],
      ["Payment Methods", paymentMethods],
      ["Prize Pool", prizeSummary],
      ["Venue", formatLabel(state.venueMode || "online")],
      ["Official", state.isOfficial ? "Yes" : "No"]
    ];

    setHtml(
      "reviewContent",
      rows
        .map(function (row) {
          return '<div class="flex items-start justify-between gap-3 rounded-xl border border-white/10 bg-black/20 px-4 py-3"><span class="text-sm text-white/55">' + escapeHtml(row[0]) + '</span><span class="text-right text-sm font-semibold text-white">' + escapeHtml(row[1]) + "</span></div>";
        })
        .join("")
    );
  }

  function applyGameDefaults(game) {
    if (!game) {
      return;
    }

    setAccent(game.primary_color || "#06b6d4");

    state.format = ensureSupportedFormat(game.recommended_format || state.format || "single_elimination");
    state.platform = game.recommended_platform || state.platform || "pc";
    setParticipationUi(getDefaultParticipation(game));

    var sizes = getRecommendedSizes(game);
    state.maxParticipants = sizes[0] || 16;

    state.rosterMin = defaultRosterMin(game);
    state.rosterMax = Math.max(state.rosterMin, defaultRosterMax(game));
    state.rosterSubs = defaultRosterSubs(game);
    state.serverRegion = getDefaultServer(game);

    if (byId("rosterMin")) byId("rosterMin").value = String(state.rosterMin);
    if (byId("rosterMax")) byId("rosterMax").value = String(state.rosterMax);
    if (byId("rosterSubs")) byId("rosterSubs").value = String(state.rosterSubs);
    if (byId("serverRegion")) byId("serverRegion").value = state.serverRegion;

    if (byId("capacitySlider")) byId("capacitySlider").value = String(state.maxParticipants);
    setText("capacityLabel", String(state.maxParticipants));

    if (byId("rulesText") && !String(byId("rulesText").value || "").trim() && game.rule_template) {
      byId("rulesText").value = String(game.rule_template);
      state.rulesText = String(game.rule_template);
    }

    setText("contextIcon", gameFallbackLetters(game));
    setText("contextTitle", gameDisplayName(game));
    setText("contextSub", gameCategory(game) + " protocol");

    var tips = Array.isArray(game.tips) && game.tips.length
      ? game.tips[0]
      : (game.subtitle || "Use game defaults and verify participant rules before launch.");
    setText("contextTip", tips);

    setText("selectedHeroIcon", gameFallbackLetters(game));
    setText("selectedHeroName", gameDisplayName(game));
    setText("quickSlots", String(state.maxParticipants));
    setText("quickRoster", state.rosterMin + "-" + state.rosterMax);
    setText("quickPlatform", platformLabel(state.platform));
    setText("quickServer", state.serverRegion || "Global");
    setText("previewGame", gameDisplayName(game));
    setText("launchGame", gameDisplayName(game));
    setText("launchGameFinal", gameDisplayName(game));

    var advisor = Array.isArray(game.tips) && game.tips.length
      ? game.tips.join(" ")
      : "Verify map/mode rules, anti-cheat expectations, and dispute process before publish.";
    setText("advisorTip", advisor);

    renderFormatCards();
    renderPlatformCards();
    renderSizeChips();
    updateArchitectureSummary();
    updateEconomySummary();
    updateReviewSummary();
  }

  function loadRuleTemplate() {
    if (!selectedGame || !byId("rulesText")) {
      return;
    }
    if (selectedGame.rule_template) {
      byId("rulesText").value = String(selectedGame.rule_template);
      state.rulesText = String(selectedGame.rule_template);
      showToast("Game-specific template loaded");
    } else {
      showToast("No game-specific template found");
    }
  }

  function generateSmartRules() {
    var formatName = formatLabel(state.format);
    var lines = [
      "DeltaCrown Tournament Rulebook",
      "",
      "1) Follow all organizer instructions and fair-play standards.",
      "2) Tournament format: " + formatName + ".",
      "3) Result proof requirement: " + formatLabel(state.resultProof) + ".",
      "4) Disputes must include clear evidence within 15 minutes.",
      "5) Check-in and schedule times are binding."
    ];

    if (state.rankRestriction) {
      lines.push("6) Rank restriction: " + state.rankRestriction + ".");
    }

    if (byId("rulesText")) {
      byId("rulesText").value = lines.join("\n");
      state.rulesText = byId("rulesText").value;
      showToast("Smart rules generated");
    }
  }

  function buildDescription() {
    var body = state.description;
    var intro = state.tournamentBrief;

    if (intro && body) {
      body = intro + "\n\n" + body;
    } else if (intro && !body) {
      body = intro;
    }

    var notes = [];
    notes.push("Region: " + (state.region || "-"));
    notes.push("Visibility: " + formatLabel(state.visibility || "-"));
    notes.push("Timezone: " + (state.timezone || "-"));

    if (state.communityLinks && state.communityLinks.length) {
      state.communityLinks.forEach(function (link) {
        notes.push("Community (" + link.platform + "): " + link.url);
      });
    }
    if (state.supportContact) {
      notes.push("Support Contact: " + state.supportContact);
    }

    body = String(body || "").trim();
    if (notes.length) {
      body += "\n\n[Organizer Metadata]\n" + notes.join("\n");
    }

    return body;
  }

  function buildRulesText() {
    var lines = [];

    if (state.rulesText) {
      lines.push(state.rulesText);
    }

    lines.push("\n[Eligibility]");
    lines.push("Min age: " + (state.minAge || "none"));
    lines.push("Country restriction: " + (state.countryRestriction || "none"));
    lines.push("Rank restriction: " + (state.rankRestriction || "none"));

    lines.push("\n[Venue]");
    lines.push("Mode: " + state.venueMode);

    if (state.venueMode === "lan" || state.venueMode === "hybrid") {
      lines.push("Venue name: " + (elValue("venueName", "") || "n/a"));
      lines.push("Venue city: " + (elValue("venueCity", "") || "n/a"));
      lines.push("Venue map: " + (elValue("venueMap", "") || "n/a"));
    }

    if (state.hasEntryFee) {
      lines.push("\n[Payment]");
      lines.push("Methods: " + (state.paymentMethods.length ? state.paymentMethods.join(", ") : "none"));
      lines.push("Receiver: " + (state.receiverNumber || "n/a"));
      lines.push("Instruction: " + (state.paymentInstruction || "n/a"));
      lines.push("Verification note: " + (state.verificationNote || "n/a"));
    }

    return lines.join("\n").trim();
  }

  function toIso(value) {
    if (!value) {
      return null;
    }
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date.toISOString();
  }

  function computeCheckInMinutesBefore() {
    if (!state.checkInOpen || !state.tournamentStart) {
      return 15;
    }

    var checkInDate = new Date(state.checkInOpen);
    var startDate = new Date(state.tournamentStart);
    if (Number.isNaN(checkInDate.getTime()) || Number.isNaN(startDate.getTime())) {
      return 15;
    }

    var diffMinutes = Math.round((startDate.getTime() - checkInDate.getTime()) / 60000);
    if (diffMinutes < 5 || diffMinutes > 120) {
      return 15;
    }

    return diffMinutes;
  }

  function buildPayload() {
    syncIdentityState();
    syncArchitectureState();
    syncEconomyState();
    syncRulesState();

    var paymentMethods = state.paymentMethods;

    var entryFeeAmount = "0.00";
    var entryFeeDeltaCoin = 0;

    if (state.hasEntryFee) {
      if (state.entryFeeCurrency === "DC") {
        entryFeeDeltaCoin = Math.max(0, toInt(state.entryFeeAmount, 0));
      } else {
        entryFeeAmount = toMoney(state.entryFeeAmount);
      }
    }

    var prizePool = "0.00";
    var prizeDeltaCoin = 0;
    if (state.prizeCurrency === "DC") {
      prizeDeltaCoin = Math.max(0, toInt(state.prizePool, 0));
    } else {
      prizePool = toMoney(state.prizePool);
    }

    var payload = {
      name: state.name,
      game_id: selectedGame ? selectedGame.id : null,
      format: state.format,
      max_participants: state.maxParticipants,
      min_participants: state.minParticipants,
      registration_start: toIso(state.registrationStart),
      registration_end: toIso(state.registrationEnd),
      tournament_start: toIso(state.tournamentStart),
      tournament_end: toIso(state.tournamentEnd),
      description: buildDescription(),
      participation_type: normalizeParticipationType(),
      has_entry_fee: state.hasEntryFee,
      entry_fee_amount: entryFeeAmount,
      entry_fee_currency: state.entryFeeCurrency,
      entry_fee_deltacoin: entryFeeDeltaCoin,
      payment_methods: paymentMethods,
      prize_pool: prizePool,
      prize_currency: state.prizeCurrency,
      prize_deltacoin: prizeDeltaCoin,
      prize_distribution: {
        first_percent: state.prizeFirst,
        second_percent: state.prizeSecond,
        third_percent: state.prizeThird,
        mvp_bonus: state.mvpBonus || ""
      },
      rules_text: buildRulesText(),
      enable_check_in: true,
      check_in_minutes_before: state.checkInMinutes || computeCheckInMinutesBefore(),
      enable_dynamic_seeding: !!state.enableDynamicSeeding,
      enable_live_updates: !!state.enableLiveUpdates,
      enable_certificates: !!state.enableCertificates,
      enable_challenges: !!state.enableChallenges,
      enable_fan_voting: !!state.enableFanVoting,
      is_official: isStaff ? !!state.isOfficial : false,
      meta_description: state.tournamentBrief || ""
    };

    return payload;
  }

  function collectResponseError(data) {
    if (!data || typeof data !== "object") {
      return "Tournament creation failed.";
    }

    if (data.message) {
      return data.message;
    }
    if (data.detail) {
      return data.detail;
    }
    if (data.error) {
      return data.error;
    }

    var keys = Object.keys(data);
    for (var i = 0; i < keys.length; i += 1) {
      var key = keys[i];
      var value = data[key];
      if (Array.isArray(value)) {
        return key + ": " + value.join(", ");
      }
      if (typeof value === "string") {
        return key + ": " + value;
      }
    }

    return "Tournament creation failed.";
  }

  function submitTournament() {
    var submitButton = byId("btnSubmit");
    if (submitButton && submitButton.disabled) {
      alert("You cannot submit this tournament right now.");
      return;
    }

    for (var step = 1; step <= 4; step += 1) {
      if (!validateStep(step)) {
        goToStep(step);
        return;
      }
    }

    var payload = buildPayload();

    if (!payload.name || !payload.game_id) {
      alert("Please complete required fields before submitting.");
      return;
    }

    setDeployOverlay(true, "Compiling architecture...", "Sending create request");
    setLoading(true);

    fetch(apiCreateUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCookie("csrftoken")
      },
      body: JSON.stringify(payload)
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            return {
              ok: response.ok,
              status: response.status,
              data: data
            };
          });
      })
      .then(function (result) {
        if (!result.ok) {
          setLoading(false);
          setDeployOverlay(false);
          alert(collectResponseError(result.data));
          return;
        }

        setDeployOverlay(true, "Tournament deployed", "Redirecting to TOC onboarding");

        var redirectUrl = result.data.redirect_url;
        if (!redirectUrl && result.data.tournament && result.data.tournament.slug) {
          redirectUrl = "/toc/" + result.data.tournament.slug + "/?onboarding=true";
        }
        if (!redirectUrl) {
          redirectUrl = "/tournaments/";
        }

        window.location.href = redirectUrl;
      })
      .catch(function () {
        setLoading(false);
        setDeployOverlay(false);
        alert("Network error while creating tournament. Please try again.");
      });
  }

  function bindInputs() {
    var gameSearch = byId("gameSearch");
    if (gameSearch) {
      gameSearch.addEventListener("input", filterGameCards);
    }

    var nameInput = byId("tournamentName");
    if (nameInput) {
      nameInput.addEventListener("input", function () {
        updateIdentityPreview();
        updateReviewSummary();
      });
    }

    ["tournamentBrief", "description", "regionSelect", "visibilitySelect", "timezoneSelect", "communityLink", "supportContact"].forEach(function (id) {
      var node = byId(id);
      if (!node) {
        return;
      }
      node.addEventListener("input", function () {
        updateIdentityPreview();
        updateReviewSummary();
      });
      node.addEventListener("change", function () {
        updateIdentityPreview();
        updateReviewSummary();
      });
    });

    var bannerInput = byId("bannerInput");
    if (bannerInput) {
      bannerInput.addEventListener("change", function () {
        var label = byId("bannerLabel");
        if (label) {
          label.textContent = bannerInput.files && bannerInput.files[0] ? bannerInput.files[0].name : "Upload banner";
        }
      });
    }

    var logoInput = byId("logoInput");
    if (logoInput) {
      logoInput.addEventListener("change", function () {
        var label = byId("logoLabel");
        if (label) {
          label.textContent = logoInput.files && logoInput.files[0] ? logoInput.files[0].name : "Upload logo";
        }
      });
    }

    var capacitySlider = byId("capacitySlider");
    if (capacitySlider) {
      capacitySlider.addEventListener("input", function () {
        state.maxParticipants = Math.max(2, Math.min(256, toInt(capacitySlider.value, 16)));
        setText("capacityLabel", String(state.maxParticipants));
        renderSizeChips();
        updateArchitectureSummary();
        updateReviewSummary();
      });
    }

    ["rosterMin", "rosterMax", "rosterSubs", "resultProof", "serverRegion"].forEach(function (id) {
      var node = byId(id);
      if (!node) {
        return;
      }
      node.addEventListener("input", function () {
        updateArchitectureSummary();
        updateReviewSummary();
      });
      node.addEventListener("change", function () {
        updateArchitectureSummary();
        updateReviewSummary();
      });
    });

    var teamBtn = byId("btnTeam");
    if (teamBtn) {
      teamBtn.addEventListener("click", function () {
        setParticipationUi("team");
        updateReviewSummary();
      });
    }

    var soloBtn = byId("btnSolo");
    if (soloBtn) {
      soloBtn.addEventListener("click", function () {
        setParticipationUi("solo");
        updateReviewSummary();
      });
    }

    var squadBtn = byId("btnSquad");
    if (squadBtn) {
      squadBtn.addEventListener("click", function () {
        setParticipationUi("squad");
        updateReviewSummary();
      });
    }

    var advancedToggle = byId("advancedToggle");
    if (advancedToggle) {
      advancedToggle.addEventListener("change", function () {
        updateExpandPanel("advancedPanel", advancedToggle.checked);
      });
    }

    ["enableDynamicSeeding", "enableLiveUpdates", "enableCertificates", "enableChallenges", "enableFanVoting"].forEach(function (id) {
      var node = byId(id);
      if (!node) {
        return;
      }
      node.addEventListener("change", function () {
        updateArchitectureSummary();
      });
    });

    var checkInMinutesInput = byId("checkInMinutes");
    if (checkInMinutesInput) {
      checkInMinutesInput.addEventListener("input", function () {
        state.checkInMinutes = Math.max(5, Math.min(120, toInt(checkInMinutesInput.value, 15)));
      });
    }

    var addLinkBtn = byId("addCommunityLink");
    if (addLinkBtn) {
      addLinkBtn.addEventListener("click", function () {
        var container = byId("communityLinksContainer");
        if (!container) return;
        var row = document.createElement("div");
        row.className = "community-link-row flex gap-2";
        row.innerHTML = '<select class="community-link-platform dc-input w-[130px] rounded-xl px-3 py-3 text-sm"><option value="discord">Discord</option><option value="whatsapp">WhatsApp</option><option value="telegram">Telegram</option><option value="facebook">Facebook</option><option value="messenger">Messenger</option><option value="other">Other</option></select><input type="url" class="community-link-url dc-input flex-1 rounded-xl px-4 py-3" placeholder="https://..."><button type="button" class="rounded-xl border border-white/10 bg-white/5 px-2 py-1 text-xs text-white/50 hover:text-red-400 hover:bg-red-500/10 transition" onclick="this.parentElement.remove()">✕</button>';
        container.appendChild(row);
      });
    }

    ["regStart", "regEnd", "checkInOpen", "tourStart", "tourEnd", "entryFeeAmount", "entryFeeCurrency", "receiverNumber", "paymentInstruction", "verificationNote", "prizePool", "prizeCurrency", "prizeFirst", "prizeSecond", "prizeThird", "mvpBonus", "venueName", "venueCity", "venueMap"].forEach(function (id) {
      var node = byId(id);
      if (!node) {
        return;
      }
      node.addEventListener("input", function () {
        updateEconomySummary();
        updateReviewSummary();
      });
      node.addEventListener("change", function () {
        updateEconomySummary();
        updateReviewSummary();
      });
    });

    var feeToggle = byId("entryFeeToggle");
    if (feeToggle) {
      feeToggle.addEventListener("change", function () {
        updateEconomySummary();
        updateReviewSummary();
      });
    }

    toArray(document.querySelectorAll(".payment-method-checkbox")).forEach(function (box) {
      box.addEventListener("change", function () {
        updateEconomySummary();
        updateReviewSummary();
      });
    });

    toArray(document.querySelectorAll('input[name="venueMode"]')).forEach(function (radio) {
      if (!isStaff && radio.value !== "online") {
        radio.disabled = true;
      }

      radio.addEventListener("change", function () {
        updateEconomySummary();
        updateReviewSummary();
      });
    });

    var officialToggle = byId("officialToggle");
    if (officialToggle) {
      if (!isStaff) {
        officialToggle.checked = false;
        officialToggle.disabled = true;
      }
      officialToggle.addEventListener("change", function () {
        updateReviewSummary();
      });
    }

    ["minAge", "countryRestriction", "rankRestriction", "rulesText"].forEach(function (id) {
      var node = byId(id);
      if (!node) {
        return;
      }
      node.addEventListener("input", updateReviewSummary);
      node.addEventListener("change", updateReviewSummary);
    });

    var loadTemplateButton = byId("btnLoadRuleTemplate");
    if (loadTemplateButton) {
      loadTemplateButton.addEventListener("click", loadRuleTemplate);
    }

    var generateRulesButton = byId("generateRules");
    if (generateRulesButton) {
      generateRulesButton.addEventListener("click", generateSmartRules);
    }

    var nextInlineButtons = toArray(document.querySelectorAll("[data-next-inline]"));
    nextInlineButtons.forEach(function (button) {
      button.addEventListener("click", nextStep);
    });

    var prevButton = byId("prevBtn");
    if (prevButton) {
      prevButton.addEventListener("click", prevStep);
    }

    var nextButton = byId("nextBtn");
    if (nextButton) {
      nextButton.addEventListener("click", nextStep);
    }

    var submitButton = byId("btnSubmit");
    if (submitButton) {
      submitButton.addEventListener("click", submitTournament);
    }


    var topupButton = byId("topupCta");
    if (topupButton) {
      topupButton.addEventListener("click", function () {
        showToast("Please top up DeltaCoin from your wallet.");
      });
    }

    var desktopGuideButton = byId("desktopGuideBtn");
    if (desktopGuideButton) {
      desktopGuideButton.addEventListener("click", openGuideModal);
    }

    var mobileGuideButton = byId("mobileGuideBtn");
    if (mobileGuideButton) {
      mobileGuideButton.addEventListener("click", openGuideModal);
    }

    var closeGuideButton = byId("closeGuide");
    if (closeGuideButton) {
      closeGuideButton.addEventListener("click", closeGuideModal);
    }

    var guideModal = byId("guideModal");
    if (guideModal) {
      guideModal.addEventListener("click", function (event) {
        if (event.target === guideModal) {
          closeGuideModal();
        }
      });
    }

    document.addEventListener(
      "pointermove",
      function (event) {
        var x = (event.clientX / window.innerWidth) * 100;
        var y = (event.clientY / window.innerHeight) * 100;
        createApp.style.setProperty("--mx", x + "%");
        createApp.style.setProperty("--my", y + "%");
      },
      { passive: true }
    );
  }

  function seedScheduleDefaults() {
    var now = new Date();
    var registrationStart = new Date(now.getTime() + 60 * 60 * 1000);
    var registrationEnd = new Date(now.getTime() + 4 * 24 * 60 * 60 * 1000);
    var tournamentStart = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    var tournamentEnd = new Date(tournamentStart.getTime() + 24 * 60 * 60 * 1000);
    var checkInOpen = new Date(tournamentStart.getTime() - 30 * 60 * 1000);

    function toLocalValue(date) {
      var local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
      return local.toISOString().slice(0, 16);
    }

    if (byId("regStart")) byId("regStart").value = toLocalValue(registrationStart);
    if (byId("regEnd")) byId("regEnd").value = toLocalValue(registrationEnd);
    if (byId("checkInOpen")) byId("checkInOpen").value = toLocalValue(checkInOpen);
    if (byId("tourStart")) byId("tourStart").value = toLocalValue(tournamentStart);
    if (byId("tourEnd")) byId("tourEnd").value = toLocalValue(tournamentEnd);

    state.registrationStart = byId("regStart") ? byId("regStart").value : "";
    state.registrationEnd = byId("regEnd") ? byId("regEnd").value : "";
    state.checkInOpen = byId("checkInOpen") ? byId("checkInOpen").value : "";
    state.tournamentStart = byId("tourStart") ? byId("tourStart").value : "";
    state.tournamentEnd = byId("tourEnd") ? byId("tourEnd").value : "";
  }

  function initialize() {
    renderSteppers();
    renderCategoryFilters();
    renderGameCards();
    renderFormatCards();
    renderPlatformCards();
    renderSizeChips();

    seedScheduleDefaults();
    bindInputs();

    if (selectedGame) {
      applyGameDefaults(selectedGame);
    }

    if (byId("entryFeeCurrency")) {
      state.entryFeeCurrency = byId("entryFeeCurrency").value || "BDT";
    }
    if (byId("prizeCurrency")) {
      state.prizeCurrency = byId("prizeCurrency").value || "BDT";
    }

    updateExpandPanel("feePanel", false);
    updateExpandPanel("advancedPanel", false);
    updateExpandPanel("lanFields", false);

    if (!isStaff) {
      var onlineRadio = document.querySelector('input[name="venueMode"][value="online"]');
      if (onlineRadio) {
        onlineRadio.checked = true;
      }
    }

    updateIdentityPreview();
    updateArchitectureSummary();
    updateEconomySummary();
    updateReviewSummary();
    updateStepperUi();

    if (!canAfford && !isStaff) {
      var submitButton = byId("btnSubmit");
      if (submitButton) {
        submitButton.disabled = true;
      }
    }
  }

  window.nextStep = nextStep;
  window.prevStep = prevStep;
  window.goToStep = goToStep;
  window.submitTournament = submitTournament;
  window.loadRuleTemplate = loadRuleTemplate;

  initialize();
})()
