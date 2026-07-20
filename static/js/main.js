document.addEventListener("DOMContentLoaded", function () {
  var toasts = document.querySelectorAll(".toast");
  toasts.forEach(function (t) {
    var close = t.querySelector(".toast-close");
    if (close) {
      close.addEventListener("click", function () { t.remove(); });
    }
    setTimeout(function () { t.remove(); }, 3000);
  });

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

  var sidebar = document.getElementById("sidebar");
  var sidebarToggle = document.getElementById("sidebarToggle");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      if (window.innerWidth <= 768) {
        sidebar.classList.toggle("open");
      }
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 768) {
        sidebar.classList.remove("open");
      }
    });
  }

  document.querySelectorAll(".sync-run-form, .remove-member-form, .delete-user-form, .delete-group-form, .delete-sync-form, .delete-audit-form").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = "";
      if (form.classList.contains("sync-run-form")) {
        text = "Start system synchronization? This may take a moment.";
      } else if (form.classList.contains("remove-member-form")) {
        var u = form.getAttribute("data-username") || "this user";
        var g = form.getAttribute("data-group") || "this group";
        text = "Remove " + u + " from " + g + "?";
      } else if (form.classList.contains("delete-user-form")) {
        text = "Are you sure you want to delete this user? This cannot be undone.";
      } else if (form.classList.contains("delete-group-form")) {
        text = "Are you sure you want to delete this group? This cannot be undone.";
      } else if (form.classList.contains("delete-sync-form")) {
        text = "Are you sure you want to delete all sync history? This cannot be undone.";
      } else if (form.classList.contains("delete-audit-form")) {
        text = "Are you sure you want to delete all audit logs? This cannot be undone.";
      }
      showConfirm("Confirm", text, form);
    });
  });
});
