/* 02 설계도 — group chips, deep links into hidden groups, zoom (PNG/SVG swap for D01~D06), SVG save, check table.
   API: window.toccata.dwg.show(groupName) — 'ext' | 'int' | 'ka' | 'rear' | 'ren'. */
(function () {
  var sec = document.getElementById('p-dwg');
  if (!sec) return;
  var KEY = 'toccata.dwg.grp';
  var groups = Array.prototype.slice.call(sec.querySelectorAll('.dwg-grp'));
  var chips = Array.prototype.slice.call(sec.querySelectorAll('.dwg-chips button'));
  var names = groups.map(function (g) { return g.getAttribute('data-grp'); });

  function show(name, keep) {
    if (names.indexOf(name) < 0) name = names[0];
    groups.forEach(function (g) { g.hidden = g.getAttribute('data-grp') !== name; });
    chips.forEach(function (c) { c.setAttribute('aria-pressed', c.getAttribute('data-grp') === name ? 'true' : 'false'); });
    if (!keep) {
      try { localStorage.setItem(KEY, name); } catch (e) { /* storage may be blocked */ }
    }
  }

  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      show(c.getAttribute('data-grp'));
      var g = sec.querySelector('.dwg-grp[data-grp="' + c.getAttribute('data-grp') + '"]');
      if (g && g.getBoundingClientRect().top < 0) g.scrollIntoView({ block: 'start' });
    });
  });

  // a hash that names an element inside a hidden group: open that group, then scroll (the page router only scrolls)
  function fromHash() {
    var raw = '';
    try { raw = decodeURIComponent((location.hash || '').slice(1)); } catch (e) { raw = (location.hash || '').slice(1); }
    if (!raw) return false;
    var el = document.getElementById(raw);
    if (!el || !sec.contains(el)) return false;
    var g = el.closest('.dwg-grp');
    if (g) {
      show(g.getAttribute('data-grp'), true);
      requestAnimationFrame(function () { el.scrollIntoView({ block: 'start' }); settle(el); });
    }
    return true;
  }

  // every sheet <img> carries width/height, so the layout should not move; if an image above the target still loads and
  // shifts it, scroll back to the target - until the viewer scrolls or types, or 10 s pass
  function settle(el) {
    var EV = ['wheel', 'touchstart', 'keydown', 'mousedown'];
    var done = false;
    var at = el.getBoundingClientRect().top;
    function stop() {
      done = true;
      EV.forEach(function (n) { window.removeEventListener(n, stop, true); });
    }
    EV.forEach(function (n) { window.addEventListener(n, stop, { capture: true, passive: true }); });
    setTimeout(stop, 10000);
    Array.prototype.forEach.call(sec.querySelectorAll('img'), function (im) {
      if (im.complete || !(im.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)) return;
      im.addEventListener('load', function () {
        if (!done && Math.abs(el.getBoundingClientRect().top - at) > 4) el.scrollIntoView({ block: 'start' });
      }, { once: true });
    });
  }
  window.addEventListener('hashchange', fromHash);

  var start = names[0];
  try { var s = localStorage.getItem(KEY); if (s && names.indexOf(s) >= 0) start = s; } catch (e) { /* ignore */ }
  show(start, true);
  fromHash();

  // zoom: 맞춤 / 2배 / 3배 on the sheet (classes are idempotent with the page-wide handler); D01~D06 swap PNG -> SVG at 3배
  sec.addEventListener('click', function (e) {
    var b = e.target.closest('.zbar button');
    if (!b || !sec.contains(b)) return;
    var f = b.closest('.csheet');
    if (!f) return;
    var z = b.getAttribute('data-z');
    f.classList.remove('z2', 'z3');
    if (z !== '1') f.classList.add('z' + z);
    f.querySelectorAll('.zbar button[data-z]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
    var img = f.querySelector('.dwimg img');
    if (img && img.getAttribute('data-png') && img.getAttribute('data-svg')) {
      var want = z === '3' ? img.getAttribute('data-svg') : img.getAttribute('data-png');
      if (img.getAttribute('src') !== want) img.setAttribute('src', want);
    }
  });

  // save one sheet as .svg through the viewer's downloads capability
  var dlPromise = null;
  function downloads() {
    if (!dlPromise) {
      dlPromise = (window.claude && typeof window.claude.use === 'function')
        ? Promise.resolve().then(function () { return window.claude.use('downloads'); }).catch(function () { return null; })
        : Promise.resolve(null);
    }
    return dlPromise;
  }
  sec.addEventListener('click', function (e) {
    var b = e.target.closest('.dwg-save');
    if (!b || !sec.contains(b)) return;
    var file = b.getAttribute('data-file');
    var name = file.split('/').pop();
    var msg = b.parentNode.querySelector('.dwg-msg');
    function say(t) { if (msg) msg.textContent = t; }
    b.disabled = true;
    downloads().then(function (dl) {
      if (!dl || typeof dl.save !== 'function') {
        say(name + ' (' + b.getAttribute('data-size') + ' KB) — 이 화면에서는 저장할 수 없습니다. "크게 보기"로 열어 저장합니다.');
        return null;
      }
      say('저장 준비 중…');
      return fetch(file).then(function (r) {
        if (!r.ok) throw { code: 'fetch ' + r.status };
        return r.blob();
      }).then(function (blob) {
        return dl.save({ filename: name, data: new Blob([blob], { type: 'image/svg+xml' }) });
      }).then(function () {
        say('저장했습니다: ' + name);
      });
    }).catch(function (err) {
      var c = (err && (err.code || err.name)) || '';
      if (/declin|cancel|abort/i.test(String(c))) say('저장을 취소했습니다.');
      else say('저장하지 못했습니다 (' + (c || '알 수 없는 오류') + ').');
    }).then(function () { b.disabled = false; });
  });

  // number check table: fetched the first time the details opens
  var chk = sec.querySelector('#dwg-checks');
  if (chk) {
    chk.addEventListener('toggle', function () {
      if (!chk.open || chk.getAttribute('data-loaded')) return;
      chk.setAttribute('data-loaded', '1');
      var body = chk.querySelector('.dwg-chkbody');
      fetch('fin/dwg/checks.json').then(function (r) { return r.json(); }).then(function (d) {
        var rows = (d.checks || []).map(function (c) {
          var tr = document.createElement('tr');
          [c.sheet, c.label, fmt(c.printed), fmt(c.ref), c.src].forEach(function (v) {
            var td = document.createElement('td');
            td.textContent = v;
            tr.appendChild(td);
          });
          var td = document.createElement('td');
          td.className = c.ok ? 'ok' : 'bad';
          td.textContent = c.ok ? '일치' : '다름';
          tr.appendChild(td);
          return tr;
        });
        body.textContent = '';
        rows.forEach(function (tr) { body.appendChild(tr); });
      }).catch(function () {
        body.innerHTML = '<tr><td colspan="6">checks.json을 불러오지 못했습니다.</td></tr>';
      });
    });
  }
  function fmt(v) { return (Math.round(v * 100) / 100).toString(); }

  window.toccata = window.toccata || {};
  window.toccata.dwg = { show: function (n) { show(n); } };
})();
