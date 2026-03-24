(function () {
  function render(canvas) {
    var context = canvas.getContext("2d");
    if (!context) {
      return;
    }

    function resize() {
      var rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      context.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
    }

    function drawFrame(time) {
      var width = canvas.clientWidth;
      var height = canvas.clientHeight;
      var cx = width / 2;
      var cy = height / 2;
      var base = Math.min(width, height) * 0.17;

      context.clearRect(0, 0, width, height);
      context.fillStyle = "#0d0d10";
      context.fillRect(0, 0, width, height);

      for (var i = 0; i < 4; i += 1) {
        context.beginPath();
        context.strokeStyle = "rgba(232, 69, 58, " + (0.12 + i * 0.06) + ")";
        context.lineWidth = 1;
        context.arc(cx, cy, base + i * 18 + Math.sin(time / 900 + i) * 3, 0, Math.PI * 2);
        context.stroke();
      }

      context.beginPath();
      context.fillStyle = "#c0392b";
      context.arc(cx, cy, 10, 0, Math.PI * 2);
      context.fill();

      requestAnimationFrame(drawFrame);
    }

    resize();
    drawFrame(0);
    window.addEventListener("resize", resize);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var canvases = document.querySelectorAll("[data-ring-art]");
    for (var i = 0; i < canvases.length; i += 1) {
      render(canvases[i]);
    }
  });
}());
