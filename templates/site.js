(() => {
  "use strict";
  document.body.classList.add("js-enabled");
  const storageKey = "truedealatlas-saved-v1";
  const readSaved = () => {
    try {
      const values = JSON.parse(localStorage.getItem(storageKey) || "[]");
      return new Set(Array.isArray(values) ? values.filter((value) => typeof value === "string") : []);
    } catch { return new Set(); }
  };
  let saved = readSaved();
  let toastTimer;
  const toast = (text) => {
    const element = document.getElementById("site-toast");
    if (!element) return;
    clearTimeout(toastTimer);
    element.textContent = text;
    element.hidden = false;
    toastTimer = setTimeout(() => { element.hidden = true; }, 3500);
  };
  const updateSaved = () => {
    document.querySelectorAll("[data-saved-count]").forEach((element) => { element.textContent = saved.size; });
    document.querySelectorAll(".saved-link").forEach((link) => {
      link.setAttribute("aria-label", "Saved offers (" + saved.size + ")");
      link.title = "Saved offers";
    });
    document.querySelectorAll(".save-offer").forEach((button) => {
      const selected = saved.has(button.dataset.id);
      button.setAttribute("aria-pressed", String(selected));
      if (!button.dataset.originalLabel) button.dataset.originalLabel = button.getAttribute("aria-label");
      button.setAttribute("aria-label", selected ? button.dataset.originalLabel.replace(/^Save /, "Unsave ") : button.dataset.originalLabel);
      button.title = selected ? "Remove saved offer" : "Save offer";
    });
  };
  document.querySelectorAll(".save-offer").forEach((button) => {
    button.addEventListener("click", () => {
      const id = button.dataset.id;
      saved.has(id) ? saved.delete(id) : saved.add(id);
      try {
        localStorage.setItem(storageKey, JSON.stringify([...saved]));
        toast(saved.has(id) ? "Offer saved" : "Offer removed from saved");
      } catch { toast("Browser storage is unavailable. Saved for this visit."); }
      updateSaved();
      renderOffers?.();
    });
  });
  document.querySelectorAll(".copy-code").forEach((button) => {
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.dataset.code);
        toast("Code " + button.dataset.code + " copied");
      } catch {
        const code = button.closest(".coupon-code").querySelector("strong");
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection.removeAllRanges();
        selection.addRange(range);
        toast("Copy is unavailable. The code is selected for copying.");
      }
    });
  });

  const grid = document.getElementById("deal-grid");
  const input = document.getElementById("deal-search");
  const form = document.getElementById("deal-search-form");
  const store = document.getElementById("store-filter");
  const sort = document.getElementById("sort-order");
  const savedOnly = document.getElementById("saved-only");
  const more = document.getElementById("load-more");
  const tabs = [...document.querySelectorAll("[role=tab][data-kind]")];
  const reset = document.getElementById("reset-filters");
  let renderOffers;
  if (grid && input && store && sort && savedOnly && more) {
    const cards = [...grid.querySelectorAll(".deal-card")];
    const pageSize = matchMedia("(max-width: 620px)").matches ? 9 : 12;
    let limit = pageSize;
    let kind = "all";
    const paramsToControls = () => {
      const params = new URLSearchParams(location.search);
      input.value = params.get("q") || "";
      store.value = params.get("store") || "";
      sort.value = params.get("sort") || "featured";
      if (!sort.value) sort.value = "featured";
      savedOnly.checked = params.get("saved") === "1";
      kind = tabs.some((tab) => tab.dataset.kind === params.get("type")) ? params.get("type") : "all";
    };
    const updateUrl = () => {
      const params = new URLSearchParams(location.search);
      for (const [key, value] of Object.entries({ q: input.value.trim(), store: store.value, sort: sort.value !== "featured" ? sort.value : "", saved: savedOnly.checked ? "1" : "", type: kind !== "all" ? kind : "" })) {
        value ? params.set(key, value) : params.delete(key);
      }
      try { history.replaceState(null, "", location.pathname + (params.size ? "?" + params.toString() : "") + location.hash); } catch {}
    };
    renderOffers = () => {
      const words = input.value.trim().toLocaleLowerCase("en-US").split(/\s+/).filter(Boolean);
      const matches = cards.filter((card) => words.every((word) => card.dataset.search.includes(word)) && (!store.value || card.dataset.store === store.value) && (kind === "all" || card.dataset.kind === kind) && (!savedOnly.checked || saved.has(card.dataset.id)));
      if (sort.value === "discount") matches.sort((a, b) => Number(b.dataset.discount) - Number(a.dataset.discount));
      if (sort.value === "newest") matches.sort((a, b) => (Date.parse(b.dataset.checked) || 0) - (Date.parse(a.dataset.checked) || 0));
      cards.forEach((card) => { card.hidden = true; });
      matches.forEach((card, index) => { grid.append(card); card.hidden = index >= limit; });
      document.getElementById("deal-result-count").textContent = matches.length ? `Showing ${Math.min(limit, matches.length)} of ${matches.length} offers` : "0 offers";
      document.getElementById("search-empty").hidden = matches.length !== 0;
      document.getElementById("empty-message").textContent = savedOnly.checked && saved.size === 0 ? "You haven't saved any offers yet." : "Try another store, offer type, or search term.";
      more.hidden = limit >= matches.length;
      tabs.forEach((tab) => {
        const selected = tab.dataset.kind === kind;
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
      });
      grid.setAttribute("aria-labelledby", "tab-" + kind);
      reset.hidden = !(words.length || store.value || kind !== "all" || savedOnly.checked || sort.value !== "featured");
      updateUrl();
    };
    const change = () => { limit = pageSize; renderOffers(); };
    const clear = () => {
      input.value = ""; store.value = ""; kind = "all"; sort.value = "featured"; savedOnly.checked = false;
      change();
    };
    if (location.pathname === "/") input.addEventListener("input", change);
    [store, sort, savedOnly].forEach((control) => control.addEventListener("change", change));
    tabs.forEach((tab, index) => {
      tab.addEventListener("click", () => { kind = tab.dataset.kind; change(); });
      tab.addEventListener("keydown", (event) => {
        let next;
        if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
        if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
        if (event.key === "Home") next = 0;
        if (event.key === "End") next = tabs.length - 1;
        if (next === undefined) return;
        event.preventDefault();
        tabs[next].focus();
        tabs[next].click();
      });
    });
    more.addEventListener("click", () => { limit += pageSize; renderOffers(); });
    reset.addEventListener("click", clear);
    document.getElementById("empty-reset").addEventListener("click", clear);
    form.addEventListener("submit", (event) => {
      if (location.pathname !== "/") return;
      event.preventDefault(); change();
      document.querySelector(".deals-section").scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
    });
    window.addEventListener("popstate", () => { paramsToControls(); change(); });
    paramsToControls(); renderOffers();
  }
  window.addEventListener("storage", (event) => {
    if (event.key === storageKey) { saved = readSaved(); updateSaved(); renderOffers?.(); }
  });
  updateSaved();

  const storeSearch = document.getElementById("store-search");
  if (storeSearch) {
    const stores = [...document.querySelectorAll("[data-store-name]")];
    storeSearch.addEventListener("input", () => {
      const query = storeSearch.value.trim().toLowerCase();
      let count = 0;
      stores.forEach((item) => { item.hidden = !item.dataset.storeName.includes(query); if (!item.hidden) count++; });
      document.getElementById("store-result-count").textContent = count + " stores";
      document.getElementById("store-empty").hidden = count > 0;
    });
  }
  const compareSort = document.getElementById("compare-sort");
  if (compareSort) {
    const rows = [...document.querySelectorAll(".compare-row")];
    compareSort.addEventListener("change", () => {
      const sorted = [...rows];
      if (compareSort.value === "discount") sorted.sort((a, b) => Number(b.dataset.discount) - Number(a.dataset.discount));
      if (compareSort.value === "newest") sorted.sort((a, b) => (Date.parse(b.dataset.checked) || 0) - (Date.parse(a.dataset.checked) || 0));
      sorted.forEach((row) => row.parentElement.append(row));
    });
  }
})();
