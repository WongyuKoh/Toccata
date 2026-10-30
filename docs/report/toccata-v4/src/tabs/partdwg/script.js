/* 03 부품 도면·출력 파일 (p-partdwg): filters + search, in-page sheet viewer, zip downloads through the downloads capability,
   3D views (2026-10-30): the print on the bed, its places in the instrument, the instrument painted by print file.
   API: window.toccata.partdwg = { open(code, mode), codeOf(file) }
     open('P-01-01')            opens the sheet viewer on that part (also switches the tab via the hash router)
     open('P-01-01', 'print')   the same in 3D: 'dwg' (default) | 'print' (the STL on the bed) | 'place' (its places in the instrument)
     codeOf('stl/print/01_건반/백건_C__7개.stl' or 'hardware/mechanical/cad/stl/...')  -> 'P-01-01' | null
   Data for other tabs: fin/parts/index.json (by_file: print file -> code; parts[]: code, name, qty, sizes, zip/svg paths). */
(function () {
  'use strict';
  var sec = document.getElementById('p-partdwg');
  if (!sec) return;
  var T = window.toccata = window.toccata || {};
  var V3 = null;

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
  new MutationObserver(function () { if (!sec.hidden) { start(); if (V3) V3.wake(); } }).observe(sec, { attributes: true, attributeFilter: ['hidden'] });
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
    if (V3) V3.filter(group);
  }
  chips.forEach(function (b) {
    b.addEventListener('click', function () {
      group = b.getAttribute('data-g');
      chips.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      apply();
    });
  });
  if (q) q.addEventListener('input', apply);

  // ---- viewer: drawing, or 3D (print shape / place in the instrument)
  var viewer = sec.querySelector('#partdwg-viewer');
  var vimg = sec.querySelector('#partdwg-vimg');
  var vbody = sec.querySelector('#partdwg-vbody');
  var vtitle = sec.querySelector('#partdwg-vtitle');
  var vopen = sec.querySelector('#partdwg-vopen');
  var v3box = sec.querySelector('#partdwg-v3d');
  var zoomBox = sec.querySelector('.partdwg-zoom');
  var zoomBtns = [].slice.call(sec.querySelectorAll('.partdwg-zoom button'));
  var modeBtns = [].slice.call(sec.querySelectorAll('.partdwg-mode button'));
  var placeBtn = sec.querySelector('.partdwg-mode [data-m="place"]');
  var current = null, lastFocus = null, vmode = 'dwg';
  function setZoom(z) {
    vbody.classList.remove('z2', 'z4');
    if (z !== '1') vbody.classList.add('z' + z);
    zoomBtns.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-z') === z ? 'true' : 'false'); });
  }
  function setMode(m) {
    if (!v3box) m = 'dwg';
    vmode = m;
    modeBtns.forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-m') === m ? 'true' : 'false'); });
    var d3 = m !== 'dwg';
    vbody.hidden = d3;
    if (v3box) v3box.hidden = !d3;
    if (zoomBox) zoomBox.hidden = d3;
    vopen.hidden = d3;
  }
  function show(card) {
    if (!card) return;
    current = card;
    var svg = card.getAttribute('data-svg'), code = card.getAttribute('data-code'), name = card.getAttribute('data-name');
    vtitle.textContent = code + ' · ' + name;
    vopen.href = svg;
    if (placeBtn) {
      placeBtn.disabled = card.getAttribute('data-place') !== '1';
      placeBtn.title = placeBtn.disabled ? '조립에 들어가지 않는 출력물(공구·지그·예비)이라 자리가 없습니다' : '';
      if (vmode === 'place' && placeBtn.disabled) setMode('print');
    }
    if (vmode === 'dwg') {
      vimg.src = svg;
      vimg.alt = code + ' ' + name + ' 부품도';
    } else if (V3) {
      V3.show(card, vmode);
    }
  }
  function openViewer(card, m) {
    if (!card) return;
    lastFocus = document.activeElement;
    setMode(m || 'dwg');
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
    if (vmode !== 'dwg' && V3) V3.leave();
    setMode('dwg');
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
    var mb = e.target.closest('[data-m]');
    if (mb && !mb.disabled) {
      var was = vmode;
      setMode(mb.getAttribute('data-m'));
      if (vmode === 'dwg' && was !== 'dwg' && V3) V3.leave();
      show(current);
      return;
    }
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
      var f = [].slice.call(viewer.querySelectorAll('button,a[href]')).filter(function (x) { return x.offsetParent !== null && !x.disabled; });
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
    } else if (act === 'v3d') {
      openViewer(b.closest('.partdwg-card'), 'print');
    } else if (act === 'dl') {
      var host = b.closest('.partdwg-card') || b.closest('.partdwg-all');
      var src = b.hasAttribute('data-zip') ? b : host;
      save(b, src.getAttribute('data-zip'), src.getAttribute('data-zipname'), src.getAttribute('data-zipbytes'),
        host && host.querySelector('.partdwg-msg'));
    }
  });

  // ---- 3D (2026-10-30). Meshes: fin/parts3d (hardware/mechanical/cad/src/part_meshes.py) - every print STL welded + uint16,
  //      print aids (tear-off key comb, bed posts) after the part's own triangles. Assembly: the 04 tab's
  //      cad/toccata.glb.b64.txt (node name = part id, uint16 KHR_mesh_quantization); the ids printed in pieces
  //      (index.json split: CU-PLY-BOTTOM / CU-PLY-BACK) are drawn from their piece STLs. One WebGL canvas moves between
  //      the overview box and the viewer and renders only when something changed. three.js r128 from cdnjs, shared with
  //      the other tabs through window.toccata.three. Model frame: mm, x along the keyboard, y front -> back, z up.
  V3 = (function () {
    var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
    var IDX_URL = 'fin/parts3d/index.json', GLB_URL = 'cad/toccata.glb.b64.txt';
    var BED = 256, FOV = 30;                       // Bambu P1S plate (mm)
    var HUE = { '01': 214, '02': 24, '03': 134, '04': 276, '05': 188, '06': 330, '07': 46, '09': 352, 'EX': 300 };
    var GKO = { '01': '건반', '02': '레버 캐리어·덮개', '03': '프레임', '04': '센서 바·패드 바·가림판·마개', '05': '본체 출력물',
                '06': '출력 공구', '07': '터치스크린', '09': '기판 지그', 'EX': '선택·대안·예비' };
    var PLAIN = 0xaebdcd, FADE = 0xc4cad3, BUY = 0x97a0ab, HI = 0x2563eb;
    var coarse = !!(window.matchMedia && matchMedia('(pointer: coarse)').matches);
    var reduce = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
    var HINT_PAGE = coarse ? '옆으로 밀어 돌리기 · 두 손가락 확대 · 조각을 누르면 파일 이름'
                           : '끌어서 돌리기 · 오른쪽(Shift) 끌기 이동 · Ctrl+휠 확대 · 조각 클릭 = 파일 이름';
    var HINT_FULL = coarse ? '한 손가락 돌리기 · 두 손가락 확대' : '끌어서 돌리기 · 오른쪽(Shift) 끌기 이동 · 휠 확대 · 두 번 클릭 = 처음 시점';
    var TH = null, renderer = null, canvas = null, raf = 0, view = null, ro = null, edgeMat = null;
    var IX = null, ixP = null, grpP = {}, geoP = {}, mats = {}, cols = {}, edgeOf = {};
    var A = null, aP = null, edgesStarted = false;
    var S = { ex: 0, ex0: 0, exT: 0, t0: 0, buy: true, group: 'all', code: null, sel: null };
    var ovBox = sec.querySelector('#partdwg-ov'), ovStage = sec.querySelector('#partdwg-ovstage');
    var ovInfo = ovBox && ovBox.querySelector('.partdwg-ovinfo'), ovLeg = ovBox && ovBox.querySelector('.partdwg-ovleg');
    var dStage = v3box, dInfo = dStage && dStage.querySelector('.partdwg-v3info');
    var OV = null, PL = null, PR = null, want = null, wantMode = 'dwg', ovTried = false;

    function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
    function hex6(n) { return ('00000' + n.toString(16)).slice(-6); }
    function f1(v) { return String(Math.round(v * 10) / 10); }
    function cp(c) { return { tx: c.tx, ty: c.ty, tz: c.tz, az: c.az, el: c.el, dist: c.dist }; }

    // ---------------------------------------------------------------- loading
    function ensureThree() {
      if (window.THREE && window.THREE.WebGLRenderer) return Promise.resolve();
      if (!T.three) {
        T.three = new Promise(function (res, rej) {
          var s = document.createElement('script');
          s.src = THREE_URL; s.async = true;
          s.onload = function () { res(); };
          s.onerror = function () { T.three = null; rej(new Error('three.js를 받지 못했습니다')); };
          document.head.appendChild(s);
        });
      }
      return T.three;
    }
    function getJSON(u) { return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); }); }
    function index() {
      if (!ixP) {
        ixP = getJSON(IDX_URL).then(function (d) { IX = d; return d; });
        ixP.catch(function () { ixP = null; });
      }
      return ixP;
    }
    function boot() {
      return ensureThree().then(function () {
        TH = window.THREE;
        if (!ensureRenderer()) throw new Error('이 브라우저에서 WebGL을 쓸 수 없습니다');
        return index();
      });
    }
    function b64u8(s) {
      var bin = atob(s), n = bin.length, u = new Uint8Array(n);
      for (var i = 0; i < n; i++) u[i] = bin.charCodeAt(i);
      return u;
    }
    function geomOf(code) {
      if (!geoP[code]) {
        geoP[code] = index().then(function (ix) {
          var f = ix.files[code];
          if (!f) throw new Error('3D 데이터가 없습니다: ' + code);
          if (!grpP[f]) { grpP[f] = getJSON(f); grpP[f].catch(function () { delete grpP[f]; }); }
          return grpP[f];
        }).then(function (d) {
          var e = d.parts[code], b = e.b, n = e.nv, q = new Uint16Array(b64u8(e.p).buffer), pos = new Float32Array(n * 3);
          var sx = (b[3] - b[0]) / 65535, sy = (b[4] - b[1]) / 65535, sz = (b[5] - b[2]) / 65535;
          for (var i = 0; i < n; i++) {
            pos[3 * i] = b[0] + q[3 * i] * sx; pos[3 * i + 1] = b[1] + q[3 * i + 1] * sy; pos[3 * i + 2] = b[2] + q[3 * i + 2] * sz;
          }
          var ib = b64u8(e.i).buffer, g = new TH.BufferGeometry();
          g.setAttribute('position', new TH.BufferAttribute(pos, 3));
          g.setIndex(new TH.BufferAttribute(e.i4 ? new Uint32Array(ib) : new Uint16Array(ib), 1));
          g.addGroup(0, e.na * 3, 0);
          if (e.nt > e.na) g.addGroup(e.na * 3, (e.nt - e.na) * 3, 1);
          g.computeBoundingBox(); g.computeBoundingSphere();
          g.userData = { b: b, aids: e.nt - e.na, sup: e.sup || null };
          return g;
        });
        geoP[code].catch(function () { delete geoP[code]; });
      }
      return geoP[code];
    }
    function loading(stage, t) {
      var el = stage && stage.querySelector('.partdwg-v3load');
      if (!el) return;
      el.hidden = !t;
      if (t) el.textContent = t;
    }
    function hint(stage, t) {
      var el = stage === ovStage ? ovBox && ovBox.querySelector('.partdwg-v3hint') : dStage && dStage.querySelector('.partdwg-v3hint');
      if (el) el.textContent = t;
    }

    // ---------------------------------------------------------------- materials, colours
    function mat(hex, mode) {
      var k = hex + ':' + mode;
      if (mats[k]) return mats[k];
      var m = new TH.MeshPhongMaterial({ color: hex, flatShading: true, shininess: 18, specular: 0x161616, side: TH.DoubleSide,
                                         polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
      var op = { g: 0.12, h: 0.05, f: 0.3, q: 0.15 }[mode];         // g / h bought (overview / place), f / q other prints
      if (op) { m.transparent = true; m.opacity = op; m.depthWrite = false; }
      else if (mode === 's') { m.emissive = new TH.Color(0x1f5fbf); m.emissiveIntensity = 0.45; }
      return (mats[k] = m);
    }
    function colOf(code) {                       // hue per folder, lightness / saturation per file
      if (cols[code] != null) return cols[code];
      var p = IX.parts[code] || { g: '' }, list = IX.groups[p.g] || [code], k = Math.max(0, list.indexOf(code));
      var h = ((HUE[p.g] || 0) + [0, -16, 14, -7, 21, -23, 7][k % 7] + 360) % 360;
      var l = [0.54, 0.68, 0.42, 0.61, 0.75, 0.48, 0.35][k % 7], s = [0.64, 0.5, 0.58, 0.72][k % 4];
      return (cols[code] = new TH.Color().setHSL(h / 360, s, l).getHex());
    }
    function matColor(m) { return /흰색/.test(m) ? 0xefede6 : /검정/.test(m) ? 0x3b3f46 : /회색/.test(m) ? 0x9aa1aa : PLAIN; }
    function tokenColor(name, fb) {             // a page colour token as a three.js colour (print aids = --amber, background = --card)
      var c = getComputedStyle(sec).getPropertyValue(name).trim();
      try { return c ? new TH.Color(c).getHex() : fb; } catch (e) { return fb; }
    }
    function bgColor() { return new TH.Color(tokenColor('--card', 0xffffff)); }

    // ---------------------------------------------------------------- renderer, views, camera
    function ensureRenderer() {
      if (renderer) return true;
      canvas = document.createElement('canvas');
      canvas.className = 'partdwg-v3c';
      try { renderer = new TH.WebGLRenderer({ canvas: canvas, antialias: true }); } catch (e) { renderer = null; return false; }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      edgeMat = new TH.LineBasicMaterial({ color: 0x1b2230, transparent: true, opacity: 0.42 });
      if (window.ResizeObserver) ro = new ResizeObserver(function () { invalidate(); });
      window.addEventListener('resize', function () { invalidate(); });
      return true;
    }
    function mkScene() {
      var s = new TH.Scene();
      s.add(new TH.HemisphereLight(0xffffff, 0x8d939e, 0.62));
      var sun = new TH.DirectionalLight(0xffffff, 0.3);
      sun.position.set(-500, -700, 1400); s.add(sun);
      var hl = new TH.DirectionalLight(0xffffff, 0.5);
      s.add(hl); s.add(hl.target);
      s.userData.hl = hl;
      return s;
    }
    function mkView(stage, scene, kind, page) {
      if (!stage.getAttribute('data-v3bound')) { stage.setAttribute('data-v3bound', '1'); bindStage(stage, page); if (ro) ro.observe(stage); }
      return { stage: stage, scene: scene, kind: kind, cam: new TH.PerspectiveCamera(FOV, 1, 1, 50000),
               c: { tx: 0, ty: 0, tz: 0, az: -0.6, el: 0.5, dist: 500 }, h: null, pick: null, pickables: null };
    }
    function applyCam(v) {
      var c = v.c, ce = Math.cos(c.el);
      v.cam.aspect = Math.max(1, v.stage.clientWidth) / Math.max(1, v.stage.clientHeight);
      v.cam.position.set(c.tx + c.dist * ce * Math.sin(c.az), c.ty - c.dist * ce * Math.cos(c.az), c.tz + c.dist * Math.sin(c.el));
      v.cam.up.set(0, 0, 1);
      v.cam.near = Math.max(0.5, c.dist / 100); v.cam.far = c.dist * 10 + 4000;
      v.cam.lookAt(c.tx, c.ty, c.tz);
      v.cam.updateProjectionMatrix();
      var hl = v.scene.userData.hl;
      hl.position.copy(v.cam.position); hl.target.position.set(c.tx, c.ty, c.tz);
    }
    function fit(v, box, az, el, k) {            // nearest distance that keeps all 8 box corners in the frustum, times k
      var c = box.getCenter(new TH.Vector3()), mn = box.min, mx = box.max;
      var w = Math.max(1, v.stage.clientWidth), h = Math.max(1, v.stage.clientHeight), tv = Math.tan(FOV * Math.PI / 360), th = tv * w / h;
      var ca = Math.cos(az), sa = Math.sin(az), ce = Math.cos(el), se = Math.sin(el), d = 1;
      for (var i = 0; i < 8; i++) {
        var x = (i & 1 ? mx.x : mn.x) - c.x, y = (i & 2 ? mx.y : mn.y) - c.y, z = (i & 4 ? mx.z : mn.z) - c.z;
        var xr = ca * x + sa * y, yu = -sa * se * x + ca * se * y + ce * z, zf = ce * sa * x - ce * ca * y + se * z;   // right, up, toward the eye
        d = Math.max(d, zf + Math.abs(xr) / th, zf + Math.abs(yu) / tv);
      }
      v.c = { tx: c.x, ty: c.y, tz: c.z, az: az, el: el, dist: d * (k || 1) };
      v.h = cp(v.c);
      invalidate();
    }
    function home(v) { if (v && v.h) { v.c = cp(v.h); invalidate(); } }
    function invalidate() { if (!raf && view && renderer) raf = requestAnimationFrame(frame); }
    function frame(now) {
      raf = 0;
      if (!view || !renderer || canvas.parentNode !== view.stage || !view.stage.offsetParent) return;
      if (view.kind === 'asm' && S.ex !== S.exT) {
        var t = reduce ? 1 : Math.min(1, (now - S.t0) / 450), e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        S.ex = t >= 1 ? S.exT : S.ex0 + (S.exT - S.ex0) * e;
        pose();
        if (S.ex !== S.exT) raf = requestAnimationFrame(frame);
      }
      var w = Math.max(1, view.stage.clientWidth), h = Math.max(1, view.stage.clientHeight), pr = renderer.getPixelRatio();
      if (canvas.width !== Math.floor(w * pr) || canvas.height !== Math.floor(h * pr)) renderer.setSize(w, h, false);
      applyCam(view);
      view.scene.background = bgColor();
      renderer.render(view.scene, view.cam);
    }
    function attach(v) {
      view = v;
      if (canvas.parentNode !== v.stage) v.stage.insertBefore(canvas, v.stage.firstChild);
      invalidate();
    }

    // ---------------------------------------------------------------- pointer: turn, move, zoom, pick
    function bindStage(stage, page) {
      var ptrs = {}, moved = 0, pinch = 0, panMode = false, hintT = 0;
      function mine() { return view && view.stage === stage && canvas && canvas.parentNode === stage ? view : null; }
      function n() { return Object.keys(ptrs).length; }
      function spread() {
        var k = Object.keys(ptrs);
        if (k.length < 2) return 0;
        var a = ptrs[k[0]], b = ptrs[k[1]];
        return Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y));
      }
      function onUi(e) { return e.target.closest && e.target.closest('button,a,.partdwg-v3info,.partdwg-v3load'); }
      stage.addEventListener('pointerdown', function (e) {
        if (!mine() || onUi(e)) return;
        ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
        try { stage.setPointerCapture(e.pointerId); } catch (x) { /* ignore */ }
        moved = 0;
        panMode = e.button === 2 || e.button === 1 || e.shiftKey;
        if (n() === 2) pinch = spread();
      });
      stage.addEventListener('pointermove', function (e) {
        var p = ptrs[e.pointerId], v = mine();
        if (!p || !v) return;
        var dx = e.clientX - p.x, dy = e.clientY - p.y;
        p.x = e.clientX; p.y = e.clientY;
        moved += Math.abs(dx) + Math.abs(dy);
        if (n() >= 2) {
          var d = spread();
          if (pinch && d) v.c.dist = clampD(v, v.c.dist * pinch / d);
          pinch = d;
        } else if (panMode) pan(v, dx, dy);
        else { v.c.az -= dx * 0.0085; v.c.el = Math.max(-1.45, Math.min(1.45, v.c.el + dy * 0.0085)); }
        invalidate();
      });
      function end(e) {
        if (!ptrs[e.pointerId]) return;
        var single = n() === 1;
        delete ptrs[e.pointerId];
        if (n() < 2) pinch = 0;
        if (single && e.type === 'pointerup' && moved < 6) pickAt(e.clientX, e.clientY);
      }
      stage.addEventListener('pointerup', end);
      stage.addEventListener('pointercancel', end);
      stage.addEventListener('contextmenu', function (e) { if (mine()) e.preventDefault(); });
      stage.addEventListener('dblclick', function (e) { var v = mine(); if (v && !onUi(e)) home(v); });
      stage.addEventListener('wheel', function (e) {
        var v = mine();
        if (!v) return;
        if (page && !(e.ctrlKey || e.metaKey)) {
          hint(stage, 'Ctrl(⌘)+휠로 확대합니다');
          clearTimeout(hintT);
          hintT = setTimeout(function () { hint(stage, HINT_PAGE); }, 1600);
          return;
        }
        e.preventDefault();
        v.c.dist = clampD(v, v.c.dist * Math.exp(e.deltaY * (e.deltaMode ? 0.05 : 0.0015)));
        invalidate();
      }, { passive: false });
    }
    function clampD(v, d) { var h = v.h ? v.h.dist : d; return Math.max(h * 0.02, Math.min(h * 6, d)); }
    function pan(v, dx, dy) {                    // right = (cos az, sin az, 0), up = (-sin az sin el, cos az sin el, cos el)
      var c = v.c, k = 2 * c.dist * Math.tan(FOV * Math.PI / 360) / Math.max(1, v.stage.clientHeight);
      var ca = Math.cos(c.az), sa = Math.sin(c.az), ce = Math.cos(c.el), se = Math.sin(c.el);
      c.tx += (-ca * dx - sa * se * dy) * k;
      c.ty += (-sa * dx + ca * se * dy) * k;
      c.tz += ce * dy * k;
    }
    function pickAt(cx, cy) {
      var v = view;
      if (!v || !v.pick || !v.pickables) return;
      var r = v.stage.getBoundingClientRect();
      var nd = new TH.Vector2((cx - r.left) / r.width * 2 - 1, -(cy - r.top) / r.height * 2 + 1);
      var rc = new TH.Raycaster();
      v.scene.updateMatrixWorld();
      rc.setFromCamera(nd, v.cam);
      var hits = rc.intersectObjects(v.pickables(), false);
      for (var i = 0; i < hits.length; i++) {
        var o = hits[i].object, m = Array.isArray(o.material) ? o.material[0] : o.material;
        if (o.visible && o.userData.code && !(m.transparent && m.opacity < 0.14)) { v.pick(o.userData.code, o.userData.id); return; }
      }
      v.pick(null);
    }

    // ---------------------------------------------------------------- the instrument (GLB of the 04 tab + piece STLs)
    function parseGLB(u8) {
      var dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
      if (dv.getUint32(0, true) !== 0x46546C67) throw new Error('GLB 파일이 아닙니다');
      var jl = dv.getUint32(12, true);
      var json = JSON.parse(new TextDecoder('utf-8').decode(u8.subarray(20, 20 + jl)));
      var bl = dv.getUint32(20 + jl, true);
      return { json: json, bin: u8.subarray(28 + jl, 28 + jl + bl) };
    }
    function asmLoad() {
      if (!aP) {
        aP = Promise.all([index(), fetch(GLB_URL).then(function (r) { if (!r.ok) throw new Error(GLB_URL + ' ' + r.status); return r.text(); })])
          .then(function (r) { return buildAsm(b64u8(r[1].replace(/\s+/g, '')), r[0]); });
        aP.catch(function () { aP = null; });
      }
      return aP;
    }
    function offOf(code) {                       // 벌려 보기: lift the stacked prints (mm, model z up)
      var p = IX.parts[code], nm = p.n, g = p.g;
      if (g === '01') return [0, 0, 150];
      if (g === '02') return /덮개/.test(nm) ? [16, 0, 100] : [0, 0, 100];
      if (g === '03') return [0, 0, /레버틀/.test(nm) ? 56 : /가이드탭/.test(nm) ? 28 : 0];
      if (g === '04') return [0, 0, /패드/.test(nm) ? 128 : 122];
      if (g === '05') return [0, 0, /^뚜껑|화면뚜껑/.test(nm) ? 95 : /기둥|집게|선반/.test(nm) ? 40 : 0];
      if (g === '07') return [0, 0, 60];
      return [0, 0, 0];
    }
    function buildAsm(u8, ix) {
      var g = parseGLB(u8), J = g.json, bin = g.bin, geo = {}, codeOf = {}, hide = {}, split = ix.split || {};
      Object.keys(ix.parts).forEach(function (c) { ix.parts[c].ids.forEach(function (id) { if (!split[id]) codeOf[id] = c; }); });
      (ix.hide || []).forEach(function (id) { hide[id] = 1; });
      function bview(a) { return J.bufferViews[a.bufferView]; }
      function positions(ai, qs) {
        var a = J.accessors[ai], v = bview(a), cnt = a.count, out = new Float32Array(cnt * 3);
        var off = bin.byteOffset + (v.byteOffset || 0) + (a.byteOffset || 0);
        if (a.componentType === 5123) {
          var st = (v.byteStride || 6) / 2, u = new Uint16Array(bin.buffer, off, st * (cnt - 1) + 3);
          for (var i = 0; i < cnt; i++) { out[3 * i] = u[i * st] * qs[0]; out[3 * i + 1] = u[i * st + 1] * qs[1]; out[3 * i + 2] = u[i * st + 2] * qs[2]; }
        } else if (a.componentType === 5126) {
          var sf = (v.byteStride || 12) / 4, fl = new Float32Array(bin.buffer, off, sf * (cnt - 1) + 3);
          for (var k = 0; k < cnt; k++) { out[3 * k] = fl[k * sf] * qs[0]; out[3 * k + 1] = fl[k * sf + 1] * qs[1]; out[3 * k + 2] = fl[k * sf + 2] * qs[2]; }
        } else throw new Error('POSITION 형식 ' + a.componentType);
        return out;
      }
      function indices(ai) {
        var a = J.accessors[ai], v = bview(a), off = bin.byteOffset + (v.byteOffset || 0) + (a.byteOffset || 0);
        if (a.componentType === 5123) return new Uint16Array(bin.buffer.slice(off, off + a.count * 2));
        if (a.componentType === 5125) return new Uint32Array(bin.buffer.slice(off, off + a.count * 4));
        throw new Error('index 형식 ' + a.componentType);
      }
      var scene = mkScene(), root = new TH.Group(), list = [], byCode = {}, box = new TH.Box3();
      scene.add(root);
      function addMesh(gg, M, id, code, hid) {
        var mesh = new TH.Mesh(gg, mat(BUY, 'g'));
        mesh.matrixAutoUpdate = false;
        mesh.matrix.copy(M);
        mesh.userData = { id: id, code: code, hide: hid, M0: M.clone(), off: code ? offOf(code) : null, e: null };
        root.add(mesh);
        list.push(mesh);
        if (code) (byCode[code] = byCode[code] || []).push(mesh);
        if (!hid) box.union(gg.boundingBox.clone().applyMatrix4(M));
      }
      J.nodes.forEach(function (nd) {
        if (nd.mesh == null || !nd.name || split[nd.name]) return;
        var m = J.meshes[nd.mesh], pr = m.primitives[0], ai = pr.attributes.POSITION;
        var qs = (m.extras && m.extras.qscale) || nd.scale || [1, 1, 1];
        var gg = geo[ai];
        if (!gg) {
          gg = geo[ai] = new TH.BufferGeometry();
          gg.setAttribute('position', new TH.BufferAttribute(positions(ai, qs), 3));
          gg.setIndex(new TH.BufferAttribute(indices(pr.indices), 1));
          gg.computeBoundingBox(); gg.computeBoundingSphere();
        }
        var t = nd.translation || [0, 0, 0];
        addMesh(gg, new TH.Matrix4().makeTranslation(t[0], t[1], t[2]), nd.name, codeOf[nd.name] || null, !!hide[nd.name]);
      });
      var pieces = [];
      Object.keys(split).forEach(function (id) { split[id].forEach(function (c) { pieces.push([id, c]); }); });
      return Promise.all(pieces.map(function (pc) { return geomOf(pc[1]); })).then(function (gs) {
        gs.forEach(function (gg, k) {
          var c = pieces[k][1], R = ix.xf[c].R, t = ix.xf[c].t;
          addMesh(gg, new TH.Matrix4().set(R[0], R[1], R[2], t[0], R[3], R[4], R[5], t[1], R[6], R[7], R[8], t[2], 0, 0, 0, 1), pieces[k][0], c, false);
        });
        A = { scene: scene, list: list, byCode: byCode, box: box };
        return A;
      });
    }
    function paint() {
      if (!A) return;
      var place = S.code, ex = S.exT > 0;
      A.list.forEach(function (m) {
        var u = m.userData, c = u.code, vis = true, mm = null, edge = false;
        if (place && c === place) { mm = mat(HI, 'n'); edge = true; }
        else if (u.hide) vis = false;
        else if (!c) { vis = S.buy && !ex; mm = mat(BUY, place ? 'h' : 'g'); }
        else if (place) mm = mat(FADE, 'q');
        else if (S.group !== 'all' && IX.parts[c].g !== S.group) mm = mat(FADE, 'f');
        else { mm = mat(colOf(c), c === S.sel ? 's' : 'n'); edge = true; }
        m.visible = vis;
        if (mm) m.material = mm;
        if (u.e) u.e.visible = vis && edge;
      });
      invalidate();
    }
    function pose() {
      if (!A) return;
      var f = S.ex;
      A.list.forEach(function (m) {
        var u = m.userData, o = u.off, el = m.matrix.elements;
        m.matrix.copy(u.M0);
        if (o && f) { el[12] += o[0] * f; el[13] += o[1] * f; el[14] += o[2] * f; }
        m.matrixWorldNeedsUpdate = true;
      });
    }
    function asmEdges() {                        // feature lines of the printed parts, built in slices after the first frame
      if (edgesStarted || !A) return;
      edgesStarted = true;
      var by = {}, order = [];
      A.list.forEach(function (m) {
        if (!m.userData.code) return;
        var k = m.geometry.uuid;
        if (!by[k]) { by[k] = { g: m.geometry, ms: [] }; order.push(k); }
        by[k].ms.push(m);
      });
      var i = 0;
      (function slice() {
        var t0 = performance.now();
        while (i < order.length && performance.now() - t0 < 14) {
          var it = by[order[i++]], eg = edgeOf[it.g.uuid] || (edgeOf[it.g.uuid] = new TH.EdgesGeometry(it.g, 28));
          it.ms.forEach(function (m) {
            var l = new TH.LineSegments(eg, edgeMat);
            l.matrixAutoUpdate = false;
            m.add(l);
            m.userData.e = l;
          });
        }
        paint();
        if (i < order.length) setTimeout(slice, 0);
      })();
    }
    function boxOf(code) {                       // the code's instances where they stand (with the lift of 벌려 보기)
      var b = new TH.Box3();
      (A.byCode[code] || []).forEach(function (m) {
        var M = m.userData.M0.clone(), o = m.userData.off;
        if (o && S.exT) M.premultiply(new TH.Matrix4().makeTranslation(o[0], o[1], o[2]));
        b.union(m.geometry.boundingBox.clone().applyMatrix4(M));
      });
      return b;
    }
    function setEx(on) {
      S.ex0 = S.ex; S.exT = on ? 1 : 0; S.t0 = performance.now();
      syncBtns();
      paint();
      if (view && view === OV) {                 // keep the lifted prints in the picture
        var b = A.box.clone();
        if (S.exT) b.max.z += 160;
        fit(OV, b, OV.c.az, OV.c.el, 1.06);
      } else if (view && view === PL && S.code) {
        fit(PL, boxOf(S.code).expandByScalar(40), PL.c.az, PL.c.el, 1.25);
        placeInfo(S.code, null);
      }
    }
    function syncBtns() {
      [].forEach.call(sec.querySelectorAll('[data-v3="ex"]'), function (b) { b.setAttribute('aria-pressed', S.exT ? 'true' : 'false'); });
      [].forEach.call(sec.querySelectorAll('[data-v3="buy"]'), function (b) {
        b.setAttribute('aria-pressed', S.buy && !S.exT ? 'true' : 'false');
        b.disabled = S.exT > 0;
        b.title = S.exT ? '벌려 보기에서는 산 부품을 숨깁니다' : '';
      });
    }

    // ---------------------------------------------------------------- overview (page)
    function partLine(code) {
      var p = IX.parts[code], pc = IX.xf[code] && IX.xf[code].piece;
      return '<b>' + esc(code + ' · ' + p.n) + '</b> — 이 STL을 <b>' + p.q + '개</b> 출력' +
        (pc ? ' (' + esc(IX.xf[code].inst) + '를 ' + IX.split[IX.xf[code].inst].length + '조각으로 나눈 ' + pc + '번째)' : '') +
        ' · ' + esc(GKO[p.g] || p.g);
    }
    function ovPick(code) {
      S.sel = code;
      paint();
      if (!ovInfo) return;
      if (!code) { ovInfo.textContent = '조각을 누르면 그 조각을 뽑는 출력 파일이 나옵니다.'; return; }
      ovInfo.innerHTML = '<span>' + partLine(code) + '</span><span class="partdwg-ovact" data-code="' + esc(code) + '">' +
        '<button type="button" class="partdwg-btn" data-ov="dwg">도면</button><button type="button" class="partdwg-btn" data-ov="print">3D 출력 모양</button>' +
        '<button type="button" class="partdwg-btn" data-ov="place">3D 조립 자리</button></span>';
    }
    function legend() {
      if (!ovLeg) return;
      var gs = ['01', '02', '03', '04', '05', '07'].filter(function (g) { return IX.groups[g]; });
      ovLeg.innerHTML = gs.map(function (g) {
        var cs = IX.groups[g].filter(function (c) { return IX.parts[c].ids.length; });
        return '<span class="partdwg-sw">' + cs.slice(0, 3).map(function (c) { return '<i style="background:#' + hex6(colOf(c)) + '"></i>'; }).join('') +
          esc(g + ' ' + GKO[g]) + ' <span class="muted">' + cs.length + '파일</span></span>';
      }).join('') + '<span class="partdwg-sw"><i class="buy"></i>산 부품</span>';
    }
    function startOverview() {
      if (OV || ovTried || !ovStage) return;
      ovTried = true;
      loading(ovStage, '3D 모델을 불러오는 중… (three.js와 악기 모델, 약 4 MB)');
      boot().then(asmLoad).then(function () {
        OV = mkView(ovStage, A.scene, 'asm', true);
        OV.pickables = function () { return A.list; };
        OV.pick = ovPick;
        legend();
        loading(ovStage, '');
        hint(ovStage, HINT_PAGE);
        fit(OV, A.box, -0.55, 0.5, 1.06);
        if (viewer.hidden || vmode === 'dwg') { S.code = null; paint(); attach(OV); }
        asmEdges();
      }).catch(function (e) {
        ovTried = false;
        loading(ovStage, '3D 모델을 불러오지 못했습니다 (' + ((e && e.message) || e) + '). 여기를 누르면 다시 해 봅니다.');
      });
    }
    if (ovStage) {
      ovStage.addEventListener('click', function () { if (!OV && !ovTried) startOverview(); });
      if ('IntersectionObserver' in window) {
        new IntersectionObserver(function (es) {
          es.forEach(function (en) { if (en.isIntersecting && !sec.hidden) startOverview(); });
        }, { rootMargin: '200px' }).observe(ovStage);
      }
      if (ovInfo) ovInfo.addEventListener('click', function (e) {
        var b = e.target.closest('[data-ov]'), host = b && b.closest('[data-code]');
        if (!host) return;
        openViewer(document.getElementById('partdwg-' + host.getAttribute('data-code')), b.getAttribute('data-ov'));
      });
    }

    // ---------------------------------------------------------------- viewer: print shape, place
    function printScene() {
      var s = mkScene(), h = BED / 2, pts = [];
      var plate = new TH.Mesh(new TH.BoxGeometry(BED, BED, 2), new TH.MeshPhongMaterial({ color: 0x30343a, shininess: 30, specular: 0x222222 }));
      plate.position.z = -1.0;
      s.add(plate);
      for (var x = -h; x <= h + 0.01; x += 32) { pts.push(x, -h, 0.05, x, h, 0.05, -h, x, 0.05, h, x, 0.05); }
      var gg = new TH.BufferGeometry();
      gg.setAttribute('position', new TH.Float32BufferAttribute(pts, 3));
      s.add(new TH.LineSegments(gg, new TH.LineBasicMaterial({ color: 0x5b6370 })));
      return s;
    }
    function aidText(code, n, sup) {           // A13: the orange faces are where Bambu Studio's support touches the print
      if (!n) return '<br>서포트 없음 — Bambu Studio 기본 설정(서포트 문턱 30°)에서 서포트가 생기지 않는 모양 (A13)';
      if (sup === 'tree') {
        return '<br><span class="partdwg-aid"></span>주황 = Bambu 트리 서포트가 닿는 면: 숨은 꼬리(빔)만 바닥에서 떠 있어(위에 레버) 여기만 '
          + '빌드 플레이트에서 올라오는 트리 서포트가 받침 — 서포트 켬 · 트리(자동) · 빌드 플레이트에서만, 출력 뒤 한 덩어리로 떨어짐';
      }
      return '<br><span class="partdwg-aid"></span>주황 = 아직 서포트가 생기는 면 (A13에서 남은 부품 — 출력 메모 참고)';
    }
    function showPrint(card) {
      var code = card.getAttribute('data-code');
      loading(dStage, '3D 출력 모양을 불러오는 중…');
      if (dInfo) dInfo.innerHTML = '';
      return boot().then(function () { return geomOf(code); }).then(function (g) {
        if (want !== code || wantMode !== 'print') return;
        if (!PR) PR = mkView(dStage, printScene(), 'print', false);
        var sc = PR.scene, b = g.userData.b, p = IX.parts[code];
        if (sc.userData.part) sc.remove(sc.userData.part);
        var mesh = new TH.Mesh(g, [mat(matColor(p.m || ''), 'n'), mat(tokenColor('--amber', 0xf2b45a), 'n')]);
        mesh.position.set(-(b[0] + b[3]) / 2, -(b[1] + b[4]) / 2, -b[2]);
        mesh.add(new TH.LineSegments(edgeOf[g.uuid] || (edgeOf[g.uuid] = new TH.EdgesGeometry(g, 28)), edgeMat));
        sc.add(mesh);
        sc.userData.part = mesh;
        var ex = [b[3] - b[0], b[4] - b[1], b[5] - b[2]];
        var bx = new TH.Box3(new TH.Vector3(-ex[0] / 2, -ex[1] / 2, 0), new TH.Vector3(ex[0] / 2, ex[1] / 2, ex[2]));
        fit(PR, bx.expandByScalar(Math.max(4, 0.06 * Math.sqrt(ex[0] * ex[0] + ex[1] * ex[1] + ex[2] * ex[2]))), -0.62, 0.62, 1.12);
        setBtns('print');
        attach(PR);
        loading(dStage, '');
        if (dInfo) dInfo.innerHTML = '<b>STL 하나 = 한 번에 뽑는 단위</b> · 베드에 놓인 그대로 · 출력 크기 <span class="mono">' +
          ex.map(f1).join(' × ') + '</span> mm (베드 256 × 256) · 이 STL을 <b>' + p.q + '개</b> 출력' +
          (p.ids.length ? '' : ' · 조립에 들어가지 않는 출력물(공구·지그·예비)') + aidText(code, g.userData.aids, g.userData.sup);
      }).catch(fail);
    }
    function showPlace(card) {
      var code = card.getAttribute('data-code');
      loading(dStage, '악기 3D 모델을 불러오는 중… (약 4 MB)');
      if (dInfo) dInfo.innerHTML = '';
      return boot().then(asmLoad).then(function () {
        if (want !== code || wantMode !== 'place') return;
        if (!PL) {
          PL = mkView(dStage, A.scene, 'asm', false);
          PL.pickables = function () { return A.list; };
          PL.pick = plPick;
        }
        S.code = code;
        S.sel = null;
        paint();
        var b = boxOf(code);
        if (b.isEmpty()) b = A.box.clone();
        var sz = b.getSize(new TH.Vector3());
        b.expandByScalar(Math.max(0, 160 - Math.max(sz.x, sz.y, sz.z)) / 2);
        fit(PL, b, -0.5, 0.78, 1.35);
        setBtns('place');
        attach(PL);
        asmEdges();
        loading(dStage, '');
        placeInfo(code, null);
      }).catch(fail);
    }
    function placeInfo(code, other) {
      if (!dInfo) return;
      var n = (A.byCode[code] || []).length;
      var s = partLine(code) + '<br>파랑 = 이 STL로 뽑은 ' + n + '개가 들어가는 자리 · 옅은 회색 = 다른 출력물' + (S.buy && !S.exT ? ' · 더 옅은 = 산 부품' : '');
      if (other && other !== code) {
        s += '<br>누른 조각: ' + esc(other + ' · ' + IX.parts[other].n) + ' (' + IX.parts[other].q + '개) ' +
          '<button type="button" class="partdwg-btn" data-go="' + esc(other) + '">이 부품 보기</button>';
      }
      dInfo.innerHTML = s;
    }
    function plPick(code) { if (S.code) placeInfo(S.code, code); }
    function setBtns(kind) {
      if (!dStage) return;
      [].forEach.call(dStage.querySelectorAll('[data-v3="ex"],[data-v3="buy"]'), function (b) { b.hidden = kind !== 'place'; });
      hint(dStage, HINT_FULL);
      syncBtns();
    }
    function fail(e) { loading(dStage, '3D를 불러오지 못했습니다 (' + ((e && e.message) || e) + ').'); }
    if (dStage) dStage.addEventListener('click', function (e) {
      var g = e.target.closest('[data-go]');
      if (g) openViewer(document.getElementById('partdwg-' + g.getAttribute('data-go')), 'place');
    });
    sec.addEventListener('click', function (e) {
      var b = e.target.closest('[data-v3]');
      if (!b || b.disabled) return;
      var a = b.getAttribute('data-v3');
      if (a === 'home') home(dStage && dStage.contains(b) ? view : OV);
      else if (a === 'ex') setEx(S.exT === 0);
      else if (a === 'buy') { S.buy = !S.buy; syncBtns(); paint(); if (S.code) placeInfo(S.code, null); }
    });

    return {
      show: function (card, m) {
        want = card.getAttribute('data-code'); wantMode = m;
        if (m === 'print') { S.code = null; if (A) paint(); return showPrint(card); }
        if (m === 'place') return showPlace(card);
      },
      leave: function () {                       // the viewer closed or went back to the drawing: the canvas goes home
        want = null; wantMode = 'dwg'; S.code = null;
        if (!renderer) return;
        if (OV) { paint(); attach(OV); }
        else { view = null; if (canvas.parentNode) canvas.parentNode.removeChild(canvas); }
      },
      filter: function (g) { S.group = g; S.sel = null; if (A && !S.code) paint(); },
      wake: function () {                        // the tab was shown: draw again, start the overview if it is on screen
        invalidate();
        if (!OV && ovStage) {
          var r = ovStage.getBoundingClientRect();
          if (r.bottom > -200 && r.top < (window.innerHeight || 800) + 200) startOverview();
        }
      }
    };
  })();

  if (!sec.hidden) setTimeout(function () { V3.wake(); }, 0);

  T.partdwg = {
    open: function (code, mode) {
      var card = document.getElementById('partdwg-' + code);
      if (!card) return false;
      if (sec.hidden) location.hash = 'partdwg-' + code;
      openViewer(card, mode);
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
