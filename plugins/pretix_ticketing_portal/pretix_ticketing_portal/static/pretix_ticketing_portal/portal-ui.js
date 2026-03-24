(function () {
  /* ── Topbar scroll + mobile nav ── */
  function initTopbar() {
    var topbar = document.querySelector("[data-topbar]");
    var toggle = document.querySelector("[data-topbar-toggle]");
    var mobileNav = document.querySelector("[data-mobile-nav]");
    if (!topbar) return;

    function sync() {
      topbar.classList.toggle("scrolled", window.scrollY > 40);
    }

    sync();
    window.addEventListener("scroll", sync, { passive: true });

    if (toggle && mobileNav) {
      toggle.addEventListener("click", function () {
        mobileNav.classList.toggle("open");
      });
      mobileNav.querySelectorAll("a").forEach(function (link) {
        link.addEventListener("click", function () {
          mobileNav.classList.remove("open");
        });
      });
    }
  }

  /* ── Hero frequency canvas (v4 style — red bars from bottom) ── */
  function initFrequencyCanvas(canvas) {
    var ctx = canvas.getContext("2d");
    if (!ctx) return;

    var W = 0;
    var H = 0;
    var t = 0;
    var animId = null;

    function resize() {
      W = canvas.offsetWidth * 2;
      H = canvas.offsetHeight * 2;
      canvas.width = W;
      canvas.height = H;
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      var barCount = 80;
      var barW = W / barCount;

      for (var i = 0; i < barCount; i++) {
        var x = i * barW;
        var h1 = Math.sin(i * 0.15 + t * 0.8) * 0.3 + 0.3;
        var h2 = Math.cos(i * 0.12 + t * 1.1) * 0.25 + 0.25;
        var h = (h1 + h2) * 0.5 * H * 0.4;
        var a = 0.04 + h1 * 0.06;
        ctx.fillStyle = "rgba(200,0,10," + a + ")";
        ctx.fillRect(x, H - h, barW - 2, h);
      }

      t += 0.015;
      animId = requestAnimationFrame(draw);
    }

    resize();
    draw();
    window.addEventListener("resize", resize);
  }

  /* ── Mouse-following card glow ── */
  function initCardGlow() {
    document.querySelectorAll(".ecard").forEach(function (card) {
      card.addEventListener("mousemove", function (e) {
        var rect = card.getBoundingClientRect();
        var x = ((e.clientX - rect.left) / rect.width) * 100;
        var y = ((e.clientY - rect.top) / rect.height) * 100;
        card.style.setProperty("--mx", x + "%");
        card.style.setProperty("--my", y + "%");
      });

      card.addEventListener("mouseleave", function () {
        card.style.setProperty("--mx", "50%");
        card.style.setProperty("--my", "50%");
      });
    });
  }

  /* ── Filter tabs + search ── */
  function initFilters() {
    var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-filter-tab]"));
    var search = document.querySelector("[data-filter-search]");
    var cards = Array.prototype.slice.call(document.querySelectorAll(".ecard"));
    if (!tabs.length || !cards.length) return;

    var currentFilter = "all";

    function matchesFilter(card) {
      if (currentFilter === "all") return true;
      if (currentFilter === "on_sale") return card.dataset.saleState === "on_sale";
      if (currentFilter === "upcoming") return card.dataset.saleState === "upcoming";
      if (currentFilter === "free") return card.dataset.isFree === "true";
      if (currentFilter === "exclusive") return card.dataset.isExclusive === "true";
      return true;
    }

    function matchesSearch(card) {
      if (!search || !search.value.trim()) return true;
      return (card.dataset.search || "").indexOf(search.value.trim().toLowerCase()) !== -1;
    }

    function applyFilters() {
      var visibleCount = 0;

      cards.forEach(function (card) {
        var visible = matchesFilter(card) && matchesSearch(card);
        card.dataset.hidden = visible ? "false" : "true";
        if (visible) visibleCount++;
      });

      /* Show/hide empty state */
      var emptyState = document.querySelector(".portal-empty-state");
      if (emptyState) {
        emptyState.style.display = visibleCount === 0 ? "" : "none";
      }
    }

    tabs.forEach(function (tab) {
      tab.addEventListener("click", function () {
        currentFilter = tab.dataset.filterTab;
        tabs.forEach(function (node) {
          node.classList.toggle("active", node === tab);
        });
        applyFilters();
      });
    });

    if (search) {
      search.addEventListener("input", applyFilters);
    }

    applyFilters();
  }

  /* ── Init ── */
  document.addEventListener("DOMContentLoaded", function () {
    initTopbar();

    var canvas = document.querySelector("[data-freq-canvas]");
    if (canvas) initFrequencyCanvas(canvas);

    initCardGlow();
    initFilters();
  });
}());
