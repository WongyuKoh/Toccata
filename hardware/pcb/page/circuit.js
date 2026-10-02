
(function(){
  document.addEventListener('click',function(e){
    var b=e.target.closest('.zbar button'); if(!b) return;
    var f=b.closest('.csheet'); var z=b.dataset.z;
    f.classList.remove('z2','z3'); if(z!=='1') f.classList.add('z'+z);
    f.querySelectorAll('.zbar button').forEach(function(x){x.setAttribute('aria-pressed', x===b?'true':'false');});
  });
})();
