(function () {
    var head = document.head;
    if (!head) {
        return;
    }

    var href = "/static/pretix_ecube_control_theme/ecube-logo.png?v=20260320006";
    var selectors = [
        'link[rel="icon"]',
        'link[rel="shortcut icon"]',
        'link[rel="apple-touch-icon"]'
    ];

    selectors.forEach(function (selector) {
        document.querySelectorAll(selector).forEach(function (node) {
            node.parentNode.removeChild(node);
        });
    });

    [
        { rel: "icon", href: href, type: "image/png" },
        { rel: "shortcut icon", href: href, type: "image/png" },
        { rel: "apple-touch-icon", href: href }
    ].forEach(function (attrs) {
        var link = document.createElement("link");
        Object.keys(attrs).forEach(function (key) {
            link.setAttribute(key, attrs[key]);
        });
        head.appendChild(link);
    });
})();
