(function () {
  var activeYear = '';
  var activeCat = '';
  var searchTerm = '';

  function readHash() {
    var hash = window.location.hash.replace('#', '');
    var params = {};
    hash.split('&').forEach(function (part) {
      var kv = part.split('=');
      if (kv[0]) params[kv[0]] = decodeURIComponent(kv[1] || '');
    });
    return params;
  }

  function writeHash() {
    var parts = [];
    if (activeYear) parts.push('year=' + activeYear);
    if (activeCat) parts.push('cat=' + activeCat);
    var hash = parts.length ? '#' + parts.join('&') : window.location.pathname + window.location.search;
    history.replaceState(null, '', parts.length ? '#' + parts.join('&') : window.location.pathname);
  }

  function applyFilters() {
    var cards = document.querySelectorAll('.post-card');
    var visible = 0;
    var term = searchTerm.toLowerCase();
    cards.forEach(function (card) {
      var yearMatch = !activeYear || card.dataset.year === activeYear;
      var catMatch = !activeCat || card.dataset.cat === activeCat;
      var textMatch = !term || card.textContent.toLowerCase().indexOf(term) > -1;
      var show = yearMatch && catMatch && textMatch;
      card.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    var countEl = document.getElementById('filter-count');
    if (countEl) {
      var hasFilter = activeYear || activeCat || searchTerm;
      countEl.textContent = hasFilter ? visible + ' sonuç' : '';
    }
    writeHash();
  }

  function setActiveBtn(selector, value) {
    document.querySelectorAll(selector).forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.value === value);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var params = readHash();
    if (params.year) activeYear = params.year;
    if (params.cat) activeCat = params.cat;

    document.querySelectorAll('.cat-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.value === activeCat);
      btn.addEventListener('click', function () {
        activeCat = btn.dataset.value;
        setActiveBtn('.cat-btn', activeCat);
        applyFilters();
      });
    });

    document.querySelectorAll('.year-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.value === activeYear);
      btn.addEventListener('click', function () {
        activeYear = btn.dataset.value;
        setActiveBtn('.year-btn', activeYear);
        applyFilters();
      });
    });

    var searchInput = document.getElementById('filter-search');
    if (searchInput) {
      searchInput.addEventListener('input', function () {
        searchTerm = this.value.trim();
        applyFilters();
      });
    }

    if (activeYear || activeCat) applyFilters();
  });
}());
