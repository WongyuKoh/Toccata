/* 04 3D 모델 — Toccata assembly viewer (hardware/mechanical/cad/viewer/cad.js; data from gen_viewer.py).
   Runtime files next to the page: cad/parts.json, cad/toccata.glb.b64.txt (base64 of viewer/toccata_viewer.glb).
   Only three.js r128 from cdnjs. GLB parsing (one node per part, uint16 positions = KHR_mesh_quantization), orbit / pan /
   zoom, touch and picking are written here (no example scripts). Loads when the tab is first shown.
   Model coordinates: mm, x across (0 = A0 left end), y from the white-key front lip backwards, z up from the desk.
   The scene root turns them into three's y-up: (x, y, z) -> (x, z, -y).

   API for other tabs:  window.toccata.cad
     focus(sel, label, opts) -> Promise<number of parts shown>
         sel   'O4-KEY-C'                 exact part id
               'O1-KEY-'                  any string that is not an exact id = id prefix ('O4-KEY-C*' forces a prefix)
               ['BAT-LFP', 'C-PWR-']      array of the above
               function (rec) { ... }     predicate over part records (see parts())
         label text for the chip ("모두 보기" clears); opts {view: 'front'|'back'|'left'|'right'|'top'|'bottom'|'front34'|'back34',
               keepView: true (no camera move), inside: true|false (sets 내부 보기)}
         Opens #cad when the tab is hidden, waits for the model, shows those parts (even if a toggle hid them), ghosts every
         other part at 15 % opacity and frames the camera on their box.
     clear()        drop the focus (same as 모두 보기)
     ready()        Promise resolved when the model is on screen (does not open the tab by itself)
     parts()        Promise<array of {id, name, kind, group, bbox:[x0,y0,z0,x1,y1,z1], file, folder, qty, material, bom:[[itemId, code, title]], note}>
     press(id)      press the key of that part id (key, lever, capstan ... of one note), e.g. press('O4-KEY-C')
     sets           [{title, ids}] = the 부분별로 보기 list (filled when ready)
     _q             optional: a script that runs before this one may push [sel, label, opts] arrays into
                    window.toccata.cad._q; they are replayed through focus() once the model is ready.
   window.toccata.three  shared Promise that loads three.js r128 once (other tabs may reuse it). */
