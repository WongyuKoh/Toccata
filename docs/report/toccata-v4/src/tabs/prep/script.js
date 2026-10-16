/* Toccata page, tab "07 준비 체크" (#p-prep): preparation tracker.
 *
 * Public API (window.toccata.prep):
 *   onChange(cb)  call cb(summary) after every change (counts, toggles, remote updates); returns an unsubscribe function
 *   summary()     {ready, pct, frac, done, total, includeTools, mode, groups:[{id, tag, name, pct, frac, done, total, inMain}]}
 *   line(id)      {id, name, need, unit, ready, done, counted} or null   (ids: a-<item>, b-…, c-…, d-<item>)
 *   lines()       array of all line ids
 * Row element ids: "prep-r-" + line id (deep link #prep-r-a-i014 opens this tab at that row).
 * A compact card is rendered into #sum-prep (summary tab) when that element exists.
 *
 * Storage: artifact db document "prep/state" = {counts:{lineId:n}, include:{lineId:true}, opts:{tools:bool}, updatedAt}.
 * One snapshot subscription; writes are debounced (600 ms), one in flight, changed keys only (update merge).
 * Without db (local preview, signed out) counts live in memory + localStorage, with a banner.
 */
(function () {
  'use strict';
  var W = window;
  var T = (W.toccata = W.toccata || {});
  var DOC_PATH = 'prep/state';
  var LS_KEY = 'toccata.prep.v1';
  var UI_KEY = 'toccata.prep.ui.v1';
  var DATA_URL = 'fin/prep/lines.json';
  var SRC_CHIP = { school: '학교 지원', personal: '사비', owned: '가진 것', gap: '준비처 없음', tool: '가진 공구' };

  /* ------------------------------------------------------------------ pure helpers */
  function emptyState() { return { counts: {}, include: {}, opts: { tools: false } }; }
  function emptyPatch() { return { counts: {}, include: {}, opts: {} }; }
  function keys(o) { return o ? Object.keys(o) : []; }
  function patchEmpty(p) { return !p || (!keys(p.counts).length && !keys(p.include).length && !keys(p.opts).length); }
  function cloneState(s) {
    return { counts: Object.assign({}, s.counts), include: Object.assign({}, s.include), opts: Object.assign({ tools: false }, s.opts) };
  }
  function applyPatch(st, p) {
    if (!p) return st;
    keys(p.counts).forEach(function (k) { st.counts[k] = p.counts[k]; });
    keys(p.include).forEach(function (k) { st.include[k] = p.include[k]; });
    keys(p.opts).forEach(function (k) { st.opts[k] = p.opts[k]; });
    return st;
  }
  function mergeUnder(dst, src) { /* put src keys into dst where dst has no newer value */
    ['counts', 'include', 'opts'].forEach(function (kind) {
      keys(src[kind]).forEach(function (k) { if (!(k in dst[kind])) dst[kind][k] = src[kind][k]; });
    });
  }
  /* Whole-unit lines floor a typed fraction (1.5 of 2 stays 1; never rounds up to done).
   * Length lines (line.dec = 1, unit m) keep one decimal, also floored (1.95 m -> 1.9 m). */
  function clampCount(v, need, dec) {
    var x = Number(v);
    if (!isFinite(x) || x < 0) return 0;
    var n = dec ? Math.floor(x * 10 + 1e-9) / 10 : Math.floor(x);
    if (n > need) n = need;
    return n;
  }
  function fmtQty(x, dec) { return String(dec ? Math.round(x * 10) / 10 : x); }
  function readyOf(line, st) {
    var v = st.counts[line.id];
    return (typeof v === 'number' && isFinite(v)) ? clampCount(v, line.need, line.dec) : 0;
  }
  function isIncluded(line, st) { return !line.opt || st.include[line.id] === true; }
  function isCounted(line, st) { return isIncluded(line, st) && (line.g !== 'tools' || st.opts.tools === true); }
  function agg(lines, st, pred) {
    var sum = 0, n = 0, done = 0;
    for (var i = 0; i < lines.length; i++) {
      var l = lines[i];
      if (!pred(l)) continue;
      var r = readyOf(l, st);
      sum += r / l.need; n++;
      if (r >= l.need) done++;
    }
    return { frac: n ? sum / n : 0, done: done, total: n };
  }
  function pctOf(frac) { return Math.floor(frac * 100 + 1e-9); }
  function summarize(data, st) {
    var all = agg(data.lines, st, function (l) { return isCounted(l, st); });
    var groups = data.groups.map(function (g) {
      var a = agg(data.lines, st, function (l) { return l.g === g.id && isIncluded(l, st); });
      return { id: g.id, tag: g.tag, name: g.name, frac: a.frac, pct: pctOf(a.frac), done: a.done, total: a.total,
        inMain: g.id !== 'tools' || st.opts.tools === true };
    });
    return { frac: all.frac, pct: pctOf(all.frac), done: all.done, total: all.total, includeTools: st.opts.tools === true, groups: groups };
  }
  function normalize(d, byId) {
    var st = emptyState();
    if (!d || typeof d !== 'object') return st;
    var c = d.counts && typeof d.counts === 'object' ? d.counts : {};
    keys(c).forEach(function (k) {
      var v = Number(c[k]);
      if (!isFinite(v)) return;
      var l = byId && byId[k];
      st.counts[k] = l ? clampCount(v, l.need, l.dec) : Math.max(0, Math.floor(v * 10 + 1e-9) / 10);
    });
    var inc = d.include && typeof d.include === 'object' ? d.include : {};
    keys(inc).forEach(function (k) { st.include[k] = inc[k] === true; });
    if (d.opts && typeof d.opts === 'object') st.opts.tools = d.opts.tools === true;
    return st;
  }
  function csvCell(v) {
    var s = v == null ? '' : String(v);
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function csvText(data, st) {
    var gBy = {}, sBy = {};
    data.groups.forEach(function (g) { gBy[g.id] = g; g.subs.forEach(function (s) { sBy[s.id] = s; }); });
    var rows = [['묶음', '소분류', '번호', '이름', '필요', '단위', '준비', '남음', '상태', '준비처·폴더', '메모']];
    data.lines.forEach(function (l) {
      var r = readyOf(l, st);
      var status = !isIncluded(l, st) ? '선택 (계산 안 함)' : r >= l.need ? '다 됨' : r > 0 ? '준비 중' : '아직';
      var g = gBy[l.g] || { tag: '', name: l.g }, s = sBy[l.s] || { name: '' };
      rows.push([g.tag + ' ' + g.name, s.name, l.code || l.file || l.id, l.n, l.need, l.u, fmtQty(r, l.dec), fmtQty(l.need - r, l.dec), status,
        l.src ? (SRC_CHIP[l.src] || l.src) : (l.fold || ''), l.m || '']);
    });
    return '﻿' + rows.map(function (r) { return r.map(csvCell).join(','); }).join('\r\n') + '\r\n';
  }

  /* ------------------------------------------------------------------ data */
  var data = null, byId = {}, subById = {}, groupById = {}, detailsLoaded = false, detailsLoading = null;
  function readInline() {
    var el = document.getElementById('prep-data');
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }
  function indexData(d) {
    data = d; byId = {}; subById = {}; groupById = {};
    d.groups.forEach(function (g) { groupById[g.id] = g; g.subs.forEach(function (s) { subById[s.id] = s; }); });
    d.lines.forEach(function (l) { byId[l.id] = l; });
  }
  function loadDetails() {
    if (detailsLoaded) return Promise.resolve(true);
    if (detailsLoading) return detailsLoading;
    detailsLoading = fetch(DATA_URL, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('http ' + r.status);
      return r.json();
    }).then(function (full) {
      (full.lines || []).forEach(function (fl) { var l = byId[fl.id]; if (l && fl.d) l.d = fl.d; });
      detailsLoaded = true;
      return true;
    }).catch(function () { detailsLoading = null; return false; });
    return detailsLoading;
  }

  /* ------------------------------------------------------------------ API (works before data/DOM) */
  var listeners = [];
  var state = emptyState();
  var store = {
    mode: 'init', reason: '', ref: null, unsub: null, readOnly: false, quota: false,
    snapReady: false, docExists: false, remote: emptyState(), updatedAt: null,
    dirty: emptyPatch(), inflight: null, timer: 0, retries: 0, subRetries: 0, failed: false, lsOk: true
  };
  function publicSummary() {
    if (!data) return { ready: false, pct: 0, frac: 0, done: 0, total: 0, includeTools: false, mode: store.mode, groups: [] };
    var s = summarize(data, state);
    s.ready = store.mode !== 'init';
    s.mode = store.readOnly ? 'readonly' : store.mode;
    return s;
  }
  T.prep = {
    onChange: function (cb) {
      if (typeof cb !== 'function') return function () {};
      listeners.push(cb);
      try { cb(publicSummary()); } catch (e) { /* listener error */ }
      return function () { listeners = listeners.filter(function (f) { return f !== cb; }); };
    },
    summary: publicSummary,
    line: function (id) {
      var l = byId[id];
      if (!l) return null;
      var r = readyOf(l, state);
      return { id: l.id, name: l.n, need: l.need, unit: l.u, ready: r, done: r >= l.need, counted: isCounted(l, state) };
    },
    lines: function () { return data ? data.lines.map(function (l) { return l.id; }) : []; },
    _test: { summarize: summarize, readyOf: readyOf, isCounted: isCounted, isIncluded: isIncluded, clampCount: clampCount, fmtQty: fmtQty,
      normalize: normalize, csvText: csvText, pctOf: pctOf, applyPatch: applyPatch, mergeUnder: mergeUnder }
  };

  if (typeof document === 'undefined' || !document.getElementById) return; /* node test: pure helpers only */
  var section = document.getElementById('p-prep');
  var inline = readInline();
  if (!section || !inline) return;
  indexData(inline);

  /* ------------------------------------------------------------------ small DOM helpers */
  function $(id) { return document.getElementById(id); }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function lsGet(k) { try { var v = W.localStorage.getItem(k); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
  function lsSet(k, v) { try { W.localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function fmtTime(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    return (d.getMonth() + 1) + '월 ' + d.getDate() + '일 ' + p(d.getHours()) + ':' + p(d.getMinutes());
  }
  function ymd() {
    var d = new Date(), p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
  }

  var ui = Object.assign({ f: 'all', g: '', q: '', closed: {} }, lsGet(UI_KEY) || {});
  function saveUi() { lsSet(UI_KEY, ui); }

  /* ------------------------------------------------------------------ rendering */
  var CHECK = '<svg viewBox="0 0 20 20" focusable="false"><circle cx="10" cy="10" r="8.6"/><path d="M5.9 10.3l2.8 2.8 5.5-5.6"/></svg>';
  var rowEls = {};

  function rowHtml(l) {
    var nm = esc(l.n);
    var meta = '';
    if (l.src) meta += '<span class="prep-chip src-' + esc(l.src) + '">' + esc(SRC_CHIP[l.src] || l.src) + '</span>';
    if (l.fold) meta += '<span class="prep-chip prep-fold">' + esc(l.fold) + '</span>';
    if (l.code) meta += '<span class="prep-code">' + esc(l.code) + '</span>';
    if (l.file) meta += '<span class="prep-code">' + esc(l.file) + '</span>';
    if (l.m) meta += '<span class="prep-m">' + esc(l.m) + '</span>';
    var warn = (l.w || []).map(function (w) { return '<p class="prep-warn"><b>확인</b> ' + esc(w) + '</p>'; }).join('');
    var opt = l.opt ? '<label class="prep-opt" for="prep-inc-' + l.id + '"><input type="checkbox" data-act="include" id="prep-inc-' + l.id + '"> 준비율에 넣기 (선택 줄)</label>' : '';
    var img = l.img ? '<img class="prep-thumb" src="' + esc(l.img) + '" alt="" loading="lazy" decoding="async" width="40" height="40">' : '';
    return '<li class="prep-row" id="prep-r-' + l.id + '" data-id="' + l.id + '">' +
      '<span class="prep-chk" aria-hidden="true">' + CHECK + '</span>' +
      '<div class="prep-main"><div class="prep-nm">' + img + '<div class="prep-nmt">' +
      '<span class="prep-name">' + nm + '</span> <span class="prep-state" id="prep-st-' + l.id + '">아직</span>' +
      '<div class="prep-meta">' + meta + '</div>' + warn + opt +
      '<details class="prep-more" data-id="' + l.id + '"><summary>자세히</summary><div class="prep-more-b"></div></details></div></div></div>' +
      '<div class="prep-need"><span class="prep-need-l">필요</span> <b class="num">' + l.need + '</b> ' + esc(l.u) + '</div>' +
      '<div class="prep-ctl" role="group" aria-label="' + nm + ' 준비 수">' +
      '<button type="button" class="prep-btn" data-act="dec" aria-label="' + nm + (l.dec ? ' 1 ' + esc(l.u) + ' 빼기' : ' 하나 빼기') + '">−</button>' +
      '<input class="prep-in num" type="number" inputmode="' + (l.dec ? 'decimal' : 'numeric') + '" min="0" max="' + l.need + '" step="' + (l.dec ? '0.1' : '1') + '" value="0" id="prep-in-' + l.id +
      '" data-act="set" aria-label="' + nm + ' 준비된 수 (필요 ' + l.need + ' ' + esc(l.u) + ')">' +
      '<button type="button" class="prep-btn" data-act="inc" aria-label="' + nm + (l.dec ? ' 1 ' + esc(l.u) + ' 더하기' : ' 하나 더하기') + '">+</button>' +
      '<button type="button" class="prep-btn prep-full" data-act="full" aria-label="' + nm + ' 다 됨으로 표시">다 됨</button>' +
      '</div><i class="prep-rbar" aria-hidden="true"><b></b></i></li>';
  }

  function buildList() {
    var html = '';
    data.groups.forEach(function (g) {
      html += '<section class="prep-g" id="prep-g-' + g.id + '" aria-labelledby="prep-gh-' + g.id + '">' +
        '<h3 id="prep-gh-' + g.id + '"><span class="no">' + esc(g.tag) + '</span>' + esc(g.name) +
        ' <span class="prep-gstat" id="prep-gs-' + g.id + '"></span></h3>' +
        '<p class="prep-gnote small muted">' + esc(g.note || '') + '</p>';
      g.subs.forEach(function (s) {
        var ls = data.lines.filter(function (l) { return l.s === s.id; });
        if (!ls.length) return;
        html += '<details class="prep-sg" id="prep-sg-' + s.id + '" data-sub="' + s.id + '"' + (ui.closed[s.id] ? '' : ' open') + '>' +
          '<summary><span class="prep-sgn">' + esc(s.name) + '</span><span class="prep-sgs num" id="prep-ss-' + s.id + '"></span>' +
          '<i class="prep-mbar" aria-hidden="true"><b id="prep-sb-' + s.id + '"></b></i></summary>' +
          '<ul class="prep-rows">' + ls.map(rowHtml).join('') + '</ul></details>';
      });
      html += '</section>';
    });
    html += '<p class="prep-empty muted" id="prep-empty" hidden>조건에 맞는 줄이 없습니다. 거르기를 바꿔 보세요.</p>';
    var list = $('prep-list');
    list.innerHTML = html;
    rowEls = {};
    data.lines.forEach(function (l) {
      var li = $('prep-r-' + l.id);
      rowEls[l.id] = { li: li, st: $('prep-st-' + l.id), inp: $('prep-in-' + l.id), inc: $('prep-inc-' + l.id),
        bar: li.querySelector('.prep-rbar b'), btns: li.querySelectorAll('.prep-btn') };
    });
    buildGroupCards();
  }

  function buildGroupCards() {
    var box = $('prep-gcards'), mini = $('prep-mini');
    var h = '', m = '';
    data.groups.forEach(function (g) {
      h += '<button type="button" class="prep-gcard" data-g="' + g.id + '" aria-pressed="false" id="prep-gc-' + g.id + '">' +
        '<span class="prep-gc-h"><span class="prep-gc-tag">' + esc(g.tag) + '</span>' + esc(g.name) + '<span class="prep-gc-pct num"></span></span>' +
        '<i class="prep-mbar" aria-hidden="true"><b></b></i><span class="prep-gc-s small muted"></span></button>';
      m += '<span class="prep-mini-i" data-g="' + g.id + '"><span>' + esc(g.tag) + ' ' + esc(g.name) + ' <b class="num"></b></span><i class="prep-mbar"><b></b></i></span>';
    });
    box.innerHTML = h;
    mini.innerHTML = m;
  }

  function canEdit() {
    if (store.readOnly) return false;
    if (store.mode === 'local') return true;
    return store.mode === 'db' && store.snapReady;
  }

  function updateRow(l) {
    var e = rowEls[l.id];
    if (!e) return;
    var r = readyOf(l, state), inc = isIncluded(l, state), edit = canEdit();
    var done = r >= l.need, part = r > 0 && !done;
    e.li.classList.toggle('is-done', done);
    e.li.classList.toggle('is-part', part);
    e.li.classList.toggle('is-excl', !inc);
    e.st.textContent = done ? '다 됨' : part ? fmtQty(l.need - r, l.dec) + ' ' + l.u + ' 남음' : '아직';
    if (document.activeElement !== e.inp || !(l.id in store.dirty.counts)) {
      if (document.activeElement !== e.inp) e.inp.value = fmtQty(r, l.dec);
    }
    e.inp.disabled = !edit;
    e.btns[0].disabled = !edit || r <= 0;
    e.btns[1].disabled = !edit || r >= l.need;
    e.btns[2].disabled = !edit || r >= l.need;
    e.btns[2].setAttribute('aria-pressed', done ? 'true' : 'false');
    if (e.inc) { e.inc.checked = inc; e.inc.disabled = !edit; }
    e.bar.style.width = (r / l.need * 100).toFixed(2) + '%';
  }

  function setBar(el, frac) { if (el) el.style.width = (Math.max(0, Math.min(1, frac)) * 100).toFixed(2) + '%'; }

  function updateHeaders(sum) {
    data.groups.forEach(function (g) {
      var gs = sum.groups.filter(function (x) { return x.id === g.id; })[0];
      var el = $('prep-gs-' + g.id);
      if (el && gs) el.textContent = gs.pct + '% · 다 된 줄 ' + gs.done + ' / ' + gs.total + (g.id === 'tools' && !gs.inMain ? ' · 전체 %에서 뺌' : '');
      g.subs.forEach(function (s) {
        var a = agg(data.lines, state, function (l) { return l.s === s.id && isIncluded(l, state); });
        var ss = $('prep-ss-' + s.id);
        if (!ss) return;
        ss.textContent = a.total ? a.done + ' / ' + a.total : '계산 안 함';
        setBar($('prep-sb-' + s.id), a.frac);
        ss.parentNode.parentNode.classList.toggle('is-done', a.total > 0 && a.done === a.total);
      });
    });
  }

  function updateSummary(sum) {
    $('prep-pct').textContent = sum.pct + '%';
    $('prep-done').textContent = '다 된 줄 ' + sum.done + ' / ' + sum.total + (sum.includeTools ? ' (공구 포함)' : '');
    setBar($('prep-bar'), sum.frac);
    $('prep-sticky').classList.toggle('is-done', sum.total > 0 && sum.done === sum.total);
    sum.groups.forEach(function (g) {
      var card = $('prep-gc-' + g.id);
      if (card) {
        card.querySelector('.prep-gc-pct').textContent = g.pct + '%';
        setBar(card.querySelector('.prep-mbar b'), g.frac);
        card.querySelector('.prep-gc-s').textContent = '다 된 줄 ' + g.done + ' / ' + g.total + (g.id === 'tools' ? (g.inMain ? ' · 전체 %에 넣음' : ' · 전체 %에서 뺌') : '');
        card.classList.toggle('is-done', g.total > 0 && g.done === g.total);
        card.setAttribute('aria-pressed', ui.g === g.id ? 'true' : 'false');
        card.setAttribute('aria-label', g.tag + ' ' + g.name + ' ' + g.pct + '%, 다 된 줄 ' + g.done + ' / ' + g.total + '. 이 묶음만 보기');
      }
      var mi = $('prep-mini').querySelector('[data-g="' + g.id + '"]');
      if (mi) { mi.querySelector('b.num').textContent = g.pct + '%'; setBar(mi.querySelector('.prep-mbar b'), g.frac); mi.classList.toggle('is-off', !g.inMain); }
    });
    var tin = $('prep-tools-in');
    tin.checked = sum.includeTools;
    tin.disabled = !canEdit();
    var sh = $('prep-sticky').offsetHeight;
    if (sh) section.style.setProperty('--prep-sh', sh + 'px');
  }

  function setSave() {
    var el = $('prep-save'), t;
    if (store.mode === 'init') t = '저장소 연결 중';
    else if (store.mode === 'local') t = store.lsOk ? '이 기기에만 저장' : '저장 안 됨 (이 화면에서만)';
    else if (!store.snapReady) t = '불러오는 중';
    else if (store.readOnly) t = '보기 전용';
    else if (store.quota) t = '저장 공간이 가득 참';
    else if (store.inflight || !patchEmpty(store.dirty)) t = store.failed ? '저장 못 함 · 다시 시도 중' : '저장 중…';
    else t = '공유 저장됨' + (store.updatedAt ? ' · ' + fmtTime(store.updatedAt) : '');
    el.textContent = t;
    el.classList.toggle('is-warn', store.mode === 'local' || store.readOnly || store.quota || store.failed);
  }

  function updateBanner() {
    var b = $('prep-banner'), t = '', tone = 'warn';
    if (store.mode === 'local') {
      if (store.reason === 'revoked') t = '공유 저장소 연결이 끊겼습니다. 지금부터 바꾸는 숫자는 이 기기에만 저장되고 다른 사람에게는 보이지 않습니다.';
      else if (store.reason === 'error') t = '공유 저장소를 읽지 못했습니다. 지금은 바꾸는 숫자를 이 기기에만 저장합니다.';
      else t = '이 화면은 공유 저장소에 연결되어 있지 않습니다(미리보기, 로그아웃 등). 준비 수는 이 기기의 브라우저에만 저장되고, 다른 기기나 다른 사람에게는 보이지 않습니다.';
      if (!store.lsOk) t += ' 이 브라우저는 저장도 막혀 있어 페이지를 닫으면 숫자가 사라집니다.';
    } else if (store.readOnly) {
      t = '보기 전용입니다. 이 페이지의 준비 수를 바꿀 권한이 없어 숫자만 볼 수 있습니다.'; tone = 'info';
    } else if (store.quota) {
      t = '저장 공간이 가득 차 마지막 변경을 저장하지 못했습니다. 화면의 숫자는 남아 있지만 다른 사람에게는 보이지 않습니다.';
    }
    b.hidden = !t;
    b.textContent = t;
    b.setAttribute('data-tone', tone);
  }

  /* ------------------------------------------------------------------ summary card for the summary tab */
  var sumCardBuilt = false;
  function renderSumCard(sum) {
    var host = $('sum-prep');
    if (!host) return;
    if (!sumCardBuilt) {
      var bar = function (h) { return '<span style="display:block;height:' + h + 'px;border-radius:' + (h / 2) + 'px;background:var(--rule);overflow:hidden"><i data-bar style="display:block;height:100%;width:0;background:var(--blue)"></i></span>'; };
      var g = data.groups.map(function (x) {
        return '<li data-g="' + x.id + '" style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:2px 10px;font-size:13px;min-width:0">' +
          '<span>' + esc(x.tag + ' ' + x.name) + '</span><span class="num" data-t></span>' +
          '<span style="grid-column:1/-1">' + bar(4) + '</span></li>';
      }).join('');
      host.innerHTML = '<div class="card" style="display:grid;gap:10px;min-width:0">' +
        '<span class="eyebrow">준비 체크</span>' +
        '<div style="display:flex;align-items:baseline;gap:12px;flex-wrap:wrap"><b class="num" data-pct style="font-size:30px;line-height:1">0%</b>' +
        '<span class="small muted" data-done></span></div>' + bar(8) +
        '<ul style="list-style:none;margin:0;padding:0;display:grid;gap:8px">' + g + '</ul>' +
        '<span class="small muted" data-mode></span>' +
        '<a href="#prep" class="small">준비 체크에서 개수 적기</a></div>';
      sumCardBuilt = true;
    }
    var card = host.firstChild;
    card.querySelector('[data-pct]').textContent = sum.pct + '%';
    card.querySelector('[data-done]').textContent = '다 된 줄 ' + sum.done + ' / ' + sum.total + (sum.includeTools ? ' (공구 포함)' : ' (공구 빼고)');
    var bars = card.querySelectorAll('[data-bar]');
    setBar(bars[0], sum.frac);
    sum.groups.forEach(function (gs, i) {
      var li = card.querySelector('li[data-g="' + gs.id + '"]');
      if (!li) return;
      li.querySelector('[data-t]').textContent = gs.pct + '% · ' + gs.done + ' / ' + gs.total;
      setBar(li.querySelector('[data-bar]'), gs.frac);
    });
    card.querySelector('[data-mode]').textContent = store.mode === 'local' ? '이 기기에 저장된 숫자입니다.' : store.mode === 'init' ? '불러오는 중입니다.' : '';
  }

  /* ------------------------------------------------------------------ refresh */
  function refresh(onlyId) {
    if (onlyId && byId[onlyId]) updateRow(byId[onlyId]);
    else data.lines.forEach(updateRow);
    var sum = summarize(data, state);
    updateHeaders(sum);
    updateSummary(sum);
    renderSumCard(sum);
    setSave();
    var pub = publicSummary();
    listeners.slice().forEach(function (cb) { try { cb(pub); } catch (e) { /* ignore listener errors */ } });
  }

  function recompute() {
    var s = cloneState(store.remote);
    applyPatch(s, store.inflight);
    applyPatch(s, store.dirty);
    state = s;
  }

  /* ------------------------------------------------------------------ edits */
  function change(kind, key, val) {
    if (!canEdit()) return;
    if (store.mode === 'local') {
      store.remote[kind][key] = val;
      store.lsOk = lsSet(LS_KEY, { counts: store.remote.counts, include: store.remote.include, opts: store.remote.opts });
    } else {
      store.dirty[kind][key] = val;
      if (store.failed) { store.failed = false; store.retries = 0; }
      schedule(600);
    }
    recompute();
    refresh(kind === 'opts' ? null : key);
    if (kind === 'opts') updateBanner();
  }
  function setCount(id, v) {
    var l = byId[id];
    if (!l) return;
    var n = clampCount(v, l.need, l.dec);
    if (readyOf(l, state) === n && (id in state.counts)) { updateRow(l); return; }
    change('counts', id, n);
  }

  /* ------------------------------------------------------------------ db */
  function schedule(ms) {
    clearTimeout(store.timer);
    store.timer = setTimeout(flush, ms);
    setSave();
  }
  function flush() {
    if (store.mode !== 'db' || store.inflight || !store.snapReady || store.readOnly || store.quota) return;
    if (patchEmpty(store.dirty)) return;
    var patch = store.dirty;
    store.dirty = emptyPatch();
    store.inflight = patch;
    setSave();
    var now = new Date().toISOString(), p;
    try {
      if (store.docExists) {
        var body = { updatedAt: now };
        if (keys(patch.counts).length) body.counts = patch.counts;
        if (keys(patch.include).length) body.include = patch.include;
        if (keys(patch.opts).length) body.opts = patch.opts;
        p = store.ref.update(body);
      } else {
        var full = applyPatch(cloneState(store.remote), patch);
        p = store.ref.set({ counts: full.counts, include: full.include, opts: full.opts, updatedAt: now });
      }
    } catch (e) { p = Promise.reject(e); }
    Promise.resolve(p).then(function () {
      applyPatch(store.remote, patch);
      store.docExists = true;
      store.updatedAt = now;
      store.inflight = null;
      store.retries = 0;
      store.failed = false;
      recompute();
      setSave();
      if (!patchEmpty(store.dirty)) schedule(250);
    }, function (e) { onWriteError(e, patch); });
  }
  function onWriteError(e, patch) {
    var code = e && e.code;
    store.inflight = null;
    mergeUnder(store.dirty, patch);
    if (code === 'invalid_argument' || code === 'transform_error') {
      /* the document may have been removed (update needs it), or this viewer may not write */
      store.ref.get().then(function (snap) {
        if (store.docExists && snap && !snap.exists) { store.docExists = false; schedule(0); }
        else goReadOnly();
      }, function () { goReadOnly(); });
      return;
    }
    if (code === 'quota_exceeded') { store.quota = true; recompute(); refresh(); updateBanner(); return; }
    if (code === 'revoked' || code === 'not_granted' || code === 'capability_disabled' || code === 'capability_removed') {
      recompute(); toLocal('revoked'); return;
    }
    /* unavailable, resource_exhausted, unknown: re-read the document, then retry with back-off */
    store.retries++;
    store.failed = store.retries > 1;
    setSave();
    if (store.retries > 5) return; /* stays dirty; the next edit retries */
    var delay = (code === 'resource_exhausted' ? 4000 : 1200) * store.retries + Math.random() * 600;
    setTimeout(function () {
      store.ref.get().then(function (snap) { onSnap(snap); }, function () { /* keep going */ }).then(function () { schedule(0); });
    }, delay);
  }
  function goReadOnly() {
    store.readOnly = true;
    store.dirty = emptyPatch();
    recompute();
    refresh();
    updateBanner();
  }
  function onSnap(snap) {
    store.snapReady = true;
    store.subRetries = 0;
    store.docExists = !!(snap && snap.exists);
    var d = store.docExists ? snap.data() : null;
    store.remote = normalize(d, byId);
    store.updatedAt = d && typeof d.updatedAt === 'string' ? d.updatedAt : null;
    recompute();
    refresh();
    updateBanner();
    if (!patchEmpty(store.dirty) && !store.inflight) schedule(300);
  }
  function subscribe() {
    try {
      store.unsub = store.ref.onSnapshot(onSnap, function (e) {
        var code = e && e.code;
        store.unsub = null;
        if (code === 'revoked' || code === 'not_granted' || code === 'capability_disabled' || code === 'capability_removed' ||
            code === 'invalid_argument' || code === 'transform_error') {
          toLocal(code === 'revoked' ? 'revoked' : 'error');
          return;
        }
        store.subRetries++;
        if (store.subRetries > 5) { toLocal('error'); return; }
        setTimeout(subscribe, 2000 * store.subRetries);
      });
    } catch (e) { toLocal('error'); }
  }
  function toLocal(reason) {
    if (store.unsub) { try { store.unsub(); } catch (e) { /* ignore */ } store.unsub = null; }
    clearTimeout(store.timer);
    store.mode = 'local';
    store.reason = reason;
    store.readOnly = false;
    store.remote = cloneState(state);
    store.dirty = emptyPatch();
    store.inflight = null;
    store.lsOk = lsSet(LS_KEY, { counts: store.remote.counts, include: store.remote.include, opts: store.remote.opts });
    recompute();
    refresh();
    updateBanner();
  }
  function startLocal(reason) {
    store.mode = 'local';
    store.reason = reason;
    store.remote = normalize(lsGet(LS_KEY), byId);
    store.lsOk = lsSet(LS_KEY + '.probe', 1);
    try { W.localStorage.removeItem(LS_KEY + '.probe'); } catch (e) { /* ignore */ }
    recompute();
    refresh();
    updateBanner();
  }
  function connect() {
    var c = W.claude;
    if (!c || typeof c.use !== 'function') { startLocal('none'); return; }
    var dbP;
    try { dbP = c.use('db'); } catch (e) { startLocal('none'); return; }
    Promise.resolve(dbP).then(function (db) {
      if (!db) { startLocal('none'); return; }
      var userP;
      try { userP = c.use('user'); } catch (e) { userP = null; }
      return Promise.resolve(userP).then(function (u) {
        if (!u || typeof u.can !== 'function') return null;
        return Promise.resolve(u.can('data.write')).catch(function () { return null; });
      }, function () { return null; }).then(function (can) {
        if (can === false) store.readOnly = true;
        try { store.ref = db.doc(DOC_PATH); } catch (e) { startLocal('error'); return; }
        store.mode = 'db';
        subscribe();
        refresh();
        updateBanner();
      });
    }, function () { startLocal('none'); });
  }

  /* ------------------------------------------------------------------ filters */
  function applyFilter() {
    var q = (ui.q || '').trim().toLowerCase();
    var shown = 0, total = 0;
    data.groups.forEach(function (g) {
      var gVisible = false;
      var gOn = !ui.g || ui.g === g.id;
      g.subs.forEach(function (s) {
        var sg = $('prep-sg-' + s.id);
        if (!sg) return;
        var any = false;
        data.lines.forEach(function (l) {
          if (l.s !== s.id) return;
          total++;
          var r = readyOf(l, state), done = r >= l.need, inc = isIncluded(l, state);
          var ok = gOn;
          if (ok && ui.f === 'todo') ok = !done && inc;
          if (ok && ui.f === 'done') ok = done;
          if (ok && q) {
            var hay = (l.n + ' ' + (l.code || '') + ' ' + (l.file || '') + ' ' + (l.m || '') + ' ' + l.id + ' ' + s.name).toLowerCase();
            ok = hay.indexOf(q) !== -1;
          }
          rowEls[l.id].li.hidden = !ok;
          if (ok) { any = true; shown++; }
        });
        sg.hidden = !any;
        if (any) gVisible = true;
      });
      $('prep-g-' + g.id).hidden = !gVisible;
    });
    $('prep-empty').hidden = shown > 0;
    $('prep-shown').textContent = shown === total ? '줄 ' + total + '개를 모두 보여 줍니다.' : '줄 ' + total + '개 중 ' + shown + '개를 보여 줍니다.';
    Array.prototype.forEach.call(section.querySelectorAll('.prep-seg button'), function (b) {
      b.setAttribute('aria-pressed', b.getAttribute('data-f') === ui.f ? 'true' : 'false');
    });
    $('prep-group-sel').value = ui.g || '';
    data.groups.forEach(function (g) { var c = $('prep-gc-' + g.id); if (c) c.setAttribute('aria-pressed', ui.g === g.id ? 'true' : 'false'); });
  }

  /* ------------------------------------------------------------------ details (fetched on demand) */
  function fillDetails(det) {
    var l = byId[det.getAttribute('data-id')];
    var body = det.querySelector('.prep-more-b');
    if (!l || body.getAttribute('data-filled') === '1') return;
    if (l.d) {
      body.innerHTML = l.d.length ? l.d.map(function (p) { return '<p><b>' + esc(p[0]) + '</b> ' + esc(p[1]) + '</p>'; }).join('') : '<p>더 적을 내용이 없습니다.</p>';
      body.setAttribute('data-filled', '1');
      return;
    }
    body.innerHTML = '<p class="muted">불러오는 중입니다.</p>';
    loadDetails().then(function (okay) {
      if (okay) { body.removeAttribute('data-filled'); fillDetails(det); }
      else body.innerHTML = '<p class="muted">자세한 설명(fin/prep/lines.json)을 불러오지 못했습니다. 발행된 페이지에서는 보입니다.</p>';
    });
  }

  /* ------------------------------------------------------------------ csv via downloads capability */
  var dlP = null;
  function getDl() {
    if (!dlP) {
      var c = W.claude;
      dlP = (c && typeof c.use === 'function')
        ? Promise.resolve().then(function () { return c.use('downloads'); }).catch(function () { return null; })
        : Promise.resolve(null);
    }
    return dlP;
  }
  function csvName() { return 'Toccata_준비체크_' + ymd() + '.csv'; }
  function csvNote(t) { var n = $('prep-csv-note'); n.textContent = t; n.hidden = !t; }
  function noDownloads() {
    var text = csvText(data, state);
    var kb = Math.max(1, Math.round(new Blob([text]).size / 1024));
    $('prep-csv').hidden = true;
    csvNote('목록 받기: ' + csvName() + ' (약 ' + kb + ' KB). 이 화면에서는 파일 받기를 쓸 수 없어 단추를 숨겼습니다. 발행된 페이지에서 받을 수 있습니다.');
  }
  function exportCsv() {
    var btn = $('prep-csv');
    btn.disabled = true;
    getDl().then(function (dl) {
      if (!dl) { noDownloads(); return; }
      var name = csvName();
      return dl.save({ filename: name, data: new Blob([csvText(data, state)], { type: 'text/csv' }) }).then(function (res) {
        csvNote(res && res.status === 'saved' ? name + ' 파일을 저장했습니다.' : '');
      }, function (e) {
        var code = e && e.code;
        if (code === 'declined') csvNote('받기를 취소했습니다.');
        else if (code === 'rate_limited') csvNote('받기 창이 이미 열려 있습니다. 잠시 뒤 다시 누르세요.');
        else if (code === 'too_large') csvNote('파일이 너무 커서 받을 수 없습니다.');
        else if (code === 'extension_not_enabled' || code === 'rejected_extension') csvNote('이 화면에서는 csv 파일 받기를 쓸 수 없습니다.');
        else if (code === 'bad_request' || code === 'transform_error') csvNote('파일을 만들지 못했습니다. 다시 눌러 보세요.');
        else noDownloads();
      });
    }).then(function () { btn.disabled = false; }, function () { btn.disabled = false; });
  }

  /* ------------------------------------------------------------------ events */
  var typeTimers = {};
  function wire() {
    var list = $('prep-list');
    list.addEventListener('click', function (ev) {
      var b = ev.target.closest('button[data-act]');
      if (!b || b.disabled) return;
      var li = b.closest('.prep-row'), id = li && li.getAttribute('data-id'), l = byId[id];
      if (!l) return;
      var r = readyOf(l, state), act = b.getAttribute('data-act');
      if (act === 'dec') setCount(id, r - 1);
      else if (act === 'inc') setCount(id, r + 1);
      else if (act === 'full') setCount(id, l.need);
    });
    list.addEventListener('input', function (ev) {
      var inp = ev.target;
      if (!inp.matches || !inp.matches('input[data-act="set"]')) return;
      var id = inp.closest('.prep-row').getAttribute('data-id');
      clearTimeout(typeTimers[id]);
      typeTimers[id] = setTimeout(function () { if (inp.value !== '') setCount(id, inp.value); }, 500);
    });
    list.addEventListener('change', function (ev) {
      var t = ev.target;
      if (t.matches && t.matches('input[data-act="set"]')) {
        var id = t.closest('.prep-row').getAttribute('data-id');
        clearTimeout(typeTimers[id]);
        setCount(id, t.value === '' ? 0 : t.value);
        t.value = fmtQty(readyOf(byId[id], state), byId[id].dec);
      } else if (t.matches && t.matches('input[data-act="include"]')) {
        change('include', t.closest('.prep-row').getAttribute('data-id'), t.checked);
        if (ui.f !== 'all') applyFilter();
      }
    });
    list.addEventListener('focusout', function (ev) {
      var t = ev.target;
      if (t.matches && t.matches('input[data-act="set"]')) {
        var l = byId[t.closest('.prep-row').getAttribute('data-id')];
        if (l) t.value = fmtQty(readyOf(l, state), l.dec);
      }
    });
    list.addEventListener('toggle', function (ev) {
      var d = ev.target;
      if (d.classList && d.classList.contains('prep-more') && d.open) fillDetails(d);
      if (d.classList && d.classList.contains('prep-sg')) {
        var sid = d.getAttribute('data-sub');
        if (d.open) delete ui.closed[sid]; else ui.closed[sid] = true;
        saveUi();
      }
    }, true);
    Array.prototype.forEach.call(section.querySelectorAll('.prep-seg button'), function (b) {
      b.addEventListener('click', function () { ui.f = b.getAttribute('data-f'); saveUi(); applyFilter(); });
    });
    $('prep-group-sel').addEventListener('change', function (ev) { ui.g = ev.target.value; saveUi(); applyFilter(); });
    var qt = 0;
    $('prep-q').addEventListener('input', function (ev) {
      clearTimeout(qt);
      var v = ev.target.value;
      qt = setTimeout(function () { ui.q = v; saveUi(); applyFilter(); }, 150);
    });
    $('prep-gcards').addEventListener('click', function (ev) {
      var c = ev.target.closest('.prep-gcard');
      if (!c) return;
      var g = c.getAttribute('data-g');
      ui.g = ui.g === g ? '' : g;
      saveUi();
      applyFilter();
      updateSummary(summarize(data, state));
      if (ui.g) {
        var sec = $('prep-g-' + ui.g);
        var reduce = W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (sec) sec.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      }
    });
    $('prep-tools-in').addEventListener('change', function (ev) { change('opts', 'tools', ev.target.checked); });
    $('prep-csv').addEventListener('click', exportCsv);
  }

  /* ------------------------------------------------------------------ first open of the tab */
  var opened = false;
  function onVisible() {
    if (opened || section.hidden) return;
    opened = true;
    loadDetails();
    getDl().then(function (dl) { if (!dl) noDownloads(); });
    var sh = $('prep-sticky').offsetHeight;
    if (sh) section.style.setProperty('--prep-sh', sh + 'px');
  }

  /* ------------------------------------------------------------------ start */
  function start() {
    buildList();
    $('prep-q').value = ui.q || '';
    wire();
    recompute();
    refresh();
    applyFilter();
    setSave();
    /* a deep link to a row (#prep-r-…) may have been evaluated before the rows existed */
    var h = (location.hash || '').slice(1);
    if (h && h.indexOf('prep-') === 0 && section.hidden && document.getElementById(h)) {
      try { W.dispatchEvent(new HashChangeEvent('hashchange')); } catch (e) { /* ignore */ }
    }
    if ('MutationObserver' in W) new MutationObserver(onVisible).observe(section, { attributes: true, attributeFilter: ['hidden'] });
    onVisible();
    connect();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
