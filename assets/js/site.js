// Scroll-reveal: the single motion pattern from the editorial style guide.
// Above-the-fold elements reveal instantly (no wait); below-the-fold fade up on scroll.
(function () {
  var els = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
  if (!els.length) return;

  function show(el) { el.classList.add('is-visible'); }

  if (!('IntersectionObserver' in window)) {
    els.forEach(show);
    return;
  }

  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) { show(entry.target); io.unobserve(entry.target); }
    });
  }, { threshold: 0.1 });

  // Reveal anything already in view synchronously so nothing is ever stuck hidden;
  // observe the rest for the scroll animation.
  function init() {
    var vh = window.innerHeight || document.documentElement.clientHeight;
    els.forEach(function (el) {
      if (el.getBoundingClientRect().top < vh * 0.95) { show(el); }
      else { io.observe(el); }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

// Mobile menu: the button toggles the nav links panel; Escape closes it.
(function () {
  var header = document.querySelector('.site-header');
  var btn = header && header.querySelector('.nav-toggle');
  if (!btn) return;
  function set(open) {
    header.classList.toggle('is-open', open);
    btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    btn.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  }
  btn.addEventListener('click', function () { set(!header.classList.contains('is-open')); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') set(false); });
})();

// Member directory: live faceted filter (search + topic + country). DOM-based,
// no fetch, so it works when the file is opened directly. Degrades to the full
// list if JS is off.
(function () {
  var form = document.getElementById('member-filters');
  var grid = document.getElementById('member-grid');
  if (!form || !grid) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll('.member-card'));
  document.querySelectorAll('[data-filtered] .member-card').forEach(function (card) { cards.push(card); });
  var search = document.getElementById('f-search');
  var topic = document.getElementById('f-topic');
  var country = document.getElementById('f-country');
  var count = document.getElementById('member-count');
  var empty = document.getElementById('member-empty');
  var total = cards.length;

  // never let the scroll-reveal hide a directory card
  cards.forEach(function (c) { c.classList.add('is-visible'); });

  function listHas(attr, value) {
    return ('|' + attr).indexOf('|' + value + '|') !== -1;
  }

  function apply() {
    var q = (search.value || '').trim().toLowerCase();
    var t = topic.value;
    var c = country.value;
    var shown = 0;
    cards.forEach(function (card) {
      var ok = (!q || card.getAttribute('data-search').indexOf(q) !== -1)
        && (!t || listHas(card.getAttribute('data-topics'), t))
        && (!c || listHas(card.getAttribute('data-countries'), c));
      card.hidden = !ok;
      if (ok) shown++;
    });
    // hide the PhD section when none of its cards match
    document.querySelectorAll('[data-filtered]').forEach(function (g) {
      var section = g.closest('section');
      if (section) section.hidden = !g.querySelector('.member-card:not([hidden])');
    });
    var filtered = q || t || c;
    count.textContent = filtered
      ? shown + ' of ' + total + ' members'
      : total + ' members';
    empty.hidden = shown !== 0;
  }

  function clear() {
    search.value = ''; topic.value = ''; country.value = ''; apply();
  }

  search.addEventListener('input', apply);
  topic.addEventListener('change', apply);
  country.addEventListener('change', apply);
  document.getElementById('f-clear').addEventListener('click', clear);
  var c2 = document.getElementById('f-clear2');
  if (c2) c2.addEventListener('click', clear);
  apply();
})();

// Count-up: the story stat numbers tick up from zero when scrolled into view.
// Respects prefers-reduced-motion (shows final values, no animation).
(function () {
  var grid = document.querySelector('.stat-grid');
  if (!grid) return;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var values = Array.prototype.slice.call(grid.querySelectorAll('.stat__value'));

  // parse "A$1,943" / "~90%" / "0.7" into {prefix, target, suffix, decimals, comma}
  var parsed = values.map(function (el) {
    var text = el.textContent;
    var m = text.match(/^(\D*?)([\d,]*\.?\d+)(\D*)$/);
    if (!m) return null;
    var numstr = m[2];
    return {
      el: el, prefix: m[1], suffix: m[3],
      target: parseFloat(numstr.replace(/,/g, '')),
      decimals: numstr.indexOf('.') !== -1 ? numstr.split('.')[1].length : 0,
      comma: numstr.indexOf(',') !== -1,
      final: text,
    };
  });

  function fmt(p, value) {
    var s = value.toFixed(p.decimals);
    if (p.comma) s = s.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return p.prefix + s + p.suffix;
  }

  function run() {
    var start = null, dur = 1100;
    function frame(ts) {
      if (start === null) start = ts;
      var t = Math.min(1, (ts - start) / dur);
      var ease = 1 - Math.pow(1 - t, 3);
      parsed.forEach(function (p) { if (p) p.el.textContent = fmt(p, p.target * ease); });
      if (t < 1) requestAnimationFrame(frame);
      else parsed.forEach(function (p) { if (p) p.el.textContent = p.final; });
    }
    requestAnimationFrame(frame);
  }

  if (reduce || !('IntersectionObserver' in window) || !parsed.some(Boolean)) return;
  parsed.forEach(function (p) { if (p) p.el.textContent = fmt(p, 0); });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { run(); io.disconnect(); }
    });
  }, { threshold: 0.4 });
  io.observe(grid);
})();
