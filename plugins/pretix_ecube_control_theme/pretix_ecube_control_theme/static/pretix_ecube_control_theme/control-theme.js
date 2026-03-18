document.documentElement.setAttribute("data-ecube-control-theme", "1");
document.documentElement.classList.add("ecube-control-theme-active");
if (document.body) {
  document.body.classList.add("ecube-control-theme-active");
} else {
  window.addEventListener("DOMContentLoaded", function () {
    document.body.classList.add("ecube-control-theme-active");
  });
}

(function () {
  function norm(path) {
    path = String(path || "").split("?")[0].split("#")[0];
    path = path.replace(/\/+/g, "/");
    if (path.length > 1) {
      path = path.replace(/\/+$/, "");
    }
    return path || "/";
  }

  function openParents(li) {
    var current = li;
    while (current) {
      current.classList.add("ecube-parent-active");
      var submenu = current.querySelector(":scope > ul");
      if (submenu) {
        submenu.classList.add("in");
        submenu.style.height = "auto";
        submenu.style.display = "block";
      }
      current = current.parentElement ? current.parentElement.closest("li") : null;
    }
  }

  function markSidebarActiveByUrl() {
    var sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;

    var current = norm(window.location.pathname);
    var links = Array.prototype.slice.call(sidebar.querySelectorAll("a[href]"));
    var bestLink = null;
    var bestLen = -1;

    links.forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href || href.indexOf("javascript:") === 0 || href === "#") return;

      try {
        var url = new URL(href, window.location.origin);
        var path = norm(url.pathname);
        if (!path || path === "/") return;

        if (current === path || current.indexOf(path + "/") === 0) {
          if (path.length > bestLen) {
            bestLink = a;
            bestLen = path.length;
          }
        }
      } catch (e) {}
    });

    if (!bestLink) return;

    var li = bestLink.closest("li");
    if (!li) return;

    li.classList.add("active", "ecube-route-active");
    bestLink.classList.add("ecube-route-match");
    openParents(li.parentElement ? li.parentElement.closest("li") : null);
  }

  function prependThemeIcons() {
    var nodes = Array.prototype.slice.call(document.querySelectorAll("a, button"));
    nodes.forEach(function (el) {
      if (el.querySelector(".ecube-inline-nav-icon")) return;

      var txt = (el.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
      if (txt !== "themes" && txt !== "custom theme") return;

      var icon = document.createElement("span");
      icon.className = "fa fa-paint-brush ecube-inline-nav-icon";
      el.insertBefore(icon, el.firstChild);
    });
  }

  function runEcubeNavFixes() {
    markSidebarActiveByUrl();
    prependThemeIcons();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", runEcubeNavFixes);
  } else {
    runEcubeNavFixes();
  }
})();
