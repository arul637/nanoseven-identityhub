document.addEventListener("DOMContentLoaded", function () {
  var usernameInput = document.getElementById("username");
  var passwordInput = document.getElementById("password");
  var confirmInput = document.getElementById("confirm");
  var strengthBar = document.getElementById("strengthBar");
  var strengthFeedback = document.getElementById("passwordFeedback");
  var usernameFeedback = document.getElementById("usernameFeedback");
  var generateBtn = document.getElementById("generatePasswordBtn");

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

  if (generateBtn) {
    generateBtn.addEventListener("click", function () {
      fetch("/users/api/generate_password")
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (passwordInput) {
            passwordInput.value = data.password;
            if (confirmInput) confirmInput.value = data.password;
            checkPassword(data.password);
          }
        });
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

  var forms = document.querySelectorAll("form[method=POST]");
  forms.forEach(function (f) {
    f.addEventListener("submit", function () {
      var btn = this.querySelector("button[type=submit]");
      if (btn) btn.disabled = true;
    });
  });
});
