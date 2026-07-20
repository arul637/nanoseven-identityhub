document.addEventListener("DOMContentLoaded", function () {
  var confirmModal = document.getElementById("confirmModal");
  var confirmOkBtn = document.getElementById("confirmOkBtn");
  var confirmCancelBtn = document.getElementById("confirmCancelBtn");
  var pendingForm = null;

  function showConfirm(title, message, form) {
    document.getElementById("confirmTitle").textContent = title;
    document.getElementById("confirmMessage").textContent = message;
    pendingForm = form;
    confirmModal.classList.add("show");
  }

  function hideConfirm() {
    confirmModal.classList.remove("show");
    pendingForm = null;
  }

  if (confirmOkBtn) {
    confirmOkBtn.addEventListener("click", function () {
      if (pendingForm) {
        pendingForm.submit();
      }
      hideConfirm();
    });
  }

  if (confirmCancelBtn) {
    confirmCancelBtn.addEventListener("click", hideConfirm);
  }

  if (confirmModal) {
    confirmModal.addEventListener("click", function (e) {
      if (e.target === confirmModal) hideConfirm();
    });
  }

  document.querySelectorAll(".remove-member-form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var username = this.getAttribute("data-username") || "this user";
      var group = this.getAttribute("data-group") || "this group";
      showConfirm("Remove Member", "Remove " + username + " from " + group + "?", this);
    });
  });
});
