/* ============================================================
   RMKCET Parent Connect – JavaScript
   ============================================================ */

// ---------- Tabs ----------
document.addEventListener('DOMContentLoaded', () => {
  function activateTab(tabBar, tabId, saveState = true) {
    if (!tabId) return;
    tabBar.querySelectorAll('.tab-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tabId);
    });
    const container = tabBar.parentElement;
    container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    const target = container.querySelector('#tab-' + tabId) || document.getElementById('tab-' + tabId);
    if (target) target.classList.add('active');

    if (saveState && tabBar.id) {
      sessionStorage.setItem('activeTab:' + tabBar.id, tabId);
    }
  }

  // Initialize all tab groups
  document.querySelectorAll('.tabs').forEach(tabBar => {
    tabBar.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activateTab(tabBar, btn.dataset.tab, true);
      });
    });

    // Restore previously active tab without triggering synthetic clicks.
    const fromQuery = new URLSearchParams(window.location.search).get('tab');
    const fromSession = tabBar.id ? sessionStorage.getItem('activeTab:' + tabBar.id) : null;
    const defaultBtn = tabBar.querySelector('.tab-btn.active') || tabBar.querySelector('.tab-btn');
    const defaultTabId = defaultBtn ? defaultBtn.dataset.tab : null;
    const targetTabId = fromQuery || fromSession || defaultTabId;
    activateTab(tabBar, targetTabId, false);
  });

  // Remove stale hash-based behavior from older versions.
  if (window.location.hash) {
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }

  // Auto-dismiss only success/info flashes; keep warning/error visible until user closes.
  setTimeout(() => {
    document.querySelectorAll('.flash-success, .flash-info').forEach(el => {
      el.style.transition = 'opacity .4s, transform .4s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-8px)';
      setTimeout(() => el.remove(), 400);
    });
  }, 5000);

  // Mobile sidebar toggle
  const sidebar = document.getElementById('sidebar');
  const mToggle = document.getElementById('mobileToggle');
  if (mToggle) {
    mToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }

  const themeToggle = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeToggleIcon');
  const savedTheme = localStorage.getItem('theme') || 'light';

  function applyTheme(theme) {
    document.body.classList.toggle('light-theme', theme === 'light');
    if (themeIcon) {
      themeIcon.classList.remove('fa-sun', 'fa-moon');
      themeIcon.classList.add(theme === 'light' ? 'fa-moon' : 'fa-sun');
    }
  }

  applyTheme(savedTheme);

  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const nextTheme = document.body.classList.contains('light-theme') ? 'dark' : 'light';
      localStorage.setItem('theme', nextTheme);
      applyTheme(nextTheme);
    });
  }
});

// ---------- Modals ----------
function openModal(id) {
  const overlay = document.getElementById('modal-' + id);
  if (overlay) overlay.classList.add('open');
}

function closeModal(id) {
  const overlay = document.getElementById('modal-' + id);
  if (overlay) overlay.classList.remove('open');
}

// Close modals on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// Close modals on Escape key
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
  }
});

// ---------- File input display ----------
function showFileName(input, labelId) {
  const label = document.getElementById(labelId);
  if (label && input.files.length > 0) {
    label.textContent = input.files[0].name;
    label.style.display = 'block';
  }
}

// ---------- Collapsible sections ----------
document.querySelectorAll('.collapse-header').forEach(h => {
  h.addEventListener('click', () => {
    const body = h.nextElementSibling;
    if (body && body.classList.contains('collapse-body')) {
      body.classList.toggle('open');
      const icon = h.querySelector('.collapse-icon');
      if (icon) icon.style.transform = body.classList.contains('open') ? 'rotate(180deg)' : '';
    }
  });
});
