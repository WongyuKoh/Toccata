/* Toccata page, tab "11 한 옥타브 조립" (#p-asm): step checkboxes (this browser only) and a full-size viewer for
 * drawings and renders. Same behaviour as the standalone guide; the step ticks share its localStorage key name but
 * live in this page's own origin. */
(function () {
  var root = document.getElementById("p-asm");
  if (!root) return;
  var KEY = "toccata-octave-steps";
  var done = {};
  try { done = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { done = {}; }
  var steps = [].slice.call(root.querySelectorAll("article[data-step]"));
  function $(id) { return document.getElementById(id); }
  function paint() {
    var n = 0;
    steps.forEach(function (s) {
      var on = !!done[s.id];
      s.classList.toggle("a-done", on);
      var cb = s.querySelector("input[type=checkbox]");
      if (cb) cb.checked = on;
      var a = root.querySelector('nav a[data-s="' + s.id + '"]');
      if (a) a.classList.toggle("a-done", on);
      if (on) n++;
    });
    $("asm-progTxt").textContent = n + " / " + steps.length + " 단계 끝냄";
    $("asm-progBar").style.width = (100 * n / steps.length) + "%";
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(done)); } catch (e) {} }
  steps.forEach(function (s) {
    var cb = s.querySelector("input[type=checkbox]");
    if (cb) cb.addEventListener("change", function () { done[s.id] = cb.checked; save(); paint(); });
  });
  $("asm-reset").addEventListener("click", function () { done = {}; save(); paint(); });
  paint();

  var lb = $("asm-lb"), img = $("asm-lbImg"), view = $("asm-lbView");
  var zoom = 1, natW = 0;
  function setZoom(z) {
    zoom = Math.max(0.25, Math.min(4, z));
    img.style.width = Math.round(natW * zoom) + "px";
  }
  function fit() {
    natW = img.naturalWidth || 1500;
    setZoom(Math.min(1, (view.clientWidth - 4) / natW));
  }
  function open(src, title) {
    $("asm-lbTitle").textContent = title;
    lb.hidden = false;
    img.style.width = "";
    img.onload = fit;
    img.src = src;
    if (img.complete && img.naturalWidth) fit();
    view.scrollLeft = 0; view.scrollTop = 0;
    $("asm-lbClose").focus();
  }
  function close() { lb.hidden = true; img.removeAttribute("src"); }
  root.querySelectorAll("[data-d]").forEach(function (b) {
    b.addEventListener("click", function () { open(b.getAttribute("data-d"), b.textContent); });
  });
  root.querySelectorAll("figure > img").forEach(function (im) {
    im.addEventListener("click", function () {
      var cap = im.parentNode.querySelector("figcaption");
      open(im.getAttribute("src"), cap ? cap.textContent : "");
    });
  });
  $("asm-zIn").addEventListener("click", function () { setZoom(zoom * 1.4); });
  $("asm-zOut").addEventListener("click", function () { setZoom(zoom / 1.4); });
  $("asm-lbClose").addEventListener("click", close);
  document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !lb.hidden) close(); });
})();

/* Toccata one-octave guide: live 3D step figures.
 *
 * Markup: an element with data-v3d-src="<model json>" (written by src/make_models.py) and, for each figure, a box
 * <div data-v3d="<view name>"><img poster></div>. The poster stays until three.js and the model are loaded (and stays
 * for good if WebGL is missing).
 *
 * One WebGL canvas, fixed over the viewport with pointer-events off, draws every visible box into its own rectangle
 * (scissor), so 13 figures cost one GL context. The boxes sit one layer above the canvas with a transparent background,
 * so the drawing shows through and the buttons stay clickable. Geometry is shared between figures; scenes are built
 * the first time a box comes into view and only redrawn when a box moves or its camera changes.
 *
 * Controls: mouse drag = turn, right drag or Shift+drag = move, Ctrl/⌘+wheel = zoom (plain wheel inside "크게 보기"),
 * click a part = its name, double click = start view. Touch: sideways swipe = turn (vertical swipes keep scrolling the
 * page); inside "크게 보기" one finger turns and two fingers zoom.
 * three.js r128 from cdnjs, shared with the 3D tab of the main page through window.toccata.three. */
