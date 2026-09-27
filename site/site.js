
(() => {
  const form = document.getElementById("deal-search-form");
  const input = document.getElementById("deal-search");
  const grid = document.getElementById("deal-grid");
  const more = document.getElementById("load-more");
  const count = document.getElementById("deal-result-count");
  const empty = document.getElementById("search-empty");
  if (!form || !input || !grid || !more || !count || !empty) return;

  const cards = Array.from(grid.querySelectorAll(".deal-card"));
  const pageSize = window.matchMedia("(max-width: 650px)").matches ? 12 : 18;
  let visibleLimit = pageSize;

  const render = () => {
    const query = input.value.trim().toLowerCase();
    const matches = cards.filter((card) => card.dataset.search.includes(query));
    cards.forEach((card) => {
      const matchIndex = matches.indexOf(card);
      card.hidden = matchIndex < 0 || (!query && matchIndex >= visibleLimit);
    });
    count.textContent = query ? `${matches.length} matching` : `${cards.length} active`;
    empty.hidden = matches.length !== 0;
    more.hidden = Boolean(query) || visibleLimit >= cards.length;
  };

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
    document.querySelector(".deals-section")?.scrollIntoView({behavior: "smooth", block: "start"});
  });
  input.addEventListener("input", render);
  more.addEventListener("click", () => {
    visibleLimit += pageSize;
    render();
  });
  render();
})();
