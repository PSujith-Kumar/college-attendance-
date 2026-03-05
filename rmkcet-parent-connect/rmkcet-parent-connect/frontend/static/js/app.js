/* ============================================================
   RMKCET Parent Connect – JavaScript
   ============================================================ */

// ---------- Tabs ----------
document.addEventListener('DOMContentLoaded', () => {
  // Initialize all tab groups
  document.querySelectorAll('.tabs').forEach(tabBar => {
    tabBar.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        // Deactivate siblings
        tabBar.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        // Find sibling panels (next siblings of the tab bar's parent)
        const container = tabBar.parentElement;
        container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        const target = document.getElementById('tab-' + tabId);
        if (target) target.classList.add('active');
        // Save active tab in URL hash
        history.replaceState(null, null, '#' + tabId);
      });
    });
  });

  // Restore tab from URL hash
  const hash = window.location.hash.slice(1);
  if (hash) {
    const btn = document.querySelector(`.tab-btn[data-tab="${hash}"]`);
    if (btn) btn.click();
  }

  // Auto-dismiss flash messages
  setTimeout(() => {
    document.querySelectorAll('.flash').forEach(el => {
      el.style.transition = 'opacity .4s, transform .4s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-8px)';
      setTimeout(() => el.remove(), 400);
    });
  }, 5000);

  // Sidebar toggle
  const sidebar = document.getElementById('sidebar');
  const sToggle = document.getElementById('sidebarToggle');
  const mToggle = document.getElementById('mobileToggle');

  if (sToggle) {
    sToggle.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      document.getElementById('mainContent').style.marginLeft =
        sidebar.classList.contains('collapsed') ? '68px' : '';
    });
  }
  if (mToggle) {
    mToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
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
