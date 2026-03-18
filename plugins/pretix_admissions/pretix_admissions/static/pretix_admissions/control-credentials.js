(function () {
  function bindCredentialPrint() {
    var buttons = document.querySelectorAll(".js-credential-print");
    if (!buttons.length) return;

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        try {
          window.focus();
        } catch (e) {}

        setTimeout(function () {
          try {
            window.print();
          } catch (e) {}
        }, 80);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindCredentialPrint);
  } else {
    bindCredentialPrint();
  }
})();
