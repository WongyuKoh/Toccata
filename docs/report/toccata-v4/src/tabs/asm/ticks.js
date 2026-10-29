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
