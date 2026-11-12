/* 01 회로도 · 회로 3D 모델 (hardware/pcb/src/circuit3d.js; page.py appends it to page/circuit.js).
   Data: fin/circuit/circuit3d.json from src/model3d.py (boards, holes, pads, parts, wires; mm, z up from the desk).
   Only three.js r128 from cdnjs, loaded once through window.toccata.three (shared with 04 3D 모델). Orbit / pan / zoom, touch,
   picking, net highlight and layer toggles are written here. Loads when the 3D block first scrolls into view (or on its button).
   Objects are merged into one mesh per material (restyle) and picked by a ray against their own triangles (pickAll); a click opens
   the same popup as the drawings (.hitpop): what the thing is, what it connects to, where it sits (scope o.m), its net.
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
  var S = { sc: -1, lay: { part: true, wire: true, cable: true, board: true, ctx: true, lab: true }, hot: null, sel: null };
  var cam = { tx: 0, ty: 0, tz: 0, dist: 300, az: -0.6, el: 0.7 };
  var prims = [], batches = [], boards = [], labels = [];
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
    if (state === 'dim') op = Math.min(op, 0.13);
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
  function prismGeo(polys, z0, z1, ax) {
    var sh = shapesOf(polys);
    if (!sh.length) return null;
    var g = new T.ExtrudeGeometry(sh, { depth: Math.max(0.05, z1 - z0), bevelEnabled: false, curveSegments: 6 });
    g.translate(0, 0, z0);
    // ax 'x': the outline is a side view (y, z) extruded along x -> (u, v, w) = (x', y', z') becomes model (w, u, v)
    if (ax === 'x') g.applyMatrix4(new T.Matrix4().set(0, 0, 1, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1));
    return g;
  }
  // perfboards: geometry + hole texture in board-local coordinates, shared by every board of the same shape (7 SB, 7 MB)
  var boardCache = {};
  function boardMesh(o) {
    var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    o.p.forEach(function (q) { x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); });
    function rel(a) { return (a || []).map(function (q) { return [Math.round((q[0] - x0) * 100) / 100, Math.round((q[1] - y0) * 100) / 100].concat(q.slice(2)); }); }
    var hg = o.hg ? [Math.round((o.hg[0] - x0) * 100) / 100, o.hg[1], o.hg[2], Math.round((o.hg[3] - y0) * 100) / 100, o.hg[4], o.hg[5]] : null;
    var P = rel(o.p), H = rel(o.h), M = rel(o.md), th = Math.round((o.z[1] - o.z[0]) * 100) / 100;
    var key = JSON.stringify([P, H, M, hg, th, o.c, o.cs]), B = boardCache[key];
    if (!B) {
      var sh = new T.Shape(P.map(function (q) { return new T.Vector2(q[0], q[1]); }));
      M.forEach(function (h) { var p = new T.Path(); p.absarc(h[0], h[1], h[2] / 2, 0, Math.PI * 2, true); sh.holes.push(p); });
      var g = new T.ExtrudeGeometry(sh, { depth: th, bevelEnabled: false, curveSegments: 16 });
      var w = x1 - x0, h = y1 - y0, ppm = Math.min(14, 2048 / Math.max(w, h)), cv = document.createElement('canvas');
      cv.width = Math.max(8, Math.round(w * ppm)); cv.height = Math.max(8, Math.round(h * ppm));
      var ctx = cv.getContext('2d');
      ctx.fillStyle = o.c; ctx.fillRect(0, 0, cv.width, cv.height);
      var holes = H.slice();
      if (hg) for (var i = 0; i < hg[2]; i++) for (var j = 0; j < hg[5]; j++) holes.push([hg[0] + hg[1] * i, hg[3] + hg[4] * j]);
      holes.forEach(function (q) {
        var cx = q[0] * ppm, cy = (h - q[1]) * ppm;
        ctx.fillStyle = '#b07a3e'; ctx.beginPath(); ctx.arc(cx, cy, 0.82 * ppm, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = '#2b2116'; ctx.beginPath(); ctx.arc(cx, cy, 0.48 * ppm, 0, Math.PI * 2); ctx.fill();
      });
      var tex = new T.CanvasTexture(cv);
      tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
      tex.repeat.set(1 / w, 1 / h);
      B = boardCache[key] = { g: g, mats: [new T.MeshStandardMaterial({ map: tex, roughness: 0.7, metalness: 0 }),
                                           new T.MeshStandardMaterial({ color: new T.Color(o.cs || '#a8863f'), roughness: 0.8 })] };
    }
    var m = new T.Mesh(B.g, B.mats);
    m.position.set(x0, y0, o.z[0]);
    return m;
  }
  // pad templates (at the origin): copper ring, solder dome up / down
  var padT = null;
  function arrays(g) {
    if (!g.attributes.normal) g.computeVertexNormals();
    var r = { pos: g.attributes.position.array, nor: g.attributes.normal.array, idx: g.index ? g.index.array : null };
    g.dispose();
    return r;
  }
  function padTemplates() {
    var ring = new T.CylinderGeometry(0.86, 0.86, 0.07, 12); ring.rotateX(Math.PI / 2);
    var up = new T.SphereGeometry(0.78, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2); up.rotateX(Math.PI / 2); up.scale(1, 1, 0.75);
    var U = arrays(up), dn = { pos: new Float32Array(U.pos), nor: new Float32Array(U.nor), idx: new (U.idx.constructor)(U.idx) };
    for (var i = 2; i < dn.pos.length; i += 3) { dn.pos[i] = -dn.pos[i]; dn.nor[i] = -dn.nor[i]; }
    for (i = 0; i < dn.idx.length; i += 3) { var t = dn.idx[i + 1]; dn.idx[i + 1] = dn.idx[i + 2]; dn.idx[i + 2] = t; }
    padT = { ring: arrays(ring), up: U, dn: dn };
  }
  function moved(t, x, y, z) {
    var pos = new Float32Array(t.pos.length);
    for (var i = 0; i < pos.length; i += 3) { pos[i] = t.pos[i] + x; pos[i + 1] = t.pos[i + 1] + y; pos[i + 2] = t.pos[i + 2] + z; }
    return { pos: pos, nor: t.nor, idx: t.idx };
  }

  // ------------------------------------------------------------------ scene load: every object -> primitives (arrays in model mm)
  // Drawing: the primitives are merged into one mesh per material (colour / opacity / state), rebuilt when the style changes - the
  // instrument scene has ~3500 objects and ~1100 pads, far too many for one draw call each. Picking: ray against the primitives.
  function addPrim(o, a, role) {
    var n = a.pos.length / 3, x0 = 1e9, y0 = 1e9, z0 = 1e9, x1 = -1e9, y1 = -1e9, z1 = -1e9, p = a.pos;
    for (var i = 0; i < p.length; i += 3) {
      if (p[i] < x0) x0 = p[i]; if (p[i] > x1) x1 = p[i];
      if (p[i + 1] < y0) y0 = p[i + 1]; if (p[i + 1] > y1) y1 = p[i + 1];
      if (p[i + 2] < z0) z0 = p[i + 2]; if (p[i + 2] > z1) z1 = p[i + 2];
    }
    prims.push({ o: o, role: role || '', pos: a.pos, nor: a.nor, idx: a.idx, n: n,
                 c: [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], r: Math.sqrt((x1 - x0) * (x1 - x0) + (y1 - y0) * (y1 - y0) + (z1 - z0) * (z1 - z0)) / 2 + 0.05 });
  }
  function clearScene() {
    if (root) {
      scene.remove(root);
      batches.forEach(function (m) { m.geometry.dispose(); });
    }
    prims = []; batches = []; boards = []; labels = [];
  }
  function loadScene(k) {
    clearScene();
    closePop();
    S.sc = k; S.hot = null; S.sel = null;
    var sd = D.scenes[k];
    JOIN = sd.join || {};
    root = new T.Group(); root.rotation.x = -Math.PI / 2; scene.add(root);
    if (!padT) padTemplates();
    sd.objs.forEach(function (o) {
      var g = null;
      if (o.k === 'l') { labels.push(o); return; }
      if (o.k === 'b') g = boxGeo(o.b);
      else if (o.k === 'c') g = cylGeo(o);
      else if (o.k === 't') g = tubeGeo(o.p, o.r);
      else if (o.k === 'e') g = prismGeo(o.p, o.z[0], o.z[1], o.ax);
      else if (o.k === 'B') {
        var m = boardMesh(o); m.userData.o = o; root.add(m); boards.push(m);
        var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
        o.p.forEach(function (q) { x0 = Math.min(x0, q[0]); y0 = Math.min(y0, q[1]); x1 = Math.max(x1, q[0]); y1 = Math.max(y1, q[1]); });
        addPrim(o, arrays(boxGeo([x0, y0, o.z[0], x1, y1, o.z[1]])), 'pick');      // boards are drawn by their own mesh, this is for picking
        return;
      }
      else if (o.k === 'p') {
        addPrim(o, moved(padT.ring, o.p[0], o.p[1], o.z[1] + 0.04), 'ring');
        addPrim(o, moved(padT.ring, o.p[0], o.p[1], o.z[0] - 0.04), 'ring');
        if (o.s && o.s.indexOf('b') >= 0) addPrim(o, moved(padT.dn, o.p[0], o.p[1], o.z[0] - 0.05), 'dome');
        if (o.s && o.s.indexOf('t') >= 0) addPrim(o, moved(padT.up, o.p[0], o.p[1], o.z[1] + 0.05), 'dome');
        return;
      }
      if (g) addPrim(o, arrays(g));
    });
    var bb = [1e9, 1e9, 1e9, -1e9, -1e9, -1e9];
    prims.forEach(function (p) { for (var i = 0; i < 3; i++) { bb[i] = Math.min(bb[i], p.c[i] - p.r); bb[i + 3] = Math.max(bb[i + 3], p.c[i] + p.r); } });
    sd._box = bb;
    restyle();
    buildViews(sd);
    buildNets(sd);
    sceneBar.querySelectorAll('button').forEach(function (b, i) { b.setAttribute('aria-pressed', i === k ? 'true' : 'false'); });
    subEl.textContent = sd.s || '';
    notesEl.innerHTML = (sd.notes || []).map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('');
    var v0 = sd.v0 && sd.views[sd.v0] ? sd.v0 : null;
    if (v0) setView(v0, true); else fit(sd._box, -0.6, 0.7, true);
  }

  // ------------------------------------------------------------------ style (layers, net highlight, selection)
  // A net name is one net only inside its scope o.m (each module has its own HALL_C); the scene's join table ties scopes together
  // (the end-part nets = the EXT nets of the end boards, one GND for the instrument).
  var JOIN = {};
  function netKey(o) { if (!o.n) return null; var k = (o.m || '') + '|' + o.n; return JOIN[k] || k; }
  function isHot(o) { return !!(S.hot && o.n && (S.hot.key ? netKey(o) === S.hot.key : o.n === S.hot.name)); }
  function sameItem(o, sel) { return o === sel || (sel.i && o.i === sel.i && (o.m || '') === (sel.m || '') && o.k !== 'p' && sel.k !== 'p'); }
  function stateOf(o) {
    var st = '';
    if (S.hot) st = isHot(o) ? 'hot' : 'dim';
    if (S.sel && sameItem(o, S.sel)) st = 'sel';
    return st;
  }
  function layerOn(o) {
    var g = o.g || 'part';
    if (g === 'pad') return S.lay.board;
    return S.lay[g] !== false;
  }
  function restyle() {
    batches.forEach(function (m) { root.remove(m); m.geometry.dispose(); });
    batches = [];
    var groups = {}, order = [], i, p, o;
    for (i = 0; i < prims.length; i++) {
      p = prims[i]; o = p.o;
      p.st = null;
      if (!layerOn(o)) continue;
      var st = stateOf(o), c, op = o.o;
      p.st = st;
      if (p.role === 'pick') continue;
      if (o.k === 'p') {
        c = p.role === 'ring' ? '#c9894b' : '#c9ccd2';
        if (st === 'hot' || st === 'sel') c = o.n ? D.nets[o.n] || '#3b82f6' : '#3b82f6';
        st = st === 'dim' ? 'dim' : (st ? 'hot' : ''); op = null;
      } else c = o.c || '#888';
      if (st === 'sel' || st === 'hot') op = null;                // a picked or lit thing is drawn solid, even a faint wire or a ghost
      var key = c + '|' + (op == null ? 1 : op) + '|' + st, G = groups[key];
      if (!G) { G = groups[key] = { c: c, o: op, st: st, list: [], nv: 0, ni: 0 }; order.push(key); }
      G.list.push(p); G.nv += p.n; G.ni += p.idx ? p.idx.length : p.n;
    }
    order.forEach(function (key) {
      var G = groups[key], pos = new Float32Array(G.nv * 3), nor = new Float32Array(G.nv * 3), idx = new Uint32Array(G.ni), vo = 0, io = 0, q;
      for (var k = 0; k < G.list.length; k++) {
        var p = G.list[k];
        pos.set(p.pos, vo * 3); nor.set(p.nor, vo * 3);
        if (p.idx) { for (q = 0; q < p.idx.length; q++) idx[io + q] = p.idx[q] + vo; io += p.idx.length; }
        else { for (q = 0; q < p.n; q++) idx[io + q] = vo + q; io += p.n; }
        vo += p.n;
      }
      var g = new T.BufferGeometry();
      g.setAttribute('position', new T.BufferAttribute(pos, 3));
      g.setAttribute('normal', new T.BufferAttribute(nor, 3));
      g.setIndex(new T.BufferAttribute(idx, 1));
      var m = new T.Mesh(g, mat(G.c, G.o, G.st));
      m.frustumCulled = false;
      if (m.material.transparent) m.renderOrder = G.st === 'dim' ? 1 : 2;
      root.add(m); batches.push(m);
    });
    var dimB = !!S.hot;
    boards.forEach(function (m) {
      m.visible = layerOn(m.userData.o);
      m.material.forEach(function (x) { x.transparent = dimB; x.opacity = dimB ? 0.32 : 1; x.depthWrite = !dimB; x.needsUpdate = true; });
    });
    invalidate();
  }

  // ------------------------------------------------------------------ UI
  function button(txt, cls, fn) {
    var b = document.createElement('button');
    b.type = 'button'; b.className = cls; b.textContent = txt;
    b.addEventListener('click', fn);
    return b;
  }
  function clearSel() { S.hot = null; S.sel = null; netSel.value = ''; restyle(); closePop(); }
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
    netSel.addEventListener('change', function () {
      S.sel = null; S.hot = netSel.value ? { name: netSel.value } : null; restyle();
      if (S.hot) showPop(netHtml({ n: netSel.value }, true), null); else closePop();
    });
    box.querySelector('.c3d-reset').addEventListener('click', function () { var sd = D.scenes[S.sc]; clearSel(); setView(sd.v0 || Object.keys(sd.views)[0]); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && pop && !pop.hidden) clearSel(); });
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

  // ------------------------------------------------------------------ click info: what it is, the product, what it connects to
  // The same block as the drawings' popup (page.py 'sheet hits'): title, lines, then the net - here with where the thing sits too.
  function infoOf(o) {
    var I = D.info, key = o.i || '', base = key.split('.')[0];
    return (o.v && I[key + '@' + o.v]) || I[key] || (o.v && I[base + '@' + o.v]) || I[base] || null;
  }
  function list(a) { return a && a.length ? '<ul>' + a.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : ''; }
  function netText(o) {
    var N = D.netinfo || {}, sd = D.scenes[S.sc], g = o.m || sd.g0 || '';
    return N[g + '|' + o.n] || N[o.n] || { t: '넷 ' + o.n, d: [] };
  }
  function netHtml(o, byName) {
    var sd = D.scenes[S.sc], N = netText(o), key = byName ? null : netKey(o), d = (N.d || []).slice(), pads = [], names = {}, cnt = 0, scopes = {};
    sd.objs.forEach(function (x) {
      if (!x.n || (byName ? x.n !== o.n : netKey(x) !== key)) return;
      if (x.m) scopes[x.m] = 1;
      if (x.n !== o.n || (!byName && (x.m || '') !== (o.m || ''))) names[(x.m ? x.m + '의 ' : '') + x.n] = 1;
      if (x.k !== 'p') return;
      cnt++;
      var t = ((x.m || '') !== (o.m || '') && x.m ? x.m + ' ' : '') + x.i;
      if (pads.indexOf(t) < 0) pads.push(t);
    });
    if (byName) {
      var sc = Object.keys(scopes);
      if (sc.length > 1) d.push('이 이름의 넷은 ' + sc.join(' · ') + '에 따로 있습니다 — 모두 밝혔습니다. 한 곳만 보려면 그 선이나 패드를 누르세요.');
    } else {
      var other = Object.keys(names).filter(function (t) { return !/GND$/.test(t); });
      if (other.length) d.push('커넥터를 지나 같은 선으로 이어진 다른 이름: ' + other.join(', '));
      if (o.n === 'GND' && Object.keys(scopes).length > 1) d.push('GND는 USB 선과 EXT 선으로 이어져 악기 전체가 한 접지입니다 — 모두 밝혔습니다.');
    }
    if (cnt) d.push(cnt > 40 ? '이 장면에서 이 넷에 이어진 패드 ' + cnt + '개 (밝아진 곳)' :
                    '이 장면에서 이 넷에 이어진 패드 ' + cnt + '개: ' + pads.slice(0, 28).join(', ') + (pads.length > 28 ? ' …' : ''));
    return '<div class="hit-n"><p><span class="sw" style="background:' + esc(D.nets[o.n] || '#555') + '"></span><b>' + esc(N.t) + '</b></p>' + list(d) + '</div>';
  }
  function infoHtml(o) {
    var I = infoOf(o), sd = D.scenes[S.sc], d = [];
    if (o.q) d.push(o.q);
    if (o.w) d.push('선 종류: ' + o.w);
    if (I && I.d) d = d.concat(I.d);
    var h = '<p class="hit-t"><b>' + esc(I ? I.t : (o.i || '')) + '</b></p>' + list(d);
    var sc = o.m && sd.scopes && sd.scopes[o.m];
    if (sc) h += '<div class="hit-n"><p><b>' + esc('자리 · ' + sc.t) + '</b></p>' + list(sc.d) + '</div>';
    if (o.n) h += netHtml(o, false);
    else if (o.k === 'p') h += '<div class="hit-n"><p>넷 없음 — 다른 곳과 이어지지 않는 패드입니다.</p></div>';
    return h;
  }
  var pop = null;
  function showPop(html, at) {
    if (!pop) {
      pop = document.createElement('div'); pop.className = 'hitpop c3d-pop'; pop.setAttribute('role', 'region'); pop.setAttribute('aria-label', '3D 모델 항목 정보');
      pop.setAttribute('aria-live', 'polite'); stage.appendChild(pop);
      pop.addEventListener('click', function (ev) { if (ev.target.closest && ev.target.closest('.hitx')) clearSel(); });
      ['pointerdown', 'wheel', 'dblclick'].forEach(function (t) { pop.addEventListener(t, function (ev) { ev.stopPropagation(); }); });
    }
    pop.innerHTML = '<button type="button" class="hitx" aria-label="닫기">×</button>' + html;
    pop.hidden = false; pop.scrollTop = 0;
    // beside the click (right, else left) so the picked thing stays visible; a net chosen from the list goes to the top right corner
    var W = stage.clientWidth, H = stage.clientHeight, pw = Math.min(360, W - 16), L, Tp;
    pop.style.width = pw + 'px';
    if (!at) { L = W - pw - 8; Tp = 8; }
    else {
      var r = stage.getBoundingClientRect(), x = at[0] - r.left, y = at[1] - r.top;
      if (x + 22 + pw <= W - 8) L = x + 22; else if (x - 22 - pw >= 8) L = x - 22 - pw; else L = Math.max(8, Math.min(x - pw / 2, W - pw - 8));
      Tp = y - 28;
    }
    pop.style.left = L + 'px';
    pop.style.top = Math.max(8, Math.min(Tp, H - pop.offsetHeight - 8)) + 'px';
  }
  function closePop() { if (pop) pop.hidden = true; }

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
      if (l.dz && cam.dist > l.dz) return;                       // a module's own labels only when the camera is near it
      var v = m2t(l.p[0], l.p[1], l.p[2]).project(camera);
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
      canvas.style.cursor = '';
      if (np === 1) drag = { mode: (e.button === 2 || e.shiftKey || e.ctrlKey || e.metaKey) ? 'pan' : 'rot', x: e.clientX, y: e.clientY, moved: false, t0: performance.now(), btn: e.button };
      else if (np === 2) { var p = Object.keys(ptrs).map(function (k) { return ptrs[k]; }); drag = { mode: 'pinch', d: Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y), cx: (p[0].x + p[1].x) / 2, cy: (p[0].y + p[1].y) / 2, moved: true, dist: cam.dist }; }
    });
    var hov = 0, hovE = null;
    canvas.addEventListener('pointermove', function (e) {
      if (!drag && (!e.pointerType || e.pointerType === 'mouse')) {       // hover: a pointer cursor over anything that can be picked
        hovE = e;
        if (!hov) hov = requestAnimationFrame(function () { hov = 0; if (!drag && camera) canvas.style.cursor = pick(hovE.clientX, hovE.clientY) ? 'pointer' : ''; });
        return;
      }
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
      var h = pick(e.clientX, e.clientY);
      if (!h) return;
      var R = h.R;                                 // the hit point in model mm
      animTo({ tx: R.o[0] + R.d[0] * h.t, ty: R.o[1] + R.d[1] * h.t, tz: R.o[2] + R.d[2] * h.t, dist: Math.max(10, cam.dist * 0.45), az: cam.az, el: cam.el });
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
  // ray against the primitives (model mm): bounding spheres first, then the triangles of the few candidates
  var ray = null;
  function pickAll(cx, cy) {
    if (!ray) ray = new T.Raycaster();
    var r = canvas.getBoundingClientRect();
    ray.setFromCamera(new T.Vector2((cx - r.left) / r.width * 2 - 1, -((cy - r.top) / r.height) * 2 + 1), camera);
    var O = ray.ray.origin, Dv = ray.ray.direction;
    var ox = O.x, oy = -O.z, oz = O.y, dx = Dv.x, dy = -Dv.z, dz = Dv.y, hits = [];       // three (x, y, z) = model (x, z, -y)
    for (var i = 0; i < prims.length; i++) {
      var p = prims[i];
      if (p.st === null) continue;                                // layer off
      var lx = p.c[0] - ox, ly = p.c[1] - oy, lz = p.c[2] - oz, tc = lx * dx + ly * dy + lz * dz;
      if (lx * lx + ly * ly + lz * lz - tc * tc > p.r * p.r) continue;
      var pos = p.pos, idx = p.idx, nt = (idx ? idx.length : p.n) / 3, best = Infinity;
      for (var k = 0; k < nt; k++) {
        var a = (idx ? idx[k * 3] : k * 3) * 3, b = (idx ? idx[k * 3 + 1] : k * 3 + 1) * 3, c = (idx ? idx[k * 3 + 2] : k * 3 + 2) * 3;
        var e1x = pos[b] - pos[a], e1y = pos[b + 1] - pos[a + 1], e1z = pos[b + 2] - pos[a + 2];
        var e2x = pos[c] - pos[a], e2y = pos[c + 1] - pos[a + 1], e2z = pos[c + 2] - pos[a + 2];
        var px = dy * e2z - dz * e2y, py = dz * e2x - dx * e2z, pz = dx * e2y - dy * e2x, det = e1x * px + e1y * py + e1z * pz;
        if (det > -1e-12 && det < 1e-12) continue;
        var inv = 1 / det, tx = ox - pos[a], ty = oy - pos[a + 1], tz = oz - pos[a + 2], u = (tx * px + ty * py + tz * pz) * inv;
        if (u < 0 || u > 1) continue;
        var qx = ty * e1z - tz * e1y, qy = tz * e1x - tx * e1z, qz = tx * e1y - ty * e1x, v = (dx * qx + dy * qy + dz * qz) * inv;
        if (v < 0 || u + v > 1) continue;
        var t = (e2x * qx + e2y * qy + e2z * qz) * inv;
        if (t > 0.01 && t < best) best = t;
      }
      if (best < Infinity) hits.push({ t: best, p: p });
    }
    hits.sort(function (a, b) { return a.t - b.t; });
    return { hits: hits, o: [ox, oy, oz], d: [dx, dy, dz] };
  }
  // thin things (wires, cable cores, pads) are hard to hit exactly: the nearest one within a few pixels of the ray, not behind
  // what the ray hits first (tmax)
  function nearThin(R, tmax, wantSolid) {
    var ox = R.o[0], oy = R.o[1], oz = R.o[2], dx = R.d[0], dy = R.d[1], dz = R.d[2], best = null, bd = 1e9, last = null;
    var pxmm = 2 * TAN / size()[1];                                 // mm per pixel at 1 mm from the camera
    function seg(p, ax, ay, az, bx, by, bz, rad) {
      // closest approach of the ray and the segment a-b
      var ux = bx - ax, uy = by - ay, uz = bz - az, wx = ox - ax, wy = oy - ay, wz = oz - az;
      var b = dx * ux + dy * uy + dz * uz, c = ux * ux + uy * uy + uz * uz, d = dx * wx + dy * wy + dz * wz, e = ux * wx + uy * wy + uz * wz;
      var den = c - b * b, s = den > 1e-9 ? (c * -d + b * e) / den : -d, u = den > 1e-9 ? (e - b * d) / den : 0;   // ray s, segment u
      if (c < 1e-12) { u = 0; s = -d; } else { u = u < 0 ? 0 : (u > 1 ? 1 : u); s = b * u - d; }
      if (s <= 0.01 || s > tmax) return;
      var qx = ox + dx * s - (ax + ux * u), qy = oy + dy * s - (ay + uy * u), qz = oz + dz * s - (az + uz * u);
      var dist = Math.sqrt(qx * qx + qy * qy + qz * qz) - rad, tol = 7 * pxmm * s;
      if (dist > tol) return;
      var score = Math.max(dist, 0) / tol + s * 1e-5;               // nearer to the ray first, then nearer to the camera
      if (score < bd) { bd = score; best = { o: p.o, t: s, R: R }; }
    }
    for (var i = 0; i < prims.length; i++) {
      var p = prims[i], o = p.o;
      if (p.st === null || o === last || (wantSolid && p.st === 'dim')) continue;
      if (o.k === 'p') { if (p.role === 'ring') { last = o; seg(p, o.p[0], o.p[1], o.z[0], o.p[0], o.p[1], o.z[1], 0.86); } continue; }
      if (o.k !== 't' || o.r > 1.0 || o.g === 'part') continue;
      // only tubes whose bounding sphere comes near the ray
      var lx = p.c[0] - ox, ly = p.c[1] - oy, lz = p.c[2] - oz, tc = lx * dx + ly * dy + lz * dz, lim = p.r + 7 * pxmm * Math.max(tc, 1);
      if (lx * lx + ly * ly + lz * lz - tc * tc > lim * lim) continue;
      for (var k = 1; k < o.p.length; k++) seg(p, o.p[k - 1][0], o.p[k - 1][1], o.p[k - 1][2], o.p[k][0], o.p[k][1], o.p[k][2], o.r);
    }
    return best;
  }
  function pick(cx, cy) {
    // what is drawn solid wins over what is dimmed or ghosted in front of it; a dimmed thing is still picked when nothing else is there.
    // A board or nothing under the pointer: a wire / pad within a few pixels wins (it must not lie behind the board).
    var R = pickAll(cx, cy), hs = R.hits, i, o, fall = null, hit = null;
    for (i = 0; i < hs.length; i++) {
      o = hs[i].p.o;
      var ghost = o.g === 'ctx' || hs[i].p.st === 'dim' || (hs[i].p.role === 'pick' && S.hot);
      if (!ghost) { hit = { o: o, t: hs[i].t, R: R, board: hs[i].p.role === 'pick' }; break; }
      if (!fall || (fall.o.g === 'ctx' && o.g !== 'ctx')) fall = { o: o, t: hs[i].t, R: R };
    }
    if (hit && !hit.board) return hit;
    var near = nearThin(R, hit ? hit.t + 0.6 : 1e9, !!S.hot && !hit && !fall);
    return near || hit || fall;
  }
  function tap(cx, cy) {
    var h = pick(cx, cy);
    if (!h) { clearSel(); return; }
    var o = h.o;
    S.sel = o;
    S.hot = o.n ? { key: netKey(o) } : null;
    netSel.value = o.n || '';
    restyle();
    showPop(infoHtml(o), [cx, cy]);
  }
})();
