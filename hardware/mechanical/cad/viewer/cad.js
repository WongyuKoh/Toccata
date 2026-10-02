/* 09 CAD 모델 — three.js viewer for cad/toccata.glb (one mesh per part, node name = part id) + cad/parts.json.
   Loads only when the tab is first shown. Model coordinates are the design's (x across, y away from the player,
   z up, mm); the scene root turns them to three's y-up: (x, y, z) -> (x, z, -y). */
(function () {
  var sec = document.getElementById('p-cad');
  if (!sec) return;
  var started = false;
  function start() { if (started) return; started = true; boot(); }
  new MutationObserver(function () { if (!sec.hidden) start(); }).observe(sec, { attributes: true, attributeFilter: ['hidden'] });
  if (!sec.hidden) start();

  function loadScript(src) {
    return new Promise(function (res, rej) {
      var s = document.createElement('script'); s.src = src; s.onload = res;
      s.onerror = function () { rej(new Error(src)); }; document.head.appendChild(s);
    });
  }
  var msg = sec.querySelector('.load');
  function boot() {
    loadScript('https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js')
      .then(function () { return loadScript('https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js'); })
      .then(function () { return loadScript('https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js'); })
      .then(function () { return fetch('cad/parts.json').then(function (r) { if (!r.ok) throw new Error('cad/parts.json ' + r.status); return r.json(); }); })
      .then(init)
      .catch(function (e) { msg.textContent = '3D 모델을 불러오지 못했습니다 (' + e.message + '). 새로고침해 보세요.'; });
  }

  function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || '#ffffff'; }
  function M(x, y, z) { return new THREE.Vector3(x, z, -y); }          // model -> three
  var KIND = { print: '출력', bought: '구매', plywood: '합판', electronics: '전자', consumable: '소모품' };

  function init(D) {
    var stage = sec.querySelector('.stage');
    var canvas = stage.querySelector('canvas');
    var svg = stage.querySelector('svg.dims');
    var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.localClippingEnabled = true;
    var scene = new THREE.Scene();
    function setBg() { scene.background = new THREE.Color(cssVar('--card')); req(); }
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8f99, 0.85));
    var sun = new THREE.DirectionalLight(0xffffff, 0.75); sun.position.set(-600, 1400, 900); scene.add(sun);
    var fill = new THREE.DirectionalLight(0xffffff, 0.35); fill.position.set(900, 500, -800); scene.add(fill);
    var camera = new THREE.PerspectiveCamera(35, 1, 2, 20000);
    var controls = new THREE.OrbitControls(camera, canvas);
    controls.enableDamping = false; controls.screenSpacePanning = true;
    controls.addEventListener('change', req);
    var root = new THREE.Group(); scene.add(root);
    var clip = new THREE.Plane(new THREE.Vector3(-1, 0, 0), 1e6);   // keeps x < constant
    var meshes = {}, byGroup = {}, info = {};
    D.parts.forEach(function (p) { info[p.id] = p; });

    var pending = false;
    function req() { if (!pending) { pending = true; requestAnimationFrame(frame); } }
    function frame() { pending = false; resize(); renderer.render(scene, camera); drawDims(); }
    function resize() {
      var w = stage.clientWidth, h = stage.clientHeight;
      if (canvas.width !== Math.floor(w * renderer.getPixelRatio()) || canvas.height !== Math.floor(h * renderer.getPixelRatio())) {
        renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
      }
    }
    window.addEventListener('resize', req);
    try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', setBg); } catch (e) {}
    new MutationObserver(setBg).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    setBg();

    msg.textContent = '3D 모델을 불러오는 중… (약 9 MB)';
    function onGltf(g) {
      var obj = g.scene;
      obj.rotation.x = -Math.PI / 2;                   // z-up model -> y-up scene (x, y, z) -> (x, z, -y)
      root.add(obj);
      obj.traverse(function (o) {
        if (!o.isMesh) return;
        var id = o.name;
        var p = info[id];
        if (!p) { var par = o.parent; while (par && !info[par.name]) par = par.parent; if (par) { id = par.name; p = info[id]; } }
        o.userData.id = id;
        o.material = o.material.clone();
        o.material.side = THREE.DoubleSide;
        o.material.clippingPlanes = [clip];
        o.material.metalness = 0; o.material.roughness = 0.8;
        meshes[id] = o;
        if (p) { (byGroup[p.g] = byGroup[p.g] || []).push(o); }
      });
      msg.hidden = true;
      buildUi();
      preset('all');
    }
    // the model ships as base64 text (the artifact host does not serve .glb); decode, then parse the GLB
    fetch('cad/toccata.glb.b64.txt').then(function (r) {
      if (!r.ok) throw new Error('cad/toccata.glb.b64.txt ' + r.status);
      return r.text();
    }).then(function (t) {
      msg.textContent = '3D 모델을 푸는 중…';
      var bin = atob(t.trim()), n = bin.length, buf = new Uint8Array(n);
      for (var i = 0; i < n; i++) buf[i] = bin.charCodeAt(i);
      new THREE.GLTFLoader().parse(buf.buffer, '', onGltf, function (err) { msg.textContent = '3D 모델을 읽지 못했습니다: ' + (err && err.message || err); });
    }).catch(function (err) { msg.textContent = '3D 모델을 불러오지 못했습니다: ' + (err && err.message || err); });

    // ---------------- visibility (kinds × groups)
    var kindOn = { print: true, bought: true, plywood: true, electronics: true, consumable: true };
    var groupOn = {};
    D.groups.forEach(function (g, i) { groupOn[i] = true; });
    function applyVis() {
      Object.keys(meshes).forEach(function (id) {
        var p = info[id]; if (!p) return;
        meshes[id].visible = kindOn[p.k] && groupOn[p.g] && !hiddenIds[id];
      });
      req();
    }
    var hiddenIds = {};

    // ---------------- selection
    var sel = null, selMat = null;
    var infoBox = sec.querySelector('.info');
    function select(id) {
      if (sel && meshes[sel]) { meshes[sel].material.emissive.setHex(0x000000); }
      sel = id;
      if (!id) { infoBox.innerHTML = '<p class="empty">부품을 누르면 이름·크기·출력 파일이 여기에 나옵니다.</p>'; req(); return; }
      var m = meshes[id]; if (m) m.material.emissive.setHex(0x2a4d8f);
      var p = info[id]; if (!p) { sel = null; req(); return; } var b = p.b;
      var h = '<span class="kd ' + p.k + '">' + (KIND[p.k] || p.k) + '</span><span class="kd">' + esc(D.groups[p.g]) + '</span>' +
        '<h4>' + esc(p.n) + '</h4><dl>' +
        '<dt>크기</dt><dd class="mono">' + f1(b[3] - b[0]) + ' × ' + f1(b[4] - b[1]) + ' × ' + f1(b[5] - b[2]) + ' mm</dd>' +
        '<dt>위치</dt><dd class="mono">x ' + f1(b[0]) + '~' + f1(b[3]) + '<br>y ' + f1(b[1]) + '~' + f1(b[4]) + '<br>z ' + f1(b[2]) + '~' + f1(b[5]) + '</dd>';
      if (p.f) h += '<dt>출력 파일</dt><dd class="mono">' + esc(p.f) + '</dd>';
      if (p.m) h += '<dt>재료</dt><dd>' + esc(p.m) + '</dd>';
      if (p.pn) h += '<dt>출력</dt><dd>' + esc(p.pn) + '</dd>';
      if (p.nt) h += '<dt>메모</dt><dd>' + esc(p.nt) + '</dd>';
      h += '<dt>id</dt><dd class="mono">' + esc(id) + '</dd></dl>';
      if (p.d && p.d.length) h += '<ul class="dl">' + p.d.map(function (d) { return '<li><b class="mono">' + esc(d[1]) + '</b> ' + esc(d[0]) + '</li>'; }).join('') + '</ul>';
      h += '<div class="gtools" style="margin-top:8px"><button type="button" data-act="hide">이 부품 숨기기</button><button type="button" data-act="focus">가까이 보기</button></div>';
      infoBox.innerHTML = h;
      req();
    }
    infoBox.addEventListener('click', function (e) {
      var a = e.target.getAttribute && e.target.getAttribute('data-act'); if (!a || !sel) return;
      if (a === 'hide') { hiddenIds[sel] = true; applyVis(); select(null); }
      if (a === 'focus') { var b = info[sel].b; frameBox(b, 1.6); }
    });
    function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
    function f1(v) { return (Math.round(v * 10) / 10).toString(); }
    var ray = new THREE.Raycaster(), down = null;
    canvas.addEventListener('pointerdown', function (e) { down = [e.clientX, e.clientY]; });
    canvas.addEventListener('pointerup', function (e) {
      if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
      var r = canvas.getBoundingClientRect();
      var v = new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
      ray.setFromCamera(v, camera);
      var hits = ray.intersectObjects(Object.keys(meshes).map(function (k) { return meshes[k]; }).filter(function (m) { return m.visible; }), false);
      hits = hits.filter(function (h) { return clip.distanceToPoint(h.point) >= 0; });
      select(hits.length ? hits[0].object.userData.id : null);
    });

    // ---------------- camera presets
    function frameBox(b, k) {
      var c = M((b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2);
      var r = Math.max(b[3] - b[0], b[4] - b[1], b[5] - b[2]) * (k || 1.2);
      var dir = camera.position.clone().sub(controls.target).normalize();
      controls.target.copy(c); camera.position.copy(c.clone().add(dir.multiplyScalar(r))); controls.update(); req();
    }
    function look(eye, tgt) { camera.position.copy(M(eye[0], eye[1], eye[2])); controls.target.copy(M(tgt[0], tgt[1], tgt[2])); controls.update(); req(); }
    var lidIds = D.lids || [];
    function preset(k) {
      lidIds.forEach(function (id) { delete hiddenIds[id]; });
      setSection(null);
      var v = (D.views || {})[k];                     // L2: presets come from parts.json (gen_viewer.l2_views)
      if (v) {
        if (v.lids === false) lidIds.forEach(function (id) { hiddenIds[id] = true; });
        if (v.section != null) setSection(v.section);
        look(v.eye, v.tgt);
      }
      else if (k === 'all') look([-260, -900, 760], [611, 225, 40]);
      else if (k === 'module') look([500, -170, 260], [622, 110, 30]);
      else if (k === 'rear') { lidIds.forEach(function (id) { hiddenIds[id] = true; }); look([611, 90, 620], [611, 350, 40]); }
      else if (k === 'section') { setSection(D.section_x); look([D.section_x + 330, 108, 60], [D.section_x, 108, 32]); }
      else if (k === 'front') look([611, -1500, 300], [611, 205, 80]);
      applyVis();
      sec.querySelectorAll('[data-preset]').forEach(function (b) { b.setAttribute('aria-pressed', b.getAttribute('data-preset') === k ? 'true' : 'false'); });
    }

    // ---------------- section plane (keeps x < value)
    var secIn = sec.querySelector('#cadSec'), secOut = sec.querySelector('#cadSecOut'), secOn = sec.querySelector('#cadSecOn');
    function setSection(x) {
      if (x == null) { clip.constant = 1e6; secOn.checked = false; secOut.textContent = '끔'; }
      else { clip.constant = x; secIn.value = x; secOn.checked = true; secOut.textContent = 'x ' + (+x).toFixed(1); }
      req();
    }
    secIn.addEventListener('input', function () { setSection(+secIn.value); });
    secOn.addEventListener('change', function () { setSection(secOn.checked ? +secIn.value : null); });

    // ---------------- dimension overlay
    var dimsOn = false;
    var dimBtn = sec.querySelector('#cadDims');
    dimBtn.addEventListener('click', function () { dimsOn = !dimsOn; dimBtn.setAttribute('aria-pressed', dimsOn ? 'true' : 'false'); req(); });
    function proj(p) {
      var v = M(p[0], p[1], p[2]).project(camera);
      return [(v.x + 1) / 2 * stage.clientWidth, (1 - v.y) / 2 * stage.clientHeight, v.z];
    }
    function drawDims() {
      if (!dimsOn) { svg.innerHTML = ''; return; }
      var out = '';
      D.dims.forEach(function (d) {
        var a = proj(d.a), b = proj(d.b);
        if (a[2] > 1 || b[2] > 1) return;
        if (d.ea) { var e0 = proj(d.ea), e1 = proj(d.eb); if (e0[2] <= 1 && e1[2] <= 1) out += '<line class="ext" x1="' + e0[0] + '" y1="' + e0[1] + '" x2="' + a[0] + '" y2="' + a[1] + '"/><line class="ext" x1="' + e1[0] + '" y1="' + e1[1] + '" x2="' + b[0] + '" y2="' + b[1] + '"/>'; }
        out += '<line x1="' + a[0] + '" y1="' + a[1] + '" x2="' + b[0] + '" y2="' + b[1] + '"/>';
        var ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        [[a, ang + Math.PI], [b, ang]].forEach(function (q) {
          var p = q[0], t = q[1], s = 7;
          out += '<line x1="' + p[0] + '" y1="' + p[1] + '" x2="' + (p[0] - s * Math.cos(t - 0.4)) + '" y2="' + (p[1] - s * Math.sin(t - 0.4)) + '"/>' +
                 '<line x1="' + p[0] + '" y1="' + p[1] + '" x2="' + (p[0] - s * Math.cos(t + 0.4)) + '" y2="' + (p[1] - s * Math.sin(t + 0.4)) + '"/>';
        });
        out += '<text x="' + (a[0] + b[0]) / 2 + '" y="' + ((a[1] + b[1]) / 2 - 6) + '" text-anchor="middle">' + esc(d.t) + '</text>';
      });
      svg.innerHTML = out;
    }

    // ---------------- UI
    function buildUi() {
      sec.querySelectorAll('[data-preset]').forEach(function (b) { b.addEventListener('click', function () { preset(b.getAttribute('data-preset')); }); });
      sec.querySelectorAll('[data-kind]').forEach(function (b) {
        b.addEventListener('click', function () {
          var k = b.getAttribute('data-kind'); kindOn[k] = !kindOn[k];
          b.setAttribute('aria-pressed', kindOn[k] ? 'true' : 'false'); applyVis();
        });
      });
      var list = sec.querySelector('.glist');
      list.innerHTML = D.groups.map(function (g, i) {
        return '<label><input type="checkbox" id="cadg' + i + '" data-g="' + i + '" checked><span>' + esc(g) + '</span><em>' + (byGroup[i] ? byGroup[i].length : 0) + '</em></label>';
      }).join('');
      list.addEventListener('change', function (e) { var i = e.target.getAttribute('data-g'); if (i == null) return; groupOn[i] = e.target.checked; applyVis(); });
      sec.querySelector('[data-gall]').addEventListener('click', function () { setAllGroups(true); });
      sec.querySelector('[data-gnone]').addEventListener('click', function () { setAllGroups(false); });
      sec.querySelector('[data-gshow]').addEventListener('click', function () { hiddenIds = {}; applyVis(); });
      select(null);
    }
    function setAllGroups(on) {
      D.groups.forEach(function (g, i) { groupOn[i] = on; var c = sec.querySelector('#cadg' + i); if (c) c.checked = on; });
      applyVis();
    }
  }
})();
