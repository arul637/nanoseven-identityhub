document.addEventListener("DOMContentLoaded", function () {
  var usernameInput = document.getElementById("username");
  var passwordInput = document.getElementById("password");
  var confirmInput = document.getElementById("confirm");
  var strengthBar = document.getElementById("strengthBar");
  var strengthFeedback = document.getElementById("passwordFeedback");
  var usernameFeedback = document.getElementById("usernameFeedback");
  var homeDirPreview = document.getElementById("homeDirPreview");
  var createHomeCheckbox = document.getElementById("create_home");

  if (usernameInput && homeDirPreview) {
    var userManuallyChanged = false;
    function updateHomeDirPreview() {
      var val = usernameInput.value.trim() || "username";
      homeDirPreview.textContent = val;
      if (createHomeCheckbox) {
        if (val.toLowerCase() === "ironman") {
          createHomeCheckbox.checked = true;
          createHomeCheckbox.disabled = true;
        } else {
          createHomeCheckbox.disabled = false;
          if (!userManuallyChanged) {
            createHomeCheckbox.checked = true;
          }
        }
      }
    }
    usernameInput.addEventListener("input", function () {
      userManuallyChanged = false;
      updateHomeDirPreview();
    });
    if (createHomeCheckbox) {
      createHomeCheckbox.addEventListener("change", function () {
        userManuallyChanged = true;
      });
    }
    updateHomeDirPreview();
  }

  if (usernameInput) {
    usernameInput.addEventListener("blur", function () {
      var val = this.value.trim();
      if (val.length < 3) return;
      fetch("/users/api/check_username?username=" + encodeURIComponent(val))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (usernameFeedback) {
            if (data.exists) {
              usernameFeedback.textContent = "Username already exists.";
              usernameFeedback.style.color = "var(--danger)";
            } else if (!data.valid) {
              usernameFeedback.textContent = data.message;
              usernameFeedback.style.color = "var(--danger)";
            } else {
              usernameFeedback.textContent = "Username available.";
              usernameFeedback.style.color = "var(--success)";
            }
          }
        });
    });
  }

  if (passwordInput) {
    passwordInput.addEventListener("input", function () {
      checkPassword(this.value);
    });
  }

  function checkPassword(pw) {
    if (!strengthBar) return;
    var username = usernameInput ? usernameInput.value.trim() : "";
    fetch("/users/api/check_password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pw, username: username })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        strengthBar.className = "strength-bar " + data.strength;
        if (strengthFeedback) {
          if (data.feedback && data.feedback.length > 0) {
            strengthFeedback.textContent = data.feedback.join("; ");
            strengthFeedback.style.color = "var(--danger)";
          } else {
            strengthFeedback.textContent = "Strong password.";
            strengthFeedback.style.color = "var(--success)";
          }
        }
      });
  }

});
