/* 05 동작 시뮬레이션 (tab sim).
   Data (lazy, on first open): fin/sim/keyaction.json + fin/sim/system.json, written by
   hardware/mechanical/key-action-v4/model/export_sim.py (model_v4.py r4.5 histories, netlist map, SCH-06 budget, CAD touch fold).
   API: window.toccata.sim = { ready: Promise<void>, setRun(colour 'white'|'black', runId 'push0.8'|'v0.5'|'v0.7'|'v1'|'v1.5'|'v2.5'),
                               setTime(ms), noteOn(midi), noteOff(midi) } */
(function () {
  'use strict';
  var sec = document.getElementById('p-sim');
  if (!sec) return;
  var NS = 'http://www.w3.org/2000/svg';
  var reduce = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var api = { ready: null, setRun: function () {}, setTime: function () {}, noteOn: function () {}, noteOff: function () {} };
  var readyResolve;
  api.ready = new Promise(function (r) { readyResolve = r; });
  window.toccata = window.toccata || {};
  window.toccata.sim = api;

  function $(id) { return document.getElementById(id); }
  function sv(tag, attrs, parent) {
    var e = document.createElementNS(NS, tag);
    if (attrs) for (var k in attrs) if (attrs[k] !== null && attrs[k] !== undefined) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  function he(tag, attrs, text, parent) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (text !== undefined && text !== null) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function f(n, d) { return (n === null || n === undefined || !isFinite(n)) ? '–' : Number(n).toFixed(d); }
  function clamp(x, a, b) { return x < a ? a : (x > b ? b : x); }
  // signed number: '0.00' when it rounds to zero (no '-0.00'), '+' in front of positive values, '−' for negative
  function signed(v, d) {
    if (v === null || v === undefined || !isFinite(v)) return '–';
    if (Math.abs(v) < 0.5 * Math.pow(10, -d)) return (0).toFixed(d);
    return (v > 0 ? '+' : '−') + Math.abs(v).toFixed(d);
  }
  function setText(id, s) { var e = $(id); if (e && e.textContent !== s) e.textContent = s; }
  function ringsPath(rings) {
    var s = '';
    for (var i = 0; i < rings.length; i++) {
      var r = rings[i];
      if (!r || r.length < 2) continue;
      s += 'M' + r[0][0] + ',' + (-r[0][1]);
      for (var j = 1; j < r.length; j++) s += 'L' + r[j][0] + ',' + (-r[j][1]);
      s += 'Z';
    }
    return s;
  }
  function polyPath(r) { return ringsPath([r]); }

  var started = false;
  function start() { if (started) return; started = true; boot(); }
  new MutationObserver(function () { if (!sec.hidden) start(); }).observe(sec, { attributes: true, attributeFilter: ['hidden'] });
  if (!sec.hidden) start();

  function getJSON(u) {
    return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });
  }
  function boot() {
    Promise.all([getJSON('fin/sim/keyaction.json'), getJSON('fin/sim/system.json')]).then(function (d) {
      setText('sim-status', '');
      init(d[0], d[1]);
      readyResolve();
    }).catch(function (e) {
      var st = $('sim-status');
      if (st) { st.textContent = '계산 기록을 불러오지 못했습니다 (' + (e && e.message || e) + '). 새로고침해 보세요.'; st.classList.add('err'); }
    });
  }

  /* ======================================================================== shared sensor law (= export_sim.py) */
  var SENS = null;
  function field(gap) {
    var R = SENS.R, L = SENS.L, Br = SENS.Br_mT;
    return Br / 2 * ((gap + L) / Math.sqrt(R * R + (gap + L) * (gap + L)) - gap / Math.sqrt(R * R + gap * gap));
  }
  function volt(gap) { return SENS.vq + SENS.mv_per_mT / 1000 * field(gap); }
  function adc(gap) { return Math.round(volt(gap) / SENS.vref * SENS.codes); }

  function init(KA, SYS) {
    SENS = KA.sensor;
    // circuit revision (hardware/pcb/netlist/sheets.json, via export_sim.py)
    if (SYS.circuit && SYS.circuit.rev) [].forEach.call(sec.querySelectorAll('.sim-rev'), function (e) { e.textContent = SYS.circuit.rev; });
    // settled rest vs design rest (the readouts at t = 0 show the settled values)
    (function restNote() {
      var W = KA.colours.white, B = KA.colours.black;
      setText('sim-rest-note', '쉼 간격 ' + f(W.gap_rest_settled, 2) + ' / ' + f(B.gap_rest_settled, 2) + ' mm(ADC ' + W.adc.rest_settled + ' / ' + B.adc.rest_settled +
        ', 백 / 흑)는 건반이 쉼 펠트에, 레버가 캡스턴에 얹혀 정착한 값입니다. 설계 쉼 ' + f(W.gap_rest_design, 2) + ' / ' + f(B.gap_rest_design, 2) + ' mm(ADC ' +
        W.adc.rest_design + ' / ' + B.adc.rest_design + ')보다 ' + f(W.gap_rest_design - W.gap_rest_settled, 2) + ' / ' + f(B.gap_rest_design - B.gap_rest_settled, 2) + ' mm 낮습니다.');
    })();
    var S = { col: 'white', run: null, t: 0, playing: false, rate: 0.05, live: false, pressed: false, holdEnd: 0, last: 0, raf: 0 };
    var C = null;         // colour block
    var R = null;         // run
    var map = null;       // time mapping of the run
    var drawn = {};       // per-frame nodes

    /* ------------------------------------------------------------------ run selector */
    var RUN_LAB = { 'push0.8': ['0.8 N 누름', '아주 여림'], 'v0.5': ['0.5 m/s', '여림'], 'v0.7': ['0.7 m/s', '보통'], 'v1': ['1.0 m/s', '셈'],
      'v1.5': ['1.5 m/s', '아주 셈'], 'v2.5': ['2.5 m/s', '과다'] };
    function runButtons() {
      var box = $('sim-run');
      box.textContent = '';
      C.runs.forEach(function (r) {
        var b = he('button', { type: 'button', 'data-run': r.id, 'aria-pressed': String(R && R.id === r.id) }, null, box);
        b.appendChild(document.createTextNode((RUN_LAB[r.id] || [r.label])[0]));
        he('small', null, (RUN_LAB[r.id] || ['', ''])[1], b);
      });
    }
    $('sim-run').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-run]');
      if (b) setRun(S.col, b.getAttribute('data-run'));
    });
    $('sim-col').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-col]');
      if (b) setRun(b.getAttribute('data-col'), R ? R.id : 'v1');
    });
    $('sim-rate').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-rate]');
      if (!b) return;
      S.rate = parseFloat(b.getAttribute('data-rate'));
      [].forEach.call($('sim-rate').querySelectorAll('button'), function (x) { x.setAttribute('aria-pressed', String(x === b)); });
    });

    function setRun(col, id) {
      var colChanged = !C || S.col !== col;
      S.col = col;
      C = KA.colours[col];
      R = C.runs.filter(function (r) { return r.id === id; })[0] || C.runs.filter(function (r) { return r.id === 'v1'; })[0];
      [].forEach.call($('sim-col').querySelectorAll('button'), function (x) { x.setAttribute('aria-pressed', String(x.getAttribute('data-col') === col)); });
      runButtons();
      prepRun();
      if (colChanged) { buildDrawing(); buildEventTable(); buildMetrics(); }
      markEventRow();
      buildPlots();
      S.t = 0; S.live = false; S.pressed = false;
      stop();
      setTime(0);
    }
    api.setRun = setRun;

    /* ------------------------------------------------------------------ run preparation: derived series, time map */
    function prepRun() {
      var d = R.data, n = d.t.length;
      var ev = R.events;
      d.travel = new Array(n); d.adc = new Array(n); d.frac = new Array(n);
      var gb = C.mag_bot_z - C.z_elem, span = C.mag_rest_z - C.mag_bot_z;
      for (var i = 0; i < n; i++) {
        d.travel[i] = C.front_rest_z - d.fz[i];
        d.adc[i] = adc(d.gap[i]);
        d.frac[i] = (d.gap[i] - gb) / span;
      }
      var tEnd = d.t[n - 1];
      var tb = (ev.t_bottom !== null ? ev.t_bottom : ev.t_noteon) || 20;
      var tRel = ev.t_release !== null ? ev.t_release : tEnd;
      var tA = Math.min(tb + 30, tRel - 12), tB = tRel - 4;
      map = { tA: tA, tB: tB, tEnd: tEnd, uA: 0.47, uB: 0.53, tRel: tRel };
      S.holdEnd = tRel - 0.001;
    }
    function tToU(t) {
      if (t <= map.tA) return map.uA * t / map.tA;
      if (t <= map.tB) return map.uA + (map.uB - map.uA) * (t - map.tA) / (map.tB - map.tA);
      return map.uB + (1 - map.uB) * (t - map.tB) / (map.tEnd - map.tB);
    }
    function uToT(u) {
      if (u <= map.uA) return map.tA * u / map.uA;
      if (u <= map.uB) return map.tA + (map.tB - map.tA) * (u - map.uA) / (map.uB - map.uA);
      return map.tB + (map.tEnd - map.tB) * (u - map.uB) / (1 - map.uB);
    }
    function idxAt(t) {
      var a = R.data.t, lo = 0, hi = a.length - 1;
      if (t <= a[0]) return 0;
      if (t >= a[hi]) return hi - 1;
      while (hi - lo > 1) { var m = (lo + hi) >> 1; if (a[m] <= t) lo = m; else hi = m; }
      return lo;
    }
    function sample(t) {
      var d = R.data, i = idxAt(t), t0 = d.t[i], t1 = d.t[i + 1] === undefined ? t0 : d.t[i + 1];
      var w = t1 > t0 ? clamp((t - t0) / (t1 - t0), 0, 1) : 0;
      var o = {};
      ['th', 'b', 'cy', 'cz', 'gap', 'fz', 'Nc', 'fup', 'ffr', 'fre', 'Ff'].forEach(function (k) {
        var a = d[k][i], b = d[k][i + 1] === undefined ? a : d[k][i + 1];
        o[k] = a + (b - a) * w;
      });
      return o;
    }

    /* ------------------------------------------------------------------ the side section drawing */
    function keyMatrix(th, cy, cz) {
      var c = Math.cos(th), s = Math.sin(th), ky = C.ck0[0], kz = C.ck0[1];
      return [c, -s, s, c, cy - c * ky + s * kz, -cz + s * ky + c * kz];
    }
    function leverMatrix(b) {
      var c = Math.cos(b), s = Math.sin(b), Ly = C.L[0], Lz = C.L[1];
      return [c, s, -s, c, Ly - c * Ly - s * Lz, -Lz - s * Ly + c * Lz];
    }
    function mStr(m) { return 'matrix(' + m.map(function (v) { return v.toFixed(6); }).join(' ') + ')'; }
    function kpt(p, th, cy, cz) {
      var rx = p[0] - C.ck0[0], rz = p[1] - C.ck0[1];
      return [cy + rx * Math.cos(th) - rz * Math.sin(th), cz + rx * Math.sin(th) + rz * Math.cos(th)];
    }

    function buildDrawing() {
      var sec_ = C.section;
      var gS = $('sim-static'), gK = $('sim-keyg'), gL = $('sim-lever'), gP = $('sim-spring'), gM = $('sim-marks'), gO = $('sim-over');
      [gS, gK, gL, gP, gM, gO].forEach(function (g) { g.textContent = ''; });
      drawn = {};
      setText('sim-side-title', '측면 단면 · ' + C.name);
      setText('sim-side-sub', 'x = ' + f(sec_.xsec, 3) + ' (건반 ' + C.key + ' 밸런스 핀 면, 모듈 좌표)');
      // fixed parts
      (sec_.neighbours || []).forEach(function (nb) { sv('path', { d: ringsPath(nb.rings), 'class': 'm-nb' }, gS); });
      sv('path', { d: ringsPath(sec_.frame), 'class': 'm-frame' }, gS);
      var cls = { felt: 'm-felt', sbar: 'm-sbar', steel: 'm-steel', pcb: 'm-pcb', bar: 'm-bar', pad: 'm-pad', cover: 'm-cover' };
      ['cover', 'bar', 'sbar', 'pcb', 'pad', 'felt', 'steel'].forEach(function (g) {
        (sec_.fixed[g] || []).forEach(function (it) {
          var p = sv('path', { d: polyPath(it.ring), 'class': cls[g] }, gS);
          sv('title', null, p).textContent = it.ko || it.part;
          if (g === 'pad') drawn.pad = p;
          if (g === 'felt' && /front felt/.test(it.part) && (C.key.indexOf('#') < 0 ? /white/.test(it.part) : /black/.test(it.part))) drawn.ffelt = p;
        });
      });
      // spring (coil and long leg fixed while loaded)
      var sp = sec_.spring;
      sv('path', { d: polyPath(sp.coil), 'class': 'm-spring' }, gP);
      sv('path', { d: 'M' + sp.long_leg[0][0] + ',' + (-sp.long_leg[0][1]) + 'L' + sp.long_leg[1][0] + ',' + (-sp.long_leg[1][1]), 'class': 'm-spring' }, gP);
      // lever (b = 0 frame)
      sec_.lever_beyond.forEach(function (r) { sv('path', { d: polyPath(r), 'class': 'm-beyond' }, gL); });
      sv('path', { d: ringsPath(sec_.lever_cut), 'class': 'm-lever' }, gL);
      sec_.lever_steel.forEach(function (r) { drawn.steel = sv('path', { d: polyPath(r), 'class': 'm-steel' }, gL); });
      sec_.lever_felt.forEach(function (r) { drawn.lfelt = sv('path', { d: polyPath(r), 'class': 'm-felt' }, gL); });
      sv('path', { d: 'M' + sp.short_leg_lf[0][0] + ',' + (-sp.short_leg_lf[0][1]) + 'L' + sp.short_leg_lf[1][0] + ',' + (-sp.short_leg_lf[1][1]), 'class': 'm-spring' }, gL);
      // key (design frame)
      sec_.key_beyond.forEach(function (r) { sv('path', { d: polyPath(r), 'class': 'm-beyond' }, gK); });
      sv('path', { d: ringsPath(sec_.key_cut), 'class': C.key.indexOf('#') >= 0 ? 'm-keyb' : 'm-key' }, gK);
      sec_.key_steel.forEach(function (r) { drawn.cap = sv('path', { d: polyPath(r), 'class': 'm-steel' }, gK); });
      sec_.key_felt.forEach(function (r) { drawn.rfelt = sv('path', { d: polyPath(r), 'class': 'm-felt' }, gK); });
      sv('path', { d: polyPath(sec_.magnet_S), 'class': 'm-magS' }, gK);
      sv('path', { d: polyPath(sec_.magnet_N), 'class': 'm-magN' }, gK);
      // sensor element (diamond) - part of the world group so the inset shows it
      var y = C.y_elem, z = C.z_elem, s = 0.9;
      sv('path', { d: 'M' + (y - s) + ',' + (-z) + 'L' + y + ',' + (-z - s) + 'L' + (y + s) + ',' + (-z) + 'L' + y + ',' + (-z + s) + 'Z', 'class': 'm-sensor' }, gM);
      // labels (main view only)
      var sensRef = sensorRef();
      sv('text', { x: y, y: -0.3, 'text-anchor': 'middle', 'class': 't-lab' }, gO).textContent = '↑ ' + sensRef + ' 센서 (소자 z' + f(z, 2) + ')';
      sv('text', { x: C.K[0] - 1.2, y: -C.K[1] + 6.8, 'class': 't-lab' }, gO).textContent = 'K';
      sv('text', { x: C.L[0] - 6.5, y: -C.L[1] + 6.5, 'class': 't-lab' }, gO).textContent = 'L';
      sv('text', { x: 168, y: -74.2, 'class': 't-lab2' }, gO).textContent = '업스톱 패드 · 패드 바';
      drawn.finger = sv('path', { d: '', 'class': 'm-finger' }, gO);
      drawn.fhead = sv('path', { d: '', 'class': 'm-fhead' }, gO);
      drawn.ftxt = sv('text', { 'class': 't-press' }, gO);
      // inset view box around the magnet / sensor
      var ins = $('sim-inset');
      ins.setAttribute('viewBox', (y - 15) + ' ' + (-(C.mag[1] + 7.5)) + ' 30 ' + (C.mag[1] + 7.5 - 4));
      setText('sim-ins-ref', sensRef + ' · 소자 z' + f(C.z_elem, 2) + ' · y' + f(C.y_elem, 0));
      var gD = $('sim-ins-dim');
      gD.textContent = '';
      drawn.dimL = sv('path', { 'class': 'd-line' }, gD);
      drawn.dimE = sv('path', { 'class': 'd-ext' }, gD);
      drawn.dimT = sv('text', { 'class': 'd-txt', 'font-size': '1.7' }, gD);
      drawn.dimT2 = sv('text', { 'class': 'd-txt2', 'font-size': '1.15' }, gD);
      // two short lines: one line does not fit right of the dimension line in the 30 mm wide inset
      drawn.dimT2a = sv('tspan', null, drawn.dimT2); drawn.dimT2a.textContent = '자석 밑면 ↔';
      drawn.dimT2b = sv('tspan', null, drawn.dimT2); drawn.dimT2b.textContent = '센서 소자';
      drawn.keyg = gK; drawn.levg = gL;
      buildInset();
    }
    // inset: a real copy of the world group (not <use>: the page CSS does not reach <use> clones, so they would draw black).
    // Copied once per drawing; per frame only the key / lever transforms and the 'hot' marks change, and they are mirrored.
    var mirror = null;
    function buildInset() {
      var gI = $('sim-ins-world'), src = $('sim-world');
      gI.textContent = '';
      mirror = new Map();
      var cl = src.cloneNode(true);
      (function pair(a, b) {
        mirror.set(a, b);
        if (b.removeAttribute) b.removeAttribute('id');
        var ca = a.children, cb = b.children;
        for (var i = 0; i < ca.length; i++) pair(ca[i], cb[i]);
      })(src, cl);
      Array.prototype.slice.call(cl.querySelectorAll('title')).forEach(function (t) { t.parentNode.removeChild(t); });
      gI.appendChild(cl);
    }
    function mir(el) { return (mirror && el) ? mirror.get(el) : null; }
    function sensorRef() {
      var midiOf = { 'D': 62, 'C#': 61 };
      var k = SYS.keys.filter(function (q) { return q.midi === midiOf[C.key]; })[0];
      return k ? k.sensor : 'U2xx';
    }
    function hot(el, on) {
      if (!el) return;
      el.classList.toggle('hot', !!on);
      var m = mir(el); if (m) m.classList.toggle('hot', !!on);
    }

    function phaseOf(t) {
      var ev = R.events;
      if (t < 5) return '쉼';
      var tb = ev.t_bottom !== null ? ev.t_bottom : ev.t_noteon;
      if (R.meta.kind === 'push') {
        if (t < (ev.t_noteon || 1e9)) return '누르는 중 (0.8 N)';
        if (t < ev.t_release) return '바닥에서 누름 유지';
      } else {
        if (t < tb) return '내려가는 중';
        if (t < tb + 25) return '바닥 · 레버가 패드에 닿음';
        if (t < ev.t_release) return '바닥에서 1 N 유지';
      }
      if (ev.t_rearm !== null && t < ev.t_rearm) return '놓음 · 올라오는 중';
      if (ev.t_full !== null && t < ev.t_full) return '재무장선 지남';
      return '쉼으로 돌아옴';
    }

    function setTime(t) {
      if (!R) return;
      t = clamp(t, 0, map.tEnd);
      S.t = t;
      var o = sample(t);
      var tK = mStr(keyMatrix(o.th, o.cy, o.cz)), tL = mStr(leverMatrix(o.b)), mK = mir(drawn.keyg), mL = mir(drawn.levg);
      drawn.keyg.setAttribute('transform', tK);
      drawn.levg.setAttribute('transform', tL);
      if (mK) mK.setAttribute('transform', tK);
      if (mL) mL.setAttribute('transform', tL);
      hot(drawn.pad, o.fup > 0.05); hot(drawn.steel, o.fup > 0.05);
      hot(drawn.ffelt, o.ffr > 0.05);
      hot(drawn.rfelt, o.fre > 0.05);
      hot(drawn.cap, o.Nc > 0.05); hot(drawn.lfelt, o.Nc > 0.05);
      // finger arrow
      if (o.Ff > 0.001) {
        var fp = kpt(C.finger, o.th, o.cy, o.cz), L = 4 + 3.2 * o.Ff;
        drawn.finger.setAttribute('d', 'M' + fp[0] + ',' + (-(fp[1] + L + 2.2)) + 'V' + (-(fp[1] + 2.2)));
        drawn.fhead.setAttribute('d', 'M' + (fp[0] - 1.3) + ',' + (-(fp[1] + 2.6)) + 'L' + fp[0] + ',' + (-fp[1] - 0.2) + 'L' + (fp[0] + 1.3) + ',' + (-(fp[1] + 2.6)) + 'Z');
        drawn.ftxt.setAttribute('x', fp[0] + 2); drawn.ftxt.setAttribute('y', -(fp[1] + L));
        drawn.ftxt.textContent = '손가락 ' + f(o.Ff, 1) + ' N';
      } else { drawn.finger.setAttribute('d', ''); drawn.fhead.setAttribute('d', ''); drawn.ftxt.textContent = ''; }
      // inset dimension: magnet face -> sensor element
      var mp = kpt(C.mag, o.th, o.cy, o.cz), ye = C.y_elem, ze = C.z_elem, xd = ye + 5.0;
      drawn.dimE.setAttribute('d', 'M' + (mp[0] + 2.5) + ',' + (-mp[1]) + 'H' + (xd + 1) + 'M' + (ye + 1) + ',' + (-ze) + 'H' + (xd + 1));
      drawn.dimL.setAttribute('d', 'M' + xd + ',' + (-mp[1]) + 'V' + (-ze));
      drawn.dimT.setAttribute('x', xd + 1.6); drawn.dimT.setAttribute('y', -(mp[1] + ze) / 2 + 0.6);
      drawn.dimT.textContent = f(o.gap, 2) + ' mm';
      var y2 = -(mp[1] + ze) / 2 - 3.4;
      drawn.dimT2a.setAttribute('x', xd + 1.6); drawn.dimT2a.setAttribute('y', y2);
      drawn.dimT2b.setAttribute('x', xd + 1.6); drawn.dimT2b.setAttribute('y', y2 + 1.45);
      // readouts
      var ev = R.events;
      setText('sim-r-phase', phaseOf(t));
      setText('sim-r-t', 't = ' + f(t, 1) + ' ms');
      setText('sim-r-travel', f(C.front_rest_z - o.fz, 2) + ' mm');
      setText('sim-r-lever', signed((o.b - C.rest.b) * 180 / Math.PI, 2) + '°');
      setText('sim-r-gap', f(o.gap, 2) + ' mm');
      setText('sim-r-field', f(field(o.gap), 1) + ' mT');
      setText('sim-r-adc', String(adc(o.gap)));
      setText('sim-r-volt', 'ADC 코드 · ' + f(volt(o.gap), 3) + ' V');
      setText('sim-r-cap', f(o.Nc, 1) + ' N');
      setText('sim-r-pad', f(o.fup, 0) + ' N');
      setText('sim-r-finger', f(o.Ff, 1) + ' N');
      var noteKf = $('sim-r-note').parentNode;
      if (ev.t_noteon !== null && t >= ev.t_noteon && (ev.t_rearm === null || t < ev.t_rearm)) {
        setText('sim-r-note', 'note-on · 벨로시티 ' + ev.midi_vel);
        setText('sim-r-vel', '추정 앞끝 속도 ' + f(ev.v_front_est, 2) + ' m/s (자석 ' + f(ev.v_mag_est, 3) + ' m/s × ' + f(ev.ratio_front_mag, 2) + '), 타건 뒤 ' + f(ev.t_noteon - 5, 1) + ' ms' +
          (ev.v_front_bottom !== null ? ' · 모델의 펠트 접촉 속도 ' + f(ev.v_front_bottom, 2) + ' m/s' : ''));
        noteKf.classList.add('on');
      } else if (ev.t_rearm !== null && t >= ev.t_rearm) {
        setText('sim-r-note', '재무장 · note-off');
        setText('sim-r-vel', '놓은 뒤 ' + f(ev.t50_after_release, 1) + ' ms에 자석이 50 % 돌아옴 → 다시 칠 수 있음');
        noteKf.classList.remove('on');
      } else {
        setText('sim-r-note', 'note-on 전');
        setText('sim-r-vel', 'ADC ' + C.adc.noteon + '(자석 90 % 내려감)을 넘으면 note-on');
        noteKf.classList.remove('on');
      }
      // plots
      plotCursor(t, o);
      // timeline
      var tl = $('sim-tl');
      if (!tl.matches(':active')) tl.value = String(Math.round(tToU(t) * 1000));
      setText('sim-tnow', f(t, 1) + ' ms');
    }
    api.setTime = function (ms) { stop(); setTime(ms); };

    /* ------------------------------------------------------------------ playback */
    function frame(now) {
      S.raf = 0;
      if (!S.playing) return;
      var dt = Math.min(0.05, (now - S.last) / 1000);
      S.last = now;
      var adv = dt * 1000 * S.rate;
      if (!S.live && S.t > map.tA && S.t < map.tB) adv *= 25;          // hold: fast-forward
      var t = S.t + adv;
      if (S.live && S.pressed && t >= S.holdEnd) t = S.holdEnd;        // key held down: stay at the bottom
      if (t >= map.tEnd) { setTime(map.tEnd); stop(); return; }
      setTime(t);
      S.raf = requestAnimationFrame(frame);
    }
    function play() {
      if (S.t >= map.tEnd - 1e-6) setTime(0);
      S.playing = true; S.last = performance.now();
      $('sim-play').setAttribute('aria-pressed', 'true'); setText('sim-play', '일시 정지');
      if (!S.raf) S.raf = requestAnimationFrame(frame);
    }
    function stop() {
      S.playing = false;
      if (S.raf) cancelAnimationFrame(S.raf);
      S.raf = 0;
      $('sim-play').setAttribute('aria-pressed', 'false');
      setText('sim-play', S.t >= (map ? map.tEnd : 1) - 1e-6 ? '다시 재생' : '재생');
    }
    $('sim-play').addEventListener('click', function () { S.live = false; if (S.playing) stop(); else play(); });
    $('sim-tl').addEventListener('input', function () { S.live = false; stop(); setTime(uToT(parseInt(this.value, 10) / 1000)); });

    // direct press: play the recorded strike, stay at the bottom while held, jump to the release part on let-go
    var pb = $('sim-press');
    function pressDown() {
      if (S.pressed) return;
      S.live = true; S.pressed = true; pb.classList.add('down');
      setTime(0); play();
    }
    function pressUp() {
      if (!S.pressed) return;
      S.pressed = false; pb.classList.remove('down');
      var ev = R.events, d = R.data;
      if (S.t < ev.t_release) {
        var cur = sample(S.t), gb = C.mag_bot_z - C.z_elem, span = C.mag_rest_z - C.mag_bot_z;
        var fc = (cur.gap - gb) / span, i0 = idxAt(ev.t_release) + 1, tj = ev.t_release;
        if (S.t < 5 || fc >= d.frac[0] - 0.005) { stop(); setTime(0); return; }   // let go before the key moved
        if (fc > d.frac[i0]) {
          tj = map.tEnd;
          for (var i = i0; i < d.t.length; i++) { if (d.frac[i] >= fc) { tj = d.t[i]; break; } }
        }
        setTime(tj);
      }
      if (!S.playing) play();
    }
    pb.addEventListener('pointerdown', function (e) { e.preventDefault(); try { pb.setPointerCapture(e.pointerId); } catch (x) {} pressDown(); });
    pb.addEventListener('pointerup', pressUp);
    pb.addEventListener('pointercancel', pressUp);
    pb.addEventListener('lostpointercapture', pressUp);
    pb.addEventListener('keydown', function (e) {
      if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) { e.preventDefault(); pressDown(); }
      else if (e.key === ' ' || e.key === 'Enter') e.preventDefault();
    });
    pb.addEventListener('keyup', function (e) { if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); pressUp(); } });
    pb.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    // a click without a pointer (screen reader activation): one press of about half a second
    pb.addEventListener('click', function (e) { if (e.detail === 0 && !S.pressed) { pressDown(); setTimeout(pressUp, 500); } });

    /* ------------------------------------------------------------------ plots */
    var PL = { x0: 40, x1: 332, y0: 14, y1: 160 };
    var plots = {};
    function px(t) { return PL.x0 + (PL.x1 - PL.x0) * tToU(t); }
    function buildPlot(id, series, yr, opts) {
      var svg = $(id);
      svg.textContent = '';
      var y = opts.sqrt ? function (v) { return PL.y1 - (PL.y1 - PL.y0) * Math.sqrt(Math.max(0, v - yr[0]) / (yr[1] - yr[0])); }
        : function (v) { return PL.y1 - (PL.y1 - PL.y0) * (v - yr[0]) / (yr[1] - yr[0]); };
      // grid + ticks
      var ticks = opts.yt;
      ticks.forEach(function (v) {
        sv('line', { x1: PL.x0, x2: PL.x1, y1: y(v), y2: y(v), 'class': 'gr' }, svg);
        sv('text', { x: PL.x0 - 4, y: y(v) + 3.5, 'text-anchor': 'end', 'class': 'tk' }, svg).textContent = opts.yfmt ? opts.yfmt(v) : String(v);
      });
      sv('line', { x1: PL.x0, x2: PL.x1, y1: PL.y1, y2: PL.y1, 'class': 'ax' }, svg);
      // time ticks: strike part 0..tA every 10 ms, release part from tRel every 10 ms
      var st1 = map.tA > 60 ? 20 : 10;
      for (var tt = 0; tt <= map.tA; tt += st1) {
        sv('line', { x1: px(tt), x2: px(tt), y1: PL.y1, y2: PL.y1 + 4, 'class': 'ax' }, svg);
        sv('text', { x: px(tt), y: PL.y1 + 15, 'text-anchor': 'middle', 'class': 'tk' }, svg).textContent = String(tt);
      }
      for (var k = 0; map.tRel + k <= map.tEnd; k += 40) {
        var t2 = map.tRel + k;
        sv('line', { x1: px(t2), x2: px(t2), y1: PL.y1, y2: PL.y1 + 4, 'class': 'ax' }, svg);
        sv('text', { x: px(t2), y: PL.y1 + 15, 'text-anchor': 'middle', 'class': 'tk' }, svg).textContent = k === 0 ? '놓음' : '+' + k;
      }
      // axis break (the hold is drawn short)
      var bx = (px(map.tA) + px(map.tB)) / 2;
      sv('rect', { x: bx - 4, y: PL.y0 - 2, width: 8, height: PL.y1 - PL.y0 + 4, 'class': 'brk' }, svg);
      sv('text', { x: bx, y: PL.y0 - 4, 'text-anchor': 'middle', 'class': 'tk' }, svg).textContent = '유지';
      sv('text', { x: PL.x1, y: PL.y1 + 28, 'text-anchor': 'end', 'class': 'tl' }, svg).textContent = '시간 ms (놓은 뒤는 놓음 기준)';
      (opts.thr || []).forEach(function (h) {
        sv('line', { x1: PL.x0, x2: PL.x1, y1: y(h.v), y2: y(h.v), 'class': 'thr' }, svg);
        sv('text', { x: PL.x1 - 2, y: y(h.v) - 3, 'text-anchor': 'end', 'class': 'tl' }, svg).textContent = h.label;
      });
      (opts.ev || []).forEach(function (t) {
        if (t === null || t === undefined) return;
        sv('line', { x1: px(t), x2: px(t), y1: PL.y0, y2: PL.y1, 'class': 'ev' }, svg);
      });
      var d = R.data;
      series.forEach(function (s) {
        var p = '', last = null;
        for (var i = 0; i < d.t.length; i++) {
          var X = px(d.t[i]), Y = y(clamp(s.v(i), yr[0], yr[1]));
          if (last !== null && Math.abs(X - last[0]) < 0.25 && Math.abs(Y - last[1]) < 0.25) continue;
          p += (p ? 'L' : 'M') + X.toFixed(1) + ',' + Y.toFixed(1);
          last = [X, Y];
        }
        sv('path', { d: p, 'class': 'ln ' + s.c }, svg);
      });
      var cur = sv('line', { x1: PL.x0, x2: PL.x0, y1: PL.y0, y2: PL.y1, 'class': 'cur' }, svg);
      var dots = series.map(function (s) { return sv('circle', { r: 3, cx: PL.x0, cy: PL.y1, 'class': 'curdot' }, svg); });
      plots[id] = { y: y, yr: yr, cur: cur, dots: dots, series: series };
    }
    function plotCursor(t, o) {
      var X = px(t);
      Object.keys(plots).forEach(function (id) {
        var p = plots[id];
        p.cur.setAttribute('x1', X); p.cur.setAttribute('x2', X);
        p.series.forEach(function (s, j) {
          var v = s.o(o);
          p.dots[j].setAttribute('cx', X);
          p.dots[j].setAttribute('cy', p.y(clamp(v, p.yr[0], p.yr[1])));
        });
      });
    }
    function niceTicks(a, b, n) {
      var span = b - a, step = Math.pow(10, Math.floor(Math.log(span / n) / Math.LN10));
      [1, 2, 2.5, 5, 10].some(function (m) { if (span / (step * m) <= n) { step = step * m; return true; } return false; });
      var out = [];
      for (var v = Math.ceil(a / step) * step; v <= b + 1e-9; v += step) out.push(Math.round(v * 1000) / 1000);
      return out;
    }
    function buildPlots() {
      var d = R.data, ev = R.events;
      var tmin = Math.min.apply(null, d.travel), tmax = Math.max.apply(null, d.travel);
      var yr1 = [Math.min(-1, Math.floor(tmin)), Math.max(C.dip + 1, Math.ceil(tmax + 0.3))];
      buildPlot('sim-p1', [{ v: function (i) { return d.travel[i]; }, o: function (o) { return C.front_rest_z - o.fz; }, c: 'c1' }], yr1,
        { yt: niceTicks(yr1[0], yr1[1], 5), thr: [{ v: C.dip, label: '설계 딥 ' + f(C.dip, 1) }], ev: [ev.t_bottom, ev.t_release] });
      var amin = Math.min.apply(null, d.adc), amax = Math.max.apply(null, d.adc);
      var yr2 = [Math.floor((amin - 60) / 100) * 100, Math.ceil((amax + 60) / 100) * 100];
      buildPlot('sim-p2', [{ v: function (i) { return d.adc[i]; }, o: function (o) { return adc(o.gap); }, c: 'c2' }], yr2,
        { yt: niceTicks(yr2[0], yr2[1], 5), thr: [{ v: C.adc.noteon, label: 'note-on ' + C.adc.noteon }, { v: C.adc.rearm, label: '재무장 ' + C.adc.rearm }],
          ev: [ev.t_noteon, ev.t_rearm] });
      var fmax = 0;
      ['fup', 'ffr', 'Nc', 'fre', 'Ff'].forEach(function (k) { fmax = Math.max(fmax, Math.max.apply(null, d[k])); });
      var yr3 = [0, Math.max(10, Math.ceil(fmax / 10) * 10)];
      var ser3 = [
        { k: 'fup', c: 'c1', lab: '업스톱 패드' }, { k: 'ffr', c: 'c2', lab: '바닥 펠트' }, { k: 'Nc', c: 'c3', lab: '캡스턴' },
        { k: 'fre', c: 'c4', lab: '쉼 펠트' }, { k: 'Ff', c: 'c5', lab: '손가락' }];
      buildPlot('sim-p3', ser3.map(function (s) { return { v: function (i) { return d[s.k][i]; }, o: function (o) { return o[s.k]; }, c: s.c }; }), yr3,
        { sqrt: true, yt: [0, 1, 5, 10, 20, 50, 100, 150].filter(function (v) { return v <= yr3[1]; }), ev: [ev.t_bottom, ev.t_release] });
      var lg = $('sim-p3-lg');
      lg.textContent = '';
      ser3.forEach(function (s) {
        var mx = Math.max.apply(null, d[s.k]);
        var sp = he('span', null, null, lg);
        he('i', { 'class': s.c }, null, sp);
        sp.appendChild(document.createTextNode(s.lab + ' 최대 ' + f(mx, mx >= 10 ? 0 : 1) + ' N'));
      });
    }

    /* ------------------------------------------------------------------ tables */
    function buildEventTable() {
      var tb = $('sim-evt');
      tb.textContent = '';
      setText('sim-evt-col', C.name + ' · 손가락 점 y' + f(C.finger[0], 1) + ', 1 N 유지 약 0.2 s 뒤 놓음');
      var head = he('thead', null, null, tb), tr = he('tr', null, null, head);
      ['세기', '바닥 펠트에 닿는 속도', '추정 속도 (펌웨어 방식)', 'MIDI 벨로시티 (가정)', 'note-on (타건 뒤)', '레버 최대 각 (쉼에서)', '업스톱 패드 최대', '최소 간격 · 최대 ADC',
        '놓은 뒤 재무장', '쉼까지'].forEach(function (h) { he('th', null, h, tr); });
      var body = he('tbody', null, null, tb);
      C.runs.forEach(function (r) {
        var e = r.events, row = he('tr', { 'data-run': r.id }, null, body);
        var td = he('td', null, null, row);
        he('button', { type: 'button', 'data-run': r.id }, (RUN_LAB[r.id] || [r.label])[0], td);
        he('td', { 'class': 'num' }, e.v_front_bottom === null ? '닿지 않음' : f(e.v_front_bottom, 2) + ' m/s', row);
        he('td', { 'class': 'num' }, f(e.v_front_est, 2) + ' m/s', row);
        he('td', { 'class': 'num' }, String(e.midi_vel), row);
        he('td', { 'class': 'num' }, f(e.t_noteon - 5, 1) + ' ms', row);
        he('td', { 'class': 'num' }, signed(e.b_max_deg - C.rest.b * 180 / Math.PI, 2) + '°', row);
        he('td', { 'class': 'num' }, f(e.up_peak, 1) + ' N', row);
        he('td', { 'class': 'num' }, f(e.gap_min, 2) + ' mm · ' + e.adc_max, row);
        he('td', { 'class': 'num' }, f(e.t50_after_release, 1) + ' ms', row);
        he('td', { 'class': 'num' }, f(e.t100_after_release, 1) + ' ms', row);
      });
    }
    $('sim-evt').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-run]');
      if (b) setRun(S.col, b.getAttribute('data-run'));
    });
    function markEventRow() {
      [].forEach.call($('sim-evt').querySelectorAll('tbody tr'), function (tr) { tr.classList.toggle('sel', tr.getAttribute('data-run') === R.id); });
    }
    function leverParts(m) {
      return f(m.steel_g, 1) + ' · ' + f(m.carrier_g, 1) + ' · ' + f(m.felt_strip_g, 2) + ' · ' + f(m.spring_g, 2) + ' · ' + f(m.bond_g, 2) + ' g';
    }
    function buildMetrics() {
      var W = KA.colours.white, B = KA.colours.black, mw = W.metrics, mb = B.metrics, g = W.metrics_global;
      var rows = [
        ['누르는 무게 DW (손가락 점, 기본 마찰)', f(mw.DW, 1) + ' g', f(mb.DW, 1) + ' g'],
        ['올라오는 무게 UW', f(mw.UW, 1) + ' g', f(mb.UW, 1) + ' g'],
        ['손가락 점 등가 질량', f(mw.meff, 1) + ' g', f(mb.meff, 1) + ' g'],
        ['재무장 시간 t50 (1.2 s 눌러 정착 뒤 놓음)', f(mw.t50, 2) + ' ms', f(mb.t50, 2) + ' ms'],
        ['연타 1/(2·t50) · 마찰 2배', f(mw.rep_hz, 1) + ' · ' + f(mw.rep_2f, 1) + ' Hz', f(mb.rep_hz, 1) + ' · ' + f(mb.rep_2f, 1) + ' Hz'],
        ['완전 복귀 t100', f(mw.t100, 2) + ' ms', f(mb.t100, 2) + ' ms'],
        ['업스톱 패드 최대 힘 1.5 m/s · 2.5 m/s (1 N 유지)', f(mw.up_play, 1) + ' · ' + f(mw.up_abuse, 1) + ' N', f(mb.up_play, 1) + ' · ' + f(mb.up_abuse, 1) + ' N'],
        ['비틀림 스프링 토크 쉼 · 바닥', f(mw.spring_T_rest, 2) + ' · ' + f(mw.spring_T_bottom, 2) + ' N·mm', f(mb.spring_T_rest, 2) + ' · ' + f(mb.spring_T_bottom, 2) + ' N·mm'],
        ['건반 · 레버 전체 (강철 블록 포함) 질량', f(mw.key_g, 1) + ' · ' + f(mw.lever_g, 1) + ' g', f(mb.key_g, 1) + ' · ' + f(mb.lever_g, 1) + ' g'],
        ['레버 전체의 내역: 강철 블록 · 출력 캐리어 · 펠트 띠 · 스프링 · MS 폴리머 접착막', leverParts(mw), leverParts(mb)],
        ['자석 이동', f(mw.mag_travel, 2) + ' mm', f(mb.mag_travel, 2) + ' mm'],
        ['자석–센서 간격 쉼 · 강체 바닥 · 최대 과다', f(mw.sensor_rest, 2) + ' · ' + f(mw.sensor_bottom, 2) + ' · ' + f(mw.sensor_ff, 2) + ' mm',
          f(mb.sensor_rest, 2) + ' · ' + f(mb.sensor_bottom, 2) + ' · ' + f(mb.sensor_ff, 2) + ' mm'],
        ['1 N 정착 바닥 간격 (패드 있음)', f(W.gap_held_1N, 2) + ' mm', f(B.gap_held_1N, 2) + ' mm'],
        ['ADC 쉼 → 강체 바닥 (이 페이지 식)', W.adc.rest_design + ' → ' + W.adc.bottom_rigid, B.adc.rest_design + ' → ' + B.adc.bottom_rigid],
        ['ADC 재무장 50 % · 1 N 바닥 · note-on 문턱 (가정)', W.adc.rearm + ' · ' + W.adc.held_1N + ' · ' + W.adc.noteon, B.adc.rearm + ' · ' + B.adc.held_1N + ' · ' + B.adc.noteon],
        ['자기장 쉼 · 강체 바닥 · 최대 과다', f(W.field.rest, 1) + ' · ' + f(W.field.bottom, 1) + ' · ' + f(W.field.over, 1) + ' mT', f(B.field.rest, 1) + ' · ' + f(B.field.bottom, 1) + ' · ' + f(B.field.over, 1) + ' mT']
      ];
      var tb = $('sim-mtbl');
      tb.textContent = '';
      var tr = he('tr', null, null, he('thead', null, null, tb));
      ['항목', '백건 D', '흑건 C#'].forEach(function (h) { he('th', null, h, tr); });
      var body = he('tbody', null, null, tb);
      rows.forEach(function (r) {
        var row = he('tr', null, null, body);
        he('td', null, r[0], row); he('td', { 'class': 'num' }, r[1], row); he('td', { 'class': 'num' }, r[2], row);
      });
      var row = he('tr', null, null, body);
      he('td', null, '유령 음 거름 (한 건반·화음 0.5~1.5 m/s, 0.45~2 N)', row);
      he('td', { colspan: '2' }, g.ghost_cases + '건 중 재무장 ' + g.ghost_armed + '건, 못 거른 것 ' + g.ghost_not_dropped + '건; 다시 닿지 않고 ' + f(g.ghost_settle_max_ms, 0) + ' ms 안에 멈춤', row);
      row = he('tr', null, null, body);
      he('td', null, '레버 받침(패드 자리) 강성 · 계산 간격', row);
      he('td', { colspan: '2' }, KA.meta.seat_k + ' N/mm (검증 실행 값) · 4 µs', row);
    }

    /* ------------------------------------------------------------------ keyboard + signal chain + sound */
    var KEYS = SYS.keys, byMidi = {};
    KEYS.forEach(function (k) { byMidi[k.midi] = k; });
    var kbd = $('sim-kbd');
    var WK = 22, BK = 14;
    var keyEl = {}, bandEl = {};
    (function buildKbd() {
      var wi = 0, xs = {};
      KEYS.forEach(function (k) {
        var el;
        if (!k.black) {
          el = he('div', { 'class': 'sim-wk', 'data-midi': String(k.midi) }, null, kbd);
          el.style.left = (wi * WK) + 'px'; el.style.width = WK + 'px';
          if (k.name.charAt(0) === 'C' || k.midi === 21) he('span', null, k.name, el);
          xs[k.midi] = [wi * WK, wi * WK + WK];
          wi++;
        } else {
          el = he('div', { 'class': 'sim-bk', 'data-midi': String(k.midi) }, null, kbd);
          var x = wi * WK - BK / 2;
          el.style.left = x + 'px'; el.style.width = BK + 'px';
          xs[k.midi] = [x, x + BK];
        }
        el.setAttribute('title', k.name + ' · ' + k.mb + ' ' + k.sensor);
        keyEl[k.midi] = el;
      });
      kbd.style.width = (wi * WK) + 'px';
      var parts = {};
      KEYS.forEach(function (k) {
        var p = parts[k.part] || (parts[k.part] = [1e9, -1e9, k.name, k.name]);
        p[0] = Math.min(p[0], xs[k.midi][0]); p[1] = Math.max(p[1], xs[k.midi][1]); p[3] = k.name;
      });
      Object.keys(parts).forEach(function (pn) {
        var p = parts[pn], b = he('div', { 'class': 'sim-band' }, null, kbd);
        b.style.left = (p[0] + 1) + 'px'; b.style.width = (p[1] - p[0] - 2) + 'px';
        b.textContent = (pn === 'EL' || pn === 'ER') ? pn : pn + ' · ' + p[2] + '~' + p[3];
        b.title = pn === 'EL' ? '왼쪽 끝 부속 EL (A0~B0) → O1 EXT' : (pn === 'ER' ? '오른쪽 끝 부속 ER (C8) → O7 EXT' : '옥타브 모듈 ' + pn);
        bandEl[pn] = b;
      });
    })();

    // velocity choice (shared run ids; colour of the pressed key decides which table)
    var velRun = 'v1';
    (function velButtons() {
      var box = $('sim-kvel');
      KA.colours.white.runs.forEach(function (r) {
        var vw = r.events.midi_vel, vb = KA.colours.black.runs.filter(function (q) { return q.id === r.id; })[0].events.midi_vel;
        var b = he('button', { type: 'button', 'data-run': r.id, 'aria-pressed': String(r.id === velRun) }, null, box);
        b.appendChild(document.createTextNode((RUN_LAB[r.id] || [r.label])[0]));
        he('small', null, '벨로시티 ' + vw + (vw !== vb ? ' / 흑 ' + vb : ''), b);
      });
      box.addEventListener('click', function (e) {
        var b = e.target.closest('button[data-run]');
        if (!b) return;
        velRun = b.getAttribute('data-run');
        [].forEach.call(box.querySelectorAll('button'), function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      });
    })();
    function velFor(k) {
      var col = k.black ? KA.colours.black : KA.colours.white;
      var r = col.runs.filter(function (q) { return q.id === velRun; })[0];
      return { vel: r.events.midi_vel, run: r, col: col };
    }

    // WebAudio: simple additive piano-like voice (not the Salamander sample set)
    var AC = null, master = null, muted = false, sustain = false, voices = {}, sustained = [];
    function audio() {
      if (muted) return null;
      if (!AC) {
        var Ctor = window.AudioContext || window.webkitAudioContext;
        if (!Ctor) return null;
        try {
          AC = new Ctor();
          var comp = AC.createDynamicsCompressor();
          comp.threshold.value = -14; comp.ratio.value = 4;
          master = AC.createGain(); master.gain.value = 0.55;
          master.connect(comp); comp.connect(AC.destination);
        } catch (e) { AC = null; return null; }
      }
      if (AC.state === 'suspended') AC.resume();
      return AC;
    }
    function startVoice(midi, vel) {
      var ac = audio();
      if (!ac) return null;
      var f0 = 440 * Math.pow(2, (midi - 69) / 12), t = ac.currentTime, vn = vel / 127;
      var env = ac.createGain(), lp = ac.createBiquadFilter();
      lp.type = 'lowpass'; lp.frequency.value = Math.min(16000, f0 * (2.5 + 16 * vn * vn) + 400); lp.Q.value = 0.4;
      env.connect(lp); lp.connect(master);
      var amp = 0.05 + 0.42 * Math.pow(vn, 1.6);
      var decay = clamp(3.6 * Math.pow(261.6 / f0, 0.6), 0.35, 10);
      var Bh = 0.00012 * Math.pow(f0 / 261.6, 1.2);
      var N = Math.max(2, Math.min(10, Math.floor(7000 / f0))), oscs = [], sum = 0, n;
      for (n = 1; n <= N; n++) sum += 1 / Math.pow(n, 1.15) * Math.exp(-(n - 1) * (0.6 - 0.38 * vn));
      for (n = 1; n <= N; n++) {
        var a = 1 / Math.pow(n, 1.15) * Math.exp(-(n - 1) * (0.6 - 0.38 * vn)) / sum;
        var o = ac.createOscillator(), g = ac.createGain();
        o.frequency.value = f0 * n * Math.sqrt(1 + Bh * n * n);
        g.gain.setValueAtTime(0, t);
        g.gain.linearRampToValueAtTime(a, t + 0.004);
        g.gain.setTargetAtTime(a * 0.25, t + 0.004, 0.08 + decay * 0.04 / n);
        g.gain.setTargetAtTime(0, t + 0.25, decay / Math.pow(n, 0.7));
        o.connect(g); g.connect(env);
        o.start(t); o.stop(t + decay * 4 + 0.5);
        oscs.push(o);
      }
      env.gain.setValueAtTime(amp, t);
      return { env: env, oscs: oscs, midi: midi };
    }
    function releaseVoice(v, fast) {
      if (!v || !AC) return;
      var t = AC.currentTime;
      try {
        v.env.gain.cancelScheduledValues(t);
        v.env.gain.setValueAtTime(v.env.gain.value, t);
        v.env.gain.setTargetAtTime(0, t, fast ? 0.02 : 0.09);
        v.oscs.forEach(function (o) { try { o.stop(t + (fast ? 0.2 : 0.7)); } catch (e) {} });
      } catch (e) {}
    }
    var down = {};
    function noteOn(midi) {
      var k = byMidi[midi];
      if (!k || down[midi]) return;
      down[midi] = true;
      var vv = velFor(k);
      if (voices[midi]) releaseVoice(voices[midi], true);
      voices[midi] = startVoice(midi, vv.vel);
      keyEl[midi].classList.add('on');
      showKey(k, vv);
    }
    function noteOff(midi) {
      if (!down[midi]) return;
      down[midi] = false;
      keyEl[midi].classList.remove('on');
      var v = voices[midi];
      if (!v) return;
      if (sustain) { sustained.push(v); voices[midi] = null; }
      else { releaseVoice(v); voices[midi] = null; }
    }
    api.noteOn = noteOn; api.noteOff = noteOff;
    $('sim-sus').addEventListener('click', function () {
      sustain = !sustain;
      this.setAttribute('aria-pressed', String(sustain));
      if (!sustain) { sustained.forEach(function (v) { releaseVoice(v); }); sustained = []; }
      showPedal();
    });
    $('sim-mute').addEventListener('click', function () {
      muted = !muted;
      this.setAttribute('aria-pressed', String(muted));
      if (muted) {
        Object.keys(voices).forEach(function (m) { releaseVoice(voices[m], true); voices[m] = null; });
        sustained.forEach(function (v) { releaseVoice(v, true); }); sustained = [];
      }
    });

    // pointer input (glide across keys while held)
    var ptr = {};
    function keyAt(x, y) {
      var el = document.elementFromPoint(x, y);
      el = el && el.closest ? el.closest('.sim-wk,.sim-bk') : null;
      return el && kbd.contains(el) ? parseInt(el.getAttribute('data-midi'), 10) : null;
    }
    kbd.addEventListener('pointerdown', function (e) {
      var m = keyAt(e.clientX, e.clientY);
      if (m === null) return;
      if (e.pointerType === 'mouse') e.preventDefault();
      ptr[e.pointerId] = m; noteOn(m);
    });
    kbd.addEventListener('pointermove', function (e) {
      if (!(e.pointerId in ptr) || ptr[e.pointerId] === null) return;
      var m = keyAt(e.clientX, e.clientY);
      if (m !== null && m !== ptr[e.pointerId]) { noteOff(ptr[e.pointerId]); ptr[e.pointerId] = m; noteOn(m); }
    });
    function ptrEnd(e) { if (e.pointerId in ptr) { if (ptr[e.pointerId] !== null) noteOff(ptr[e.pointerId]); delete ptr[e.pointerId]; } }
    kbd.addEventListener('pointerup', ptrEnd);
    kbd.addEventListener('pointercancel', ptrEnd);
    kbd.addEventListener('pointerleave', function (e) { if (e.pointerType === 'mouse') ptrEnd(e); });
    // computer keys
    var KMAP = { KeyA: 0, KeyW: 1, KeyS: 2, KeyE: 3, KeyD: 4, KeyF: 5, KeyT: 6, KeyG: 7, KeyY: 8, KeyH: 9, KeyU: 10, KeyJ: 11, KeyK: 12, KeyO: 13, KeyL: 14, KeyP: 15, Semicolon: 16 };
    var base = 60, kdown = {};
    function octLabel() { setText('sim-oct', byMidi[base] ? byMidi[base].name : 'C' + (base / 12 - 1)); }
    octLabel();
    document.addEventListener('keydown', function (e) {
      if (sec.hidden || e.ctrlKey || e.metaKey || e.altKey) return;
      var tg = e.target;
      if (tg && (tg.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(tg.tagName))) return;
      if (tg && tg.closest && tg.closest('#sim-press')) return;
      if (e.code === 'KeyZ' || e.code === 'KeyX') {
        if (!e.repeat) { base = clamp(base + (e.code === 'KeyZ' ? -12 : 12), 24, 96); octLabel(); }
        e.preventDefault(); return;
      }
      if (!(e.code in KMAP)) return;
      e.preventDefault();
      if (e.repeat || kdown[e.code] !== undefined) return;
      var m = base + KMAP[e.code];
      if (m < 21 || m > 108) return;
      kdown[e.code] = m; noteOn(m);
    });
    document.addEventListener('keyup', function (e) {
      if (kdown[e.code] !== undefined) { noteOff(kdown[e.code]); delete kdown[e.code]; }
    });
    window.addEventListener('blur', function () { Object.keys(kdown).forEach(function (c) { noteOff(kdown[c]); }); kdown = {}; });

    // USB cable of the key's module: cables.csv row (W201~W207) carried in system.json as k.usb_cable / k.usb_port
    function usbOf(k) {
      var c = (SYS.cables && SYS.cables[k.usb]) || {};
      var cable = k.usb_cable || c['선'] || '', port = k.usb_port || c['한쪽'] || '허브';
      var m = /(\d+(?:\.\d+)?\s*c?m)\s*$/.exec(cable);
      return { cable: cable, port: port, len: m ? m[1] : '' };
    }
    // signal chain highlight + info panel
    function showKey(k, vv) {
      Object.keys(bandEl).forEach(function (p) { bandEl[p].classList.toggle('on', p === k.part); });
      var isEnd = k.part === 'EL' || k.part === 'ER';
      setText('sim-c1', k.name + (k.black ? ' (흑건)' : ' (백건)'));
      setText('sim-c1b', 'x ' + f(k.x_sensor, 2) + ' · y67');
      setText('sim-c2', k.sensor);
      setText('sim-c2b', (isEnd ? k.board + ' 기판 · ' : 'SB ' + k.mb + ' · ') + 'OUT');
      setText('sim-c3a', isEnd ? '리드 → JST-XH → 연장선' : '16심 리본 2651-16P');
      setText('sim-c3', isEnd ? (k.part === 'EL' ? 'W401 → W403' : 'W411 → W413') : k.ribbon + ' ' + k.j_pin + '번');
      setText('sim-c3b', isEnd ? 'J302.' + k.j_pin + ' = ' + k.ext : 'J201.' + k.j_pin + ' → J301.' + k.j_pin);
      setText('sim-c4', k.mux_ch + ' (J1.' + k.mux_hdr.split('.')[1] + ')');
      setText('sim-c4b', 'S3~S0 = ' + k.sel_bits);
      setText('sim-c5', 'GP26 ADC0');
      setText('sim-c5b', k.mb + ' · 약 ' + f(SYS.scan[k.mb].khz, 1) + ' kHz');
      setText('sim-c6', k.usb + (usbOf(k).len ? ' ' + usbOf(k).len : ''));
      setText('sim-c7', 'note-on ' + k.midi + ' · ' + vv.vel);
      setText('sim-c7b', "'" + k.usb_name + "'");
      setText('sim-c8', k.name + ' ' + f(k.freq, 2) + ' Hz');
      for (var i = 1; i <= 14; i++) {
        var n = $('sim-n' + i);
        if (!n) continue;
        n.classList.add('on');
        if (!reduce) { n.classList.remove('flash'); void n.getBoundingClientRect(); n.classList.add('flash'); }
      }
      // info panel
      var box = $('sim-info');
      box.textContent = '';
      he('h4', null, k.name + ' · MIDI ' + k.midi + ' · ' + f(k.freq, 2) + ' Hz', box);
      var dl = he('dl', null, null, box);
      function row(a, b, mono) { he('dt', null, a, dl); var dd = he('dd', null, null, dl); if (mono) he('span', { 'class': 'mono' }, b, dd); else dd.textContent = b; return dd; }
      var x0 = SYS.mod_x0[k.mb];
      row('부속', isEnd ? (k.part === 'EL' ? '왼쪽 끝 부속 EL (x0~47) → 모듈 O1이 읽음' : '오른쪽 끝 부속 ER (x1198.5~1222) → 모듈 O7이 읽음')
        : '옥타브 모듈 ' + k.mb + ' (x' + f(x0, 1) + '~' + f(x0 + 164.5, 1) + ')');
      row('센서', k.sensor + ' DRV5055A2 · ' + (isEnd ? k.board + ' 기판' : 'SB 기판') + ' · x' + f(k.x_sensor, 2) + ' mm, y67, 소자 z' + (k.black ? '10.15' : '12.68'));
      var col = k.black ? KA.colours.black : KA.colours.white;
      row('자석', 'Ø5×2 N35, S극 아래 · ' + (k.black ? '흑건' : '백건') + ' 대표값: 간격 쉼 ' + f(col.gap_rest_design, 2) + ' → 바닥 ' + f(col.gap_bottom_rigid, 2) + ' mm (ADC ' + col.adc.rest_design + ' → ' + col.adc.bottom_rigid + ')');
      var pd = row('신호선', '');
      var ol = he('ol', null, null, pd);
      k.path.forEach(function (s) { he('li', null, s, ol); });
      if (k.wires && k.wires.length) {
        row('선 (자르는 길이)', k.wires.map(function (w) {
          return w.W + ' ' + w['심 번호'] + '번 심 (' + w['색'] + ') ' + w['끝 A'] + '.' + w['A 핀'] + ' → ' + w['끝 B'] + '.' + w['B 핀'] + ', ' + w['자르는 길이'];
        }).join(' / '));
      }
      var rt = k.mb_route.filter(function (w) { return /A302/.test(w.a) || /A302/.test(w.b); });
      if (rt.length) row('제어 기판 배선', rt.map(function (w) { return w.a + ' (' + f(w.ax, 2) + ', ' + f(w.ay, 2) + ') → ' + w.b + ' (' + f(w.bx, 2) + ', ' + f(w.by, 2) + ') 약 ' + w.len_mm + ' mm'; }).join(' / '), true);
      row('먹스', 'A302 CD74HC4067 채널 ' + k.mux_ch + ' (심볼 핀 ' + k.mux_sym_pin + ' = 모듈 ' + k.mux_hdr + '), 선택 GP5~GP2(S3~S0) = ' + k.sel_bits + ', 공통 SIG(J2.8) → MUX_SIG');
      var sa = SYS.scan_assume || { settle_us: 4, conv_us: 2 };
      row('ADC', k.adc + ' · ' + k.adc_pad + ' · 채널 ' + SYS.scan[k.mb].channels + '개를 약 ' + f(SYS.scan[k.mb].period_us, 0) + ' µs마다 한 바퀴, 건반마다 약 ' + f(SYS.scan[k.mb].khz, 1) +
        ' kHz (추정: 채널마다 ' + f(sa.settle_us, 0) + ' µs 대기 + ' + f(sa.conv_us, 0) + ' µs 변환)');
      var ub = usbOf(k), w209 = (SYS.cables && SYS.cables.W209) || {};
      row('USB', k.usb + ' (' + ub.cable + ') → A604 ' + ub.port + ' → W209' + (w209['선'] ? ' (' + w209['선'] + ')' : '') + ' → Pi 5 · 장치 이름 ‘' + k.usb_name + '’');
      row('MIDI', 'note-on 음 ' + k.midi + ', 세기 ' + vv.vel + ' (' + (RUN_LAB[vv.run.id] || [vv.run.label])[0] + ', 추정 앞끝 ' + f(vv.run.events.v_front_est, 2) + ' m/s)');
      row('소리', 'FluidSynth (Salamander) → USB 동글 A701 → J701(헤드폰 잭 노멀) → J702 → HPF 2 µF + 1 kΩ → TPA3110 A702 → XT60 → LS701 · LS702');
      if (isEnd) he('p', { 'class': 'muted' }, '끝 부속 선에는 센서 옆 1 kΩ 직렬 저항과 제어 기판 쪽 100 kΩ 풀다운이 있어, 끝 부속을 뽑아도 입력이 떠서 유령 음이 나지 않습니다(△8).', box);
    }
    function showPedal() {
      if (!sustain) return;
      var box = $('sim-info');
      box.textContent = '';
      he('h4', null, '서스테인 페달 · MIDI CC64', box);
      var ol = he('ol', null, null, box);
      SYS.pedal.path.forEach(function (s) { he('li', null, s, ol); });
      he('p', { 'class': 'muted' }, '페달 안 센서 ' + SYS.pedal.sensor + '. 밟으면 손을 떼도 소리가 이어집니다.', box);
    }

    /* ------------------------------------------------------------------ power */
    var PW = SYS.power, pw = { amp: 4, vb: PW.batt.v_nom, scr: true, peak: false };
    var pwEl = {};
    (function buildPower() {
      var svg = $('sim-pwsvg');
      function box(id, x, y, w, h, t, s, v) {
        var g = sv('g', null, svg);
        pwEl[id] = { rect: sv('rect', { x: x, y: y, width: w, height: h, rx: 8, 'class': 'pw-box' }, g) };
        sv('text', { x: x + 10, y: y + 20, 'class': 'pw-t' }, g).textContent = t;
        sv('text', { x: x + 10, y: y + 37, 'class': 'pw-s' }, g).textContent = s;
        pwEl[id].v = sv('text', { x: x + 10, y: y + 54, 'class': 'pw-v' }, g);
        if (v) pwEl[id].v.textContent = v;
        return g;
      }
      function wire(id, d, cls) { pwEl[id] = sv('path', { d: d, 'class': cls }, svg); }
      wire('w0', 'M120 60 H150', 'pw-w12'); wire('w1', 'M260 60 H290', 'pw-w12'); wire('w2', 'M400 60 H430', 'pw-w12');
      wire('w3', 'M540 60 H600 V40 H620', 'pw-w12'); wire('w3b', 'M600 60 V200 H620', 'pw-w12');
      wire('w4', 'M730 40 H745 V35 H760', 'pw-w5'); wire('w4b', 'M745 40 V125 H760', 'pw-w5');
      wire('w5', 'M730 200 H760', 'pw-wsp');
      box('bt', 10, 20, 110, 70, 'BT601 전지', 'LiFePO4 12.8 V 6 Ah');
      box('xt', 150, 20, 110, 70, 'XT60 (빨강)', 'X605 ⇄ X606 · W601');
      box('fu', 290, 20, 110, 70, 'F601 퓨즈', '5 A ATO 블레이드');
      box('sw', 430, 20, 110, 70, 'SW601 스위치', 'KCD1-104 · +12V8 버스');
      box('bk', 620, 5, 110, 70, 'A602 강압', 'XL4016 → 5.1 V');
      box('pi', 760, 0, 152, 70, 'Pi 5 A603', '+ 화면 2.15 W · 동글');
      box('hb', 760, 90, 152, 70, '허브 A604', 'RP2040 8개 · 센서 89개');
      box('am', 620, 165, 110, 70, 'A702 앰프', 'TPA3110 · PVCC 버스');
      box('sp', 760, 165, 152, 70, '스피커 L · R', 'XT60 파랑 SPK');
      sv('text', { x: 10, y: 130, 'class': 'pw-s' }, svg).textContent = '★ 별 접지점 = 강압 IN− (전지 −, 앰프 GND가 여기서만 만남)';
      pwEl.vbus = sv('text', { x: 430, y: 118, 'class': 'pw-v' }, svg);
      pwEl.cut = sv('text', { x: 10, y: 150, 'class': 'pw-s' }, svg);
      sv('text', { x: 10, y: 285, 'class': 'pw-s' }, svg).textContent = '선 굵기 = 전류. 주황 12.8 V 버스, 파랑 5.1 V, 초록 스피커 출력. 값: SCH-06 전원 예산, 퓨즈 F601은 bom.csv.';
    })();
    function updPower() {
      var L = PW.loads, B = PW.batt;
      var disp = pw.scr ? L.disp_w : 0;
      var five = L.pi_w + L.hub_w + L.dongle_w + disp, buckIn = five / L.eff;
      var ampAvg = pw.amp, ampNow = pw.peak ? 2 * B.amp_w_ch / B.amp_eff : ampAvg;
      var P = buckIn + ampNow, I = P / pw.vb, I10 = P / B.v_min;
      var Pavg = buckIn + ampAvg, hours = B.wh * B.usable / Pavg;
      var iBuck = five / L.v5, iPi = (L.pi_w + L.dongle_w + disp) / L.v5, iHub = L.hub_w / L.v5, iAmp = ampNow / pw.vb;
      setText('sim-vol-o', f(pw.amp, 1) + ' W');
      setText('sim-vb-o', f(pw.vb, 1) + ' V');
      setText('sim-pw-p', f(P, 1) + ' W');
      setText('sim-pw-i', f(I, 2) + ' A');
      setText('sim-pw-is', '퓨즈 ' + f(B.fuse_a, 0) + ' A의 ' + f(100 * I / B.fuse_a, 0) + ' % (전지 = 퓨즈 = 스위치 전류)');
      setText('sim-pw-b', f(iBuck, 2) + ' A');
      setText('sim-pw-pi', f(iPi, 2) + ' A');
      setText('sim-pw-h', f(hours, 1) + ' h');
      setText('sim-pw-hs', '연주 시간 (' + f(B.wh, 1) + ' Wh × ' + B.usable + ' ÷ 평균 ' + f(Pavg, 1) + ' W)');
      setText('sim-pw-10', f(I10, 2) + ' A');
      var bar = $('sim-pw-bar');
      bar.style.width = clamp(100 * I / B.fuse_a, 0, 100) + '%';
      bar.classList.toggle('warn', I > 0.8 * B.fuse_a);
      pwEl.bt.v.textContent = f(pw.vb, 1) + ' V · ' + f(P, 1) + ' W';
      pwEl.xt.v.textContent = f(I, 2) + ' A';
      pwEl.fu.v.textContent = f(I, 2) + ' / ' + f(B.fuse_a, 0) + ' A';
      pwEl.sw.v.textContent = '+12V8 = ' + f(pw.vb, 1) + ' V';
      pwEl.bk.v.textContent = f(buckIn / pw.vb, 2) + ' A → ' + f(iBuck, 2) + ' A';
      pwEl.pi.v.textContent = f(iPi, 2) + ' A' + (pw.scr ? ' (화면 켬)' : ' (화면 끔)');
      pwEl.hb.v.textContent = f(iHub, 2) + ' A · ' + f(L.hub_w, 1) + ' W';
      pwEl.am.v.textContent = f(iAmp, 2) + ' A · ' + f(ampNow, 1) + ' W';
      pwEl.sp.v.textContent = pw.peak ? '최대 2 × ' + f(B.amp_w_ch, 0) + ' W' : '평균 약 ' + f(ampAvg * 0.8, 1) + ' W 이하';
      var wv = function (a) { return f(clamp(1.5 + 2.6 * a, 1.5, 12), 2); };
      ['w0', 'w1', 'w2'].forEach(function (k) { pwEl[k].setAttribute('stroke-width', wv(I)); });
      pwEl.w3.setAttribute('stroke-width', wv(buckIn / pw.vb)); pwEl.w3b.setAttribute('stroke-width', wv(iAmp));
      pwEl.w4.setAttribute('stroke-width', wv(iPi)); pwEl.w4b.setAttribute('stroke-width', wv(iHub));
      pwEl.w5.setAttribute('stroke-width', wv(iAmp));
      pwEl.vbus.textContent = '버스 ' + f(pw.vb, 1) + ' V (강압은 약 ' + f(B.buck_min_v, 0) + ' V 이상, 앰프 8~26 V에서 동작)';
      pwEl.cut.textContent = pw.vb <= B.v_min + 1e-9 ? 'BMS 저전압 차단 직전 (보통 약 10.0 V): 이 아래에서 전지가 출력을 끊어 모두 한꺼번에 꺼집니다.' : '전지 끝 10.0 V에서는 같은 부하가 ' + f(I10, 2) + ' A를 씁니다.';
      setText('sim-pw-note', '평균 ' + f(PW.budget.avg[0], 2) + '~' + f(PW.budget.avg[1], 2) + ' W (전류 ' + f(PW.budget.avg_a[0], 2) + '~' + f(PW.budget.avg_a[1], 2) + ' A), 가장 센 순간 ' + f(PW.budget.peak, 1) +
        ' W (' + f(PW.budget.peak_a, 2) + ' A, 10 V에서 ' + f(PW.budget.peak_a_min_v, 2) + ' A), 연주 시간 ' + f(PW.budget.run[1], 1) + '~' + f(PW.budget.run[0], 1) +
        ' h (SCH-06). F601은 ' + f(B.fuse_a, 0) + ' A ATO 블레이드 퓨즈입니다. 가장 센 순간도 10 V에서 ' + f(PW.budget.peak_a_min_v, 2) + ' A(정격의 ' +
        f(100 * PW.budget.peak_a_min_v / B.fuse_a, 0) + ' %)라 연주 중에는 끊기지 않습니다. 켤 때 끊기면 7.5 A ATO(갈색)로 바꿉니다(bom.csv F601). 앰프는 12.8 V에서 약 8 W/ch라 소프트웨어 음량 상한을 약 4 dB 낮춥니다.');
    }
    $('sim-vol').addEventListener('input', function () { pw.amp = parseFloat(this.value); updPower(); });
    $('sim-vb').addEventListener('input', function () { pw.vb = parseFloat(this.value); updPower(); });
    $('sim-scr').addEventListener('click', function () { pw.scr = !pw.scr; this.setAttribute('aria-pressed', String(pw.scr)); updPower(); });
    $('sim-peak').addEventListener('click', function () { pw.peak = !pw.peak; this.setAttribute('aria-pressed', String(pw.peak)); updPower(); });
    updPower();

    /* ------------------------------------------------------------------ touchscreen fold */
    var TS = SYS.touch, tsG = null, legG = null, tsAng = 25, tsRaf = 0;
    (function buildTouch() {
      var svg = $('sim-tsvg');
      if (!TS) { svg.parentNode.parentNode.hidden = true; return; }
      var AY = TS.axis[0], AZ = TS.axis[1];
      (TS.static || []).forEach(function (s) { sv('path', { d: ringsPath(s.rings), 'class': 'm-frame' }, svg).appendChild(document.createElementNS(NS, 'title')).textContent = s.name; });
      if (TS.leg) { legG = sv('g', null, svg); sv('path', { d: ringsPath(TS.leg.rings), 'class': 'm-lever' }, legG).appendChild(document.createElementNS(NS, 'title')).textContent = TS.leg.name + ' (x' + TS.leg.x + ', 사용 자세)'; }
      tsG = sv('g', null, svg);
      TS.parts.forEach(function (p) {
        var cl = p.kind === 'electronics' ? 'm-keyb' : (p.id === 'TS-WINCOVER' ? 'm-sbar' : 'm-lever');
        // rings are (u, w): drawn as (x = u, y = w) and placed by the pose matrix
        var d = '';
        p.rings.forEach(function (r) { d += 'M' + r.map(function (q) { return q[0] + ',' + q[1]; }).join('L') + 'Z'; });
        sv('path', { d: d, 'class': cl }, tsG).appendChild(document.createElementNS(NS, 'title')).textContent = p.name;
      });
      sv('circle', { cx: AY, cy: -AZ, r: 1.6, 'class': 'm-steel' }, svg);
      sv('path', { d: 'M' + (AY - 6) + ',' + (-AZ) + 'H' + (AY + 6) + 'M' + AY + ',' + (-AZ - 6) + 'V' + (-AZ + 6), 'class': 'm-axis' }, svg);
      sv('text', { x: 201, y: -AZ - 9, 'class': 't-lab' }, svg).textContent = '경첩 축';
      sv('text', { x: 201, y: -AZ - 5, 'class': 't-lab2' }, svg).textContent = 'y' + AY + ' z' + AZ;
      tsG.lab = sv('text', { x: 205, y: -195, 'class': 't-press' }, svg);
    })();
    function setTouch(a) {
      if (!tsG) return;
      tsAng = a;
      var th = a * Math.PI / 180, s = Math.sin(th), c = Math.cos(th), AY = TS.axis[0], AZ = TS.axis[1], AU = TS.axis_uw[0], AW = TS.axis_uw[1];
      tsG.setAttribute('transform', mStr([s, -c, c, s, AY - AU * s - AW * c, -AZ + AU * c - AW * s]));
      if (legG) legG.style.display = a <= TS.tilt_use + 0.01 ? '' : 'none';
      tsG.lab.textContent = '기울기 ' + f(a, 1) + '° (수직에서 뒤로)';
      $('sim-tang').value = String(a);
      setText('sim-tang-o', f(a, 1) + '°');
      [].forEach.call($('sim-tpose').querySelectorAll('button'), function (b) { b.setAttribute('aria-pressed', String(Math.abs(parseFloat(b.getAttribute('data-th')) - a) < 0.01)); });
    }
    $('sim-tang').addEventListener('input', function () { if (tsRaf) cancelAnimationFrame(tsRaf); tsRaf = 0; setTouch(parseFloat(this.value)); });
    $('sim-tpose').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-th]');
      if (!b) return;
      var to = parseFloat(b.getAttribute('data-th')), from = tsAng;
      if (tsRaf) cancelAnimationFrame(tsRaf);
      if (reduce) { setTouch(to); return; }
      var t0 = performance.now(), dur = 300 + 12 * Math.abs(to - from);
      (function step(now) {
        var k = clamp((now - t0) / dur, 0, 1), e2 = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        setTouch(from + (to - from) * e2);
        tsRaf = k < 1 ? requestAnimationFrame(step) : 0;
      })(t0);
    });
    if (TS) setTouch(TS.tilt_use);

    /* ------------------------------------------------------------------ self checks */
    (function checks() {
      var ul = $('sim-chklist'), bad = 0;
      KA.checks.forEach(function (c) {
        var li = he('li', { 'class': c.ok ? '' : 'bad' }, null, ul);
        he('b', null, c.ok ? '통과' : '확인', li);
        he('span', null, c.name + (c.detail ? ' — ' + c.detail : ''), li);
        if (!c.ok) bad++;
      });
      setText('sim-chk-sum', KA.checks.length + '건 중 ' + (KA.checks.length - bad) + '건 통과. 데이터 만든 때 ' + KA.meta.generated + ', 스크립트 ' + KA.meta.script + '.');
    })();

    // first view
    setRun('white', 'v1');
    if (!reduce) play();
  }
})();
