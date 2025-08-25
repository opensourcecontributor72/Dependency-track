document.addEventListener('DOMContentLoaded', () => {
  const loginForm = document.getElementById('loginForm');
  const usernameInput = document.getElementById('username');
  const passwordInput = document.getElementById('password');
  const loginBtn = document.getElementById('loginBtn');
  const errorMessage = document.getElementById('errorMessage');

  loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
      showError('Please enter both username and password.');
      return;
    }

    // Add loading state
    loginBtn.innerHTML = '<span class="loading"></span>Logging in...';
    loginBtn.disabled = true;

    loginUser(username, password)
      .then(response => {
        if (response.success) {
          loginBtn.innerHTML = '<span class="success-checkmark"></span>Logged in';
          setTimeout(() => {
            window.location.href = '/getToken';
          }, 2000);
        } else {
          showError(response.message || 'Login failed.');
          resetLoginButton();
        }
      })
      .catch(error => {
        showError(error.message);
        resetLoginButton();
      });
  });

  // Enable Enter key for login
  usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !loginBtn.disabled) {
      loginForm.dispatchEvent(new Event('submit'));
    }
  });

  passwordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !loginBtn.disabled) {
      loginForm.dispatchEvent(new Event('submit'));
    }
  });

  // Clear error message when user starts typing
  usernameInput.addEventListener('input', clearError);
  passwordInput.addEventListener('input', clearError);

  // Focus management
  usernameInput.focus();

  function loginUser(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    return fetch('/login', {
      method: 'POST',
      body: formData,
    })
      .then(response => {
        if (!response.ok) throw new Error('Failed to log in');
        return response.json();
      });
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    setTimeout(() => {
      errorMessage.classList.add('hidden');
    }, 8000);
  }

  function clearError() {
    if (!errorMessage.classList.contains('hidden')) {
      errorMessage.classList.add('hidden');
    }
  }

  function resetLoginButton() {
    loginBtn.innerHTML = 'Login';
    loginBtn.disabled = false;
  }
});