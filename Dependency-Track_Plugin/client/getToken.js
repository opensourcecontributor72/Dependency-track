// Enhanced Dependency-Track Plugin JavaScript - KEEPING YOUR ORIGINAL LOGIC + ADMIN PROTECTION
document.addEventListener('DOMContentLoaded', () => {
  const usernameInput = document.getElementById('username');
  const fetchTeamsBtn = document.getElementById('fetchTeamsBtn');
  const teamSection = document.getElementById('teamSection');
  const teamSelect = document.getElementById('teamSelect');
  const generateTokenBtn = document.getElementById('generateTokenBtn');
  const tokenResult = document.getElementById('tokenResult');
  const apiToken = document.getElementById('apiToken');
  const copyTokenBtn = document.getElementById('copyTokenBtn');
  const errorMessage = document.getElementById('errorMessage');
  const hiddenUsername = document.getElementById('hiddenUsername'); // New reference
  
  // Toaster elements
  const toasterOverlay = document.getElementById('toasterOverlay');
  const toasterMessage = document.getElementById('toasterMessage');
  const toasterYes = document.getElementById('toasterYes');
  const toasterNo = document.getElementById('toasterNo');

  let userEmail = ''; // Store the email globally
  let currentTeam = ''; // Store current team for confirmation

  // Prefill username from hidden input on page load
  if (hiddenUsername) {
    usernameInput.value = hiddenUsername.value || '';
  }

  // ADMIN PROTECTION CONFIGURATION
  const RESTRICTED_TEAMS = [
    'admin',
    'administrator',
    'administrators', 
    'dt admin',
    'dt-admin',
    'dependency-track admin',
    'dependencytrack admin',
    'system admin',
    'system administrator',
    'root',
    'superuser',
    'super admin'
  ];

  // Check if a team name is restricted/admin team
  function isRestrictedTeam(teamName) {
    if (!teamName) return false;
    
    const normalizedTeamName = teamName.toLowerCase().trim();
    
    return RESTRICTED_TEAMS.some(restrictedTeam => 
      normalizedTeamName === restrictedTeam.toLowerCase() ||
      normalizedTeamName.includes('admin')
    );
  }

  fetchTeamsBtn.addEventListener('click', () => {
    const username = usernameInput.value.trim();
    if (!username) {
      showError('Please enter a username or email address.');
      return;
    }

    // Add loading state
    fetchTeamsBtn.innerHTML = '<span class="loading"></span>Fetching...';
    fetchTeamsBtn.disabled = true;

    fetchTeams(username)
      .then(data => {
        userEmail = data.email || 'not_provided'; // Store the email from the response
        teamSelect.innerHTML = '<option value="">Select a team</option>';
        if (data.teams.length === 0) {
          showError('No teams found for this user.');
          resetFetchButton();
          return;
        }
        data.teams.forEach(team => {
          const option = document.createElement('option');
          option.value = team;
          option.textContent = team;
          
          // Mark restricted teams visually (but still allow selection for the error message)
          if (isRestrictedTeam(team)) {
            option.textContent += ' ⚠️';
            option.style.color = '#ffc107';
            option.title = 'Admin team - Access restricted';
          }
          
          teamSelect.appendChild(option);
        });
        teamSection.classList.remove('hidden');
        generateTokenBtn.disabled = false;
        errorMessage.classList.add('hidden');
        
        // Show success state
        fetchTeamsBtn.innerHTML = '<span class="success-checkmark"></span>Teams Loaded';
        setTimeout(() => {
          resetFetchButton();
        }, 2000);
      })
      .catch(error => {
        showError(error.message);
        resetFetchButton();
      });
  });

  generateTokenBtn.addEventListener('click', () => {
    const selectedTeam = teamSelect.value;
    if (!selectedTeam) {
      showError('Please select a team.');
      return;
    }

    // ADMIN PROTECTION CHECK - Block admin teams immediately
    if (isRestrictedTeam(selectedTeam)) {
      showError(`Access Denied: You do not have permission to fetch tokens for the admin team "${selectedTeam}". This action has been blocked for security reasons.`);
      
      // Reset team selection for security
      teamSelect.value = '';
      generateTokenBtn.disabled = true;
      tokenResult.classList.add('hidden');
      
      return;
    }

    currentTeam = selectedTeam;
    toasterMessage.textContent = `This will generate a new API key for team '${selectedTeam}'. Do you want to proceed?`;
    showToaster();
  });

  toasterYes.addEventListener('click', () => {
    hideToaster();
    generateApiToken();
  });

  toasterNo.addEventListener('click', () => {
    hideToaster();
  });

  copyTokenBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(apiToken.textContent)
      .then(() => {
        copyTokenBtn.innerHTML = '<span class="success-checkmark"></span>Copied!';
        
        // Show warning toaster about token disappearing
        setTimeout(() => {
          showWarningToaster(
            'Token Copied Successfully!',
            'Please save this token securely. It will disappear once you close this message for security reasons.',
            () => {
              // Hide token after user confirms they saved it
              tokenResult.classList.add('hidden');
              resetGenerateButton();
            }
          );
        }, 1000);
      })
      .catch(() => showError('Failed to copy token.'));
  });

  // API Functions - YOUR ORIGINAL IMPLEMENTATION
  function fetchTeams(username) {
    return fetch(`/api/fetch_teams?username=${encodeURIComponent(username)}`)
      .then(response => {
        if (!response.ok) throw new Error('Failed to fetch teams');
        return response.json();
      })
      .then(data => {
        if (data.error) throw new Error(data.error);
        return data;
      });
  }

  function generateApiToken() {
    const username = usernameInput.value.trim();
    
    // Double-check for admin teams (additional security layer)
    if (isRestrictedTeam(currentTeam)) {
      showError(`Security Error: Cannot generate token for admin team "${currentTeam}".`);
      resetGenerateButton();
      return;
    }
    
    generateTokenBtn.innerHTML = '<span class="loading"></span>Generating...';
    generateTokenBtn.disabled = true;

    generateToken(currentTeam, username, userEmail)
      .then(data => {
        if (data.error) {
          showError(data.error);
          resetGenerateButton();
        } else {
          apiToken.textContent = data.token || 'Token generation failed';
          tokenResult.classList.remove('hidden');
          copyTokenBtn.disabled = false;
          errorMessage.classList.add('hidden');
          
          // Show success state
          generateTokenBtn.innerHTML = '<span class="success-checkmark"></span>Token Generated';
          setTimeout(() => {
            resetGenerateButton();
          }, 2000);
        }
      })
      .catch(error => {
        showError(error.message);
        resetGenerateButton();
      });
  }

  function generateToken(teamName, username, email) {
    return fetch(`/api/generate_token?team=${encodeURIComponent(teamName)}&username=${encodeURIComponent(username)}&email=${encodeURIComponent(email)}`)
      .then(response => {
        if (!response.ok) throw new Error('Failed to generate token');
        return response.json();
      });
  }

  // UI Helper Functions
  function showToaster() {
    toasterOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function hideToaster() {
    toasterOverlay.classList.remove('show');
    document.body.style.overflow = 'auto';
  }

  function showWarningToaster(title, message, onConfirm) {
    // Update toaster content for warning message
    const toasterTitle = document.querySelector('.toaster-title');
    const toasterIcon = document.querySelector('.toaster-icon');
    const toasterYesBtn = document.getElementById('toasterYes');
    const toasterNoBtn = document.getElementById('toasterNo');

    toasterTitle.textContent = title;
    toasterMessage.textContent = message;
    toasterIcon.textContent = '💾'; // Save icon
    toasterIcon.classList.add('save');
    toasterYesBtn.textContent = 'I have saved it';
    toasterNoBtn.textContent = 'Let me save it';

    // Remove old event listeners and add new ones
    const newYesBtn = toasterYesBtn.cloneNode(true);
    const newNoBtn = toasterNoBtn.cloneNode(true);
    toasterYesBtn.parentNode.replaceChild(newYesBtn, toasterYesBtn);
    toasterNoBtn.parentNode.replaceChild(newNoBtn, toasterNoBtn);

    newYesBtn.addEventListener('click', () => {
      hideToaster();
      onConfirm();
      resetToasterContent();
    });

    newNoBtn.addEventListener('click', () => {
      hideToaster();
      resetToasterContent();
    });

    showToaster();
  }

  function resetToasterContent() {
    // Reset toaster to original confirmation state
    const toasterTitle = document.querySelector('.toaster-title');
    const toasterIcon = document.querySelector('.toaster-icon');
    const toasterYesBtn = document.querySelector('.toaster-button-yes');
    const toasterNoBtn = document.querySelector('.toaster-button-no');

    toasterTitle.textContent = 'Confirm Action';
    toasterIcon.textContent = '⚠️';
    toasterIcon.classList.remove('save');
    toasterYesBtn.textContent = 'Yes, Proceed';
    toasterNoBtn.textContent = 'Cancel';
  }

  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.classList.remove('hidden');
    
    // Auto-hide error after 8 seconds for longer admin messages
    setTimeout(() => {
      errorMessage.classList.add('hidden');
    }, 8000);
  }

  function resetFetchButton() {
    fetchTeamsBtn.innerHTML = 'Get Teams';
    fetchTeamsBtn.disabled = false;
  }

  function resetGenerateButton() {
    generateTokenBtn.innerHTML = 'Get Token';
    generateTokenBtn.disabled = false;
  }

  // Event Listeners for Enhanced UX
  
  // Close toaster when clicking overlay
  toasterOverlay.addEventListener('click', (e) => {
    if (e.target === toasterOverlay) {
      hideToaster();
    }
  });

  // Close toaster with Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && toasterOverlay.classList.contains('show')) {
      hideToaster();
    }
  });

  // Enable Enter key for username input
  usernameInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !fetchTeamsBtn.disabled) {
      fetchTeamsBtn.click();
    }
  });

  // Enable Enter key for team selection
  teamSelect.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !generateTokenBtn.disabled && teamSelect.value) {
      generateTokenBtn.click();
    }
  });

  // Clear error message when user starts typing
  usernameInput.addEventListener('input', () => {
    if (!errorMessage.classList.contains('hidden')) {
      errorMessage.classList.add('hidden');
    }
  });

  // Enhanced team selection with admin protection
  teamSelect.addEventListener('change', () => {
    const selectedTeam = teamSelect.value;
    
    // Clear error message when team is selected
    if (!errorMessage.classList.contains('hidden')) {
      errorMessage.classList.add('hidden');
    }
    
    // Enable/disable button based on selection
    generateTokenBtn.disabled = !selectedTeam;
    
    // Hide token result when changing teams
    if (selectedTeam && !tokenResult.classList.contains('hidden')) {
      tokenResult.classList.add('hidden');
    }
  });

  // Focus management for better UX
  usernameInput.addEventListener('blur', () => {
    if (usernameInput.value.trim()) {
      usernameInput.value = usernameInput.value.trim();
    }
  });

  // Focus on username input when page loads
  usernameInput.focus();
});