// Theme handling
;(function () {
  const savedTheme = localStorage.getItem('theme')
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark)
  document.documentElement.classList.toggle('dark', isDark)
  updateThemeIcons(isDark)
})()

function updateThemeIcons(isDark) {
  const lightIcon = document.getElementById('theme-toggle-light-icon');
  const darkIcon = document.getElementById('theme-toggle-dark-icon');
  if (lightIcon && darkIcon) {
    lightIcon.classList.toggle('hidden', !isDark);
    darkIcon.classList.toggle('hidden', isDark);
  }
}

const themeToggleBtn = document.getElementById('theme-toggle')
if (themeToggleBtn) {
  themeToggleBtn.addEventListener('click', () => {
    const isDark = !document.documentElement.classList.contains('dark')
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem('theme', isDark ? 'dark' : 'light')
    updateThemeIcons(isDark)
  })
}

// Sidebar and dropdown handling
const sidebar = document.getElementById('sidebar')
const sidebarBackdrop = document.getElementById('sidebar-backdrop')
const openSidebarButton = document.getElementById('open-sidebar')
const closeSidebarButton = document.getElementById('close-sidebar')
const addDataButton = document.getElementById('addDataButton')
const addDataMenu = document.getElementById('addDataMenu')
const dropdownArrow = document.getElementById('dropdown-arrow')

// Toggle sidebar
function openSidebar() {
  if (sidebar && sidebarBackdrop) {
    sidebar.classList.remove('-translate-x-full')
    sidebarBackdrop.classList.remove('hidden')
    // Prevent body scrolling when sidebar is open on mobile
    if (window.innerWidth < 768) {
      document.body.classList.add('overflow-hidden')
    }
  }
}

function closeSidebar() {
  if (sidebar && sidebarBackdrop) {
    sidebar.classList.add('-translate-x-full')
    sidebarBackdrop.classList.add('hidden')
    // Restore body scrolling
    document.body.classList.remove('overflow-hidden')
  }
}

if (openSidebarButton) {
  openSidebarButton.addEventListener('click', (e) => {
    e.stopPropagation()
    openSidebar()
  })
}

if (closeSidebarButton) {
  closeSidebarButton.addEventListener('click', () => {
    closeSidebar()
  })
}

if (sidebarBackdrop) {
  sidebarBackdrop.addEventListener('click', () => {
    closeSidebar()
  })
}

// Toggle dropdown
if (addDataButton && addDataMenu && dropdownArrow) {
  addDataButton.addEventListener('click', (e) => {
    e.stopPropagation()
    const isHidden = addDataMenu.classList.toggle('hidden')
    // Rotate arrow when dropdown is toggled
    dropdownArrow.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(180deg)'
  })
}

// Close sidebar and dropdown when clicking outside
document.addEventListener('click', (e) => {
  // Close sidebar if click is outside sidebar and outside the open button
  if (sidebar && !sidebar.contains(e.target) && openSidebarButton && !openSidebarButton.contains(e.target)) {
    // Check if sidebar is currently open before closing
    if (!sidebar.classList.contains('-translate-x-full')) {
        closeSidebar()
    }
  }
  // Close dropdown if click is outside the dropdown button and menu
  if (addDataMenu && !addDataMenu.classList.contains('hidden') && addDataButton && !addDataButton.contains(e.target) && !addDataMenu.contains(e.target)) {
    addDataMenu.classList.add('hidden')
    if (dropdownArrow) {
        dropdownArrow.style.transform = 'rotate(0deg)'
    }
  }
})

// Handle window resize: Ensure body scroll is not locked on larger screens
window.addEventListener('resize', () => {
  if (window.innerWidth >= 768) { // md breakpoint
    document.body.classList.remove('overflow-hidden')
    // Optional: If you want the sidebar to auto-close on resize to desktop view
    // if (sidebar && !sidebar.classList.contains('-translate-x-full')) {
    //   closeSidebar();
    // }
  } else {
      // Re-apply overflow hidden if sidebar is open on mobile view after resize
      if (sidebar && !sidebar.classList.contains('-translate-x-full')) {
          document.body.classList.add('overflow-hidden');
      }
  }
})

// Initial check in case the page loads on a larger screen
if (window.innerWidth >= 768) {
    document.body.classList.remove('overflow-hidden');
}
