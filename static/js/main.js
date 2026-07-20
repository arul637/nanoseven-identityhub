document.addEventListener("DOMContentLoaded", function () {
  var toasts = document.querySelectorAll(".toast");
  toasts.forEach(function (t) {
    var close = t.querySelector(".toast-close");
    if (close) {
      close.addEventListener("click", function () { t.remove(); });
    }
    setTimeout(function () { t.remove(); }, 6000);
  });
});