(function () {
  'use strict';
  var sec = document.getElementById('p-cad');
  if (!sec) return;
  var NS = window.toccata = window.toccata || {};
  var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  var PARTS_URL = 'cad/parts.json', GLB_URL = 'cad/toccata.glb.b64.txt';
  var FOV = 30, TAN = Math.tan(FOV / 2 * Math.PI / 180);
  var mqReduce = window.matchMedia ? matchMedia('(prefers-reduced-motion: reduce)') : null;
  function reduced() { return !!(mqReduce && mqReduce.matches); }
  var KIND = { print: '출력', bought: '구매', electronics: '전자', consumable: '소모품', plywood: '합판' };

  var stage = sec.querySelector('.cadstage');
  var canvas = stage.querySelector('canvas');
  var svg = stage.querySelector('.cadover');
  var loadBox = stage.querySelector('.cadload'), loadTxt = loadBox.querySelector('.cadload-t'),
      loadBar = loadBox.querySelector('.cadprog i'), retryBtn = loadBox.querySelector('.cadretry');
  var hintEl = stage.querySelector('.cadhint'), viewLbl = stage.querySelector('.cadviewlbl');
  var chip = stage.querySelector('.cadfocus'), chipT = chip.querySelector('.cadfocus-t');
  var infoBox = sec.querySelector('.cadinfo');

  // ---------------------------------------------------------------- readiness + public API
  var D = null, loaded = false, loading = false, waiters = [], glbBytes = null;
  function waitReady() {
    if (loaded) return Promise.resolve();
    return new Promise(function (res, rej) { waiters.push([res, rej]); });
  }
  function settle(err) {
    var w = waiters; waiters = [];
    w.forEach(function (p) { if (err) p[1](err); else p[0](); });
  }
  function openTab() {
    if (!sec.hidden) return Promise.resolve();
    return new Promise(function (res) {
      var done = false;
      function fin() { if (done) return; done = true; window.removeEventListener('hashchange', fin); setTimeout(res, 30); }
      window.addEventListener('hashchange', fin);
      setTimeout(fin, 400);
      location.hash = '#cad';
    });
  }
  var api = NS.cad = NS.cad || {};
  var queued = api._q || [];
  api.focus = function (sel, label, opts) {
    return openTab().then(function () { start(); return waitReady(); }).then(function () {
      var n = focusIdx(resolveSel(sel), label, opts || {});
      try { stage.scrollIntoView({ block: 'center', behavior: reduced() ? 'auto' : 'smooth' }); } catch (e) { /* old browsers */ }
      return n;
    });
  };
  api.clear = function () { if (loaded) clearFocus(); };
  api.ready = function () { return waitReady(); };
  api.parts = function () { return waitReady().then(function () { return D.parts.map(function (p, i) { return rec(i); }); }); };
  api.press = function (id) { return waitReady().then(function () { var i = idIndex[id]; if (i != null && keyOf[i] != null) pressKey(keyOf[i]); }); };
  api.sets = [];
  delete api._q;

  NS.three = NS.three || null;
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

  var started = false;
  function start() { if (started) return; started = true; boot(); }
  new MutationObserver(function () { if (!sec.hidden) { start(); invalidate(); } else stopLoop(); })
    .observe(sec, { attributes: true, attributeFilter: ['hidden'] });
  if (!sec.hidden) start();
  retryBtn.addEventListener('click', function () { retryBtn.hidden = true; boot(); });

  function setLoad(t, frac) {
    loadBox.hidden = false; loadTxt.textContent = t;
    if (frac != null) loadBar.style.width = Math.round(Math.max(0, Math.min(1, frac)) * 100) + '%';
  }
  function fail(e) {
    loading = false;
    setLoad('3D 모델을 불러오지 못했습니다 (' + (e && e.message || e) + ').', null);
    retryBtn.hidden = false;
    settle(e || new Error('load failed'));
  }
  function getJSON(u) {
    return fetch(u).then(function (r) { if (!r.ok) throw new Error(u + ' ' + r.status); return r.json(); });
  }
  function getB64(u, expect) {
    return fetch(u).then(function (r) {
      if (!r.ok) throw new Error(u + ' ' + r.status);
      var total = +(r.headers.get('content-length') || 0) || expect || 0;
      if (!r.body || !r.body.getReader) return r.text();
      var rd = r.body.getReader(), chunks = [], got = 0;
      function pump() {
        return rd.read().then(function (x) {
          if (x.done) return;
          chunks.push(x.value); got += x.value.length;
          if (total) setLoad('3D 모델을 받는 중… ' + (got / 1e6).toFixed(1) + ' / ' + (total / 1e6).toFixed(1) + ' MB', 0.05 + 0.85 * got / total);
          return pump();
        });
      }
      return pump().then(function () {
        var all = new Uint8Array(got), o = 0;
        chunks.forEach(function (c) { all.set(c, o); o += c.length; });
        return new TextDecoder('ascii').decode(all);
      });
    }).then(function (t) {
      var bin = atob(t.replace(/\s+/g, '')), n = bin.length, buf = new Uint8Array(n);
      for (var i = 0; i < n; i++) buf[i] = bin.charCodeAt(i);
      return buf;
    });
  }
  function boot() {
    if (loading || loaded) return;
    loading = true;
    setLoad('3D 모델을 준비하는 중…', 0.02);
    Promise.all([ensureThree(), D ? Promise.resolve(D) : getJSON(PARTS_URL)])
      .then(function (r) { D = r[1]; return glbBytes || getB64(GLB_URL, D.glb && D.glb.b64); })
      .then(function (bytes) {
        glbBytes = bytes;
        setLoad('3D 모델을 조립하는 중…', 0.95);
        return new Promise(function (res) { requestAnimationFrame(function () { setTimeout(res, 0); }); });
      })
      .then(init)
      .catch(fail);
  }

  // ---------------------------------------------------------------- data helpers
  var idIndex = {}, keyOf = {}, recCache = [];
  function txt(i) { return i == null ? '' : D.txt[i] || ''; }
  function rec(i) {
    if (recCache[i]) return recCache[i];
    var p = D.parts[i];
    var r = { id: p.id, name: p.n, kind: p.k, group: D.groups[p.g].n, bbox: p.b.slice(), file: p.f || '', folder: p.fd || '', qty: p.q || 0,
              material: p.m || '', bom: (p.r || []).map(function (k) { return D.bom[k].slice(); }), note: txt(p.nt) };
    recCache[i] = r;
    return r;
  }
  function resolveSel(sel) {
    var out = [], seen = {};
    function add(i) { if (!seen[i]) { seen[i] = 1; out.push(i); } }
    if (typeof sel === 'function') {
      D.parts.forEach(function (p, i) { var ok = false; try { ok = !!sel(rec(i)); } catch (e) { ok = false; } if (ok) add(i); });
      return out;
    }
    [].concat(sel == null ? [] : sel).forEach(function (s) {
      if (typeof s !== 'string' || !s) return;
      var pre = null;
      if (s.charAt(s.length - 1) === '*') pre = s.slice(0, -1);
      else if (idIndex[s] != null) { add(idIndex[s]); return; }
      else pre = s;
      D.parts.forEach(function (p, i) { if (p.id.indexOf(pre) === 0) add(i); });
    });
    return out;
  }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function f2(v) { return String(Math.round(v * 100) / 100); }
  function cssVar(n, fb) { var v = getComputedStyle(sec).getPropertyValue(n).trim(); return v || fb; }

  // ---------------------------------------------------------------- scene state
  var T, renderer, scene, root, pcam, ocam, camera, headlight, plane, edgeMat;
  var meshes = [], base = [], geoms = [], geomOf = [], edgesBuilt = false, edgesQueue = null;
  var mats = {};
  var S = {
    ortho: false, inside: false, edges: true, dims: false, press: true,
    ex: 0, exT: 0, fold: 0, foldT: 0,
    sec: { ax: null, v: 0, flip: false },
    focus: null, sel: -1, view: 'front34'
  };
  var kindOn = { print: true, bought: true, electronics: true, consumable: true, plywood: true };
  var groupOn = [], hidden = {};
  var useOf = {}, altOf = {}, hideOf = {}, optOf = {};
  var presses = [];        // {k: key index, t0}
  var cam = { tx: 611, ty: 60, tz: -170, az: 0, el: 0.4, dist: 2000 };
  var tween = null;
  var fitted = null;       // last framing set by a fit {bx, az, el, k}; refitted when the stage changes size, dropped when the user orbits / pans / zooms
  var raf = 0, lastT = 0, poseDirty = true;

  function init() {
    T = window.THREE;
    try {
      renderer = new T.WebGLRenderer({ canvas: canvas, antialias: true, powerPreference: 'high-performance' });
    } catch (e) { fail(new Error('이 브라우저에서 WebGL을 쓸 수 없습니다')); return; }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.localClippingEnabled = true;
    scene = new T.Scene();
    root = new T.Group();
    root.rotation.x = -Math.PI / 2;
    scene.add(root);
    pcam = new T.PerspectiveCamera(FOV, 1, 1, 20000);
    ocam = new T.OrthographicCamera(-1, 1, 1, -1, 1, 20000);
    camera = pcam;
    scene.add(new T.HemisphereLight(0xffffff, 0x8d939e, 0.62));
    headlight = new T.DirectionalLight(0xffffff, 0.5);
    scene.add(headlight); scene.add(headlight.target);
    var sun = new T.DirectionalLight(0xffffff, 0.32);
    sun.position.set(-500, 1400, 700); scene.add(sun);
    plane = new T.Plane(new T.Vector3(-1, 0, 0), 1e7);
    edgeMat = new T.LineBasicMaterial({ color: 0x1d2433, transparent: true, opacity: 0.42, clippingPlanes: [plane] });
    setTheme();

    D.parts.forEach(function (p, i) { idIndex[p.id] = i; groupOn[p.g] = true; });
    D.groups.forEach(function (g, gi) { groupOn[gi] = g.s !== 'floor'; });
    D.keys.forEach(function (k, ki) { k.k.concat(k.l).forEach(function (i) { keyOf[i] = ki; }); });
    var FD = D.fold;
    FD.use.forEach(function (i) { useOf[i] = 1; });
    FD.alt.forEach(function (i) { altOf[i] = 1; });
    FD.hide.forEach(function (i) { hideOf[i] = 1; });
    FD.opt.forEach(function (i) { optOf[i] = 1; });
    api.sets = D.sets.filter(function (s) { return s.ix; }).map(function (s) { return { title: s.t, ids: s.ix.map(function (i) { return D.parts[i].id; }) }; });

    try { buildMeshes(parseGLB(glbBytes)); } catch (e) { fail(e); return; }
    loaded = true; loading = false;
    wireUi();
    applySection();
    refresh();
    setView('front34', { anim: false });
    loadBox.hidden = true;
    renderAll();
    if (S.edges) buildEdges();
    settle(null);
    queued.forEach(function (q) { try { api.focus.apply(api, q); } catch (e) { /* ignore */ } });
    queued = [];
  }

  // ---------------------------------------------------------------- GLB (written by gen_viewer.write_glb)
  function parseGLB(u8) {
    var dv = new DataView(u8.buffer, u8.byteOffset, u8.byteLength);
    if (dv.getUint32(0, true) !== 0x46546C67) throw new Error('GLB 파일이 아닙니다');
    var jl = dv.getUint32(12, true);
    var json = JSON.parse(new TextDecoder('utf-8').decode(u8.subarray(20, 20 + jl)));
    var bl = dv.getUint32(20 + jl, true);
    return { json: json, bin: u8.subarray(28 + jl, 28 + jl + bl) };
  }
  function buildMeshes(g) {
    var J = g.json, bin = g.bin, geoByAcc = {};
    function view(acc) { return J.bufferViews[acc.bufferView]; }
    function positions(ai, qs) {
      var a = J.accessors[ai], v = view(a), n = a.count, out = new Float32Array(n * 3);
      var off = bin.byteOffset + (v.byteOffset || 0) + (a.byteOffset || 0);
      if (a.componentType === 5123) {
        var st = (v.byteStride || 6) / 2, u = new Uint16Array(bin.buffer, off, st * (n - 1) + 3);
        for (var i = 0; i < n; i++) { out[3 * i] = u[i * st] * qs[0]; out[3 * i + 1] = u[i * st + 1] * qs[1]; out[3 * i + 2] = u[i * st + 2] * qs[2]; }
      } else if (a.componentType === 5126) {
        var sf = (v.byteStride || 12) / 4, fl = new Float32Array(bin.buffer, off, sf * (n - 1) + 3);
        for (var k = 0; k < n; k++) { out[3 * k] = fl[k * sf] * qs[0]; out[3 * k + 1] = fl[k * sf + 1] * qs[1]; out[3 * k + 2] = fl[k * sf + 2] * qs[2]; }
      } else throw new Error('POSITION 형식 ' + a.componentType);
      return out;
    }
    function indices(ai) {
      var a = J.accessors[ai], v = view(a), off = bin.byteOffset + (v.byteOffset || 0) + (a.byteOffset || 0);
      if (a.componentType === 5123) return new Uint16Array(bin.buffer.slice(off, off + a.count * 2));
      if (a.componentType === 5125) return new Uint32Array(bin.buffer.slice(off, off + a.count * 4));
      throw new Error('index 형식 ' + a.componentType);
    }
    J.nodes.forEach(function (nd) {
      if (nd.mesh == null) return;
      var i = idIndex[nd.name];
      if (i == null) return;
      var m = J.meshes[nd.mesh], pr = m.primitives[0], ai = pr.attributes.POSITION;
      var qs = (m.extras && m.extras.qscale) || nd.scale || [1, 1, 1];
      var gi = geoByAcc[ai];
      if (gi == null) {
        var geo = new T.BufferGeometry();
        geo.setAttribute('position', new T.BufferAttribute(positions(ai, qs), 3));
        geo.setIndex(new T.BufferAttribute(indices(pr.indices), 1));
        geo.computeBoundingSphere(); geo.computeBoundingBox();
        gi = geoByAcc[ai] = geoms.length;
        geoms.push({ g: geo, users: [] });
      }
      geoms[gi].users.push(i);
      geomOf[i] = gi;
      var mesh = new T.Mesh(geoms[gi].g, mat(D.parts[i].c, 'n'));
      mesh.matrixAutoUpdate = false;
      mesh.userData.i = i;
      var t = nd.translation || [0, 0, 0];
      base[i] = [t[0], t[1], t[2]];
      meshes[i] = mesh;
      root.add(mesh);
    });
    var miss = D.parts.filter(function (p, i) { return !meshes[i]; }).length;
    if (miss) throw new Error('GLB에 없는 부품 ' + miss + '개');
  }
  function capTint(sh) {
    sh.fragmentShader = sh.fragmentShader.replace('#include <dithering_fragment>',
      '#include <dithering_fragment>\n\tif (!gl_FrontFacing) gl_FragColor.rgb = mix(gl_FragColor.rgb, vec3(0.80, 0.28, 0.24), 0.75);');
  }
  function mat(col, mode) {
    var k = col + mode;
    if (mats[k]) return mats[k];
    var m = new T.MeshPhongMaterial({ color: new T.Color(col), flatShading: true, shininess: 16, specular: 0x151515, side: T.DoubleSide,
                                      clippingPlanes: [plane], polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
    if (mode === 'g') { m.transparent = true; m.opacity = 0.15; m.depthWrite = false; }
    else m.onBeforeCompile = capTint;
    if (mode === 's') { m.emissive = new T.Color(0x1f5fbf); m.emissiveIntensity = 0.5; }
    mats[k] = m;
    return m;
  }
  function setTheme() {
    if (!scene) return;
    scene.background = new T.Color(cssVar('--card', '#ffffff'));
    invalidate();
  }

  // ---------------------------------------------------------------- edges (built in slices after the model shows)
  function buildEdges() {
    if (edgesBuilt || edgesQueue) return;
    edgesQueue = geoms.map(function (g, gi) { return gi; });
    var idle = window.requestIdleCallback || function (cb) { return setTimeout(function () { cb({ timeRemaining: function () { return 8; } }); }, 16); };
    function step(dl) {
      var t0 = performance.now();
      while (edgesQueue.length && (performance.now() - t0 < 12 || (dl && dl.timeRemaining() > 2))) {
        var gi = edgesQueue.shift(), gg = geoms[gi];
        var eg = new T.EdgesGeometry(gg.g, 28);
        gg.users.forEach(function (i) {
          var ls = new T.LineSegments(eg, edgeMat);
          ls.matrixAutoUpdate = false; ls.raycast = function () {};
          meshes[i].add(ls); meshes[i].userData.e = ls;
        });
      }
      if (edgesQueue.length) idle(step);
      else { edgesQueue = null; edgesBuilt = true; refresh(); }
    }
    idle(step);
  }

  // ---------------------------------------------------------------- visibility + materials
  function shown(i) {
    var p = D.parts[i];
    var inFocus = S.focus && S.focus[i];
    if (p.a) return S.fold >= 1 && !optOf[i] && !(S.inside && p.in && !inFocus);
    if (useOf[i] && S.fold >= 1) return false;
    if (hideOf[i] && S.fold > 0) return false;
    if (inFocus) return true;
    if (!kindOn[p.k] || !groupOn[p.g] || hidden[i]) return false;
    if (S.inside && p.in) return false;
    return true;
  }
  function refresh() {
    if (!loaded) return;
    for (var i = 0; i < meshes.length; i++) {
      var m = meshes[i], vis = shown(i);
      m.visible = vis;
      if (!vis) continue;
      var mode = i === S.sel ? 's' : (S.focus && !S.focus[i] ? 'g' : 'n');
      m.material = mat(D.parts[i].c, mode);
      if (m.userData.e) m.userData.e.visible = S.edges && mode !== 'g';
    }
    invalidate();
  }

  // ---------------------------------------------------------------- pose: explode, key press, fold (rotations about x)
  function rotX(deg, py, pz) {
    var a = deg * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    return { c: c, s: s, ty: py - c * py + s * pz, tz: pz - s * py - c * pz };
  }
  function comp(A, B) {          // A after B
    return { c: A.c * B.c - A.s * B.s, s: A.s * B.c + A.c * B.s, ty: A.c * B.ty - A.s * B.tz + A.ty, tz: A.s * B.ty + A.c * B.tz + A.tz };
  }
  function smooth(a, b, x) { var t = Math.max(0, Math.min(1, (x - a) / (b - a))); return t * t * (3 - 2 * t); }
  var rotOf = [];
  function poseAll() {
    var n = meshes.length, i, s = S.ex;
    for (i = 0; i < n; i++) rotOf[i] = null;
    var P = D.press;
    presses.forEach(function (pr) {
      if (pr.a <= 0) return;
      var kd = D.keys[pr.k], col = kd.b ? 'b' : 'w';
      var ka = rotX(P.key[col] * pr.a, P.kaxis[0], P.kaxis[1]), la = rotX(-P.lever[col] * pr.a, P.laxis[0], P.laxis[1]);
      kd.k.forEach(function (j) { rotOf[j] = ka; });
      kd.l.forEach(function (j) { rotOf[j] = la; });
    });
    if (S.fold > 0) {
      var FD = D.fold, g1 = smooth(0, 0.4, S.fold), g2 = smooth(0.35, 1, S.fold);
      var cr = rotX(FD.ang * g2, FD.axis[0], FD.axis[1]);
      FD.move.forEach(function (j) { rotOf[j] = cr; });
      rotOf[FD.leg.i] = comp(cr, rotX(FD.leg.ang * g1, FD.leg.pivot[0], FD.leg.pivot[1]));
    }
    for (i = 0; i < n; i++) {
      var b = base[i], e = D.parts[i].e, A = rotOf[i];
      var ex = e ? e[0] * s : 0, ey = e ? e[1] * s : 0, ez = e ? e[2] * s : 0;
      var c = A ? A.c : 1, sn = A ? A.s : 0, ty = A ? A.ty : 0, tz = A ? A.tz : 0;
      meshes[i].matrix.set(1, 0, 0, b[0] + ex,
                           0, c, -sn, c * b[1] - sn * b[2] + ty + ey,
                           0, sn, c, sn * b[1] + c * b[2] + tz + ez,
                           0, 0, 0, 1);
    }
    poseDirty = false;
  }

  // ---------------------------------------------------------------- camera
  function dirOf(az, el) { return new T.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az)); }
  function upOf(az, el) {
    if (Math.abs(Math.cos(el)) > 1e-4) return new T.Vector3(0, 1, 0);
    var s = el > 0 ? -1 : 1;
    return new T.Vector3(s * Math.sin(az), 0, s * Math.cos(az));
  }
  function size() { return [Math.max(1, stage.clientWidth), Math.max(1, stage.clientHeight)]; }
  function applyCam() {
    var wh = size(), asp = wh[0] / wh[1];
    var pr = renderer.getPixelRatio();
    if (canvas.width !== Math.floor(wh[0] * pr) || canvas.height !== Math.floor(wh[1] * pr)) renderer.setSize(wh[0], wh[1], false);
    var tgt = new T.Vector3(cam.tx, cam.ty, cam.tz), d = dirOf(cam.az, cam.el), hh = cam.dist * TAN;
    if (S.ortho) {
      var back = Math.max(cam.dist, 3500);
      ocam.left = -hh * asp; ocam.right = hh * asp; ocam.top = hh; ocam.bottom = -hh;
      ocam.near = 1; ocam.far = back + 4000;
      ocam.position.copy(tgt).addScaledVector(d, back);
      camera = ocam;
    } else {
      pcam.aspect = asp; pcam.near = Math.max(0.5, cam.dist / 300); pcam.far = cam.dist * 6 + 5000;
      pcam.position.copy(tgt).addScaledVector(d, cam.dist);
      camera = pcam;
    }
    camera.up.copy(upOf(cam.az, cam.el));
    camera.lookAt(tgt);
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
    headlight.position.copy(camera.position);
    headlight.target.position.copy(tgt);
    headlight.target.updateMatrixWorld();
  }
  function basis(az, el) {
    var d = dirOf(az, el), up = upOf(az, el), f = d.clone().negate();
    var r = new T.Vector3().crossVectors(f, up).normalize(), u = new T.Vector3().crossVectors(r, f).normalize();
    return { r: r, u: u, d: d };
  }
  function m2t(x, y, z) { return new T.Vector3(x, z, -y); }
  function boxOf(list) {       // model bbox (with explode offsets) of part indices -> three Box3
    var bx = new T.Box3(), any = false;
    list.forEach(function (i) {
      var p = D.parts[i], b = p.b, e = p.e, s = S.ex;
      var ox = e ? e[0] * s : 0, oy = e ? e[1] * s : 0, oz = e ? e[2] * s : 0;
      bx.expandByPoint(m2t(b[0] + ox, b[1] + oy, b[2] + oz));
      bx.expandByPoint(m2t(b[3] + ox, b[4] + oy, b[5] + oz));
      any = true;
    });
    return any ? bx : null;
  }
  function fit(bx, az, el, k) {
    var B = basis(az, el), c = bx.getCenter(new T.Vector3());
    var wh = size(), asp = wh[0] / wh[1], hw = 0, hh = 0, hd = 0;
    for (var n = 0; n < 8; n++) {
      var p = new T.Vector3(n & 1 ? bx.max.x : bx.min.x, n & 2 ? bx.max.y : bx.min.y, n & 4 ? bx.max.z : bx.min.z).sub(c);
      hw = Math.max(hw, Math.abs(p.dot(B.r))); hh = Math.max(hh, Math.abs(p.dot(B.u))); hd = Math.max(hd, Math.abs(p.dot(B.d)));
    }
    var need = Math.max(hh, hw / asp, 4) * (k || 1.12);
    var dist = need / TAN + (S.ortho ? 0 : hd);
    return { tx: c.x, ty: c.y, tz: c.z, az: az, el: el, dist: Math.max(20, Math.min(9000, dist)) };
  }
  function shownList() {
    var out = [];
    for (var i = 0; i < meshes.length; i++) if (meshes[i].visible && !(S.focus && !S.focus[i])) out.push(i);
    return out;
  }
  function goCam(goal, anim) {
    if (!anim || reduced()) { tween = null; Object.assign(cam, goal); invalidate(); return; }
    var from = Object.assign({}, cam), daz = goal.az - from.az;
    daz = Math.atan2(Math.sin(daz), Math.cos(daz));
    tween = { from: from, to: Object.assign({}, goal, { az: from.az + daz }), t0: performance.now(), dur: 650 };
    invalidate();
  }
  function fitCam(bx, az, el, k, anim) {   // frame bx and remember it, so a resize keeps the same framing
    fitted = { bx: bx.clone(), az: az, el: el, k: k };
    goCam(fit(bx, az, el, k), anim);
  }
  function userCam() { fitted = null; }    // the user moved the camera: a resize must not undo it
  function refit() {
    if (!fitted || !loaded || stage.clientWidth < 2 || stage.clientHeight < 2) return;   // hidden tab: wait for the real size
    var g = fit(fitted.bx, fitted.az, fitted.el, fitted.k), dst = tween ? tween.to : cam;
    dst.tx = g.tx; dst.ty = g.ty; dst.tz = g.tz; dst.dist = g.dist;   // az / el stay (a running tween keeps its shortest-turn az)
    invalidate();
  }
  function azElOf(d) {         // model direction (target -> eye) -> az / el
    var v = m2t(d[0], d[1], d[2]).normalize();
    var az = (Math.abs(v.x) < 1e-9 && Math.abs(v.z) < 1e-9) ? 0 : Math.atan2(v.x, v.z);   // straight up / down: front edge at the bottom (atan2(0, -0) would give pi)
    return [az, Math.asin(Math.max(-1, Math.min(1, v.y)))];
  }
  function setView(name, o) {
    o = o || {};
    var v = D.views[name];
    if (!v) return;
    var ae = azElOf(v.d);
    if (o.ortho != null) S.ortho = o.ortho; else S.ortho = !!v.o;
    S.view = name;
    var bx = o.box || boxOf(o.list || shownList()) || boxOf(D.parts.map(function (p, i) { return i; }));
    fitCam(bx, ae[0], ae[1], o.k, o.anim !== false);
    syncViewUi();
  }
  function syncViewUi() {
    sec.querySelectorAll('[data-cad-view]').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-cad-view') === S.view ? 'true' : 'false'); });
    sec.querySelectorAll('[data-cad-proj]').forEach(function (b) { b.setAttribute('aria-pressed', (b.getAttribute('data-cad-proj') === 'ortho') === S.ortho ? 'true' : 'false'); });
    var v = D.views[S.view];
    viewLbl.textContent = (v ? v.t : '자유 시점') + ' · ' + (S.ortho ? '정투영' : '원근');
  }
  function freeView() { if (S.view) { S.view = null; syncViewUi(); } }

  // ---------------------------------------------------------------- render loop
  function invalidate() { if (!raf && loaded) raf = requestAnimationFrame(tick); }
  function stopLoop() { if (raf) { cancelAnimationFrame(raf); raf = 0; } }
  function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  var PRESS = { down: 240, hold: 320, up: 420 };
  var scaleRun = null;
  function tick(now) {
    raf = 0;
    if (sec.hidden) return;
    var dt = lastT ? Math.min(80, now - lastT) : 16; lastT = now;
    var more = false;
    if (tween) {
      var t = Math.min(1, (now - tween.t0) / tween.dur), k = ease(t);
      ['tx', 'ty', 'tz', 'az', 'el'].forEach(function (q) { cam[q] = tween.from[q] + (tween.to[q] - tween.from[q]) * k; });
      cam.dist = tween.from.dist * Math.pow(tween.to.dist / tween.from.dist, k);
      if (t >= 1) tween = null; else more = true;
    }
    if (S.ex !== S.exT) {
      if (reduced()) S.ex = S.exT;
      else { S.ex += (S.exT - S.ex) * (1 - Math.exp(-dt / 110)); if (Math.abs(S.exT - S.ex) < 0.002) S.ex = S.exT; }
      poseDirty = true; more = more || S.ex !== S.exT;
    }
    if (S.fold !== S.foldT) {
      var wasFull = S.fold >= 1, wasZero = S.fold <= 0;
      if (reduced()) S.fold = S.foldT;
      else { var st = dt / 1700; S.fold = S.foldT > S.fold ? Math.min(S.foldT, S.fold + st) : Math.max(S.foldT, S.fold - st); }
      poseDirty = true;
      if ((S.fold >= 1) !== wasFull || (S.fold <= 0) !== wasZero) refresh();
      more = more || S.fold !== S.foldT;
    }
    if (scaleRun) {
      while (scaleRun.next < scaleRun.list.length && now >= scaleRun.t0 + scaleRun.next * 170) { pressKey(scaleRun.list[scaleRun.next], now); scaleRun.next++; }
      if (scaleRun.next >= scaleRun.list.length) scaleRun = null; else more = true;
    }
    if (presses.length) {
      presses = presses.filter(function (pr) {
        var u = now - pr.t0, r = reduced();
        if (u < PRESS.down) pr.a = r ? 1 : ease(u / PRESS.down);
        else if (u < PRESS.down + PRESS.hold + (r ? 400 : 0)) pr.a = 1;
        else if (u < PRESS.down + PRESS.hold + PRESS.up + (r ? 400 : 0)) pr.a = r ? 0 : 1 - ease((u - PRESS.down - PRESS.hold) / PRESS.up);
        else { pr.a = 0; return false; }
        return true;
      });
      poseDirty = true; more = true;
    }
    renderAll();
    if (more) raf = requestAnimationFrame(tick); else lastT = 0;
  }
  function renderAll() {
    if (!loaded) return;
    if (poseDirty) poseAll();
    applyCam();
    renderer.render(scene, camera);
    drawOverlay();
  }

  // ---------------------------------------------------------------- overlay: dimensions, scale bar, axis triad
  function proj(p) {
    var v = m2t(p[0], p[1], p[2]).project(camera), wh = size();
    return [(v.x + 1) / 2 * wh[0], (1 - v.y) / 2 * wh[1], v.z];
  }
  function niceLen(px, mmpp) {
    var want = px * mmpp, p = Math.pow(10, Math.floor(Math.log(want) / Math.LN10)), best = p;
    [1, 2, 5, 10].forEach(function (m) { if (m * p <= want) best = m * p; });
    return best;
  }
  function drawOverlay() {
    var wh = size(), out = '';
    if (S.dims && S.ex < 0.005) {
      out += '<g class="cdim">';
      D.dims.forEach(function (d) {
        if (d.ts && S.fold > 0) return;
        var a = proj(d.a), b = proj(d.b);
        if (a[2] > 1 || b[2] > 1 || a[2] < -1 || b[2] < -1) return;
        if (Math.hypot(b[0] - a[0], b[1] - a[1]) < 26) return;
        if (d.ea) {
          var e0 = proj(d.ea), e1 = proj(d.eb);
          out += '<line class="ext" x1="' + e0[0] + '" y1="' + e0[1] + '" x2="' + a[0] + '" y2="' + a[1] + '"/><line class="ext" x1="' + e1[0] + '" y1="' + e1[1] + '" x2="' + b[0] + '" y2="' + b[1] + '"/>';
        }
        out += '<line x1="' + a[0] + '" y1="' + a[1] + '" x2="' + b[0] + '" y2="' + b[1] + '"/>';
        var ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        [[a, ang + Math.PI], [b, ang]].forEach(function (q) {
          var p = q[0], t = q[1], s = 7;
          out += '<line x1="' + p[0] + '" y1="' + p[1] + '" x2="' + (p[0] - s * Math.cos(t - 0.4)) + '" y2="' + (p[1] - s * Math.sin(t - 0.4)) + '"/>' +
                 '<line x1="' + p[0] + '" y1="' + p[1] + '" x2="' + (p[0] - s * Math.cos(t + 0.4)) + '" y2="' + (p[1] - s * Math.sin(t + 0.4)) + '"/>';
        });
        out += '<text x="' + (a[0] + b[0]) / 2 + '" y="' + ((a[1] + b[1]) / 2 - 6) + '" text-anchor="middle">' + esc(d.t) + '</text>';
      });
      out += '</g>';
    }
    if (S.ortho) {
      var mmpp = 2 * cam.dist * TAN / wh[1], L = niceLen(Math.min(150, wh[0] * 0.3), mmpp), px = L / mmpp;
      var x1 = wh[0] - 16, x0 = x1 - px, y = wh[1] - 16;
      out += '<g class="cbar"><line x1="' + x0 + '" y1="' + y + '" x2="' + x1 + '" y2="' + y + '"/><line x1="' + x0 + '" y1="' + (y - 5) + '" x2="' + x0 + '" y2="' + (y + 1) + '"/>' +
             '<line x1="' + x1 + '" y1="' + (y - 5) + '" x2="' + x1 + '" y2="' + (y + 1) + '"/><text x="' + (x0 + x1) / 2 + '" y="' + (y - 8) + '" text-anchor="middle">' + L + ' mm</text></g>';
    }
    var ib = camera.matrixWorldInverse, cx = wh[0] - 40, cy = S.ortho ? wh[1] - 66 : wh[1] - 40;
    out += '<g class="cax">';
    [['x', [1, 0, 0]], ['y', [0, 0, -1]], ['z', [0, 1, 0]]].forEach(function (ax) {
      var v = new T.Vector3(ax[1][0], ax[1][1], ax[1][2]).transformDirection(ib);
      var ex = cx + v.x * 22, ey = cy - v.y * 22;
      out += '<g class="ax-' + ax[0] + '"><line x1="' + cx + '" y1="' + cy + '" x2="' + ex + '" y2="' + ey + '"/><text x="' + (cx + v.x * 31) + '" y="' + (cy - v.y * 31 + 4) + '" text-anchor="middle">' + ax[0] + '</text></g>';
    });
    out += '</g>';
    svg.innerHTML = out;
  }

  // ---------------------------------------------------------------- section plane
  var secIn = sec.querySelector('#cad-sec'), secOut = sec.querySelector('#cad-sec-out'), secFlip = sec.querySelector('#cad-sec-flip'),
      secLook = sec.querySelector('#cad-sec-look');
  var SEC_LBL = { x: ['오른쪽', '왼쪽'], y: ['앞쪽', '뒤쪽'], z: ['위쪽', '아래쪽'] };
  function secRange(ax) {
    var b = D.box, k = { x: 0, y: 1, z: 2 }[ax];
    return [Math.floor(b[k] - 2), Math.ceil(b[k + 3] + 2)];
  }
  function applySection() {
    var s = S.sec;
    if (!s.ax) { plane.normal.set(-1, 0, 0); plane.constant = 1e7; }
    else if (s.ax === 'x') { plane.normal.set(-1, 0, 0); plane.constant = s.v; }
    else if (s.ax === 'y') { plane.normal.set(0, 0, -1); plane.constant = -s.v; }
    else { plane.normal.set(0, -1, 0); plane.constant = s.v; }
    if (s.ax && s.flip) { plane.normal.negate(); plane.constant = -plane.constant; }
    sec.querySelectorAll('[data-cad-sec]').forEach(function (b) { b.setAttribute('aria-pressed', (b.getAttribute('data-cad-sec') === (s.ax || 'off')) ? 'true' : 'false'); });
    secIn.disabled = !s.ax; secLook.disabled = !s.ax;
    if (s.ax) {
      var r = secRange(s.ax);
      secIn.min = r[0]; secIn.max = r[1]; secIn.value = s.v;
      secOut.textContent = s.ax + ' ' + f2(s.v) + ' (' + SEC_LBL[s.ax][s.flip ? 1 : 0] + ' 뗌)';
    } else secOut.textContent = '끔';
    secFlip.checked = !!s.flip;
    invalidate();
  }
  function setSection(ax, v, flip) {
    S.sec.ax = ax || null;
    if (ax) {
      var r = secRange(ax);
      if (v == null) v = S.sec.lastAx === ax ? S.sec.v : (r[0] + r[1]) / 2;
      S.sec.v = Math.max(r[0], Math.min(r[1], v));
      S.sec.lastAx = ax;
    }
    if (flip != null) S.sec.flip = !!flip;
    applySection();
  }
  function lookAtCut() {
    var s = S.sec; if (!s.ax) return;
    var name = { x: ['right', 'left'], y: ['front', 'back'], z: ['top', 'bottom'] }[s.ax][s.flip ? 1 : 0];
    setView(name, { ortho: true });
  }

  // ---------------------------------------------------------------- focus
  function focusIdx(list, label, opts) {
    opts = opts || {};
    sec.querySelectorAll('.cadset').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
    if (!list.length) {
      S.focus = null; refresh();
      chip.hidden = false; chipT.textContent = '찾는 부품이 없습니다' + (label ? ': ' + label : '');
      return 0;
    }
    var F = {};
    list.forEach(function (i) { F[i] = 1; });
    S.focus = F;
    if (opts.inside != null) setInside(!!opts.inside);
    var hasAlt = list.some(function (i) { return D.parts[i].a; }), hasUse = list.some(function (i) { return useOf[i]; });
    if (hasAlt && !hasUse) setFold(true);
    if (S.sel >= 0 && !F[S.sel]) select(-1);
    refresh();
    chip.hidden = false;
    chipT.textContent = (label || '선택한 부품') + ' · ' + list.length + '개';
    if (!opts.keepView) {
      var vis = list.filter(function (i) { return shown(i); });
      var bx = boxOf(vis.length ? vis : list);
      if (opts.view && D.views[opts.view]) setView(opts.view, { box: bx, k: 1.25 });
      else { fitCam(bx, cam.az, cam.el, 1.25, true); }
    }
    return list.length;
  }
  function clearFocus() {
    S.focus = null; chip.hidden = true;
    sec.querySelectorAll('.cadset').forEach(function (b) { b.setAttribute('aria-pressed', 'false'); });
    refresh();
  }

  // ---------------------------------------------------------------- selection + info panel
  function select(i) {
    S.sel = i;
    refresh();
    if (i < 0) { infoBox.innerHTML = '<p class="cadempty">부품을 누르면 이름·크기·재료·출력 파일이 여기에 나옵니다.</p>'; return; }
    var p = D.parts[i], b = p.b, h = '';
    h += '<div><span class="cadkd cadkd-' + p.k + '">' + esc(KIND[p.k] || p.k) + '</span><span class="cadkd">' + esc(D.groups[p.g].n) + '</span></div>';
    h += '<h4>' + esc(p.n) + '</h4><dl>';
    h += '<dt>크기</dt><dd class="mono">' + f2(b[3] - b[0]) + ' × ' + f2(b[4] - b[1]) + ' × ' + f2(b[5] - b[2]) + ' mm</dd>';
    h += '<dt>위치</dt><dd class="mono">x ' + f2(b[0]) + '~' + f2(b[3]) + '<br>y ' + f2(b[1]) + '~' + f2(b[4]) + '<br>z ' + f2(b[2]) + '~' + f2(b[5]) + '</dd>';
    if (p.m) h += '<dt>재료</dt><dd>' + esc(p.m) + '</dd>';
    if (p.f) {
      h += '<dt>출력 파일</dt><dd class="mono">' + esc((p.fd ? p.fd.replace(/^@extra\//, 'print_extra/') + '/' : '') + p.f) + '</dd>';
      h += '<dt>출력 개수</dt><dd>이 파일로 ' + p.q + '개' + (p.pm ? ' · 1개 ' + p.pm + ' g (속을 채운 PETG 기준)' : '') + '</dd>';
    }
    if (p.r && p.r.length) h += '<dt>구매 목록</dt><dd>' + p.r.map(function (k) { var r = D.bom[k]; return '<span class="mono">' + esc(r[0]) + (r[1] && /^[A-Z]{1,4}\d/.test(r[1]) ? ' · ' + esc(r[1]) : '') + '</span> ' + esc(r[2]); }).join('<br>') + '</dd>';
    if (keyOf[i] != null) { var kd = D.keys[keyOf[i]], col = kd.b ? 'b' : 'w'; h += '<dt>누름</dt><dd>' + esc(kd.n) + ' · 건반 ' + D.press.key[col] + '°, 레버 ' + D.press.lever[col] + '°</dd>'; }
    h += '<dt>id</dt><dd class="mono">' + esc(p.id) + '</dd>';
    [['출력 방법', txt(p.pn)], ['메모', txt(p.nt)], ['치수 출처', txt(p.s)]].forEach(function (q) {
      if (!q[1]) return;
      if (q[1].length <= 160) h += '<dt>' + q[0] + '</dt><dd>' + esc(q[1]) + '</dd>';
      else h += '<details><summary>' + q[0] + ' (' + q[1].length + '자)</summary><p>' + esc(q[1]) + '</p></details>';
    });
    h += '</dl>';
    if (p.d && p.d.length) h += '<ul class="caddl">' + p.d.map(function (d) { return '<li><b>' + esc(d[1]) + '</b> ' + esc(d[0]) + '</li>'; }).join('') + '</ul>';
    h += '<div class="cadacts"><button type="button" data-cad-act="zoom">가까이</button><button type="button" data-cad-act="iso">이것만 보기</button>';
    if (p.f && p.q > 1) h += '<button type="button" data-cad-act="same">같은 파일 ' + p.q + '개</button>';
    if (keyOf[i] != null) h += '<button type="button" data-cad-act="press">눌러 보기</button>';
    h += '<button type="button" data-cad-act="group">이 그룹만</button><button type="button" data-cad-act="hide">숨기기</button></div>';
    infoBox.innerHTML = h;
  }
  infoBox.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-cad-act]');
    if (!b || S.sel < 0) return;
    var i = S.sel, p = D.parts[i], a = b.getAttribute('data-cad-act');
    if (a === 'zoom') fitCam(boxOf([i]), cam.az, cam.el, 1.8, true);
    else if (a === 'iso') focusIdx([i], p.n);
    else if (a === 'same') focusIdx(D.parts.map(function (q, j) { return j; }).filter(function (j) { return D.parts[j].f === p.f && D.parts[j].fd === p.fd; }), p.f);
    else if (a === 'press') pressKey(keyOf[i]);
    else if (a === 'group') focusIdx(D.parts.map(function (q, j) { return j; }).filter(function (j) { return D.parts[j].g === p.g; }), D.groups[p.g].n);
    else if (a === 'hide') { hidden[i] = true; select(-1); }
  });

  // ---------------------------------------------------------------- picking + key press
  var ray = null;
  function pick(cx, cy) {
    if (!ray) ray = new T.Raycaster();
    var r = canvas.getBoundingClientRect();
    ray.setFromCamera(new T.Vector2((cx - r.left) / r.width * 2 - 1, -(cy - r.top) / r.height * 2 + 1), camera);
    scene.updateMatrixWorld();
    var solid = [], ghost = [];
    meshes.forEach(function (m, i) { if (m.visible) ((S.focus && !S.focus[i]) ? ghost : solid).push(m); });
    function first(list) {
      var hits = ray.intersectObjects(list, false);
      for (var k = 0; k < hits.length; k++) if (!S.sec.ax || plane.distanceToPoint(hits[k].point) >= 0) return hits[k].object.userData.i;
      return -1;
    }
    var i = first(solid);
    return i >= 0 ? i : first(ghost);
  }
  function pressKey(ki, now) {
    if (ki == null) return;
    presses = presses.filter(function (p) { return p.k !== ki; });
    presses.push({ k: ki, t0: now || performance.now(), a: 0 });
    invalidate();
  }

  // ---------------------------------------------------------------- toggles
  function setInside(on) { S.inside = on; var b = sec.querySelector('#cad-inside'); b.setAttribute('aria-pressed', on ? 'true' : 'false'); refresh(); }
  function setFold(on) {
    S.foldT = on ? 1 : 0;
    var b = sec.querySelector('#cad-fold');
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.textContent = on ? '화면 펴기' : '화면 접기';
    if (S.fold > 0 && S.fold < 1) refresh();
    if (!on && S.fold >= 1) { S.fold = 0.9999; refresh(); }
    invalidate();
  }

  // ---------------------------------------------------------------- UI wiring (after load)
  function wireUi() {
    sec.querySelectorAll('[data-cad-view]').forEach(function (b) {
      b.addEventListener('click', function () { setView(b.getAttribute('data-cad-view')); });
    });
    sec.querySelectorAll('[data-cad-proj]').forEach(function (b) {
      b.addEventListener('click', function () {
        var o = b.getAttribute('data-cad-proj') === 'ortho';
        if (o === S.ortho) return;
        S.ortho = o; syncViewUi(); invalidate();
      });
    });
    sec.querySelector('#cad-inside').addEventListener('click', function () { setInside(!S.inside); });
    sec.querySelector('#cad-fold').addEventListener('click', function () { setFold(S.foldT < 1); });
    var pb = sec.querySelector('#cad-press');
    pb.addEventListener('click', function () { S.press = !S.press; pb.setAttribute('aria-pressed', S.press ? 'true' : 'false'); });
    sec.querySelector('#cad-scale').addEventListener('click', function () {
      var list = [];
      D.keys.forEach(function (k, ki) { var id = D.parts[k.k[0]].id; if (/^O4-KEY-/.test(id)) list.push(ki); });
      D.keys.forEach(function (k, ki) { if (D.parts[k.k[0]].id === 'O5-KEY-C') list.push(ki); });
      scaleRun = { list: list, next: 0, t0: performance.now() };
      invalidate();
    });
    var eb = sec.querySelector('#cad-edges');
    eb.addEventListener('click', function () { S.edges = !S.edges; eb.setAttribute('aria-pressed', S.edges ? 'true' : 'false'); if (S.edges) buildEdges(); refresh(); });
    var db = sec.querySelector('#cad-dims');
    db.addEventListener('click', function () { S.dims = !S.dims; db.setAttribute('aria-pressed', S.dims ? 'true' : 'false'); invalidate(); });
    var ex = sec.querySelector('#cad-explode'), exo = sec.querySelector('#cad-explode-out');
    ex.addEventListener('input', function () { S.exT = (+ex.value) / 100; exo.textContent = ex.value + ' %'; invalidate(); });
    sec.querySelectorAll('[data-cad-sec]').forEach(function (b) {
      b.addEventListener('click', function () { var a = b.getAttribute('data-cad-sec'); setSection(a === 'off' ? null : a); });
    });
    secIn.addEventListener('input', function () { if (S.sec.ax) { S.sec.v = +secIn.value; applySection(); } });
    secFlip.addEventListener('change', function () { S.sec.flip = secFlip.checked; applySection(); });
    secLook.addEventListener('click', lookAtCut);
    sec.querySelectorAll('[data-cad-set]').forEach(function (b) {
      b.addEventListener('click', function () {
        var s = D.sets[+b.getAttribute('data-cad-set')];
        if (!s) return;
        if (s.sec) {
          clearFocus();
          setSection(s.sec.ax, s.sec.v, !!s.sec.flip);
          var bx = new T.Box3(m2t(s.box[0], s.box[1], s.box[2]), m2t(s.box[0], s.box[1], s.box[2]));
          bx.expandByPoint(m2t(s.box[3], s.box[4], s.box[5]));
          setView(s.v || 'right', { ortho: true, box: bx, k: 1.06 });
        } else {
          focusIdx(s.ix, s.t, { view: s.v });
        }
        b.setAttribute('aria-pressed', 'true');
        if (window.innerWidth <= 980) { try { stage.scrollIntoView({ block: 'nearest', behavior: reduced() ? 'auto' : 'smooth' }); } catch (e) { /* */ } }
      });
    });
    sec.querySelectorAll('[data-cad-kind]').forEach(function (b) {
      b.addEventListener('click', function () { var k = b.getAttribute('data-cad-kind'); kindOn[k] = !kindOn[k]; b.setAttribute('aria-pressed', kindOn[k] ? 'true' : 'false'); refresh(); });
    });
    var layerOn = {};
    sec.querySelectorAll('[data-cad-layer]').forEach(function (b) {
      var ly = b.getAttribute('data-cad-layer'); layerOn[ly] = true;
      b.addEventListener('click', function () {
        layerOn[ly] = !layerOn[ly];
        b.setAttribute('aria-pressed', layerOn[ly] ? 'true' : 'false');
        D.groups.forEach(function (g, gi) {
          if (g.n.slice(-ly.length - 1) === ' ' + ly && (g.s === 'mod' || g.s === 'end' || g.s === 'elec')) {
            groupOn[gi] = layerOn[ly];
            var c = sec.querySelector('[data-cad-g="' + gi + '"]'); if (c) c.checked = layerOn[ly];
          }
        });
        refresh();
      });
    });
    var gl = sec.querySelector('.cadglist');
    gl.addEventListener('change', function (e) { var g = e.target.getAttribute('data-cad-g'); if (g == null) return; groupOn[+g] = e.target.checked; refresh(); });
    function setAll(on) {
      sec.querySelectorAll('[data-cad-g]').forEach(function (c) { var gi = +c.getAttribute('data-cad-g'); if (D.groups[gi].s === 'floor') return; groupOn[gi] = on; c.checked = on; });
      refresh();
    }
    sec.querySelector('[data-cad-gall]').addEventListener('click', function () { setAll(true); });
    sec.querySelector('[data-cad-gnone]').addEventListener('click', function () { setAll(false); });
    sec.querySelector('[data-cad-gshow]').addEventListener('click', function () { hidden = {}; refresh(); });
    chip.querySelector('.cadfocus-x').addEventListener('click', clearFocus);

    // pointer: rotate / pan / pinch / tap
    var ptrs = {}, np = 0, drag = null;
    function hideHint() { hintEl.classList.add('is-off'); }
    canvas.addEventListener('contextmenu', function (e) { e.preventDefault(); });
    canvas.addEventListener('pointerdown', function (e) {
      try { canvas.setPointerCapture(e.pointerId); } catch (x) { /* */ }
      ptrs[e.pointerId] = { x: e.clientX, y: e.clientY }; np = Object.keys(ptrs).length;
      if (tween) { tween = null; userCam(); }   // stopping a camera move halfway leaves a framing the user chose
      hideHint();
      if (np === 1) drag = { mode: (e.button === 1 || e.button === 2 || e.shiftKey || e.ctrlKey || e.metaKey) ? 'pan' : 'rot', x: e.clientX, y: e.clientY, x0: e.clientX, y0: e.clientY, t0: performance.now(), moved: false, btn: e.button };
      else if (np === 2) { var pp = pts(); drag = { mode: 'pinch', d: dist2(pp), m: mid(pp), moved: true }; }
    });
    function pts() { return Object.keys(ptrs).map(function (k) { return ptrs[k]; }); }
    function dist2(p) { return Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y) || 1; }
    function mid(p) { return { x: (p[0].x + p[1].x) / 2, y: (p[0].y + p[1].y) / 2 }; }
    canvas.addEventListener('pointermove', function (e) {
      if (!ptrs[e.pointerId] || !drag) return;
      ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
      var wh = size();
      if (drag.mode === 'pinch' && np >= 2) {
        var pp = pts(), d = dist2(pp), m = mid(pp);
        zoomAt(m.x, m.y, drag.d / d);
        pan(m.x - drag.m.x, m.y - drag.m.y);
        drag.d = d; drag.m = m; freeView(); return;
      }
      var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      drag.x = e.clientX; drag.y = e.clientY;
      if (!drag.moved && Math.hypot(e.clientX - drag.x0, e.clientY - drag.y0) > 5) drag.moved = true;
      if (!drag.moved) return;
      if (drag.mode === 'rot') {
        cam.az -= dx * 2 * Math.PI / Math.max(600, wh[0]);
        cam.el = Math.max(-Math.PI / 2, Math.min(Math.PI / 2, cam.el + dy * Math.PI / Math.max(400, wh[1])));
        if (S.view) freeView();
        userCam(); invalidate();
      } else pan(dx, dy);
    });
    function endPtr(e) {
      if (!ptrs[e.pointerId]) return;
      delete ptrs[e.pointerId]; np = Object.keys(ptrs).length;
      if (drag && drag.mode !== 'pinch' && np === 0 && !drag.moved && performance.now() - drag.t0 < 650 && drag.btn === 0 && e.type === 'pointerup') onTap(e.clientX, e.clientY);
      if (np === 1) { var p = pts()[0]; drag = { mode: 'rot', x: p.x, y: p.y, x0: p.x, y0: p.y, t0: 0, moved: true, btn: -1 }; }
      else if (np === 0) drag = null;
    }
    canvas.addEventListener('pointerup', endPtr);
    canvas.addEventListener('pointercancel', endPtr);
    canvas.addEventListener('wheel', function (e) {
      e.preventDefault(); tween = null; hideHint();
      var k = Math.exp(e.deltaY * (e.deltaMode === 1 ? 0.05 : 0.0015));
      zoomAt(e.clientX, e.clientY, k);
    }, { passive: false });
    canvas.addEventListener('dblclick', function (e) { var i = pick(e.clientX, e.clientY); if (i >= 0) fitCam(boxOf([i]), cam.az, cam.el, 1.8, true); });
    canvas.addEventListener('keydown', function (e) {
      var k = e.key, st = 0.08;
      if (k === 'ArrowLeft' || k === 'ArrowRight' || k === 'ArrowUp' || k === 'ArrowDown') {
        e.preventDefault(); tween = null;
        if (e.shiftKey) pan(k === 'ArrowLeft' ? 30 : k === 'ArrowRight' ? -30 : 0, k === 'ArrowUp' ? 30 : k === 'ArrowDown' ? -30 : 0);
        else {
          if (k === 'ArrowLeft') cam.az += st; if (k === 'ArrowRight') cam.az -= st;
          if (k === 'ArrowUp') cam.el = Math.min(Math.PI / 2, cam.el + st); if (k === 'ArrowDown') cam.el = Math.max(-Math.PI / 2, cam.el - st);
          freeView(); userCam(); invalidate();
        }
      } else if (k === '+' || k === '=') { e.preventDefault(); zoomCenter(1 / 1.2); }
      else if (k === '-' || k === '_') { e.preventDefault(); zoomCenter(1.2); }
      else if (k === 'Escape') { if (S.sel >= 0) select(-1); else if (S.focus) clearFocus(); }
    });
    // the stage can change size after the first fit (pane widened, phone rotated, side panel): keep the fitted framing
    function onResize() { refit(); invalidate(); }
    if (window.ResizeObserver) new ResizeObserver(onResize).observe(stage);
    else window.addEventListener('resize', onResize);
    requestAnimationFrame(function () { requestAnimationFrame(onResize); });   // after the first frame, once layout has settled
    var mqDark = window.matchMedia ? matchMedia('(prefers-color-scheme: dark)') : null;
    if (mqDark && mqDark.addEventListener) mqDark.addEventListener('change', setTheme);
    new MutationObserver(setTheme).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'class'] });
    canvas.addEventListener('webglcontextlost', function (e) { e.preventDefault(); setLoad('그래픽 메모리가 부족해 3D 화면이 멈췄습니다. 새로고침해 주세요.', null); });
  }
  function onTap(x, y) {
    var i = pick(x, y);
    select(i);
    if (i >= 0 && S.press && keyOf[i] != null) pressKey(keyOf[i]);
  }
  function pan(dx, dy) {
    var wh = size(), wpp = 2 * cam.dist * TAN / wh[1], B = basis(cam.az, cam.el);
    cam.tx += (-B.r.x * dx + B.u.x * dy) * wpp; cam.ty += (-B.r.y * dx + B.u.y * dy) * wpp; cam.tz += (-B.r.z * dx + B.u.z * dy) * wpp;
    userCam(); invalidate();
  }
  function zoomAt(cx, cy, k) {
    var r = canvas.getBoundingClientRect(), wh = size();
    var nx = (cx - r.left) / r.width * 2 - 1, ny = -(cy - r.top) / r.height * 2 + 1;
    var hh = cam.dist * TAN, hw = hh * wh[0] / wh[1], B = basis(cam.az, cam.el);
    var P = new T.Vector3(cam.tx, cam.ty, cam.tz).addScaledVector(B.r, nx * hw).addScaledVector(B.u, ny * hh);
    var nd = Math.max(15, Math.min(9000, cam.dist * k)), kk = nd / cam.dist;
    cam.tx = P.x + (cam.tx - P.x) * kk; cam.ty = P.y + (cam.ty - P.y) * kk; cam.tz = P.z + (cam.tz - P.z) * kk;
    cam.dist = nd;
    userCam(); invalidate();
  }
  function zoomCenter(k) { var r = canvas.getBoundingClientRect(); zoomAt(r.left + r.width / 2, r.top + r.height / 2, k); }

  // ---------------------------------------------------------------- save the GLB (zip, through the viewer's downloads capability)
  var saveBtn = sec.querySelector('#cad-save'), saveMsg = sec.querySelector('#cad-save-msg');
  var crcT = null;
  function crc32(u) {
    if (!crcT) { crcT = new Uint32Array(256); for (var n = 0; n < 256; n++) { var c = n; for (var k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; crcT[n] = c >>> 0; } }
    var x = 0xFFFFFFFF;
    for (var i = 0; i < u.length; i++) x = crcT[(x ^ u[i]) & 255] ^ (x >>> 8);
    return (x ^ 0xFFFFFFFF) >>> 0;
  }
  function zipStore(files) {
    var parts = [], cd = [], off = 0, enc = new TextEncoder(), now = new Date();
    var dt = ((now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1)) & 0xFFFF;
    var dd = (((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate()) & 0xFFFF;
    files.forEach(function (fl) {
      var name = enc.encode(fl.name), data = fl.data, crc = crc32(data);
      var h = new DataView(new ArrayBuffer(30));
      h.setUint32(0, 0x04034b50, true); h.setUint16(4, 20, true); h.setUint16(6, 0x0800, true); h.setUint16(8, 0, true);
      h.setUint16(10, dt, true); h.setUint16(12, dd, true); h.setUint32(14, crc, true); h.setUint32(18, data.length, true);
      h.setUint32(22, data.length, true); h.setUint16(26, name.length, true); h.setUint16(28, 0, true);
      var c = new DataView(new ArrayBuffer(46));
      c.setUint32(0, 0x02014b50, true); c.setUint16(4, 20, true); c.setUint16(6, 20, true); c.setUint16(8, 0x0800, true); c.setUint16(10, 0, true);
      c.setUint16(12, dt, true); c.setUint16(14, dd, true); c.setUint32(16, crc, true); c.setUint32(20, data.length, true); c.setUint32(24, data.length, true);
      c.setUint16(28, name.length, true); c.setUint32(42, off, true);
      parts.push(h.buffer, name, data); cd.push(c.buffer, name);
      off += 30 + name.length + data.length;
    });
    var cdSize = cd.reduce(function (s, b) { return s + (b.byteLength || b.length); }, 0);
    var end = new DataView(new ArrayBuffer(22));
    end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
    end.setUint32(12, cdSize, true); end.setUint32(16, off, true);
    return new Blob(parts.concat(cd, [end.buffer]), { type: 'application/zip' });
  }
  saveBtn.addEventListener('click', function () {
    var use = window.claude && window.claude.use;
    if (typeof use !== 'function') {
      saveMsg.textContent = '이 화면에서는 저장 기능을 쓸 수 없습니다. 저장소의 hardware/mechanical/cad/viewer/toccata_viewer.glb를 쓰세요.';
      return;
    }
    saveBtn.disabled = true; saveMsg.textContent = '파일을 만드는 중…';
    var dl;
    Promise.resolve().then(function () { return use.call(window.claude, 'downloads'); }).then(function (x) {
      dl = x;
      if (!dl) throw { code: 'unavailable' };
      if (glbBytes) return glbBytes;
      return (D ? Promise.resolve(D) : getJSON(PARTS_URL)).then(function (d) { D = d; return getB64(GLB_URL, d.glb && d.glb.b64); })
        .then(function (b) { glbBytes = b; return b; });
    }).then(function (bytes) {
      var readme = 'Toccata 전체 조립 3D (hardware/mechanical/cad/viewer/toccata_viewer.glb)\n' +
        '- glTF 2.0 바이너리, 부품마다 노드 1개 (노드 이름 = 부품 id, manifest.json과 같음)\n' +
        '- 위치는 KHR_mesh_quantization (uint16) - 대부분의 GLB 뷰어가 엽니다\n' +
        '- 최상위 노드가 mm를 m로, z 위를 y 위로 바꿉니다 (실제 크기 1.254 m)\n' +
        '- 출력은 이 파일이 아니라 hardware/mechanical/cad/stl/print/ 의 STL로 합니다\n';
      var blob = zipStore([{ name: 'Toccata_assembly.glb', data: bytes }, { name: 'README.txt', data: new TextEncoder().encode(readme) }]);
      return dl.save({ filename: 'Toccata_assembly.zip', data: blob }).then(function () { saveMsg.textContent = 'Toccata_assembly.zip을 저장했습니다 (' + (blob.size / 1e6).toFixed(1) + ' MB).'; });
    }).catch(function (err) {
      var code = err && (err.code || err.name) || '';
      if (code === 'declined' || code === 'cancelled' || code === 'canceled' || code === 'AbortError') saveMsg.textContent = '저장을 취소했습니다.';
      else if (code === 'unavailable') saveMsg.textContent = '이 화면에서는 저장 기능을 쓸 수 없습니다. 저장소의 hardware/mechanical/cad/viewer/toccata_viewer.glb를 쓰세요.';
      else saveMsg.textContent = '저장하지 못했습니다 (' + (code || (err && err.message) || '알 수 없는 오류') + ').';
    }).then(function () { saveBtn.disabled = false; });
  });
})();
