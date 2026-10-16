
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