(function () {
  'use strict';
  var host = document.querySelector('[data-v3d-src]');
  var boxes = [].slice.call(document.querySelectorAll('[data-v3d]'));
  if (!host || !boxes.length) return;
  var SRC = host.getAttribute('data-v3d-src');
  var NS = window.toccata = window.toccata || {};
  var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  var BG = 0xf6f7f8, FOV = 28;
  var coarse = window.matchMedia && matchMedia('(pointer: coarse)').matches;
  var HINT = coarse ? '옆으로 밀어 돌리기 · 부품을 누르면 이름' : '끌어서 돌리기 · 오른쪽 끌기 이동 · Ctrl+휠 확대 · 부품 클릭 = 이름';
  var HINT_FULL = coarse ? '한 손가락 돌리기 · 두 손가락 확대' : '끌어서 돌리기 · 오른쪽 끌기 이동 · 휠 확대';

  function ensureThree() {
    if (window.THREE && window.THREE.WebGLRenderer) return Promise.resolve();
    if (!NS.three) {
      NS.three = new Promise(function (res, rej) {
        var s = document.createElement('script');
        s.src = THREE_URL; s.async = true;
        s.onload = function () { res(); };
        s.onerror = function () { NS.three = null; rej(new Error('three.js')); };
        document.head.appendChild(s);
      });
    }
    return NS.three;
  }

  // ---- buttons on every box (added at once, so the page looks the same before and after loading)
  var views = boxes.map(function (box) {
    var ui = document.createElement('div');
    ui.className = 'v3d-ui';
    ui.innerHTML = '<span class="v3d-hint" aria-live="polite">3D 모델 불러오는 중…</span>' +
      '<span class="v3d-btns"><button type="button" data-a="home">처음 시점</button>' +
      '<button type="button" data-a="full">크게 보기</button></span>';
    box.appendChild(ui);
    return { box: box, name: box.getAttribute('data-v3d'), ui: ui, hint: ui.querySelector('.v3d-hint'),
             fullBtn: ui.querySelector('[data-a=full]'), scene: null, dirty: true, key: '' };
  });

  var started = false;
  function start() {
    if (started) return;
    started = true;
    Promise.all([ensureThree(), fetch(SRC).then(function (r) {
      if (!r.ok) throw new Error(SRC + ' ' + r.status);
      return r.json();
    })]).then(function (a) { boot(a[1]); }).catch(function () {
      views.forEach(function (v) { v.hint.textContent = '3D 모델을 불러오지 못해 그림으로 보여 줍니다'; v.box.classList.add('v3d-off'); });
    });
  }
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (es) {
      if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); start(); }
    }, { rootMargin: '400px' });
    boxes.forEach(function (b) { io.observe(b); });
  } else start();

  function boot(data) {
    var T = window.THREE;
    var canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:fixed;left:0;top:0;width:100%;height:100%;pointer-events:none;z-index:5';
    var renderer;
    try {
      renderer = new T.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
    } catch (e) {
      views.forEach(function (v) { v.hint.textContent = '이 브라우저는 3D를 그리지 못해 그림으로 보여 줍니다'; v.box.classList.add('v3d-off'); });
      return;
    }
    document.body.appendChild(canvas);
    renderer.autoClear = false;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    var cw = 0, ch = 0;

    // ---- shared geometry (decoded once, built per part on first use)
    var raw = atob(data.bin), buf = new ArrayBuffer(raw.length), u8 = new Uint8Array(buf);
    for (var i = 0; i < raw.length; i++) u8[i] = raw.charCodeAt(i);
    var P = new Int16Array(buf, 0, data.nv * 3), I = new Uint16Array(buf, data.nv * 6, data.ni), q = data.q;
    var geoms = {}, edges = {}, mats = {}, lmats = {};
    function geom(k) {
      if (geoms[k]) return geoms[k];
      var p = data.parts[k], f = new Float32Array(p.vn * 3);
      for (var j = 0; j < f.length; j++) f[j] = P[p.vo * 3 + j] * q;
      var g = new T.BufferGeometry();
      g.setAttribute('position', new T.BufferAttribute(f, 3));
      g.setIndex(new T.BufferAttribute(I.slice(p.io, p.io + p.in), 1));
      g.computeBoundingSphere();
      return (geoms[k] = g);
    }
    function edge(k) { return edges[k] || (edges[k] = new T.EdgesGeometry(geom(k), 30)); }
    function mat(c, a) {
      var key = c + a;
      if (!mats[key]) {
        mats[key] = new T.MeshPhongMaterial({ color: c, flatShading: true, shininess: 14, specular: 0x161616,
          transparent: a < 1, opacity: a, depthWrite: a >= 1, polygonOffset: true, polygonOffsetFactor: 1, polygonOffsetUnits: 1 });
      }
      return mats[key];
    }
    function lmat(c, a) {
      var key = c + a;
      if (!lmats[key]) {
        var col = new T.Color(c).multiplyScalar(0.5);
        lmats[key] = new T.LineBasicMaterial({ color: col, transparent: a < 1, opacity: a < 1 ? 0.28 : 1, depthWrite: a >= 1 });
      }
      return lmats[key];
    }

    function build(v) {
      var spec = data.views[v.name];
      if (!spec) { v.hint.textContent = '이 그림의 3D 자료가 없습니다'; return false; }
      var scene = new T.Scene(), box = new T.Box3(), pick = [];
      scene.add(new T.HemisphereLight(0xffffff, 0x8d939c, 0.62));
      spec.parts.forEach(function (r) {
        var k = r[0], c = r[1], a = r[2];
        var m = new T.Mesh(geom(k), mat(c, a));
        m.position.set(r[3], r[4], r[5]);
        m.userData.name = data.parts[k].name;
        if (a < 1) m.renderOrder = 2; else pick.push(m);
        var l = new T.LineSegments(edge(k), lmat(c, a));
        l.position.copy(m.position);
        if (a < 1) l.renderOrder = 3;
        scene.add(m); scene.add(l);
        m.updateMatrixWorld();
        box.expandByObject(m);
      });
      var cam = new T.PerspectiveCamera(FOV, 4 / 3, 1, 8000);
      cam.up.set(0, 0, 1);
      var light = new T.DirectionalLight(0xffffff, 0.55);
      light.position.set(0.4, 0.6, 1);
      cam.add(light);
      scene.add(cam);
      var sphere = box.getBoundingSphere(new T.Sphere());
      var c6 = spec.cam, dir = new T.Vector3(c6[0] - c6[3], c6[1] - c6[4], c6[2] - c6[5]).normalize();
      v.home = { target: sphere.center.clone(), dir: dir, radius: sphere.radius };
      v.scene = scene; v.cam = cam; v.pick = pick;
      home(v);
      v.hint.textContent = HINT;
      return true;
    }
    function home(v) {
      var h = v.home;
      v.target = h.target.clone();
      v.r = h.radius / Math.sin(FOV / 2 * Math.PI / 180) * 0.86;   // the bounding sphere is loose; 0.86 fills the box
      v.theta = Math.atan2(h.dir.y, h.dir.x);
      v.phi = Math.acos(Math.max(-1, Math.min(1, h.dir.z)));
      v.dirty = true;
    }
    function place(v, aspect) {
      var c = v.cam, fit = aspect < 1 ? 1 / aspect : 1;     // keep the model inside a tall (phone) box too
      c.aspect = aspect; c.updateProjectionMatrix();
      var s = Math.sin(v.phi), r = v.r * fit;
      c.position.set(v.target.x + r * s * Math.cos(v.theta), v.target.y + r * s * Math.sin(v.theta), v.target.z + r * Math.cos(v.phi));
      c.lookAt(v.target);
    }

    // ---- drawing loop: redraw only when a visible box moved, appeared, or its camera changed
    var shownKey = '';
    function frame() {
      requestAnimationFrame(frame);
      var W = window.innerWidth, H = window.innerHeight;
      if (W !== cw || H !== ch) { cw = W; ch = H; renderer.setSize(W, H, false); shownKey = '#'; }
      var list = [], any = false, keyAll = '';
      var full = views.filter(function (v) { return v.box.classList.contains('v3d-full'); });
      (full.length ? full : views).forEach(function (v) {
        if (v.box.classList.contains('v3d-off')) return;
        var r = v.box.getBoundingClientRect();
        if (r.width < 4 || r.height < 4 || r.bottom < 0 || r.top > H || r.right < 0 || r.left > W) return;
        var key = Math.round(r.left) + ',' + Math.round(r.top) + ',' + Math.round(r.width) + ',' + Math.round(r.height);
        if (key !== v.key || v.dirty) any = true;
        v.key = key; v.rect = r; keyAll += v.name + ';';
        list.push(v);
      });
      if (!any && keyAll === shownKey) return;
      shownKey = keyAll;
      renderer.setScissorTest(false);
      renderer.setClearColor(0x000000, 0);
      renderer.clear();
      renderer.setScissorTest(true);
      list.forEach(function (v) {
        if (!v.scene && !build(v)) return;
        var r = v.rect, x = r.left + 1, y = H - r.bottom + 1, w = r.width - 2, h = r.height - 2;
        renderer.setViewport(x, y, w, h);
        renderer.setScissor(x, y, w, h);
        renderer.setClearColor(BG, 1);
        renderer.clear();
        place(v, w / h);
        renderer.render(v.scene, v.cam);
        v.dirty = false;
        v.box.classList.add('v3d-live');
      });
    }
    requestAnimationFrame(frame);

    // ---- controls
    var ray = new T.Raycaster(), ndc = new T.Vector2();
    views.forEach(function (v) {
      var box = v.box, ptrs = {}, mode = null, last = null, down = null, pinch = 0;
      box.addEventListener('contextmenu', function (e) { e.preventDefault(); });
      box.addEventListener('pointerdown', function (e) {
        if (!v.scene || e.target.closest('button')) return;
        ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
        var n = Object.keys(ptrs).length;
        if (n === 2) { mode = 'pinch'; pinch = dist(); return; }
        mode = (e.button === 2 || e.shiftKey) ? 'pan' : 'turn';
        last = down = { x: e.clientX, y: e.clientY };
        try { box.setPointerCapture(e.pointerId); } catch (err) {}
      });
      box.addEventListener('pointermove', function (e) {
        if (!ptrs[e.pointerId] || !mode) return;
        ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
        if (mode === 'pinch') {
          var d = dist();
          if (pinch > 0 && d > 0) { v.r = clampR(v, v.r * pinch / d); v.dirty = true; }
          pinch = d;
          return;
        }
        var dx = e.clientX - last.x, dy = e.clientY - last.y;
        last = { x: e.clientX, y: e.clientY };
        var full = box.classList.contains('v3d-full');
        if (mode === 'turn') {
          v.theta -= dx * 0.008;
          if (e.pointerType !== 'touch' || full) v.phi = Math.max(0.05, Math.min(Math.PI - 0.05, v.phi - dy * 0.008));
        } else {
          var c = v.cam, k = v.r * 0.0016;
          var right = new T.Vector3().setFromMatrixColumn(c.matrix, 0), up = new T.Vector3().setFromMatrixColumn(c.matrix, 1);
          v.target.addScaledVector(right, -dx * k).addScaledVector(up, dy * k);
        }
        v.dirty = true;
      });
      function end(e) {
        var p = ptrs[e.pointerId];
        delete ptrs[e.pointerId];
        if (e.type === 'pointerup' && mode === 'turn' && down && p && Math.abs(p.x - down.x) + Math.abs(p.y - down.y) < 5) pickAt(e);
        if (!Object.keys(ptrs).length) mode = null;
        else if (mode === 'pinch') { mode = 'turn'; var k0 = ptrs[Object.keys(ptrs)[0]]; last = down = { x: k0.x, y: k0.y }; }
      }
      box.addEventListener('pointerup', end);
      box.addEventListener('pointercancel', end);
      box.addEventListener('dblclick', function (e) { if (v.scene && !e.target.closest('button')) home(v); });
      box.addEventListener('wheel', function (e) {
        if (!v.scene) return;
        if (!(box.classList.contains('v3d-full') || e.ctrlKey || e.metaKey)) return;
        e.preventDefault();
        v.r = clampR(v, v.r * Math.exp(e.deltaY * 0.0015));
        v.dirty = true;
      }, { passive: false });
      v.ui.querySelector('[data-a=home]').addEventListener('click', function () { if (v.scene) home(v); });
      v.fullBtn.addEventListener('click', function () { setFull(v, !box.classList.contains('v3d-full')); });
      function dist() {
        var k = Object.keys(ptrs);
        if (k.length < 2) return 0;
        var a = ptrs[k[0]], b = ptrs[k[1]];
        return Math.hypot(a.x - b.x, a.y - b.y);
      }
      function pickAt(e) {
        var r = box.getBoundingClientRect();
        ndc.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
        ray.setFromCamera(ndc, v.cam);
        var hit = ray.intersectObjects(v.pick, false)[0];
        v.hint.textContent = hit ? hit.object.userData.name : (box.classList.contains('v3d-full') ? HINT_FULL : HINT);
      }
    });
    function clampR(v, r) { return Math.max(v.home.radius * 0.25, Math.min(v.home.radius * 12, r)); }
    function setFull(v, on) {
      views.forEach(function (o) { if (o !== v && o.box.classList.contains('v3d-full')) setFull(o, false); });
      v.box.classList.toggle('v3d-full', on);
      v.fullBtn.textContent = on ? '닫기' : '크게 보기';
      v.hint.textContent = on ? HINT_FULL : HINT;
      canvas.style.zIndex = on ? '60' : '5';
      v.dirty = true;
      if (on) v.fullBtn.focus();
    }
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      views.forEach(function (v) { if (v.box.classList.contains('v3d-full')) setFull(v, false); });
    });
  }
})();
