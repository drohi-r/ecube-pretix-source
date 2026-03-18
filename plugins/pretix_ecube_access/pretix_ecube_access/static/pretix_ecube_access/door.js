(function () {
    function byId(id) { return document.getElementById(id); }
    function text(el, value) { if (el) el.textContent = value; }
    function show(el) { if (el) el.classList.remove('eca-hidden'); }
    function hide(el) { if (el) el.classList.add('eca-hidden'); }
    function cleanResultLabel(s) { return String(s || 'pending').split('_').join(' ').toUpperCase(); }
    function isMobile() { return window.innerWidth <= 767; }
    function isTabletOrPhone() { return window.innerWidth <= 1279; }

    var root = byId('ecaDoorRoot');
    if (!root) return;

    var apiUrl = root.getAttribute('data-api-url') || '';
    var defaultAction = root.getAttribute('data-default-action') || 'entry';

    var pageShell = byId('pageShell');
    var body = document.body;
    var video = byId('cameraPreview');
    var scannerStage = byId('scannerStage');
    var lockPill = byId('lockPill');
    var scanFrameLabel = byId('scanFrameLabel');
    var scannerFlash = byId('scannerFlash');

    var startBtn = byId('startCameraBtn');
    var stopBtn = byId('stopCameraBtn');
    var resumeBtn = byId('resumeScanBtn');
    var kioskBtn = byId('kioskModeBtn');
var manualPayload = byId('manualPayload');
    var manualSubmit = byId('manualSubmit');
    var statusBox = byId('cameraStatus');

    var entryModeBtn = byId('entryModeBtn');
    var exitModeBtn = byId('exitModeBtn');
    var actionEl = byId('scanAction');
    var gateEl = byId('scanGate');
    var operatorEl = byId('scanOperator');
    var deviceEl = byId('scanDevice');
    var headerMode = byId('headerMode');
    var liveClock = byId('liveClock');

    var resultBackdrop = byId('resultBackdrop');
    var resultWrapMobile = byId('resultWrapMobile');

    var currentStream = null;
    var scanning = false;
    var scannerLocked = false;
    var lastScan = '';
    var lastScanAt = 0;
    var canvas = document.createElement('canvas');
    var ctx = canvas.getContext('2d');
    var resetTimer = null;
    var holdResult = false;
    var lockUntil = 0;
    var LOCK_MS = 5000;

    var desktop = {
        box: byId('resultBoxDesktop'),
        badge: byId('resultBadgeDesktop'),
        idle: byId('resultIdleDesktop'),
        live: byId('resultLiveDesktop'),
        statusWord: byId('statusWordDesktop'),
        statusSub: byId('statusSubDesktop'),
        photo: byId('resultPhotoDesktop'),
        noPhoto: byId('resultNoPhotoDesktop'),
        photoChip: byId('photoStatusChipDesktop'),
        name: byId('resultNameDesktop'),
        type: byId('resultTypeDesktop'),
        message: byId('resultMessageDesktop'),
        code: byId('resultCodeDesktop'),
        engine: byId('resultEngineDesktop'),
        objectType: byId('resultObjectTypeDesktop'),
        gate: byId('resultGateDesktop'),
        action: byId('resultActionDesktop'),
        timestamp: byId('resultTimestampDesktop'),
        entryMode: byId('resultEntryModeDesktop'),
        inside: byId('resultInsideDesktop'),
        holdBtn: byId('holdResultBtnDesktop'),
        clearBtn: byId('clearResultBtnDesktop')
    };

    var mobile = {
        box: byId('resultBoxMobile'),
        badge: byId('resultBadgeMobile'),
        idle: byId('resultIdleMobile'),
        live: byId('resultLiveMobile'),
        statusWord: byId('statusWordMobile'),
        statusSub: byId('statusSubMobile'),
        photo: byId('resultPhotoMobile'),
        noPhoto: byId('resultNoPhotoMobile'),
        photoChip: byId('photoStatusChipMobile'),
        name: byId('resultNameMobile'),
        type: byId('resultTypeMobile'),
        message: byId('resultMessageMobile'),
        code: byId('resultCodeMobile'),
        engine: byId('resultEngineMobile'),
        objectType: byId('resultObjectTypeMobile'),
        gate: byId('resultGateMobile'),
        action: byId('resultActionMobile'),
        timestamp: byId('resultTimestampMobile'),
        entryMode: byId('resultEntryModeMobile'),
        inside: byId('resultInsideMobile'),
        holdBtn: byId('holdResultBtnMobile'),
        clearBtn: byId('clearResultBtnMobile')
    };

    function setStatus(msg) {
        text(statusBox, msg);
    }

    function setActionMode(mode) {
        if (!actionEl) return;
        actionEl.value = mode;
        if (entryModeBtn) entryModeBtn.classList.toggle('active', mode === 'entry');
        if (exitModeBtn) exitModeBtn.classList.toggle('active', mode === 'exit');
        if (entryModeBtn) entryModeBtn.classList.toggle('entry', true);
        if (exitModeBtn) exitModeBtn.classList.toggle('exit', true);
        text(headerMode, mode.toUpperCase());
    }

    function updateClock() {
        var d = new Date();
        var hh = String(d.getHours()).padStart(2, '0');
        var mm = String(d.getMinutes()).padStart(2, '0');
        var ss = String(d.getSeconds()).padStart(2, '0');
        text(liveClock, hh + ':' + mm + ':' + ss);
    }

    function playTone(kind) {
        try {
            var Ctx = window.AudioContext || window.webkitAudioContext;
            if (!Ctx) return;
            var ac = new Ctx();

            function tone(freq, start, duration, gain) {
                var osc = ac.createOscillator();
                var g = ac.createGain();
                osc.type = 'sine';
                osc.frequency.value = freq;
                g.gain.value = gain;
                osc.connect(g);
                g.connect(ac.destination);
                osc.start(ac.currentTime + start);
                osc.stop(ac.currentTime + start + duration);
            }

            if (kind === 'allowed') {
                tone(880, 0, 0.08, 0.02);
                tone(1174, 0.09, 0.10, 0.02);
            } else if (kind === 'allowed_exit') {
                tone(740, 0, 0.08, 0.02);
                tone(988, 0.09, 0.10, 0.02);
            } else if (kind === 'pending') {
                tone(620, 0, 0.08, 0.015);
            } else {
                tone(240, 0, 0.16, 0.025);
                tone(180, 0.18, 0.16, 0.025);
            }
        } catch (e) {}
    }

    function vibrate(pattern) {
        try {
            if (navigator.vibrate) navigator.vibrate(pattern);
        } catch (e) {}
    }

    function clearResetTimer() {
        if (resetTimer) {
            window.clearTimeout(resetTimer);
            resetTimer = null;
        }
    }

    function flashScanner(result) {
        if (!scannerFlash) return;
        scannerFlash.className = 'eca-flash ' + result;
        requestAnimationFrame(function () {
            scannerFlash.classList.add('show');
            setTimeout(function () {
                scannerFlash.classList.remove('show');
            }, 180);
        });
    }

    function applyHeroClass(panel, result) {
        if (!panel.statusWord) return;
        panel.statusWord.classList.remove('hero-allow', 'hero-exit', 'hero-deny');
        if (result === 'allowed') panel.statusWord.classList.add('hero-allow');
        else if (result === 'allowed_exit') panel.statusWord.classList.add('hero-exit');
        else if (result !== 'pending') panel.statusWord.classList.add('hero-deny');
    }

    function setPanelIdle(panel) {
        if (!panel.box) return;
        panel.box.className = panel.box.className.replace(/\bidle\b|\ballowed_exit\b|\ballowed\b|\bpending\b|\binvalid\b|\brevoked\b|\bblocked\b|\bdenied\b|\berror\b|\bexpired\b|\bduplicate\b|\bnot_inside\b|\bpop\b/g, '').trim();
        panel.box.className += ' idle';
        if (panel.statusWord) panel.statusWord.classList.remove('hero-allow', 'hero-exit', 'hero-deny');
        show(panel.idle);
        hide(panel.live);
        if (panel.badge) {
            panel.badge.className = 'eca-badge pending';
            panel.badge.textContent = 'PENDING';
        }
        text(panel.statusWord, 'PENDING');
        text(panel.statusSub, 'Awaiting scan result');
        text(panel.name, 'Unknown');
        text(panel.type, 'Unknown');
        text(panel.code, '—');
        text(panel.engine, '—');
        text(panel.objectType, '—');
        text(panel.gate, '—');
        text(panel.action, '—');
        text(panel.timestamp, '—');
        text(panel.entryMode, '—');
        text(panel.inside, '—');
        text(panel.message, '—');
        text(panel.photoChip, 'Photo status pending');
        if (panel.photo) {
            panel.photo.removeAttribute('src');
            hide(panel.photo);
        }
        show(panel.noPhoto);
    }

    function humanStatus(result) {
        if (result === 'allowed') return ['ALLOWED', 'Access granted'];
        if (result === 'allowed_exit') return ['EXIT OK', 'Exit recorded'];
        if (result === 'duplicate') return ['ALREADY INSIDE', 'Duplicate or re-entry blocked'];
        if (result === 'revoked') return ['REVOKED', 'Credential is revoked'];
        if (result === 'blocked') return ['BLOCKED', 'Credential is blocked'];
        if (result === 'expired') return ['EXPIRED', 'Credential validity ended'];
        if (result === 'not_inside') return ['NOT INSIDE', 'Exit requested for someone not inside'];
        if (result === 'invalid') return ['INVALID', 'Credential not recognized'];
        if (result === 'pending') return ['PENDING', 'Further action required'];
        return ['DENIED', 'Access denied'];
    }

    function fillPanel(panel, data, action, result) {
        if (!panel.box) return;
        panel.box.className = panel.box.className.replace(/\bidle\b|\ballowed_exit\b|\ballowed\b|\bpending\b|\binvalid\b|\brevoked\b|\bblocked\b|\bdenied\b|\berror\b|\bexpired\b|\bduplicate\b|\bnot_inside\b|\bpop\b/g, '').trim();
        panel.box.className += ' ' + result + ' pop';

        hide(panel.idle);
        show(panel.live);

        var hs = humanStatus(result);
        if (panel.badge) {
            panel.badge.className = 'eca-badge ' + result;
            panel.badge.textContent = cleanResultLabel(result);
        }

        text(panel.statusWord, hs[0]);
        text(panel.statusSub, hs[1]);
        applyHeroClass(panel, result);

        text(panel.name, data.display_name || 'Unknown');
        text(panel.type, data.display_type || 'Unknown');
        text(panel.code, data.code || '—');
        text(panel.engine, data.engine || '—');
        text(panel.objectType, data.object_type || '—');
        text(panel.gate, data.gate || '—');
        text(panel.action, action || 'entry');
        text(panel.timestamp, data.timestamp || '—');
        text(panel.entryMode, (data.meta && data.meta.entry_mode) ? data.meta.entry_mode : '—');
        text(panel.inside, (data.meta && typeof data.meta.is_inside !== 'undefined') ? String(data.meta.is_inside) : '—');
        text(panel.message, data.message || '—');

        if (data.photo_url) {
            if (panel.photo) {
                panel.photo.src = data.photo_url;
                show(panel.photo);
            }
            hide(panel.noPhoto);
            text(panel.photoChip, 'Photo available');
        } else {
            if (panel.photo) {
                panel.photo.removeAttribute('src');
                hide(panel.photo);
            }
            show(panel.noPhoto);
            text(panel.photoChip, 'No photo on file');
        }

        setTimeout(function () {
            if (panel.box) panel.box.classList.remove('pop');
        }, 260);
    }

    function openMobileOverlay() {
        if (!isMobile()) return;
        if (resultWrapMobile) resultWrapMobile.classList.add('active');
        if (resultBackdrop) resultBackdrop.classList.add('active');
        if (body) body.classList.add('eca-no-scroll');
    }

    function closeMobileOverlay() {
        if (resultWrapMobile) resultWrapMobile.classList.remove('active');
        if (resultBackdrop) resultBackdrop.classList.remove('active');
        if (body) body.classList.remove('eca-no-scroll');
    }

    function lockScanner(reason) {
        scannerLocked = true;
        lockUntil = Date.now() + LOCK_MS;
        if (scannerStage) scannerStage.classList.add('locked');
        text(lockPill, reason || 'Result locked');
        text(scanFrameLabel, 'Scanner paused');
        openMobileOverlay();
    }

    function unlockScanner(reason) {
        if (holdResult) return;
        scannerLocked = false;
        lockUntil = 0;
        if (scannerStage) scannerStage.classList.remove('locked');
        text(scanFrameLabel, 'Present QR inside frame');
        lastScan = '';
        lastScanAt = 0;
        if (reason) setStatus(reason);
    }

    function resetResult() {
        clearResetTimer();
        setPanelIdle(desktop);
        setPanelIdle(mobile);
        closeMobileOverlay();
    }

    function scheduleReset() {
        clearResetTimer();
        if (holdResult) return;
        resetTimer = window.setTimeout(function () {
            resetResult();
            unlockScanner('Auto-resumed scanning');
        }, LOCK_MS);
    }

    async function apiScan(payload) {
        var req = {
            payload: payload,
            action: actionEl ? (actionEl.value || 'entry') : 'entry',
            gate: gateEl ? (gateEl.value || '') : '',
            operator_name: operatorEl ? (operatorEl.value || '') : '',
            device_id: deviceEl ? (deviceEl.value || '') : ''
        };

        try {
            var res = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(req),
                credentials: 'same-origin'
            });

            var contentType = String(res.headers.get('content-type') || '').toLowerCase();
            var data = null;

            if (contentType.indexOf('application/json') !== -1) {
                data = await res.json();
            } else {
                var raw = await res.text();
                data = {
                    ok: false,
                    result: 'error',
                    engine: 'ecube_access',
                    object_type: 'unknown',
                    code: payload,
                    message: 'Non-JSON scan response (' + res.status + '). Endpoint was blocked or errored before returning JSON.',
                    meta: { raw_preview: String(raw || '').slice(0, 300) }
                };
            }

            if (!res.ok && (!data || typeof data !== 'object')) {
                data = {
                    ok: false,
                    result: 'error',
                    engine: 'ecube_access',
                    object_type: 'unknown',
                    code: payload,
                    message: 'Scan request failed with HTTP ' + res.status
                };
            }

            renderResult(data || {
                ok: false,
                result: 'error',
                engine: 'ecube_access',
                object_type: 'unknown',
                code: payload,
                message: 'Empty scan response'
            }, req.action);
        } catch (err) {
            renderResult({
                ok: false,
                result: 'error',
                engine: 'ecube_access',
                object_type: 'unknown',
                code: payload,
                message: 'Scan request failed: ' + (err && err.message ? err.message : String(err))
            }, req.action);
        }
    }

    function renderResult(data, action) {
        clearResetTimer();
        lockScanner('Result held — scanning paused');

        var result = String(data.result || 'pending');
        fillPanel(desktop, data, action, result);
        fillPanel(mobile, data, action, result);
        flashScanner(result);

        if (result === 'allowed' || result === 'allowed_exit') {
            playTone(result);
            vibrate([60]);
        } else if (result === 'pending') {
            playTone('pending');
            vibrate([50, 40, 50]);
        } else {
            playTone('deny');
            vibrate([90, 50, 90]);
        }

        scheduleReset();
    }

    async function tryGetUserMedia(constraintsList) {
        var lastError = null;
        for (var i = 0; i < constraintsList.length; i++) {
            var constraints = constraintsList[i];
            try {
                setStatus('Trying camera with constraints: ' + JSON.stringify(constraints));
                var stream = await navigator.mediaDevices.getUserMedia(constraints);
                return stream;
            } catch (err) {
                lastError = err;
                setStatus('Camera attempt failed: ' + (err.name || 'Error') + ' — ' + (err.message || String(err)));
            }
        }
        throw lastError || new Error('No camera constraints succeeded');
    }

    async function startCamera() {
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                setStatus('This browser does not support getUserMedia.');
                return;
            }
            if (typeof window.jsQR === 'undefined') {
                setStatus('jsQR library not loaded.');
                return;
            }

            var constraintsList = [
                { video: { facingMode: { ideal: 'environment' } }, audio: false },
                { video: { facingMode: 'environment' }, audio: false },
                { video: true, audio: false }
            ];

            currentStream = await tryGetUserMedia(constraintsList);
            if (video) {
                video.srcObject = currentStream;
                await video.play();
            }

            scanning = true;
            unlockScanner();
            setStatus('Camera started. Scanner active.');
            scanLoop();
        } catch (err) {
            setStatus('Could not start camera: ' + (err.name || 'Error') + ' — ' + (err.message || String(err)));
        }
    }

    function stopCamera() {
        scanning = false;
        if (currentStream) {
            currentStream.getTracks().forEach(function (track) { track.stop(); });
            currentStream = null;
        }
        if (video) video.srcObject = null;
        setStatus('Camera stopped.');
    }

    async function scanLoop() {
        if (!scanning || !video || !ctx || typeof window.jsQR === 'undefined') {
            requestAnimationFrame(scanLoop);
            return;
        }

        try {
            if (scannerLocked) {
                if (!holdResult && lockUntil && Date.now() >= lockUntil) {
                    resetResult();
                    unlockScanner('Scanner resumed');
                }
                requestAnimationFrame(scanLoop);
                return;
            }

            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                var w = video.videoWidth || 0;
                var h = video.videoHeight || 0;

                if (w > 0 && h > 0) {
                    canvas.width = w;
                    canvas.height = h;
                    ctx.drawImage(video, 0, 0, w, h);

                    var imageData = ctx.getImageData(0, 0, w, h);
                    var code = window.jsQR(imageData.data, w, h, {
                        inversionAttempts: 'dontInvert'
                    });

                    if (code && code.data) {
                        var rawValue = String(code.data || '').trim();
                        var now = Date.now();

                        if (rawValue && (rawValue !== lastScan || now - lastScanAt > 2500)) {
                            lastScan = rawValue;
                            lastScanAt = now;
                            setStatus('QR detected: ' + rawValue);
                            await apiScan(rawValue);
                        }
                    }
                }
            }
        } catch (err) {
            setStatus('QR decode error: ' + (err.message || String(err)));
        }

        requestAnimationFrame(scanLoop);
    }

    function toggleHold() {
        holdResult = !holdResult;
        text(desktop.holdBtn, holdResult ? 'Held' : 'Hold result');
        text(mobile.holdBtn, holdResult ? 'Held' : 'Hold result');
        if (!holdResult) {
            scheduleReset();
        } else {
            clearResetTimer();
            scannerLocked = true;
            text(lockPill, 'Result held manually');
        }
    }

    function clearAndResume() {
        holdResult = false;
        text(desktop.holdBtn, 'Hold result');
        text(mobile.holdBtn, 'Hold result');
        resetResult();
        unlockScanner('Scanner resumed');
    }

    async function toggleKioskMode() {
        var goingOn = !pageShell.classList.contains('kiosk');
        pageShell.classList.toggle('kiosk', goingOn);

        if (goingOn) {
            text(kioskBtn, 'Exit kiosk');
            try {
                var el = document.documentElement;
                if (el.requestFullscreen) await el.requestFullscreen();
                else if (el.webkitRequestFullscreen) el.webkitRequestFullscreen();
            } catch (e) {}
        } else {
            text(kioskBtn, 'Fullscreen / kiosk');
            try {
                if (document.fullscreenElement && document.exitFullscreen) await document.exitFullscreen();
                else if (document.webkitFullscreenElement && document.webkitExitFullscreen) document.webkitExitFullscreen();
            } catch (e) {}
        }
    }

    if (entryModeBtn) entryModeBtn.addEventListener('click', function () { setActionMode('entry'); });
    if (exitModeBtn) exitModeBtn.addEventListener('click', function () { setActionMode('exit'); });

    if (desktop.holdBtn) desktop.holdBtn.addEventListener('click', toggleHold);
    if (mobile.holdBtn) mobile.holdBtn.addEventListener('click', toggleHold);
    if (desktop.clearBtn) desktop.clearBtn.addEventListener('click', clearAndResume);
    if (mobile.clearBtn) mobile.clearBtn.addEventListener('click', clearAndResume);

    if (resumeBtn) resumeBtn.addEventListener('click', clearAndResume);
    if (kioskBtn) kioskBtn.addEventListener('click', toggleKioskMode);

    if (resultBackdrop) {
        resultBackdrop.addEventListener('click', function () {
            if (!holdResult) clearAndResume();
        });
    }
if (startBtn) startBtn.addEventListener('click', startCamera);
    if (stopBtn) stopBtn.addEventListener('click', stopCamera);

    if (manualSubmit) {
        manualSubmit.addEventListener('click', function () {
            var value = String((manualPayload && manualPayload.value) || '').trim();
            if (!value) return;
            apiScan(value);
        });
    }

    if (manualPayload) {
        manualPayload.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (manualSubmit) manualSubmit.click();
            }
        });
    }

    setActionMode(defaultAction || 'entry');
    updateClock();
    window.setInterval(updateClock, 1000);
    resetResult();

    if (deviceEl && !deviceEl.value) {
        deviceEl.value = 'door-device-01';
    }

    document.addEventListener('fullscreenchange', function () {
        if (!document.fullscreenElement && pageShell.classList.contains('kiosk')) {
            pageShell.classList.remove('kiosk');
            text(kioskBtn, 'Fullscreen / kiosk');
        }
    });

    setStatus('Ready to scan');
})();

