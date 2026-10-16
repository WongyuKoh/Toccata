/* 06 부품·사용처 (#p-parts): every final item / print file / plywood piece with where it goes, drawn from the CAD.
   Data (fetched when the tab is first opened):
     fin/loc/cards.json     card text (built by src/tabs/parts/build_section.py from data/final_items.json + fin/loc/overlays.json)
     fin/loc/overlays.json  CAD locations (hardware/mechanical/cad/src/locate.py): frames {plan, side, front} with viewBox + base SVG,
                            entries[key] = {frames: {f: {d, pts, bb, small}}, host_frames, ids, vis, rep, xrule, detail, ...}
   The card anchors (id parts-<key>) are in the HTML so deep links work; this script fills them and draws each location figure
   (base SVG as <img> + an inline overlay <svg> with the same viewBox) only when the card scrolls into view.
   API: window.toccata.parts = { ready: Promise, show(key) }   e.g. show('i014'), show('p-KEY-C'), show('ply-pod-side')
   Uses (if present): window.toccata.cad.focus(ids, name) for '3D에서 보기', window.toccata.prep.line(id) / onChange(cb) for status. */
(function () {
  'use strict';
  var sec = document.getElementById('p-parts');
  if (!sec) return;
  var T = window.toccata = window.toccata || {};
  var FN = { plan: '위', side: '옆', front: '앞' };
  var data = null, ov = null, started = false, ovWaiters = [];
  var cards = {}, order = [];
  var st = { mode: 'item', src: '', cat: '', fold: '', q: '' };
  var resolveReady;
  var ready = new Promise(function (r) { resolveReady = r; });
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  T.parts = {
    ready: ready,
    show: function (key) { location.hash = '#parts-' + key; }
  };

  var $ = function (s, el) { return (el || sec).querySelector(s); };
  var $$ = function (s, el) { return Array.prototype.slice.call((el || sec).querySelectorAll(s)); };
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function status(t, warn) {
    var el = $('#parts-status');
    if (!el) return;
    el.textContent = t || '';
    el.classList.toggle('warn', !!warn);
  }
  function getJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }
  function idExists(id) { return !!document.getElementById(id); }

  // ------------------------------------------------------------------ start (first open)
  function start() {
    if (started) return;
    started = true;
    status('부품 목록을 불러오는 중…');
    getJSON('fin/loc/cards.json').then(function (d) {
      data = d;
      d.cards.forEach(function (c) { cards[c.key] = c; order.push(c.key); });
      render();
      wire();
      applyFilter();
      status('');
      resolveReady();
      prepHook();
      jumpToHash(true);
    }).catch(function (e) {
      status('부품 목록(fin/loc/cards.json)을 불러오지 못했습니다: ' + (e && e.message ? e.message : e) + '. 페이지를 새로 고쳐 보세요.', true);
    });
    getJSON('fin/loc/overlays.json').then(function (d) {
      ov = d;
      var w = ovWaiters; ovWaiters = [];
      w.forEach(function (f) { try { f(); } catch (e) { /* keep going */ } });
    }).catch(function (e) {
      ov = { frames: {}, entries: {}, failed: true };
      status('위치 그림 자료(fin/loc/overlays.json)를 불러오지 못했습니다: ' + (e && e.message ? e.message : e), true);
      var w = ovWaiters; ovWaiters = [];
      w.forEach(function (f) { try { f(); } catch (er) { /* */ } });
    });
  }
  function withOv(f) { if (ov) f(); else ovWaiters.push(f); }
  new MutationObserver(function () { if (!sec.hidden) start(); }).observe(sec, { attributes: true, attributeFilter: ['hidden'] });
  if (!sec.hidden) start();

  // ------------------------------------------------------------------ card HTML
  function srcChip(c) {
    if (c.g === 'print') return '<span class="pc-chip src-print">출력</span>';
    if (c.g === 'plywood') return '<span class="pc-chip src-ply">합판</span>';
    return '<span class="pc-chip src-' + esc(c.src) + '" title="' + esc(data.src_long[c.src] || '') + '">' + esc(data.src_ko[c.src] || c.src) + '</span>';
  }
  function figHTML(c) {
    if (!c.fr || !c.fr.length) return '';
    var first = c.fr[0];
    var b = c.fr.map(function (f) {
      return '<button type="button" data-f="' + f + '" aria-pressed="' + (f === first) + '">' + FN[f] + '</button>';
    }).join('');
    var vb = data.frames[first].vb;
    return '<figure class="pc-loc"><div class="pc-locbar"><div class="seg pc-seg" role="group" aria-label="보는 방향">' + b + '</div>' +
      '<button type="button" class="pc-zoom" aria-pressed="false">크게</button></div>' +
      '<div class="pc-sheet"><div class="pc-stagewrap"><div class="pc-stage" data-f="' + first + '" role="img" aria-label="' + esc(c.name) +
      ' 위치 그림 (' + FN[first] + ')" style="--ar:' + vb[2] + '/' + vb[3] + '"></div></div>' +
      '<figcaption><span class="pc-fcap"></span><span class="pc-legend"><span><i class="lg-hit"></i>이 물건</span>' +
      '<span class="pc-lg-host" hidden><i class="lg-host"></i>붙는 자리</span></span></figcaption></div></figure>';
  }
  function detHTML(c) {
    if (!c.det) return '';
    return '<details class="pc-det"><summary>확대 그림 — ① 위에서 ② 단면 · 좌표·크기 (mm)</summary>' +
      '<div class="pc-detimg"><img data-src="' + esc(c.det) + '" alt="' + esc(c.name) + '의 대표 자리를 위에서 본 그림과 단면" decoding="async"></div>' +
      '<p class="small muted pc-detcap"><button type="button" class="pc-zoom pc-detz" aria-pressed="false">2배로 보기</button> 대표 자리: ' + esc(c.rep || '') +
      ' · 빨강 = 이 물건, 주황 = 붙는 자리. 좌표는 x 가로 · y 앞에서 뒤로 · z 책상에서 위로 (mm).</p></details>';
  }
  function actHTML(c) {
    var a = [];
    if (c.fr && c.fr.length) a.push('<button type="button" class="pc-btn" data-act="3d">3D에서 보기</button>');
    (c.pd || []).forEach(function (code) {
      var href = idExists('partdwg-' + code) ? '#partdwg-' + code : '#partdwg';
      a.push('<a class="pc-link" href="' + esc(href) + '">부품 도면 ' + esc(code) + '</a>');
    });
    (c.sch || []).forEach(function (s) {
      a.push('<a class="pc-link" href="' + esc(schHref(s, c.cat)) + '">회로도 ' + esc(s) + '</a>');
    });
    var pl = prepIds(c);
    if (pl.length && idExists('p-prep')) a.push('<a class="pc-link" href="#prep-r-' + esc(pl[0]) + '">준비 체크</a>');
    if (c.store) a.push('<a class="pc-link" href="' + esc(c.store) + '" target="_blank" rel="noopener noreferrer">판매처 ↗</a>');
    if (!a.length) return '';
    return '<div class="pc-act">' + a.join('') + '<span class="pc-msg small" role="status" aria-live="polite"></span></div>';
  }
  // 01 tab anchors: circuit-sch-01..07; SCH-06 is split into circuit-sch-06-pwr (power) and circuit-sch-06-ts (touchscreen).
  function schHref(s, cat) {
    var n = (s.match(/\d+/) || [''])[0];
    var pre = 'circuit-sch-' + n;
    var cands = cat === '터치스크린' ? [pre + '-ts', pre, pre + '-pwr'] : [pre, pre + '-pwr', pre + '-ts'];
    cands = cands.concat(['sch-' + n, 'sch-' + n + '-pwr', 'circuit-' + s.toLowerCase(), 'sch' + parseInt(n, 10)]);
    for (var i = 0; i < cands.length; i++) if (idExists(cands[i])) return '#' + cands[i];
    return '#circuit';
  }
  function cardHTML(c) {
    var h = [];
    if (c.g === 'item') {
      var img = c.img ? '<img src="' + esc(c.img) + '" alt="' + esc(c.name) + ' 사진" loading="lazy" decoding="async" width="96" height="96">'
        : '<span class="pc-noimg">사진 없음</span>';
      h.push('<div class="pc-top"><div class="pc-ph">' + img + '</div><div class="pc-hd"><div class="pc-meta">' + srcChip(c) +
        '<span class="mono pc-code">' + esc(c.key) + (c.code ? ' · ' + esc(c.code) : '') + '</span><span class="pc-cat">' + esc(c.cat) + ' · ' + esc(c.role) +
        (c.opt ? ' · 준비율에서 뺌' : '') + '</span></div><h4 class="pc-name">' + esc(c.name) + '</h4>' +
        (c.full ? '<p class="pc-full">' + esc(c.full) + '</p>' : '') +
        '<p class="pc-qty"><b class="num">' + esc(c.qty) + '</b>' + esc(c.unit) + ' 필요' + (c.pack ? '<span class="pc-pack"> · ' + esc(c.pack) + '</span>' : '') + '</p>' +
        (c.ord ? '<p class="pc-ord small">' + esc(c.ord) + '</p>' : '') +
        '<p class="pc-prep small" hidden></p></div></div>');
      h.push('<p class="pc-where"><b>쓰는 곳</b>' + esc(c.where) + '</p>');
      if (c.wnote) h.push('<p class="pc-wn small"><b>그림의 자리</b>' + esc(c.wnote) + '</p>');
      (c.issues || []).forEach(function (x) {
        h.push('<p class="pc-issue small' + (x[0] === '높음' ? ' hi' : '') + '"><b>' + (x[0] === '높음' ? '빠진 것' : '확인') + '</b> ' + esc(x[1]) + '</p>');
      });
    } else {
      var meta = c.g === 'print'
        ? '<span class="mono pc-code">' + esc((c.file || '').split('/').pop()) + '</span><span class="pc-cat">' + esc((data.fold_ko || {})[c.fold] || c.fold || '') + '</span>'
        : '<span class="mono pc-code">' + esc(c.ids || '') + '</span><span class="pc-cat">오꾸메 11.5T 한 장 (i096)에서</span>';
      var q = c.g === 'print'
        ? '<b class="num">' + esc(c.qty) + '</b>개 출력 · ' + esc(c.mat) + ' · ' + esc(c.size) + ' mm' + (c.mass ? ' · 속 꽉 채움 ' + esc(c.mass) + ' g' : '')
        : '<b class="num">' + esc(c.qty) + '</b>조각 · ' + esc(c.size) + ' mm';
      h.push('<div class="pc-hd"><div class="pc-meta">' + srcChip(c) + meta + '</div><h4 class="pc-name">' + esc(c.name) + '</h4>' +
        '<p class="pc-qty">' + q + '</p><p class="pc-prep small" hidden></p></div>');
      h.push('<p class="pc-where"><b>들어가는 곳</b>' + esc(c.where) + '</p>');
    }
    if (c.fr && c.fr.length) {
      h.push(figHTML(c));
      if (c.cnt) h.push('<p class="pc-cnt small">' + esc(c.cnt) + '</p>');
      h.push(detHTML(c));
    } else if (c.nofig) {
      h.push('<p class="pc-nofig small muted">' + esc(c.nofig) + '</p>');
    }
    h.push(actHTML(c));
    if (c.specs && c.specs.length) h.push('<details class="spec pc-spec"><summary>' + (c.g === 'item' ? '사양·확인' : '파일·메모') + '</summary></details>');
    return h.join('');
  }
  function specTable(c) {
    return '<div class="tbl"><table><tbody>' + c.specs.map(function (r) {
      return '<tr><td>' + esc(r[0]) + '</td><td>' + esc(r[1]) + '</td></tr>';
    }).join('') + '</tbody></table></div>';
  }

  var io = null;
  function render() {
    io = ('IntersectionObserver' in window) ? new IntersectionObserver(onSee, { rootMargin: '300px 0px' }) : null;
    order.forEach(function (k) {
      var el = document.getElementById('parts-' + k);
      if (!el) return;
      var c = cards[k];
      el.innerHTML = cardHTML(c);
      el.classList.remove('pc-wait');
      el.setAttribute('tabindex', '-1');
      el.setAttribute('aria-label', c.name);
      c.el = el;
      c.q = [c.key, c.code, c.name, c.full, c.where, c.wnote, c.cat, c.src && data.src_ko[c.src], c.ord, c.file, c.ids, c.rep, (c.pd || []).join(' ')]
        .join(' ').toLowerCase();
      var stg = el.querySelector('.pc-stage');
      if (stg) { if (io) io.observe(stg); else drawStage(stg, k); }
    });
  }
  function onSee(entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      io.unobserve(en.target);
      var el = en.target.closest('.pc');
      if (el) drawStage(en.target, el.getAttribute('data-k'));
    });
  }

  // ------------------------------------------------------------------ location figure
  function drawStage(stage, key) {
    stage.setAttribute('data-want', '1');
    withOv(function () { paint(stage, key); });
  }
  function paint(stage, key) {
    var f = stage.getAttribute('data-f');
    var F = ov.frames[f], E = ov.entries[key];
    var fig = stage.closest('.pc-loc');
    var cap = fig && fig.querySelector('.pc-fcap');
    if (!F || !E) {
      stage.innerHTML = '<div class="pc-empty">위치 자료를 불러오지 못했습니다.</div>';
      return;
    }
    var vb = F.vb;
    stage.style.setProperty('--ar', vb[2] + '/' + vb[3]);
    var hit = E.frames && E.frames[f], host = E.host_frames && E.host_frames[f];
    var svg = [];
    if (host && host.d) svg.push('<path class="ov-host" fill-rule="evenodd" d="' + host.d + '"/>');
    if (hit && hit.d) svg.push('<path class="ov-hit" fill-rule="evenodd" d="' + hit.d + '"/>');
    var marks = (hit && hit.pts && hit.pts.length && hit.small) ? hit.pts : (!hit && host && host.small && host.pts ? host.pts : null);
    if (marks) {
      marks.forEach(function (p) { svg.push('<circle class="ov-ring" cx="' + p[0] + '" cy="' + p[1] + '" r="1"/>'); });
    }
    stage.innerHTML = '<img src="' + esc(F.src) + '" alt="" decoding="async">' +
      '<svg class="pc-ov" viewBox="' + vb.join(' ') + '" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">' + svg.join('') + '</svg>' +
      (!hit && !host ? '<div class="pc-empty">이 방향 그림 안에는 자리가 없습니다' + (E.offdesk ? ' (악기 밖, 바닥에 두는 부품)' : '') + '.</div>' : '');
    ringSize(stage);
    var t = '<b>' + esc(F.look) + '</b> · ' + esc(F.cut);
    if (f === 'plan' && E.removed_in_plan) t += ' · 이 부품은 바탕에서 뗀 자리에 겹쳐 그림';
    else if (f === 'plan' && E.vis != null && E.vis < 0.25) t += ' · 위에서는 가려져 안 보이는 자리 (겹쳐 그림)';
    if (f !== 'plan') t += ' · 빨강 = 이 물건을 그 방향으로 투영한 모양';
    if (E.offdesk) t += ' · 이 물건은 악기 밖(바닥)에 두고, 주황은 선을 꽂는 자리입니다';
    if (cap) cap.innerHTML = t;
    var lgh = fig && fig.querySelector('.pc-lg-host');
    if (lgh) lgh.hidden = !host;
    stage.setAttribute('aria-label', (cards[key] ? cards[key].name : key) + ' 위치 그림 (' + FN[f] + ', ' + F.look + ')');
  }
  function ringSize(stage) {
    var svg = stage.querySelector('svg.pc-ov');
    if (!svg) return;
    var rings = svg.querySelectorAll('circle.ov-ring');
    if (!rings.length) return;
    var vb = svg.viewBox && svg.viewBox.baseVal;
    var w = stage.clientWidth || 600, h = stage.clientHeight || 200;
    var k = vb ? Math.max(vb.width / w, vb.height / h) : 2;
    var r = (6 * k).toFixed(2);
    for (var i = 0; i < rings.length; i++) rings[i].setAttribute('r', r);
  }
  var rsT = null;
  window.addEventListener('resize', function () {
    clearTimeout(rsT);
    rsT = setTimeout(function () { $$('.pc-stage[data-want]').forEach(ringSize); }, 150);
  });

  // ------------------------------------------------------------------ events
  function wire() {
    sec.addEventListener('click', function (ev) {
      var b = ev.target.closest('button');
      if (!b || !sec.contains(b)) return;
      var card = b.closest('.pc');
      if (b.closest('.pc-seg') && card) {
        var f = b.getAttribute('data-f');
        $$('.pc-seg button', card).forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        var stg = card.querySelector('.pc-stage');
        stg.setAttribute('data-f', f);
        drawStage(stg, card.getAttribute('data-k'));
        return;
      }
      if (b.classList.contains('pc-zoom') && card) {
        var on = b.getAttribute('aria-pressed') !== 'true';
        b.setAttribute('aria-pressed', String(on));
        b.textContent = on ? '작게' : '크게';
        b.closest('.pc-loc').classList.toggle('pc-zoomed', on);
        var s2 = card.querySelector('.pc-stage');
        if (s2) requestAnimationFrame(function () { ringSize(s2); });
        return;
      }
      if (b.getAttribute('data-act') === '3d' && card) { focus3d(card); return; }
      if (b.classList.contains('pc-detz') && card) {
        var box = b.closest('.pc-det').querySelector('.pc-detimg');
        var z = b.getAttribute('aria-pressed') !== 'true';
        b.setAttribute('aria-pressed', String(z));
        b.textContent = z ? '원래 크기' : '2배로 보기';
        if (box) box.classList.toggle('pc-z2', z);
        return;
      }
      if (b.closest('.parts-mode')) { setMode(b.getAttribute('data-m')); return; }
      if (b.closest('.parts-srcs')) {
        st.src = b.getAttribute('data-src') || '';
        $$('.parts-srcs button').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
        applyFilter();
      }
    });
    sec.addEventListener('toggle', function (ev) {
      var d = ev.target;
      if (!d || !d.open || d.tagName !== 'DETAILS') return;
      if (d.classList.contains('pc-det')) {
        var img = d.querySelector('img[data-src]');
        if (img && !img.getAttribute('src')) {
          img.addEventListener('error', function () {
            var p = document.createElement('p');
            p.className = 'small muted';
            p.textContent = '확대 그림을 불러오지 못했습니다: ' + img.getAttribute('data-src');
            img.replaceWith(p);
          }, { once: true });
          img.setAttribute('src', img.getAttribute('data-src'));
        }
      } else if (d.classList.contains('pc-spec') && !d.getAttribute('data-done')) {
        var card = d.closest('.pc');
        var c = card && cards[card.getAttribute('data-k')];
        if (c) d.insertAdjacentHTML('beforeend', specTable(c));
        d.setAttribute('data-done', '1');
      }
    }, true);
    var cat = $('#parts-cat'), fold = $('#parts-fold'), q = $('#parts-q');
    if (cat) cat.addEventListener('change', function () { st.cat = cat.value; applyFilter(); });
    if (fold) fold.addEventListener('change', function () { st.fold = fold.value; applyFilter(); });
    var qt = null;
    if (q) q.addEventListener('input', function () {
      clearTimeout(qt);
      qt = setTimeout(function () { st.q = q.value.trim().toLowerCase(); applyFilter(); }, 120);
    });
    window.addEventListener('hashchange', function () { jumpToHash(false); });
  }
  function setMode(m) {
    st.mode = m;
    $$('.parts-mode button').forEach(function (x) { x.setAttribute('aria-pressed', String(x.getAttribute('data-m') === m)); });
    var srcs = $('.parts-srcs'), cat = $('#parts-cat'), fold = $('#parts-fold');
    if (srcs) srcs.hidden = m !== 'item';
    if (cat) cat.closest('label').hidden = m !== 'item';
    if (fold) fold.closest('label').hidden = m !== 'print';
    applyFilter();
  }
  function applyFilter() {
    if (!data) return;
    var n = 0, tot = 0;
    var words = st.q ? st.q.split(/\s+/).filter(Boolean) : [];
    order.forEach(function (k) {
      var c = cards[k];
      if (!c.el) return;
      var show = c.g === st.mode;
      if (show) tot++;
      if (show && st.mode === 'item') {
        if (st.src && c.src !== st.src) show = false;
        if (st.cat && c.cat !== st.cat) show = false;
      }
      if (show && st.mode === 'print' && st.fold && c.fold !== st.fold) show = false;
      if (show && words.length) for (var i = 0; i < words.length; i++) if (c.q.indexOf(words[i]) < 0) { show = false; break; }
      c.el.hidden = !show;
      if (show) n++;
    });
    var out = $('#parts-count');
    var unit = st.mode === 'plywood' ? '가지' : (st.mode === 'print' ? '파일' : '줄');
    if (out) out.textContent = (n === tot ? tot + unit : tot + unit + ' 중 ' + n + unit);
    var em = $('#parts-empty');
    if (em) em.hidden = n > 0;
  }

  // ------------------------------------------------------------------ deep links
  function jumpToHash(first) {
    var h = decodeURIComponent((location.hash || '').slice(1));
    if (!/^parts-/.test(h)) return;
    var key = h.slice(6);
    var c = cards[key];
    if (!c || !c.el) return;
    if (c.el.hidden || c.g !== st.mode) {
      st.src = ''; st.cat = ''; st.fold = ''; st.q = '';
      var q = $('#parts-q'); if (q) q.value = '';
      var cat = $('#parts-cat'); if (cat) cat.value = '';
      var fold = $('#parts-fold'); if (fold) fold.value = '';
      $$('.parts-srcs button').forEach(function (x) { x.setAttribute('aria-pressed', String(!x.getAttribute('data-src'))); });
      setMode(c.g);
    }
    $$('.pc.pc-target').forEach(function (x) { x.classList.remove('pc-target'); });
    c.el.classList.add('pc-target');
    requestAnimationFrame(function () {
      c.el.scrollIntoView({ block: 'start', behavior: (first || reduce) ? 'auto' : 'smooth' });
      try { c.el.focus({ preventScroll: true }); } catch (e) { /* old browsers */ }
    });
  }

  // ------------------------------------------------------------------ 3D tab
  function focus3d(card) {
    var key = card.getAttribute('data-k');
    var c = cards[key];
    var msg = card.querySelector('.pc-msg');
    var say = function (t, w) { if (msg) { msg.textContent = t; msg.classList.toggle('warn', !!w); } };
    withOv(function () {
      var E = ov.entries[key] || {};
      var ids = (E.ids && E.ids.length ? E.ids : (E.host_ids || [])).slice();
      if (!ids.length) { say('3D 모델에 이 물건의 부품이 없습니다.', true); return; }
      if (!document.getElementById('p-cad')) { say('3D 모델 탭이 이 페이지에 없습니다.', true); return; }
      say('3D 모델 탭에서 ' + ids.length + '곳을 보여 줍니다…');
      location.hash = '#cad';
      var t0 = Date.now();
      (function tryFocus() {
        var api = T.cad;
        if (api && typeof api.focus === 'function') {
          try { api.focus(ids, c ? c.name : key); say(''); } catch (e) { say('3D 탭에서 부품을 고르지 못했습니다: ' + (e && e.message ? e.message : e), true); }
          return;
        }
        if (Date.now() - t0 < 8000) setTimeout(tryFocus, 200);
        else say('3D 모델 탭이 아직 준비되지 않았습니다. 3D 탭을 연 뒤 다시 눌러 보세요.', true);
      })();
    });
  }

  // ------------------------------------------------------------------ prep status (07 준비 체크)
  var prepHooked = false, prepTries = 0;
  function prepHook() {
    var P = T.prep;
    if (!P || typeof P.line !== 'function') {
      if (prepTries++ < 6) setTimeout(prepHook, 1500);
      return;
    }
    if (!prepHooked && typeof P.onChange === 'function') {
      prepHooked = true;
      try { P.onChange(prepUpdate); } catch (e) { /* */ }
    }
    prepUpdate();
  }
  /* c.prep is one 07 line id, or a list when the card covers several lines (plywood L + R pieces) */
  function prepIds(c) {
    if (!c || !c.prep) return [];
    return Array.isArray(c.prep) ? c.prep : [c.prep];
  }
  function prepUpdate() {
    var P = T.prep;
    if (!P || typeof P.line !== 'function') return;
    order.forEach(function (k) {
      var c = cards[k];
      var ids = prepIds(c);
      if (!c.el || !ids.length) return;
      var el = c.el.querySelector('.pc-prep');
      if (!el) return;
      var need = 0, have = 0, done = true, unit = '', n = 0;
      ids.forEach(function (id) {
        var L = null;
        try { L = P.line(id); } catch (e) { L = null; }
        if (!L) return;
        n++;
        need += +L.need || 0;
        have += +L.ready || 0;
        done = done && !!L.done;
        unit = unit || L.unit || '';
      });
      if (!n) { el.hidden = true; return; }
      done = done && n === ids.length;
      el.hidden = false;
      el.classList.toggle('ok', done);
      el.innerHTML = (done ? '✓ 준비 끝 ' : '준비 ') + '<span class="num">' + esc(have) + ' / ' + esc(need) + '</span>' + esc(unit);
    });
  }
})();
