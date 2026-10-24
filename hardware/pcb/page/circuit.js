
(function(){
  // zoom bars: page-wide (every drawing tab uses the same .zbar / .csheet markup)
  document.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('.zbar button') : null; if(!b) return;
    var f = b.closest('.csheet'); if(!f) return;
    var z = b.getAttribute('data-z');
    f.classList.remove('z2', 'z3'); if(z !== '1') f.classList.add('z' + z);
    f.querySelectorAll('.zbar button').forEach(function(x){ x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
  });
  var sec = document.getElementById('p-circuit'); if(!sec) return;
  // sheet crops: inline SVG <image> would load at once; give it its href only when the tab is first shown
  var started = false;
  function start(){
    if(started || sec.hidden) return; started = true;
    sec.querySelectorAll('image[data-href]').forEach(function(im){ im.setAttribute('href', im.getAttribute('data-href')); });
  }
  try { new MutationObserver(start).observe(sec, {attributes: true, attributeFilter: ['hidden']}); } catch(err) {}
  start();
  // downloads (window.claude downloads capability; CSV as text, the ZIP is shipped as base64 text)
  var status = sec.querySelector('#circuit-dl-status');
  function say(t){ if(status) status.textContent = t; }
  sec.addEventListener('click', function(e){
    var b = e.target && e.target.closest ? e.target.closest('button[data-dl]') : null; if(!b) return;
    var file = b.getAttribute('data-dl'), name = b.getAttribute('data-name'), kind = b.getAttribute('data-kind');
    var repo = b.getAttribute('data-repo') || 'hardware/pcb/';
    var use = window.claude && typeof window.claude.use === 'function' ? window.claude.use : null;
    if(!use){ say('이 화면에서는 파일 받기를 쓸 수 없습니다. 같은 내용이 저장소 ' + repo + '에 있습니다.'); return; }
    b.disabled = true; say(name + ' 준비 중…');
    Promise.resolve().then(function(){ return use.call(window.claude, 'downloads'); }).then(function(dl){
      if(!dl || typeof dl.save !== 'function') throw {code: 'unavailable'};
      return fetch(file).then(function(r){
        if(!r.ok) throw {code: 'fetch ' + r.status};
        if(kind === 'zip') return r.text().then(function(t){
          var bin = atob(t.replace(/\s+/g, '')), u = new Uint8Array(bin.length);
          for(var i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
          return new Blob([u], {type: 'application/zip'});
        });
        return r.arrayBuffer().then(function(a){ return new Blob([a], {type: 'text/csv'}); });
      }).then(function(blob){ return dl.save({filename: name, data: blob}); });
    }).then(function(){ say(name + ' 저장을 요청했습니다.'); }, function(err){
      var c = String((err && (err.code || err.name || err.message)) || '');
      if(/declin|cancel|abort|denied/i.test(c)) say('저장을 취소했습니다.');
      else if(c === 'unavailable') say('이 화면에서는 파일 받기를 쓸 수 없습니다. 같은 내용이 저장소 ' + repo + '에 있습니다.');
      else say('받기에 실패했습니다 (' + c + ').');
    }).then(function(){ b.disabled = false; });
  });
})();
/* 01 회로도 · 회로 3D 모델 (hardware/pcb/src/circuit3d.js; page.py appends it to page/circuit.js).
   Data: fin/circuit/circuit3d.json from src/model3d.py (boards, holes, pads, parts, wires; mm, z up from the desk).
   Only three.js r128 from cdnjs, loaded once through window.toccata.three (shared with 04 3D 모델). Orbit / pan / zoom, touch,
   picking, net highlight and layer toggles are written here. Loads when the 3D block first scrolls into view (or on its button).
   Model -> three: the root group is turned -90 deg about x, so (x, y, z) model = (x, z, -y) three. */
(function () {
  'use strict';
  var box = document.getElementById('circuit-3d-view');
  if (!box) return;
  var sec = document.getElementById('p-circuit');
  var NS = window.toccata = window.toccata || {};
  var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  var SRC = box.getAttribute('data-src');
  var stage = box.querySelector('.c3d-stage'), canvas = stage.querySelector('canvas'), over = stage.querySelector('.c3d-over');
  var loadBox = stage.querySelector('.c3d-load'), loadTxt = loadBox.querySelector('.c3d-load-t'), goBtn = loadBox.querySelector('.c3d-go');
  var sceneBar = box.querySelector('.c3d-scenes'), viewBar = box.querySelector('.c3d-views'), togBar = box.querySelector('.c3d-togs');
  var netSel = box.querySelector('.c3d-net'), infoBox = box.querySelector('.c3d-info'), subEl = box.querySelector('.c3d-sub'),
      notesEl = box.querySelector('.c3d-notes');
  var mq = window.matchMedia ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  var METAL = { '#c0c6cc': 1, '#c9ccd2': 1, '#b8bec6': 1, '#d8c27a': 1, '#5a5f66': 1, '#c9894b': 1 };
  var LAYERS = [['part', '부품'], ['wire', '기판 배선'], ['cable', '선·리본'], ['board', '기판'], ['ctx', '주변 출력물'], ['lab', '이름표']];
  var FOV = 30, TAN = Math.tan(FOV / 2 * Math.PI / 180);

  var T = null, D = null, renderer = null, camera = null, scene = null, root = null, raf = 0;
  var S = { sc: -1, lay: { part: true, wire: true, cable: true, board: true, ctx: true, lab: true }, net: null, sel: null };
  var cam = { tx: 0, ty: 0, tz: 0, dist: 300, az: -0.6, el: 0.7 };
  var meshes = [], labels = [], picks = [];
  var started = false;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function css(name, fb) { try { var v = getComputedStyle(box).getPropertyValue(name).trim(); return v || fb; } catch (e) { return fb; } }

  // ------------------------------------------------------------------ start (lazy)
  function ensureThree() {
    if (window.THREE && window.THREE.WebGLRenderer) return Promise.resolve();
    if (!NS.three) {
      NS.three = new Promise(function (res, rej) {
        var s = document.createElement('script');
        s.src = THREE_URL; s.async = true;
        s.onload = function () { res(); };
        s.onerror = function () { NS.three = null; rej(new Error('three.js를 받지 못했습니다')); };
        document.head.appendChild(s);
      });
    }
    return NS.three;
  }
  function say(t) { loadBox.hidden = false; loadTxt.textContent = t; }
  function start() {
    if (started) return; started = true;
    goBtn.hidden = true;
    say('3D 모델을 불러오는 중…');
    Promise.all([ensureThree(), fetch(SRC).then(function (r) { if (!r.ok) throw new Error('모델 파일 ' + r.status); return r.json(); })])
      .then(function (a) { D = a[1]; T = window.THREE; init(); })
      .catch(function (e) { started = false; goBtn.hidden = false; say('불러오지 못했습니다: ' + (e && e.message ? e.message : e)); });
  }
  goBtn.addEventListener('click', start);
  // start once the block is on screen while the tab is shown (the router may un-hide the tab after the first intersection report)
  var inView = false;
  function visible() { return !sec || !sec.hidden; }
  function maybe() { if (inView && visible()) start(); }
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (en) { en.forEach(function (x) { inView = x.isIntersecting; }); maybe(); }, { rootMargin: '200px' }).observe(stage);
  } else goBtn.hidden = false;
  if (sec) try { new MutationObserver(function () { if (!sec.hidden) { maybe(); invalidate(); } }).observe(sec, { attributes: true, attributeFilter: ['hidden'] }); } catch (e) { /* */ }
  setTimeout(function () { if (!started) goBtn.hidden = false; }, 1500);

  // ------------------------------------------------------------------ three setup
  function init() {
    try {
      renderer = new T.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    } catch (e) { say('이 브라우저에서는 WebGL을 쓸 수 없습니다.'); return; }
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.setClearColor(0x000000, 0);
    scene = new T.Scene();
    camera = new T.PerspectiveCamera(FOV, 1, 0.5, 20000);
    scene.add(new T.HemisphereLight(0xffffff, 0x9aa0a8, 1.05));
    var d1 = new T.DirectionalLight(0xffffff, 0.85); d1.position.set(-0.6, 1.0, 0.8); scene.add(d1);
    var d2 = new T.DirectionalLight(0xffffff, 0.45); d2.position.set(0.7, -0.6, -0.5); scene.add(d2);
    camera.userData.lights = [d1, d2];
    buildUi();
    bindPointer();
    if ('ResizeObserver' in window) new ResizeObserver(function () { invalidate(); }).observe(stage);
    else window.addEventListener('resize', invalidate);
    var want = 0, h = (location.hash || '').replace('#', '');
    D.scenes.forEach(function (s, k) { if (h === 'circuit-3d-' + s.id) want = k; });
    loadScene(want);
    loadBox.hidden = true;
  }

  // ------------------------------------------------------------------ materials (shared by colour / state)
  var mats = {};
  function mat(c, o, state) {
    var key = c + '|' + (o == null ? 1 : o) + '|' + (state || '');
    if (mats[key]) return mats[key];
    var metal = !!METAL[c];
    var m = new T.MeshStandardMaterial({ color: new T.Color(c), roughness: metal ? 0.35 : 0.62, metalness: metal ? 0.55 : 0.0 });
    var op = o == null ? 1 : o;
    if (state === 'dim') op = Math.min(op, 0.08);
    if (op < 1) { m.transparent = true; m.opacity = op; m.depthWrite = op > 0.5; }
    if (state === 'hot') { m.emissive = new T.Color(c); m.emissiveIntensity = 0.45; }
    if (state === 'sel') { m.emissive = new T.Color('#3b82f6'); m.emissiveIntensity = 0.55; }
    mats[key] = m;
    return m;
  }

  // ------------------------------------------------------------------ geometry builders (model coordinates)
  function boxGeo(b) {
    var g = new T.BoxGeometry(Math.max(0.02, b[3] - b[0]), Math.max(0.02, b[4] - b[1]), Math.max(0.02, b[5] - b[2]));
    g.translate((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2);
    return g;
  }
  function cylGeo(o) {
    var L = Math.max(0.02, o.s[1] - o.s[0]), mid = (o.s[0] + o.s[1]) / 2, g;
    if (o.ring) { g = new T.TorusGeometry(o.r, 0.17, 6, 18); if (o.a === 'x') g.rotateY(Math.PI / 2); else if (o.a === 'y') g.rotateX(Math.PI / 2); }
    else {
      g = new T.CylinderGeometry(o.r, o.r, L, o.r > 1.5 ? 24 : 14);
      if (o.a === 'z') g.rotateX(Math.PI / 2); else if (o.a === 'x') g.rotateZ(-Math.PI / 2);
    }
    if (o.a === 'z') g.translate(o.p[0], o.p[1], mid);
    else if (o.a === 'y') g.translate(o.p[0], mid, o.p[1]);
    else g.translate(mid, o.p[0], o.p[1]);
    return g;
  }
  function tubeGeo(pts, r) {
    var n = pts.length, seg = r > 1.2 ? 10 : 7, P = [], pos = [], idx = [];
    for (var i = 0; i < n; i++) P.push(new T.Vector3(pts[i][0], pts[i][1], pts[i][2]));
    var Nv = null;
    for (i = 0; i < n; i++) {
      var tin = i > 0 ? P[i].clone().sub(P[i - 1]).normalize() : null, tout = i < n - 1 ? P[i + 1].clone().sub(P[i]).normalize() : null;
      var t = (tin && tout) ? tin.clone().add(tout) : (tin || tout).clone();
      if (t.lengthSq() < 1e-9) t = (tout || tin).clone();
      t.normalize();
      var sc = 1;
      if (tin && tout) { var c = Math.max(0.35, Math.sqrt(Math.max(0, (1 + tin.dot(tout)) / 2))); sc = Math.min(1.6, 1 / c); }
      if (!Nv) { Nv = Math.abs(t.z) < 0.9 ? new T.Vector3(0, 0, 1) : new T.Vector3(1, 0, 0); }
      Nv.sub(t.clone().multiplyScalar(Nv.dot(t))); if (Nv.lengthSq() < 1e-9) Nv = Math.abs(t.z) < 0.9 ? new T.Vector3(0, 0, 1) : new T.Vector3(1, 0, 0);
      Nv.normalize();
      var Bv = new T.Vector3().crossVectors(t, Nv).normalize();
      for (var k = 0; k < seg; k++) {
        var a = k / seg * Math.PI * 2, ca = Math.cos(a) * r * sc, sa = Math.sin(a) * r * sc;
        pos.push(P[i].x + ca * Nv.x + sa * Bv.x, P[i].y + ca * Nv.y + sa * Bv.y, P[i].z + ca * Nv.z + sa * Bv.z);
      }
    }
    for (i = 0; i < n - 1; i++) for (k = 0; k < seg; k++) {
      var a0 = i * seg + k, a1 = i * seg + (k + 1) % seg, b0 = a0 + seg, b1 = a1 + seg;
      idx.push(a0, b0, a1, a1, b0, b1);
    }
    // end caps (flat)
    [[0, 1], [n - 1, -1]].forEach(function (e) {
      var base = pos.length / 3, c = P[e[0]];
      pos.push(c.x, c.y, c.z);
      for (var q = 0; q < seg; q++) {
        var u = e[0] * seg + q, v = e[0] * seg + (q + 1) % seg;
        if (e[1] > 0) idx.push(base, v, u); else idx.push(base, u, v);
      }
    });
    var g = new T.BufferGeometry();
    g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    return g;
  }
  function shapesOf(polys) {
    if (!polys.length) return [];
    if (typeof polys[0][0] === 'number') polys = [polys];
    var outers = [], holes = [];
    polys.forEach(function (p) {
      if (p.length < 3) return;
      var v = p.map(function (q) { return new T.Vector2(q[0], q[1]); });
      if (T.ShapeUtils.isClockWise(v)) holes.push(v); else outers.push(v);
    });
    if (!outers.length && holes.length) { outers = holes.map(function (h) { return h.slice().reverse(); }); holes = []; }
    var shapes = outers.map(function (v) { return new T.Shape(v); });
    holes.forEach(function (h) {
      var p = h[0], best = 0;
      for (var i = 0; i < outers.length; i++) if (inPoly(p, outers[i])) { best = i; break; }
      if (shapes[best]) shapes[best].holes.push(new T.Path(h));
    });
    return shapes;
  }
  function inPoly(p, v) {
    var c = false;
    for (var i = 0, j = v.length - 1; i < v.length; j = i++) {
      if (((v[i].y > p.y) !== (v[j].y > p.y)) && (p.x < (v[j].x - v[i].x) * (p.y - v[i].y) / (v[j].y - v[i].y) + v[i].x)) c = !c;
    }
    return c;
  }
  function prismGeo(polys, z0, z1) {
    var sh = shapesOf(polys);
    if (!sh.length) return null;
    var g = new T.ExtrudeGeometry(sh, { depth: Math.max(0.05, z1 - z0), bevelEnabled: false, curveSegments: 6 });
    g.translate(0, 0, z0);
    return g;
  }
  function boardMesh(o) {
    var sh = new T.Shape(o.p.map(function (q) { return new T.Vector2(q[0], q[1]); }));
    (o.m || []).forEach(function (h) { var p = new T.Path(); p.absarc(h[0], h[1], h[2] / 2, 0, Math.PI * 2, true); sh.holes.push(p); });
    var g = new T.ExtrudeGeometry(sh, { depth: o.z[1] - o.z[0], bevelEnabled: false, curveSegments: 16 });
    g.translate(0, 0, o.z[0]);
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    o.p.forEach(function (q) { x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); });
    var w = x1 - x0, h = y1 - y0, ppm = Math.min(14, 2048 / Math.max(w, h)), cv = document.createElement('canvas');
    cv.width = Math.max(8, Math.round(w * ppm)); cv.height = Math.max(8, Math.round(h * ppm));
    var ctx = cv.getContext('2d');
    ctx.fillStyle = o.c; ctx.fillRect(0, 0, cv.width, cv.height);
    (o.h || []).forEach(function (q) {
      var cx = (q[0] - x0) * ppm, cy = (y1 - q[1]) * ppm;
      ctx.fillStyle = '#b07a3e'; ctx.beginPath(); ctx.arc(cx, cy, 0.82 * ppm, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#2b2116'; ctx.beginPath(); ctx.arc(cx, cy, 0.48 * ppm, 0, Math.PI * 2); ctx.fill();
    });
    var tex = new T.CanvasTexture(cv);
    tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    tex.repeat.set(1 / w, 1 / h); tex.offset.set(-x0 / w, -y0 / h);
    var cap = new T.MeshStandardMaterial({ map: tex, roughness: 0.7, metalness: 0 });
    var side = new T.MeshStandardMaterial({ color: new T.Color(o.cs || '#a8863f'), roughness: 0.8 });
    var m = new T.Mesh(g, [cap, side]);
    m.userData.fixedMat = [cap, side];
    return m;
  }
  var padGeoRing = null, padGeoDome = null;
  function padGroup(o) {
    if (!padGeoRing) {
      padGeoRing = new T.CylinderGeometry(0.86, 0.86, 0.07, 16); padGeoRing.rotateX(Math.PI / 2);
      padGeoDome = new T.SphereGeometry(0.78, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2); padGeoDome.rotateX(Math.PI / 2); padGeoDome.scale(1, 1, 0.75);
    }
    var gp = new T.Group(), list = [];
    var rT = new T.Mesh(padGeoRing); rT.position.set(o.p[0], o.p[1], o.z[1] + 0.04);
    var rB = new T.Mesh(padGeoRing); rB.position.set(o.p[0], o.p[1], o.z[0] - 0.04);
    rT.userData.role = rB.userData.role = 'ring';
    list.push(rT, rB);
    if (o.s && o.s.indexOf('b') >= 0) { var d = new T.Mesh(padGeoDome); d.position.set(o.p[0], o.p[1], o.z[0] - 0.05); d.scale.z = -1; d.userData.role = 'dome'; list.push(d); }
    if (o.s && o.s.indexOf('t') >= 0) { var u = new T.Mesh(padGeoDome); u.position.set(o.p[0], o.p[1], o.z[1] + 0.05); u.userData.role = 'dome'; list.push(u); }
    list.forEach(function (m) { gp.add(m); });
    return gp;
  }

  // ------------------------------------------------------------------ scene load
  function clearScene() {
    if (root) {
      scene.remove(root);
      root.traverse(function (m) {
        if (m.geometry && m.geometry !== padGeoRing && m.geometry !== padGeoDome) m.geometry.dispose();
        if (m.userData && m.userData.fixedMat) m.userData.fixedMat.forEach(function (x) { if (x.map) x.map.dispose(); x.dispose(); });
      });
    }
    meshes = []; labels = []; picks = [];
  }
  function loadScene(k) {
    clearScene();
    S.sc = k; S.net = null; S.sel = null;
    var sd = D.scenes[k];
    root = new T.Group(); root.rotation.x = -Math.PI / 2; scene.add(root);
    var bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    function grow(b) { for (var i = 0; i < 3; i++) { bb[i] = Math.min(bb[i], b[i]); bb[i + 3] = Math.max(bb[i + 3], b[i + 3]); } }
    sd.objs.forEach(function (o) {
      var m = null;
      if (o.k === 'l') { labels.push(o); return; }
      if (o.k === 'b') { m = new T.Mesh(boxGeo(o.b)); grow(o.b); }
      else if (o.k === 'c') { m = new T.Mesh(cylGeo(o)); }
      else if (o.k === 't') { m = new T.Mesh(tubeGeo(o.p, o.r)); }
      else if (o.k === 'e') { var g = prismGeo(o.p, o.z[0], o.z[1]); if (!g) return; m = new T.Mesh(g); }
      else if (o.k === 'B') { m = boardMesh(o); }
      else if (o.k === 'p') { m = padGroup(o); }
      if (!m) return;
      m.userData.o = o;
      root.add(m);
      meshes.push(m);
      if (o.k === 'p') m.children.forEach(function (c) { c.userData.o = o; picks.push(c); }); else picks.push(m);
    });
    root.updateMatrixWorld(true);
    var b3 = new T.Box3().setFromObject(root);
    sd._box = [b3.min.x, -b3.max.z, b3.min.y, b3.max.x, -b3.min.z, b3.max.y];
    restyle();
    buildViews(sd);
    buildNets(sd);
    sceneBar.querySelectorAll('button').forEach(function (b, i) { b.setAttribute('aria-pressed', i === k ? 'true' : 'false'); });
    subEl.textContent = sd.s || '';
    notesEl.innerHTML = (sd.notes || []).map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('');
    showInfo(null);
    var v0 = sd.v0 && sd.views[sd.v0] ? sd.v0 : null;
    if (v0) setView(v0, true); else fit(sd._box, -0.6, 0.7, true);
  }

  // ------------------------------------------------------------------ style (layers, net highlight, selection)
  function layerOn(o) {
    var g = o.g || 'part';
    if (g === 'pad') return S.lay.board;
    return S.lay[g] !== false;
  }
  function restyle() {
    var hot = S.net, sel = S.sel;
    meshes.forEach(function (m) {
      var o = m.userData.o;
      m.visible = layerOn(o);
      if (!m.visible) return;
      var state = '';
      if (hot) state = (o.n === hot) ? 'hot' : 'dim';
      if (sel && sameItem(o, sel)) state = 'sel';
      if (o.k === 'B') {
        var fm = m.userData.fixedMat;
        fm.forEach(function (x) { x.transparent = state === 'dim'; x.opacity = state === 'dim' ? 0.25 : 1; x.depthWrite = state !== 'dim'; });
        return;
      }
      if (o.k === 'p') {
        m.children.forEach(function (c) {
          var base = c.userData.role === 'ring' ? '#c9894b' : '#c9ccd2';
          if (state === 'hot' || state === 'sel') base = o.n ? D.nets[o.n] || '#3b82f6' : '#3b82f6';
          c.material = mat(base, null, state === 'dim' ? 'dim' : (state ? 'hot' : ''));
        });
        return;
      }
      m.material = mat(o.c || '#888', o.o, state);
    });
    invalidate();
  }
  function sameItem(o, sel) { return o === sel || (sel.i && o.i === sel.i && o.k !== 'p' && sel.k !== 'p'); }

  // ------------------------------------------------------------------ UI
  function button(txt, cls, fn) {
    var b = document.createElement('button');
    b.type = 'button'; b.className = cls; b.textContent = txt;
    b.addEventListener('click', fn);
    return b;
  }
  function buildUi() {
    sceneBar.innerHTML = '';
    D.scenes.forEach(function (s, k) {
      var b = button(s.st || s.t, 'c3d-btn', function () { loadScene(k); });
      b.title = s.t;
      sceneBar.appendChild(b);
    });
    togBar.innerHTML = '';
    LAYERS.forEach(function (L) {
      var b = button(L[1], 'c3d-btn c3d-tog', function () {
        S.lay[L[0]] = !S.lay[L[0]]; b.setAttribute('aria-pressed', S.lay[L[0]] ? 'true' : 'false'); restyle();
      });
      b.setAttribute('aria-pressed', 'true');
      togBar.appendChild(b);
    });
    netSel.addEventListener('change', function () { S.net = netSel.value || null; S.sel = null; restyle(); showNet(); });
    box.querySelector('.c3d-reset').addEventListener('click', function () { var sd = D.scenes[S.sc]; S.net = null; S.sel = null; netSel.value = ''; restyle(); showInfo(null); setView(sd.v0 || Object.keys(sd.views)[0]); });
  }
  function buildViews(sd) {
    viewBar.innerHTML = '';
    Object.keys(sd.views).forEach(function (name) {
      viewBar.appendChild(button(name, 'c3d-btn', function () { setView(name); }));
    });
  }
  function buildNets(sd) {
    var seen = {};
    sd.objs.forEach(function (o) { if (o.n) seen[o.n] = (seen[o.n] || 0) + 1; });
    var names = Object.keys(seen).sort(function (a, b) {
      var pa = /^(\+|GND|AGND)/.test(a) ? 0 : 1, pb = /^(\+|GND|AGND)/.test(b) ? 0 : 1;
      return pa - pb || a.localeCompare(b);
    });
    netSel.innerHTML = '<option value="">넷 강조: 없음</option>' + names.map(function (n) { return '<option value="' + esc(n) + '">' + esc(n) + ' (' + seen[n] + ')</option>'; }).join('');
    netSel.disabled = !names.length;
  }
  function infoOf(o) {
    var I = D.info, key = o.i || '', base = key.split('.')[0];
    return I[key] || I[base] || null;
  }
  function showInfo(o) {
    if (!o) {
      infoBox.innerHTML = '<p class="c3d-muted">부품·패드·선을 누르면 이름, 값, 넷, 구매 상태가 여기에 나옵니다. 패드나 선을 누르면 같은 넷이 함께 밝아집니다.</p>';
      return;
    }
    var I = infoOf(o), key = o.i || '', pin = key.indexOf('.') > 0 ? key.slice(key.indexOf('.') + 1) : null;
    var h = '<p class="c3d-it"><b>' + esc(I ? I.t : key) + '</b></p>';
    if (pin) h += '<p class="c3d-net-l">패드 <span class="mono">' + esc(key) + '</span>' + (o.n ? ' · 넷 <b class="mono" style="color:' + esc(D.nets[o.n] || 'inherit') + '">' + esc(o.n) + '</b>' : ' · 연결 없음') + '</p>';
    else if (o.n) h += '<p class="c3d-net-l">넷 <b class="mono" style="color:' + esc(D.nets[o.n] || 'inherit') + '">' + esc(o.n) + '</b>' + (o.w ? ' · ' + esc(o.w) : '') + '</p>';
    if (I && I.d && I.d.length) h += '<ul>' + I.d.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>';
    infoBox.innerHTML = h;
  }
  function showNet() {
    if (!S.net) { showInfo(null); return; }
    var n = 0;
    D.scenes[S.sc].objs.forEach(function (o) { if (o.n === S.net && o.k === 'p') n++; });
    infoBox.innerHTML = '<p class="c3d-it"><b class="mono" style="color:' + esc(D.nets[S.net] || 'inherit') + '">' + esc(S.net) + '</b></p><p>이 장면에서 패드 ' + n +
      '개와 그 넷의 선·핀이 밝아지고 나머지는 흐려집니다. 넷 목록에서 "없음"을 고르거나 빈 곳을 누르면 돌아갑니다.</p>';
  }

  // ------------------------------------------------------------------ camera
  function size() { return [Math.max(1, stage.clientWidth), Math.max(1, stage.clientHeight)]; }
  function m2t(x, y, z) { return new T.Vector3(x, z, -y); }
  function applyCam() {
    var wh = size();
    camera.aspect = wh[0] / wh[1];
    var t = m2t(cam.tx, cam.ty, cam.tz), ce = Math.cos(cam.el);
    var dir = new T.Vector3(Math.sin(cam.az) * ce, Math.sin(cam.el), Math.cos(cam.az) * ce);
    camera.position.copy(t).add(dir.multiplyScalar(cam.dist));
    camera.up.set(0, 1, 0);
    if (Math.abs(Math.sin(cam.el)) > 0.999) camera.up.set(-Math.sin(cam.az), 0, -Math.cos(cam.az));
    camera.lookAt(t);
    camera.near = Math.max(0.2, cam.dist / 200); camera.far = cam.dist * 30 + 5000;
    camera.updateProjectionMatrix();
  }
  function fit(b, az, el, now) {
    // frame the 8 corners of box b (model mm) for a camera at (az, el): centre the projected extents, then back off until all fit
    var wh = size(), asp = wh[0] / wh[1], ce = Math.cos(el);
    var dir = new T.Vector3(Math.sin(az) * ce, Math.sin(el), Math.cos(az) * ce);
    var up = new T.Vector3(0, 1, 0);
    if (Math.abs(Math.sin(el)) > 0.999) up.set(-Math.sin(az), 0, -Math.cos(az));
    var right = new T.Vector3().crossVectors(up, dir).normalize(), upv = new T.Vector3().crossVectors(dir, right).normalize();
    var c = m2t((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2), pts = [];
    for (var i = 0; i < 8; i++) pts.push(m2t(i & 1 ? b[3] : b[0], i & 2 ? b[4] : b[1], i & 4 ? b[5] : b[2]).sub(c));
    var xr = pts.map(function (p) { return p.dot(right); }), yu = pts.map(function (p) { return p.dot(upv); });
    var sx = (Math.max.apply(null, xr) + Math.min.apply(null, xr)) / 2, sy = (Math.max.apply(null, yu) + Math.min.apply(null, yu)) / 2;
    c.add(right.clone().multiplyScalar(sx)).add(upv.clone().multiplyScalar(sy));
    var D = 0;
    pts.forEach(function (p, k) {
      var x = Math.abs(xr[k] - sx), y = Math.abs(yu[k] - sy), z = p.dot(dir);
      D = Math.max(D, z + x / (TAN * asp), z + y / TAN);
    });
    animTo({ tx: c.x, ty: -c.z, tz: c.y, dist: Math.max(8, D * 1.08), az: az, el: el }, now);
  }
  function setView(name, now) {
    var sd = D.scenes[S.sc], v = sd.views[name];
    if (!v) return;
    fit(v.b, v.az * Math.PI / 180, v.el * Math.PI / 180, now);
  }
  var anim = null;
  function animTo(goal, now) {
    if (now || (mq && mq.matches)) { Object.assign(cam, goal); anim = null; invalidate(); return; }
    var from = Object.assign({}, cam);
    var da = goal.az - from.az; while (da > Math.PI) da -= 2 * Math.PI; while (da < -Math.PI) da += 2 * Math.PI;
    anim = { from: from, goal: Object.assign({}, goal, { az: from.az + da }), t0: performance.now(), dur: 420 };
    invalidate();
  }
  function invalidate() { if (!raf && renderer) raf = requestAnimationFrame(frame); }
  function frame(now) {
    raf = 0;
    if (!renderer || (sec && sec.hidden)) return;
    var wh = size();
    var cw = Math.round(wh[0]), ch = Math.round(wh[1]);
    if (canvas.width !== Math.round(cw * renderer.getPixelRatio()) || canvas.height !== Math.round(ch * renderer.getPixelRatio())) renderer.setSize(cw, ch, false);
    if (anim) {
      var u = Math.min(1, (now - anim.t0) / anim.dur), e = u < 0.5 ? 2 * u * u : 1 - Math.pow(-2 * u + 2, 2) / 2;
      ['tx', 'ty', 'tz', 'dist', 'az', 'el'].forEach(function (k) { cam[k] = anim.from[k] + (anim.goal[k] - anim.from[k]) * e; });
      if (u >= 1) anim = null;
    }
    applyCam();
    renderer.render(scene, camera);
    drawLabels();
    if (anim) invalidate();
  }

  // ------------------------------------------------------------------ labels (SVG overlay, greedy de-overlap)
  function drawLabels() {
    if (!S.lay.lab) { over.innerHTML = ''; return; }
    var wh = size(), placed = [], out = '';
    var list = labels.slice().sort(function (a, b) { return (a.lv || 0) - (b.lv || 0); });
    list.forEach(function (l) {
      var v = m2t(l.p[0], l.p[1], l.p[2]).applyMatrix4(new T.Matrix4()).project(camera);
      if (v.z > 1 || v.z < -1) return;
      var x = (v.x + 1) / 2 * wh[0], y = (1 - v.y) / 2 * wh[1];
      if (x < 4 || y < 10 || x > wh[0] - 4 || y > wh[1] - 4) return;
      var w = l.t.length * 7.2 + 10, h = 18, r = [x - w / 2, y - h, x + w / 2, y];
      for (var i = 0; i < placed.length; i++) { var q = placed[i]; if (r[0] < q[2] && r[2] > q[0] && r[1] < q[3] && r[3] > q[1]) return; }
      placed.push(r);
      out += '<text class="lv' + (l.lv || 0) + '" x="' + x.toFixed(1) + '" y="' + (y - 5).toFixed(1) + '" text-anchor="middle">' + esc(l.t) + '</text>';
    });
    over.innerHTML = out;
  }

  // ------------------------------------------------------------------ pointer: rotate / pan / pinch / tap
  function bindPointer() {
    var ptrs = {}, drag = null;
    canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    canvas.addEventListener('pointerdown', function (e) {
      try { canvas.setPointerCapture(e.pointerId); } catch (x) { /* */ }
      ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
      var np = Object.keys(ptrs).length;
      anim = null;
      if (np === 1) drag = { mode: (e.button === 2 || e.shiftKey || e.ctrlKey || e.metaKey) ? 'pan' : 'rot', x: e.clientX, y: e.clientY, moved: false, t0: performance.now(), btn: e.button };
      else if (np === 2) { var p = Object.keys(ptrs).map(function (k) { return ptrs[k]; }); drag = { mode: 'pinch', d: Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y), cx: (p[0].x + p[1].x) / 2, cy: (p[0].y + p[1].y) / 2, moved: true, dist: cam.dist }; }
    });
    canvas.addEventListener('pointermove', function (e) {
      if (!ptrs[e.pointerId] || !drag) return;
      ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
      if (drag.mode === 'pinch') {
        var p = Object.keys(ptrs).map(function (k) { return ptrs[k]; });
        if (p.length < 2) return;
        var d = Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y), cx = (p[0].x + p[1].x) / 2, cy = (p[0].y + p[1].y) / 2;
        cam.dist = Math.max(4, drag.dist * drag.d / Math.max(10, d));
        pan(cx - drag.cx, cy - drag.cy); drag.cx = cx; drag.cy = cy;
        invalidate(); return;
      }
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
      drag.x = e.clientX; drag.y = e.clientY;
      if (drag.mode === 'rot') { cam.az -= dx * 0.008; cam.el = Math.max(-1.55, Math.min(1.55, cam.el + dy * 0.008)); }
      else pan(dx, dy);
      invalidate();
    });
    function end(e) {
      if (!ptrs[e.pointerId]) return;
      delete ptrs[e.pointerId];
      var np = Object.keys(ptrs).length;
      if (drag && drag.mode !== 'pinch' && np === 0 && !drag.moved && performance.now() - drag.t0 < 650 && drag.btn === 0 && e.type === 'pointerup') tap(e.clientX, e.clientY);
      if (np === 0) drag = null;
    }
    canvas.addEventListener('pointerup', end);
    canvas.addEventListener('pointercancel', end);
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault(); anim = null;
      var f = Math.exp((e.deltaMode === 1 ? e.deltaY * 16 : e.deltaY) * 0.0012);
      zoomAt(e.clientX, e.clientY, f);
    }, { passive: false });
    canvas.addEventListener('dblclick', function (e) {
      var h = hit(e.clientX, e.clientY);
      if (!h) return;
      var p = h.point.clone();                    // three world -> model
      animTo({ tx: p.x, ty: -p.z, tz: p.y, dist: Math.max(10, cam.dist * 0.45), az: cam.az, el: cam.el });
    });
    canvas.addEventListener('keydown', function (e) {
      var k = e.key, used = true;
      if (k === 'ArrowLeft') cam.az += 0.08; else if (k === 'ArrowRight') cam.az -= 0.08;
      else if (k === 'ArrowUp') cam.el = Math.min(1.55, cam.el + 0.08); else if (k === 'ArrowDown') cam.el = Math.max(-1.55, cam.el - 0.08);
      else if (k === '+' || k === '=') cam.dist *= 0.85; else if (k === '-') cam.dist /= 0.85; else used = false;
      if (used) { e.preventDefault(); invalidate(); }
    });
  }
  function pan(dx, dy) {
    var wh = size(), mmpp = 2 * cam.dist * TAN / wh[1];
    var right = new T.Vector3(), up = new T.Vector3();
    camera.matrixWorld.extractBasis(right, up, new T.Vector3());
    var d = right.multiplyScalar(-dx * mmpp).add(up.multiplyScalar(dy * mmpp));
    cam.tx += d.x; cam.ty += -d.z; cam.tz += d.y;
  }
  function zoomAt(cx, cy, f) {
    var r = canvas.getBoundingClientRect(), wh = size();
    var nx = (cx - r.left) / wh[0] - 0.5, ny = (cy - r.top) / wh[1] - 0.5;
    var before = cam.dist;
    cam.dist = Math.max(4, Math.min(20000, cam.dist * f));
    var k = (before - cam.dist) / before;                // move the target toward the cursor as we zoom in
    pan(-nx * wh[0] * k, -ny * wh[1] * k);
    invalidate();
  }
  var ray = null;
  function hit(cx, cy) {
    if (!ray) ray = new T.Raycaster();
    var r = canvas.getBoundingClientRect();
    ray.setFromCamera(new T.Vector2((cx - r.left) / r.width * 2 - 1, -((cy - r.top) / r.height) * 2 + 1), camera);
    var vis = picks.filter(function (m) { var o = m.userData.o; return layerOn(o) && !(S.net && o.n !== S.net && o.g === 'ctx'); });
    var hs = ray.intersectObjects(vis, false);
    for (var i = 0; i < hs.length; i++) {
      var o = hs[i].object.userData.o;
      if (o.g === 'ctx' && hs.length > i + 1) continue;          // ghosts never hide what is behind them
      if (S.net && o.n !== S.net && hs[i].object.material && hs[i].object.material.opacity < 0.2) continue;
      return hs[i];
    }
    return null;
  }
  function tap(cx, cy) {
    var h = hit(cx, cy);
    if (!h) { S.sel = null; S.net = null; netSel.value = ''; restyle(); showInfo(null); return; }
    var o = h.object.userData.o;
    S.sel = o;
    if (o.n) { S.net = o.n; netSel.value = o.n; } else if (S.net && o.n !== S.net) { S.net = null; netSel.value = ''; }
    restyle();
    showInfo(o);
  }
})();
