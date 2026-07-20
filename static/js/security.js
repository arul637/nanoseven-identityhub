document.addEventListener("DOMContentLoaded", function () {
  var checkboxes = document.querySelectorAll("input[type=checkbox]");
  checkboxes.forEach(function (cb) {
    cb.addEventListener("change", function () {
      var hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = this.name;
      hidden.value = this.checked ? "true" : "false";
      if (this.checked) {
        var existing = document.querySelector("input[type=hidden][name='" + this.name + "']");
        if (existing) existing.remove();
      } else {
        this.parentNode.appendChild(hidden);
      }
    });
    if (!cb.checked) {
      var hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = cb.name;
      hidden.value = "false";
      cb.parentNode.appendChild(hidden);
    }
  });
});
