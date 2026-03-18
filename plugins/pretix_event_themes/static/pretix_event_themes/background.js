(function () {
    function installThemesBackground() {
        var meta = document.querySelector('meta[name="event-themes-bg-url"]');
        if (!meta || !meta.content || !document.body) return;

        var bgUrl = meta.content;
        var mobile = window.matchMedia('(max-width: 768px)').matches;

        var overlayOpacity = mobile ? 0.72 : 0.55;
        var bgPosition = mobile ? 'center top' : 'center center';
        var grainOpacity = mobile ? 0.06 : 0.10;
        var grainSize = mobile ? '8px 8px' : '6px 6px';

        if (!document.getElementById('event-themes-bg-layer')) {
            var bg = document.createElement('div');
            bg.id = 'event-themes-bg-layer';
            bg.style.position = 'fixed';
            bg.style.inset = '0';
            bg.style.zIndex = '0';
            bg.style.pointerEvents = 'none';
            bg.style.backgroundRepeat = 'no-repeat';
            bg.style.backgroundSize = 'cover';
            document.body.insertBefore(bg, document.body.firstChild);
        }

        var bgLayer = document.getElementById('event-themes-bg-layer');
        bgLayer.style.backgroundImage =
            'linear-gradient(rgba(8,8,8,' + overlayOpacity + '), rgba(8,8,8,' + overlayOpacity + ')), url("' + bgUrl + '")';
        bgLayer.style.backgroundPosition = bgPosition;

        if (!document.getElementById('event-themes-bg-grain')) {
            var grain = document.createElement('div');
            grain.id = 'event-themes-bg-grain';
            grain.style.position = 'fixed';
            grain.style.inset = '0';
            grain.style.zIndex = '1';
            grain.style.pointerEvents = 'none';
            grain.style.backgroundImage =
                'radial-gradient(rgba(255,255,255,0.08) 0.6px, transparent 0.6px)';
            document.body.insertBefore(grain, document.body.firstChild);
        }

        var grainLayer = document.getElementById('event-themes-bg-grain');
        grainLayer.style.opacity = String(grainOpacity);
        grainLayer.style.backgroundSize = grainSize;
    }

    function init() {
        installThemesBackground();
        window.addEventListener('resize', installThemesBackground);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

