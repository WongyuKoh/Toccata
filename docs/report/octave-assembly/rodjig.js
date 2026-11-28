/* Toccata one-octave guide, step 02: rod cut jig simulation.
 *
 * Markup: <div class="rj" data-rj-src="model/rodjig.json"> with a canvas box (.rj-stage), length buttons
 * (button[data-len]), phase chips (button[data-ph]), play/pause (button[data-a="play"]) and a caption (.rj-cap).
 * Meshes come from src/make_rodjig.py (= hardware/mechanical/cad/src/rod_cut_jig.py, the printed STLs), in jig
 * coordinates: x along the rod (0 = plug stub tip = rod stop, saw slot near face at x = L), y across, z up.
 * The rod, the cut piece, the saw blade and the file are drawn here (simple shapes) and moved on one timeline.
 * three.js r128 from cdnjs, shared with viewer3d.js through window.toccata.three. */
(function () {
  'use strict';
  var host = document.querySelector('[data-rj-src]');
  if (!host) return;
  var stage = host.querySelector('.rj-stage');
  var cap = host.querySelector('.rj-cap');
  var hint = host.querySelector('.rj-hint');
  var playBtn = host.querySelector('[data-a="play"]');
  var NS = window.toccata = window.toccata || {};
  var THREE_URL = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

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

  // phases: [start s, end s, caption]
  var PH = [
    [0.0, 2.0, '① 끝 마개를 "마개" 쪽 끝 구멍에 꽂습니다. 플랜지가 판 끝면에 빈틈 없이 닿을 때까지 — 덜 들어가면 토막이 그만큼 짧아집니다.'],
    [2.0, 5.5, '② 봉 끝을 줄로 직각으로 다듬고, 반대쪽 모따기 입구로 밀어 넣습니다. 위쪽 창으로 봉 끝이 마개 꼭지에 닿은 것을 봅니다.'],
    [5.5, 10.0, '③ 봉을 마개 쪽으로 누른 채, 쇠톱을 "톱" 홈(폭 1.3)에 넣고 자릅니다. 날은 홈 바깥(버리는 쪽)으로 지나갑니다.'],
    [10.0, 11.6, '④ 남은 긴 봉을 입구 쪽으로 빼냅니다.'],
    [11.6, 13.0, '⑤ 날개를 잡고 끝 마개를 뺍니다.'],
    [13.0, 15.0, '⑥ 토막을 마개 쪽 구멍으로 밀어 꺼냅니다. 끝을 줄로 0.1~0.3 다듬으면 허용 범위 안입니다.'],
    [15.0, 17.5, '⑦ 다음 토막 전에 남은 봉의 잘린 끝을 다시 직각으로 다듬습니다 — 그 끝이 다음 토막의 0점입니다.']
  ];
  var T_END = 18.5;

  var data, THREE, renderer, scene, camera, jigMesh, plug, rodA, rodB, piece, saw, file, winMark;
  var J, L = 161.4, lenKey = '161.4', jigs = {}, geoms = {};
  var t = 0, playing = !reduce, last = 0, az = -0.85, el = 0.62, dist = 300, target;
  var started = false;
  var qt = /[?&]rjt=([\d.]+)/.exec(location.search), ql = /[?&]rjl=([\d.]+)/.exec(location.search);   // still frames for checks
  if (qt) { t = +qt[1]; playing = false; }
  if (ql) lenKey = ql[1];

  function decode(d) {
    var bin = atob(d.blob), buf = new ArrayBuffer(bin.length), u8 = new Uint8Array(buf);
    for (var i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
    Object.keys(d.meshes).forEach(function (k) {
      var m = d.meshes[k];
      var q = new Int16Array(buf, m.v[0], m.v[1] * 3), pos = new Float32Array(q.length);
      for (var j = 0; j < q.length; j++) pos[j] = q[j] * d.q;
      var idx = new Uint16Array(buf, m.i[0], m.i[1]);
      var g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      g.setIndex(new THREE.BufferAttribute(new Uint16Array(idx), 1));
      g.computeVertexNormals();
      geoms[k] = g;
    });
  }

  function rodMesh(len, color) {
    var g = new THREE.CylinderGeometry(2, 2, 1, 28);
    g.rotateZ(-Math.PI / 2);          // axis y -> x
    g.translate(0.5, 0, 0);           // x 0..1
    var m = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ color: color, metalness: 0.75, roughness: 0.32 }));
    m.scale.x = len;
    return m;
  }

  function build() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf6f7f8);
    camera = new THREE.PerspectiveCamera(28, 4 / 3, 1, 5000);
    camera.up.set(0, 0, 1);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a929c, 0.9));
    var dl = new THREE.DirectionalLight(0xffffff, 0.75); dl.position.set(-120, -200, 300); scene.add(dl);
    var dl2 = new THREE.DirectionalLight(0xffffff, 0.3); dl2.position.set(200, 150, 120); scene.add(dl2);
    // desk
    var desk = new THREE.Mesh(new THREE.PlaneGeometry(4000, 3000), new THREE.MeshLambertMaterial({ color: 0xbdb6a8 }));
    desk.position.set(100, 0, -0.05); scene.add(desk);
    jigMesh = new THREE.Mesh(geoms['jig161.4'], new THREE.MeshStandardMaterial({
      color: 0x7d98b3, roughness: 0.7, metalness: 0, transparent: true, opacity: 0.62, depthWrite: false, flatShading: true,
      side: THREE.DoubleSide }));
    jigMesh.renderOrder = 2;
    scene.add(jigMesh);
    plug = new THREE.Mesh(geoms.plug, new THREE.MeshStandardMaterial({ color: 0xe0782f, roughness: 0.6, flatShading: true }));
    scene.add(plug);
    rodA = rodMesh(420, 0xc9ced4); scene.add(rodA);         // the bar (before the cut: whole; after: remainder)
    piece = rodMesh(161.4, 0xd7dce2); scene.add(piece);      // the cut piece
    // hacksaw: blade + frame
    saw = new THREE.Group();
    // only the blade (the hacksaw frame would hide the jig); a short blue grip marks the handle end
    var blade = new THREE.Mesh(new THREE.BoxGeometry(0.65, 80, 10), new THREE.MeshStandardMaterial({ color: 0x5b6470, metalness: 0.6, roughness: 0.4 }));
    blade.position.set(0, 0, 5);
    var grip = new THREE.Mesh(new THREE.BoxGeometry(6, 22, 14), new THREE.MeshStandardMaterial({ color: 0x2e6fd0, roughness: 0.6 }));
    grip.position.set(0, 50, 7);
    saw.add(blade, grip);
    scene.add(saw);
    // flat file
    file = new THREE.Group();
    // lies across the rod end: flat face toward +x (the sawn end), length along y, strokes along y
    var fb = new THREE.Mesh(new THREE.BoxGeometry(3, 60, 12), new THREE.MeshStandardMaterial({ color: 0x6d737b, metalness: 0.5, roughness: 0.7 }));
    var hg = new THREE.CylinderGeometry(4, 4, 36, 16);          // axis y already
    var fh = new THREE.Mesh(hg, new THREE.MeshStandardMaterial({ color: 0xa5652d, roughness: 0.8 }));
    fh.position.set(0, 58, 0);
    file.add(fb, fh);
    scene.add(file);
    // window marker: thin green ring that flashes when the rod reaches the stop
    winMark = new THREE.Mesh(new THREE.TorusGeometry(3.6, 0.45, 8, 32), new THREE.MeshBasicMaterial({ color: 0x2f9d58, transparent: true, opacity: 0 }));
    winMark.rotation.y = Math.PI / 2;
    scene.add(winMark);
  }

  function setLen(key) {
    var j = jigs[key]; if (!j) return;
    lenKey = key; L = j.L;
    jigMesh.geometry = geoms['jig' + key];
    piece.scale.x = L;
    target = new THREE.Vector3(L / 2 + 4, 0, J.ax_z);
    dist = Math.max(130, L * 1.2 + 90);
    host.querySelectorAll('[data-len]').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-len') === key ? 'true' : 'false'); });
    var info = host.querySelector('.rj-info');
    if (info) info.innerHTML = '<b>' + j.key + ' mm</b> · ' + j.who + ' · ' + j.count + ' · 허용 ' + j.range + ' · <code>' + j.file + '</code>';
    draw();
  }

  function ease(a) { a = Math.max(0, Math.min(1, a)); return a * a * (3 - 2 * a); }
  function seg(i) { return ease((t - PH[i][0]) / (PH[i][1] - PH[i][0])); }

  function pose() {
    var s = J.stub, ft = J.flange_t, ax = J.ax_z, kerf = J.kerf;
    // plug: in from -30 (0..2 s), out again 11.6..13
    var pin = seg(0), pout = seg(4);
    plug.position.x = -30 * (1 - pin) - 22 * pout;
    plug.position.y = -26 * ease((t - PH[4][1] + 0.6) / 0.6);
    // rod: comes in from the outfeed side; front end at x = (L + 140)(1 - a)
    var a = seg(1);
    var front = (L + J.out + 120) * (1 - a);
    var cut = t >= PH[2][1];
    var sawA = seg(2);
    if (!cut) {
      rodA.position.x = front; rodA.scale.x = 420; rodA.visible = true; piece.visible = false;
    } else {
      // after the cut: remainder starts at L + kerf, pulled out +x in phase 4; piece 0..L, pushed out -x in phase 6
      var pull = seg(3) * (J.out + 22);
      rodA.position.x = L + kerf + pull; rodA.scale.x = 420 - L - kerf; rodA.visible = true;
      piece.visible = true; piece.position.x = -seg(5) * Math.min(L + 20, 70);
    }
    rodA.position.z = piece.position.z = ax;
    // saw: above the slot, comes down through the rod in phase 3 with strokes along y
    var sx = L + kerf / 2;
    var down = sawA;
    var zTop = ax + 22, zBot = J.slot_floor + 0.2;
    var inPhase = t >= PH[2][0] && t < PH[2][1] + 0.6;
    saw.visible = t >= PH[2][0] - 0.8 && t < PH[3][1];
    var appear = ease((t - (PH[2][0] - 0.8)) / 0.8), leave = ease((t - PH[2][1]) / 0.8);
    saw.position.set(sx, inPhase ? Math.sin(t * 9) * 16 * (down > 0 && down < 1 ? 1 : 0.2) : 0,
      zTop + (zBot - zTop) * down + 60 * (1 - appear) + 60 * leave);
    // file: squares the remainder's sawn end in phase 7
    var fa = seg(6);
    file.visible = t >= PH[6][0] - 0.5 && t < PH[6][1] + 0.6;
    var rEnd = L + kerf + (J.out + 22);
    file.position.set(rEnd - 1.7, Math.sin(t * 8) * 12 * (fa > 0 && fa < 1 ? 1 : 0),
      ax + 50 * (1 - ease((t - PH[6][0] + 0.5) / 0.5)) + 70 * ease((t - PH[6][1]) / 0.6));
    // window flash when the rod touches the stop
    winMark.position.set(0.5, 0, ax);
    winMark.material.opacity = t > PH[1][1] - 0.2 && t < PH[2][0] + 1.6 ? 0.9 : 0;
    // caption
    var ph = 0;
    for (var i = 0; i < PH.length; i++) if (t >= PH[i][0]) ph = i;
    if (cap && cap.getAttribute('data-ph') !== String(ph)) {
      cap.setAttribute('data-ph', String(ph));
      cap.textContent = PH[ph][2];
      host.querySelectorAll('[data-ph]').forEach(function (b) {
        if (b !== cap) b.setAttribute('aria-current', b.getAttribute('data-ph') === String(ph) ? 'step' : 'false');
      });
    }
  }

  function size() {
    var w = stage.clientWidth, h = stage.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function draw() {
    if (!renderer) return;
    pose();
    var ce = Math.cos(el);
    camera.position.set(target.x + dist * ce * Math.cos(az), target.y + dist * ce * Math.sin(az), target.z + dist * Math.sin(el));
    camera.lookAt(target);
    renderer.render(scene, camera);
  }

  function loop(now) {
    if (!started) return;
    var dt = last ? Math.min(0.1, (now - last) / 1000) : 0;
    last = now;
    if (playing && visible) {
      t += dt;
      if (t > T_END) t = 0;
      draw();
    }
    requestAnimationFrame(loop);
  }

  function setPlaying(on) {
    playing = on;
    if (playBtn) { playBtn.textContent = on ? '일시정지' : '재생'; playBtn.setAttribute('aria-pressed', on ? 'true' : 'false'); }
  }

  var visible = false;
  function start() {
    if (started) return;
    started = true;
    if (hint) hint.textContent = '3D 불러오는 중…';
    Promise.all([ensureThree(), fetch(host.getAttribute('data-rj-src')).then(function (r) { return r.json(); })]).then(function (res) {
      THREE = window.THREE; data = res[1]; J = data.J;
      data.jigs.forEach(function (j) { jigs[j.key] = j; });
      decode(data);
      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
      renderer.outputEncoding = THREE.sRGBEncoding;
      stage.insertBefore(renderer.domElement, stage.firstChild);
      build();
      size();
      setLen(lenKey);
      if (hint) hint.textContent = window.matchMedia('(pointer: coarse)').matches ? '옆으로 밀어 돌리기' : '끌어서 돌리기 · Ctrl+휠 확대';
      stage.classList.add('rj-live');
      requestAnimationFrame(loop);
    }).catch(function () {
      if (hint) hint.textContent = '3D를 불러오지 못했습니다 — 아래 순서 글을 보세요.';
      started = false;
    });
  }

  // controls
  host.querySelectorAll('[data-len]').forEach(function (b) {
    b.addEventListener('click', function () { lenKey = b.getAttribute('data-len'); if (renderer) { setLen(lenKey); } });
  });
  host.querySelectorAll('button[data-ph]').forEach(function (b) {
    b.addEventListener('click', function () {
      var i = +b.getAttribute('data-ph');
      t = PH[i][0] + 0.001;
      if (i === 1 || i === 2) t = PH[i][0] + 0.001;
      draw();
    });
  });
  if (playBtn) playBtn.addEventListener('click', function () { setPlaying(!playing); last = 0; });
  setPlaying(playing);

  var drag = null;
  stage.addEventListener('pointerdown', function (e) {
    drag = { x: e.clientX, y: e.clientY, az: az, el: el, touch: e.pointerType === 'touch' };
    if (!drag.touch) stage.setPointerCapture(e.pointerId);
  });
  stage.addEventListener('pointermove', function (e) {
    if (!drag || !renderer) return;
    var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (drag.touch && Math.abs(dy) > Math.abs(dx) * 1.2) return;
    az = drag.az - dx * 0.008;
    if (!drag.touch) el = Math.max(0.05, Math.min(1.45, drag.el + dy * 0.006));
    draw();
  });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (n) { stage.addEventListener(n, function () { drag = null; }); });
  stage.addEventListener('wheel', function (e) {
    if (!renderer || !(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    dist = Math.max(60, Math.min(900, dist * Math.exp(e.deltaY * 0.0015)));
    draw();
  }, { passive: false });
  window.addEventListener('resize', function () { if (renderer) { size(); draw(); } });

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (es) {
      es.forEach(function (en) { visible = en.isIntersecting; if (visible) start(); });
    }, { rootMargin: '200px' }).observe(stage);
  } else { visible = true; start(); }
})();
