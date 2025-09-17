document.addEventListener('DOMContentLoaded', () => {
  // Toast notification system
  function showToast(message, type = 'success') {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col space-y-2';
      document.body.appendChild(toastContainer);
    }

    // Create toast element
    const toast = document.createElement('div');
    toast.className = `px-4 py-3 rounded-lg shadow-lg flex items-center ${type === 'success' ? 'bg-green-500' : 'bg-red-500'} text-white transform transition-all duration-300 translate-y-2 opacity-0`;

    // Add icon based on type
    const icon = document.createElement('i');
    icon.className = `fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} mr-2`;
    toast.appendChild(icon);

    // Add message
    const text = document.createElement('span');
    text.textContent = message;
    toast.appendChild(text);

    // Add close button
    const closeBtn = document.createElement('button');
    closeBtn.className = 'ml-auto text-white hover:text-gray-200';
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    closeBtn.addEventListener('click', () => removeToast(toast));
    toast.appendChild(closeBtn);

    // Add to container
    toastContainer.appendChild(toast);

    // Animate in
    setTimeout(() => {
      toast.classList.remove('translate-y-2', 'opacity-0');
    }, 10);

    // Auto remove after 5 seconds
    setTimeout(() => removeToast(toast), 5000);
  }

  function removeToast(toast) {
    toast.classList.add('translate-y-2', 'opacity-0');
    setTimeout(() => toast.remove(), 300);
  }

  // Contact information Modal with animations
  const contactModal = document.getElementById('editModal');
  const contactModalContent = document.getElementById('modalContent');
  const cancelBtn = document.getElementById('cancelBtn');

  function openModal() {
    // Show the modal background
    contactModal.classList.remove('hidden');

    // Animate the modal content after a tiny delay
    setTimeout(() => {
      contactModalContent.classList.remove('scale-95', 'opacity-0');
      contactModalContent.classList.add('scale-100', 'opacity-100');
    }, 50);
  }

  function closeModal() {
    // Animate out
    contactModalContent.classList.remove('scale-100', 'opacity-100');
    contactModalContent.classList.add('scale-95', 'opacity-0');

    // Hide the modal after animation completes
    setTimeout(() => {
      contactModal.classList.add('hidden');
    }, 300);
  }

  // Event Listeners
  document.getElementById('openModal').addEventListener('click', openModal);
  document.getElementById('closeModal').addEventListener('click', closeModal);
  if (cancelBtn) cancelBtn.addEventListener('click', closeModal);

  contactModal.addEventListener('click', function(event) {
    if (event.target === this) {
      closeModal();
    }
  });

  // Add keyboard support for closing modals with Escape key
  document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
      if (!contactModal.classList.contains('hidden')) {
        closeModal();
      }
    }
  });

  // Profile photo upload handler
  const profilePhotoUpload = document.getElementById('profile-photo-upload');
  if (profilePhotoUpload) {
    profilePhotoUpload.addEventListener('change', function() {
      if (this.files && this.files[0]) {
        const file = this.files[0];

        // Check file size before upload (120KB = 120 * 1024 bytes)
        const maxSize = 120 * 1024;
        if (file.size > maxSize) {
          showToast(`File size too large. Maximum allowed size is 120KB. Your file is ${Math.round(file.size / 1024)}KB.`, 'error');
          this.value = ''; // Clear the input
          return;
        }

        // Check file type
        const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif'];
        if (!allowedTypes.includes(file.type)) {
          showToast('Invalid file type. Only JPEG, PNG, and GIF images are allowed.', 'error');
          this.value = ''; // Clear the input
          return;
        }

        const form = document.getElementById('profile-photo-form');

        // Show loading indicator
        const profileImg = document.querySelector('[alt="Profile Photo"]');
        const originalOpacity = profileImg.style.opacity;
        profileImg.style.opacity = '0.5';

        const formData = new FormData(form);

        fetch(form.action, {
          method: 'POST',
          body: formData,
          headers: {
            'X-Requested-With': 'XMLHttpRequest'
          }
        })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            // Update the profile image
            profileImg.src = data.profile_photo;
            profileImg.style.opacity = originalOpacity;

            // Show success message
            showToast('Profile photo updated successfully!', 'success');
          } else {
            profileImg.style.opacity = originalOpacity;
            showToast(data.error || 'Failed to update profile photo', 'error');
          }
        })
        .catch(error => {
          profileImg.style.opacity = originalOpacity;
          showToast('Network error. Please try again.', 'error');
        });
      }
    });
  }

  // Contact form submission with enhanced feedback
  const contactForm = document.getElementById('contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
      e.preventDefault();

      // Show loading state
      const submitBtn = document.getElementById('contactSubmitBtn');
      const btnText = document.getElementById('contactBtnText');
      const loadingSpinner = document.getElementById('contactLoadingSpinner');
      const formStatus = document.getElementById('contactFormStatus');

      submitBtn.disabled = true;
      btnText.textContent = 'Saving...';
      loadingSpinner.classList.remove('hidden');

      // Get form data
      const formData = new FormData(contactForm);

      // Send AJAX request
      fetch(contactForm.action, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.json())
      .then(data => {
        // Reset button state
        submitBtn.disabled = false;
        btnText.textContent = 'Save Changes';
        loadingSpinner.classList.add('hidden');

        if (data.success) {
          // Show success message with icon
          formStatus.classList.remove('hidden', 'bg-red-100', 'text-red-700');
          formStatus.classList.add('bg-green-100', 'text-green-700');
          formStatus.innerHTML = `
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <i class="fas fa-check-circle text-green-500 text-xl"></i>
              </div>
              <div class="ml-3">
                <p class="text-sm font-medium text-green-800">Contact information updated successfully!</p>
              </div>
            </div>
          `;

          // Update the displayed contact info with animation
          const phoneText = document.getElementById('phone-text');
          const cityText = document.getElementById('city-text');
          const countryText = document.getElementById('country-text');

          // Add highlight animation
          [phoneText, cityText, countryText].forEach(el => {
            el.classList.add('transition-all', 'duration-500');
            el.style.backgroundColor = 'rgba(16, 185, 129, 0.2)';  // Light green background

            // Set the new values
            if (el === phoneText) el.textContent = data.phone || 'Not provided';
            if (el === cityText) el.textContent = data.city || 'Not provided';
            if (el === countryText) el.textContent = data.country || 'Not provided';

            // Remove highlight after animation
            setTimeout(() => {
              el.style.backgroundColor = 'transparent';
            }, 2000);
          });

          // Close modal after a delay
          setTimeout(() => {
            closeModal();
          }, 1500);
        } else {
          // Show error message with icon
          formStatus.classList.remove('hidden', 'bg-green-100', 'text-green-700');
          formStatus.classList.add('bg-red-100', 'text-red-700');
          formStatus.innerHTML = `
            <div class="flex items-center">
              <div class="flex-shrink-0">
                <i class="fas fa-exclamation-circle text-red-500 text-xl"></i>
              </div>
              <div class="ml-3">
                <p class="text-sm font-medium text-red-800">${data.error || 'An error occurred. Please try again.'}</p>
              </div>
            </div>
          `;
        }
      })
      .catch(error => {
        // Handle error with icon
        submitBtn.disabled = false;
        btnText.textContent = 'Save Changes';
        loadingSpinner.classList.add('hidden');

        formStatus.classList.remove('hidden', 'bg-green-100', 'text-green-700');
        formStatus.classList.add('bg-red-100', 'text-red-700');
        formStatus.innerHTML = `
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <i class="fas fa-wifi-slash text-red-500 text-xl"></i>
            </div>
            <div class="ml-3">
              <p class="text-sm font-medium text-red-800">Network error. Please check your connection and try again.</p>
            </div>
          </div>
        `;
      });
    });
  }
});