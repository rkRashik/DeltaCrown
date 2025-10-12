(function () {
  "use strict";

  class TeamsArenaPage {
    constructor() {
      this.debounceDelay = 250;
      this.debounceHandle = null;
      this.isLoading = false;
      this.currentView = localStorage.getItem("teams-arena-view") || "list";

      this.handleGameChipClick = (event) => this.onGameChipClick(event);
      this.handleLoadMoreClick = (event) => this.onLoadMore(event);
      this.handleViewToggleClick = (event) => this.onViewToggle(event);
      this.handleResetFiltersClick = (event) => this.onResetFilters(event);

      this.cacheElements();
      if (!this.teamList) {
        return;
      }

      this.currentFilters = this.readFiltersFromUrl();
      this.syncUiFromFilters();
      this.bindStaticEvents();
      this.bindDynamicControls();
      this.updateViewClasses();
      this.updateStateFromDom();
      this.toggleClearButton();
    }

    cacheElements() {
      this.searchInput = document.getElementById("team-search");
      this.clearButton = document.getElementById("search-clear");
      this.sortSelect = document.getElementById("sort-select");
      this.sortToggle = document.getElementById("sort-direction-toggle");
      this.sortIcon = document.getElementById("sort-direction-icon");
      this.teamList = document.getElementById("team-list");
      this.resultsSection = document.getElementById("teams-results");
      this.gameWrap = document.getElementById("game-chip-wrap");
      this.loadMoreWrapper = document.querySelector(".load-more-wrap");
      this.loadMoreBtn = document.getElementById("load-more-btn");
      this.feedback = document.getElementById("team-feedback");
      this.resetFiltersBtn = document.getElementById("reset-filters");
      this.viewModeGroup = document.querySelector(".view-mode");
      this.viewButtons = Array.from(document.querySelectorAll(".view-toggle"));
      this.paginationNav = document.querySelector(".pagination-fallback");
    }

    readFiltersFromUrl() {
      const params = new URLSearchParams(window.location.search);
      const filters = {};
      params.forEach((value, key) => {
        if (key === "page") {
          return;
        }
        filters[key] = value;
      });
      return filters;
    }

    syncUiFromFilters() {
      if (this.searchInput) {
        this.searchInput.value = this.currentFilters.q || "";
      }

      if (this.sortSelect && this.currentFilters.sort) {
        this.sortSelect.value = this.currentFilters.sort;
      }

      this.updateSortDirectionIcon();
    }

    bindStaticEvents() {
      if (this.searchInput) {
        this.searchInput.addEventListener("input", (event) => {
          const value = event.target.value.trim();
          this.toggleClearButton(value.length > 0);
          clearTimeout(this.debounceHandle);
          this.debounceHandle = window.setTimeout(() => {
            this.updateFilter("q", value);
            this.fetchPage(1);
          }, this.debounceDelay);
        });

        this.searchInput.addEventListener("keydown", (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            const value = event.target.value.trim();
            clearTimeout(this.debounceHandle);
            this.updateFilter("q", value);
            this.fetchPage(1);
          }
        });
      }

      if (this.clearButton) {
        this.clearButton.addEventListener("click", () => {
          if (!this.searchInput) {
            return;
          }
          this.searchInput.value = "";
          this.toggleClearButton(false);
          this.updateFilter("q", "");
          this.fetchPage(1);
          this.searchInput.focus();
        });
      }

      if (this.sortSelect) {
        this.sortSelect.addEventListener("change", (event) => {
          const value = event.target.value;
          this.updateFilter("sort", value);
          this.fetchPage(1);
        });
      }

      if (this.sortToggle) {
        this.sortToggle.addEventListener("click", () => {
          const nextOrder = this.currentFilters.order === "asc" ? "desc" : "asc";
          this.updateFilter("order", nextOrder);
          this.updateSortDirectionIcon();
          this.fetchPage(1);
        });
      }
    }

    bindDynamicControls() {
      if (this.gameWrap) {
        this.gameWrap.removeEventListener("click", this.handleGameChipClick);
        this.gameWrap.addEventListener("click", this.handleGameChipClick);
      }

      if (this.loadMoreBtn) {
        this.loadMoreBtn.removeEventListener("click", this.handleLoadMoreClick);
        this.loadMoreBtn.addEventListener("click", this.handleLoadMoreClick);
      }

      if (this.viewModeGroup) {
        this.viewModeGroup.removeEventListener("click", this.handleViewToggleClick);
        this.viewModeGroup.addEventListener("click", this.handleViewToggleClick);
      }

      if (this.resetFiltersBtn) {
        this.resetFiltersBtn.removeEventListener("click", this.handleResetFiltersClick);
        this.resetFiltersBtn.addEventListener("click", this.handleResetFiltersClick);
      }

      this.updateViewButtons();
    }

    onGameChipClick(event) {
      const chip = event.target.closest(".game-chip");
      if (!chip) {
        return;
      }
      event.preventDefault();
      const gameCode = chip.dataset.game || "";
      const currentGame = this.currentFilters.game || "";
      if (gameCode === currentGame) {
        return;
      }
      this.updateFilter("game", gameCode);
      this.fetchPage(1);
    }

    onLoadMore(event) {
      event.preventDefault();
      if (this.isLoading || this.currentPage >= this.totalPages) {
        return;
      }
      const nextPage = this.currentPage + 1;
      this.fetchNextPage(nextPage);
    }

    onViewToggle(event) {
      const button = event.target.closest(".view-toggle");
      if (!button) {
        return;
      }
      const view = button.dataset.view || "list";
      if (view === this.currentView) {
        return;
      }
      this.currentView = view;
      localStorage.setItem("teams-arena-view", view);
      this.updateViewClasses();
      this.updateViewButtons();
    }

    onResetFilters(event) {
      event.preventDefault();
      this.updateFilter("q", "");
      this.updateFilter("game", "");
      if (this.searchInput) {
        this.searchInput.value = "";
      }
      this.toggleClearButton(false);
      this.fetchPage(1);
    }

    toggleClearButton(forceVisible) {
      if (!this.clearButton) {
        return;
      }
      if (typeof forceVisible === "boolean") {
        this.clearButton.hidden = !forceVisible;
        return;
      }
      const hasValue = Boolean(this.searchInput && this.searchInput.value.trim());
      this.clearButton.hidden = !hasValue;
    }

    updateFilter(key, value) {
      if (typeof value === "string") {
        const trimmed = value.trim();
        if (trimmed.length === 0) {
          delete this.currentFilters[key];
          return;
        }
        this.currentFilters[key] = trimmed;
        return;
      }

      if (value === undefined || value === null) {
        delete this.currentFilters[key];
      } else {
        this.currentFilters[key] = value;
      }
    }

    updateSortDirectionIcon() {
      if (!this.sortToggle || !this.sortIcon) {
        return;
      }
      const order = this.currentFilters.order === "asc" ? "asc" : "desc";
      this.currentFilters.order = order;
      if (order === "asc") {
        this.sortIcon.className = "fas fa-sort-amount-up";
        this.sortToggle.setAttribute("title", "Sort: Low to High");
      } else {
        this.sortIcon.className = "fas fa-sort-amount-down";
        this.sortToggle.setAttribute("title", "Sort: High to Low");
      }
    }

    updateViewClasses() {
      if (!this.teamList) {
        return;
      }
      this.teamList.classList.remove("view-list", "view-grid");
      this.teamList.classList.add(`view-${this.currentView}`);
    }

    updateViewButtons() {
      if (!this.viewButtons) {
        return;
      }
      this.viewButtons.forEach((button) => {
        const view = button.dataset.view;
        button.classList.toggle("active", view === this.currentView);
      });
    }

    async fetchPage(page) {
      if (this.isLoading) {
        return;
      }
      this.isLoading = true;
      this.showFeedback("Updating teams");

      try {
        const query = this.buildQueryString({ page });
        const response = await fetch(`${window.location.pathname}?${query}`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            Accept: "text/html"
          }
        });

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`);
        }

        const html = await response.text();
        this.replaceSections(html);
        this.updateUrl(page);
      } catch (error) {
        console.error(error);
        this.showFeedback("Could not update teams. Please try again.", "error");
      } finally {
        this.isLoading = false;
        this.clearFeedback();
      }
    }

    async fetchNextPage(page) {
      if (this.isLoading) {
        return;
      }
      this.isLoading = true;
      this.showFeedback("Loading more teams");

      try {
        const query = this.buildQueryString({ page });
        const response = await fetch(`${window.location.pathname}?${query}`, {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            Accept: "text/html"
          }
        });

        if (!response.ok) {
          throw new Error(`Load more failed with status ${response.status}`);
        }

        const html = await response.text();
        this.appendTeams(html);
        this.updateUrl(page);
      } catch (error) {
        console.error(error);
        this.showFeedback("Failed to load more teams.", "error");
      } finally {
        this.isLoading = false;
        this.clearFeedback();
      }
    }

    replaceSections(html) {
      const doc = new DOMParser().parseFromString(html, "text/html");
      this.swapElement("teams-results", doc);
      this.swapElement("game-chip-wrap", doc);
      this.cacheElements();
      this.bindDynamicControls();
      this.updateViewClasses();
      this.updateStateFromDom();
    }

    appendTeams(html) {
      const doc = new DOMParser().parseFromString(html, "text/html");
      const newList = doc.getElementById("team-list");
      const currentList = document.getElementById("team-list");

      if (newList && currentList) {
        const fragment = document.createDocumentFragment();
        Array.from(newList.children).forEach((child) => {
          fragment.appendChild(child.cloneNode(true));
        });
        currentList.appendChild(fragment);
        currentList.dataset.currentPage = newList.dataset.currentPage || String(this.currentPage + 1);
        currentList.dataset.totalPages = newList.dataset.totalPages || currentList.dataset.totalPages;
      }

      this.replaceOptionalElement(".load-more-wrap", doc);
      this.replaceOptionalElement(".pagination-fallback", doc);
      this.cacheElements();
      this.bindDynamicControls();
      this.updateViewClasses();
      this.updateStateFromDom();
    }

    replaceOptionalElement(selector, doc) {
      const current = document.querySelector(selector);
      const incoming = doc.querySelector(selector);

      if (current && incoming) {
        current.replaceWith(incoming.cloneNode(true));
      } else if (current && !incoming) {
        current.remove();
      } else if (!current && incoming && this.resultsSection) {
        this.resultsSection.appendChild(incoming.cloneNode(true));
      }
    }

    swapElement(id, doc) {
      const current = document.getElementById(id);
      const incoming = doc.getElementById(id);
      if (current && incoming) {
        current.replaceWith(incoming.cloneNode(true));
      }
    }

    updateStateFromDom() {
      if (!this.teamList) {
        this.currentPage = 1;
        this.totalPages = 1;
        return;
      }
      this.currentPage = this.parseNumber(this.teamList.dataset.currentPage, 1);
      this.totalPages = this.parseNumber(this.teamList.dataset.totalPages, 1);
      this.toggleLoadMore();
    }

    parseNumber(value, fallback) {
      const parsed = Number(value);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
    }

    toggleLoadMore() {
      const hasMore = this.currentPage < this.totalPages;
      if (this.loadMoreWrapper) {
        this.loadMoreWrapper.classList.toggle("hidden", !hasMore);
      }
      if (this.loadMoreBtn) {
        this.loadMoreBtn.disabled = !hasMore;
      }
    }

    buildQueryString(extra) {
      const merged = { ...this.currentFilters, ...extra };
      const params = new URLSearchParams();

      Object.entries(merged).forEach(([key, value]) => {
        if (value === undefined || value === null) {
          return;
        }
        const stringValue = String(value).trim();
        if (!stringValue) {
          return;
        }
        if (key === "page" && Number(stringValue) <= 1) {
          return;
        }
        params.set(key, stringValue);
      });

      return params.toString();
    }

    updateUrl(page) {
      const query = this.buildQueryString({ page });
      const newUrl = query ? `${window.location.pathname}?${query}` : window.location.pathname;
      window.history.replaceState({}, "", newUrl);
    }

    showFeedback(message, type = "info") {
      if (!this.feedback) {
        return;
      }
      this.feedback.textContent = message;
      this.feedback.dataset.state = type;
      this.feedback.classList.add("visible");
    }

    clearFeedback() {
      if (!this.feedback) {
        return;
      }
      this.feedback.textContent = "";
      this.feedback.dataset.state = "";
      this.feedback.classList.remove("visible");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    new TeamsArenaPage();
  });
})();
