(function () {
  function draw(canvas) {
    var context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    var particles = [];

    function resize() {
      var rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      context.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
      particles = [];
      var count = Math.max(24, Math.floor(rect.width / 36));
      for (var i = 0; i < count; i += 1) {
        particles.push({
          x: Math.random() * rect.width,
          y: Math.random() * rect.height,
          r: Math.random() * 1.8 + 0.4,
          dx: (Math.random() - 0.5) * 0.18,
          dy: (Math.random() - 0.5) * 0.18,
          a: Math.random() * 0.35 + 0.08
        });
      }
    }

    function frame() {
      var width = canvas.clientWidth;
      var height = canvas.clientHeight;
      context.clearRect(0, 0, width, height);
      for (var i = 0; i < particles.length; i += 1) {
        var particle = particles[i];
        particle.x += particle.dx;
        particle.y += particle.dy;
        if (particle.x < -8) particle.x = width + 8;
        if (particle.x > width + 8) particle.x = -8;
        if (particle.y < -8) particle.y = height + 8;
        if (particle.y > height + 8) particle.y = -8;
        context.beginPath();
        context.fillStyle = "rgba(232, 69, 58, " + particle.a + ")";
        context.arc(particle.x, particle.y, particle.r, 0, Math.PI * 2);
        context.fill();
      }
      requestAnimationFrame(frame);
    }

    resize();
    frame();
    window.addEventListener("resize", resize);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var canvases = document.querySelectorAll("[data-particle-field]");
    for (var i = 0; i < canvases.length; i += 1) {
      draw(canvases[i]);
    }
  });
}());
