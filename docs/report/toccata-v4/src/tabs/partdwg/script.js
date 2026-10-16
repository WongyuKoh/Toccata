/* 03 부품 도면·출력 파일 (p-partdwg): filters + search, in-page sheet viewer, zip downloads through the downloads capability.
   API: window.toccata.partdwg = { open(code), codeOf(file) }
     open('P-01-01')            opens the sheet viewer on that part (also switches the tab via the hash router)
     codeOf('stl/print/01_건반/백건_C__7개.stl' or 'hardware/mechanical/cad/stl/...')  -> 'P-01-01' | null
   Data for other tabs: fin/parts/index.json (by_file: print file -> code; parts[]: code, name, qty, sizes, zip/svg paths). */
(function () {
  'use strict';
  var sec = document.getElementById('p-partdwg');
  if (!sec) return;
  var T = window.toccata = window.toccata || {};

  // ---- downloads capability (resolved once, when the tab is first opened)
  var dlP = null;
  function getDl() {
    if (!dlP) {
      try {
        dlP = (window.claude && typeof window.claude.use === 'function')
          ? Promise.resolve(window.claude.use('downloads')).catch(function () { return null; })
          : Promise.resolve(null);
      } catch (e) { dlP = Promise.resolve(null); }
    }
    return dlP;
  }
  var started = false;
  function start() { if (started) return; started = true; getDl(); }
  new MutationObserver(function () { if (!sec.hidden) start(); }).observe(sec, { attributes: true, attributeFilter: ['hidden'] });
  if (!sec.hidden) start();

  function kb(n) {
    n = +n || 0;
    return n >= 1048576 ? (n / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
  }
  function say(el, text, cls) {
    if (!el) return;
    el.textContent = text;
    el.className = 'small partdwg-msg' + (cls ? ' ' + cls : '');
  }
  function b64ToBlob(txt) {
    var bin = atob(txt.replace(/\s+/g, ''));
    var u8 = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    return new Blob([u8], { type: 'application/zip' });
  }
  var busy = false;
  function save(btn, path, name, bytes, msg) {
    if (busy) { say(msg, '다른 파일을 준비하고 있습니다. 잠시 뒤 다시 누르세요.', 'warn'); return; }
    busy = true;
    btn.disabled = true;
    say(msg, '저장 기능을 확인하는 중…');
    getDl().then(function (dl) {
      if (!dl || typeof dl.save !== 'function') {
        say(msg, '이 화면에서는 파일 저장을 쓸 수 없습니다. 발행된 claude.ai 페이지에서 받으세요. 파일: ' + name + ' (' + kb(bytes) + ')', 'warn');
        return null;
      }
      say(msg, 'zip 준비 중… (' + kb(bytes) + ')');
      return fetch(path).then(function (r) {
        if (!r.ok) throw { code: 'fetch', message: 'HTTP ' + r.status };
        return r.text();
      }).then(function (txt) {
        return dl.save({ filename: name, data: b64ToBlob(txt) });
      }).then(function () {
        say(msg, '저장했습니다: ' + name, 'ok');
      });
    }).catch(function (e) {
      var c = (e && e.code) || '';
      var t = {
        declined: '저장을 취소했습니다.',
        rate_limited: '저장 창이 이미 열려 있습니다. 잠시 뒤 다시 누르세요.',
        too_large: '파일이 커서 이 화면에서는 저장할 수 없습니다.',
        rejected_extension: '이 화면에서는 zip 저장이 막혀 있습니다.',
        extension_not_enabled: '이 화면에서는 zip 저장이 막혀 있습니다.',
        fetch: '파일을 불러오지 못했습니다 (' + ((e && e.message) || '') + ').'
      }[c] || ('저장하지 못했습니다' + (c ? ' (' + c + ')' : '') + '. 파일: ' + name);
      say(msg, t, 'warn');
    }).then(function () { busy = false; btn.disabled = false; });
  }

  // ---- filters + search
  var chips = [].slice.call(sec.querySelectorAll('.partdwg-chips button'));
  var q = sec.querySelector('#partdwg-q');
  var cards = [].slice.call(sec.querySelectorAll('.partdwg-card'));
  var grids = [].slice.call(sec.querySelectorAll('.partdwg-grid'));
  var count = sec.querySelector('#partdwg-count');
  var empty = sec.querySelector('.partdwg-empty');
  var group = 'all';
  function apply() {
    var words = ((q && q.value) || '').toLowerCase().trim().split(/\s+/).filter(Boolean);
    var n = 0;
    cards.forEach(function (c) {
      var hay = c.getAttribute('data-q') || '';
      var ok = (group === 'all' || c.getAttribute('data-g') === group) &&
        words.every(function (w) { return hay.indexOf(w) >= 0; });
      c.hidden = !ok;
      if (ok) n++;
    });
    grids.forEach(function (g) {
      var any = !!g.querySelector('.partdwg-card:not([hidden])');
      g.hidden = !any;
      var h = sec.querySelector('.partdwg-gh[data-g="' + g.getAttribute('data-g') + '"]');
      if (h) h.hidden = !any;
    });
    if (count) count.textContent = n + '장 보임';
    if (empty) empty.hidden = n > 0;
  }
  chips.forEach(function (b) {
    b.addEventListener('click', function () {
      group = b.getAttribute('data-g');
      chips.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      apply();
    });
  });
  if (q) q.addEventListener('input', apply);

  // ---- viewer
  var viewer = sec.querySelector('#partdwg-viewer');
  var vimg = sec.querySelector('#partdwg-vimg');
  var vbody = sec.querySelector('#partdwg-vbody');
  var vtitle = sec.querySelector('#partdwg-vtitle');
  var vopen = sec.querySelector('#partdwg-vopen');
  var zoomBtns = [].slice.call(sec.querySelectorAll('.partdwg-zoom button'));
  var current = null, lastFocus = null;
  function setZoom(z) {
    vbody.classList.remove('z2', 'z4');
    if (z !== '1') vbody.classList.add('z' + z);
    zoomBtns.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-z') === z ? 'true' : 'false'); });
  }
  function show(card) {
    if (!card) return;
    current = card;
    var svg = card.getAttribute('data-svg');
    vimg.src = svg;
    vimg.alt = card.getAttribute('data-code') + ' ' + card.getAttribute('data-name') + ' 부품도';
    vtitle.textContent = card.getAttribute('data-code') + ' · ' + card.getAttribute('data-name');
    vopen.href = svg;
  }
  function openViewer(card) {
    if (!card) return;
    lastFocus = document.activeElement;
    show(card);
    setZoom('1');
    viewer.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    var c = viewer.querySelector('.partdwg-vclose');
    if (c) c.focus();
  }
  function closeViewer() {
    viewer.hidden = true;
    document.documentElement.style.overflow = '';
    vimg.removeAttribute('src');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function step(d) {
    var vis = cards.filter(function (c) { return !c.hidden; });
    var i = vis.indexOf(current);
    if (i < 0 || !vis.length) return;
    show(vis[(i + d + vis.length) % vis.length]);
  }
  zoomBtns.forEach(function (b) { b.addEventListener('click', function () { setZoom(b.getAttribute('data-z')); }); });
  viewer.addEventListener('click', function (e) {
    var b = e.target.closest('[data-v]');
    if (!b) return;
    var v = b.getAttribute('data-v');
    if (v === 'close') closeViewer();
    else if (v === 'prev') step(-1);
    else if (v === 'next') step(1);
  });
  document.addEventListener('keydown', function (e) {
    if (viewer.hidden) return;
    if (e.key === 'Escape') { e.preventDefault(); closeViewer(); }
    else if (e.key === 'ArrowRight' && !(e.target.closest && e.target.closest('input'))) step(1);
    else if (e.key === 'ArrowLeft' && !(e.target.closest && e.target.closest('input'))) step(-1);
    else if (e.key === 'Tab') {
      var f = [].slice.call(viewer.querySelectorAll('button,a[href]'));
      if (!f.length) return;
      var first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  // close the viewer when the tab is left (hash change hides the section)
  new MutationObserver(function () { if (sec.hidden && !viewer.hidden) closeViewer(); })
    .observe(sec, { attributes: true, attributeFilter: ['hidden'] });

  // ---- card actions (event delegation)
  sec.addEventListener('click', function (e) {
    var b = e.target.closest('[data-act]');
    if (!b || !sec.contains(b) || viewer.contains(b)) return;
    var act = b.getAttribute('data-act');
    if (act === 'view') {
      openViewer(b.closest('.partdwg-card'));
    } else if (act === 'dl') {
      var host = b.closest('.partdwg-card') || b.closest('.partdwg-all');
      var src = b.hasAttribute('data-zip') ? b : host;
      save(b, src.getAttribute('data-zip'), src.getAttribute('data-zipname'), src.getAttribute('data-zipbytes'),
        host && host.querySelector('.partdwg-msg'));
    }
  });

  T.partdwg = {
    open: function (code) {
      var card = document.getElementById('partdwg-' + code);
      if (!card) return false;
      if (sec.hidden) location.hash = 'partdwg-' + code;
      openViewer(card);
      return true;
    },
    codeOf: function (file) {
      if (!file) return null;
      var f = String(file).replace(/^hardware\/mechanical\/cad\//, '');
      for (var i = 0; i < cards.length; i++) {
        var cf = (cards[i].getAttribute('data-file') || '').replace(/^hardware\/mechanical\/cad\//, '');
        if (cf && cf === f) return cards[i].getAttribute('data-code');
      }
      return null;
    }
  };
})();
