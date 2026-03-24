(function () {
    function initLaser() {
        var canvas = document.getElementById('ec-laser-canvas');
        if (!canvas) return;
        var ctx = canvas.getContext('2d');
        var beams = [];
        var W, H;

        function resize() {
            var parent = canvas.parentElement;
            W = canvas.width = parent.offsetWidth;
            H = canvas.height = parent.offsetHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        function randBeam() {
            var fromTop = Math.random() > 0.5;
            return {
                x: Math.random() * W,
                y: fromTop ? 0 : H,
                angle: fromTop
                    ? (Math.PI / 4 + Math.random() * Math.PI / 4)
                    : (-Math.PI / 4 - Math.random() * Math.PI / 4),
                speed: 0.4 + Math.random() * 0.6,
                len: 80 + Math.random() * 120,
                alpha: 0,
                maxAlpha: 0.10 + Math.random() * 0.16,
                life: 0,
                maxLife: 180 + Math.random() * 120
            };
        }

        for (var i = 0; i < 5; i++) beams.push(randBeam());

        function draw() {
            ctx.clearRect(0, 0, W, H);
            beams.forEach(function (b) {
                b.life++;
                if (b.life < 30) {
                    b.alpha = b.maxAlpha * (b.life / 30);
                } else if (b.life > b.maxLife - 30) {
                    b.alpha = b.maxAlpha * ((b.maxLife - b.life) / 30);
                } else {
                    b.alpha = b.maxAlpha;
                }

                var ex = b.x + Math.cos(b.angle) * b.len;
                var ey = b.y + Math.sin(b.angle) * b.len;
                var grad = ctx.createLinearGradient(b.x, b.y, ex, ey);
                grad.addColorStop(0, 'rgba(200,0,10,0)');
                grad.addColorStop(0.5, 'rgba(200,0,10,' + b.alpha + ')');
                grad.addColorStop(1, 'rgba(200,0,10,0)');
                ctx.strokeStyle = grad;
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.moveTo(b.x, b.y);
                ctx.lineTo(ex, ey);
                ctx.stroke();

                b.x += Math.cos(b.angle) * b.speed;
                b.y += Math.sin(b.angle) * b.speed;

                if (b.life >= b.maxLife) {
                    Object.assign(b, randBeam());
                }
            });

            if (beams.length < 6 && Math.random() < 0.012) {
                beams.push(randBeam());
            }

            requestAnimationFrame(draw);
        }

        draw();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLaser);
    } else {
        initLaser();
    }
})();
