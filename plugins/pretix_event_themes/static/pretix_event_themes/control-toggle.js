(function () {
  function applyMode() {
    var mode = localStorage.getItem('ecubePretixMode') || 'dark';
    document.documentElement.classList.toggle('ecube-light', mode === 'light');
    var btn = document.getElementById('ecube-theme-toggle');
    if (btn) btn.textContent = mode === 'light' ? 'Dark mode' : 'Light mode';
  }

  function ensureButton() {
    if (document.getElementById('ecube-theme-toggle')) return;
    var btn = document.createElement('button');
    btn.id = 'ecube-theme-toggle';
    btn.className = 'ecube-theme-toggle';
    btn.type = 'button';
    btn.textContent = 'Light mode';
    btn.addEventListener('click', function () {
      var current = localStorage.getItem('ecubePretixMode') || 'dark';
      localStorage.setItem('ecubePretixMode', current === 'light' ? 'dark' : 'light');
      applyMode();
    });
    document.body.appendChild(btn);
  }

  function init() {
    applyMode();
    ensureButton();
    applyMode();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

