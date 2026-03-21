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
  const sidebarClose = document.getElementById('sidebarClose');

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
  }

  if (mToggle) {
    mToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }

  if (sidebarClose) {
    sidebarClose.addEventListener('click', closeSidebar);
  }

  if (sidebar) {
    sidebar.querySelectorAll('.nav-link').forEach((link) => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 768) {
          closeSidebar();
        }
      });
    });
  }

  document.addEventListener('click', (e) => {
    if (!sidebar || window.innerWidth > 768) return;
    const clickedInsideSidebar = sidebar.contains(e.target);
    const clickedToggle = mToggle && mToggle.contains(e.target);
    if (sidebar.classList.contains('open') && !clickedInsideSidebar && !clickedToggle) {
      closeSidebar();
    }
  });

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

// ---------- User Table Filtering & Sorting ----------
const USER_SUGGESTION_LIMIT = 5;
const LARGE_USER_TABLE_THRESHOLD = 50;

function isUserTableLarge(rows) {
  return (rows?.length || 0) > LARGE_USER_TABLE_THRESHOLD;
}

function refreshUserSearchSuggestions(searchTerm, allRows) {
  const suggestionsList = document.getElementById('userSearchSuggestions');
  if (!suggestionsList) return;

  const q = String(searchTerm || '').trim().toLowerCase();
  if (!q) {
    suggestionsList.style.display = 'none';
    suggestionsList.innerHTML = '';
    return;
  }

  const suggestions = Array.from(allRows || [])
    .map(row => String(row.dataset.userNameDisplay || '').trim())
    .filter(Boolean)
    .filter((name, index, list) => list.findIndex(item => item.toLowerCase() === name.toLowerCase()) === index)
    .filter(name => name.toLowerCase().includes(q))
    .slice(0, USER_SUGGESTION_LIMIT);

  suggestionsList.innerHTML = suggestions
    .map(name => `<li onclick="document.getElementById('userSearchBox').value='${name.replace(/'/g, "\\'")}';filterUserTable()">${name}</li>`)
    .join('');
  suggestionsList.style.display = suggestions.length > 0 ? 'block' : 'none';
}

function filterUserTable() {
  const searchBox = document.getElementById('userSearchBox');
  const filterDept = document.getElementById('filterDepartment');
  const filterRole = document.getElementById('filterRole');
  const filterStatus = document.getElementById('filterStatus');
  
  if (!searchBox) return;
  
  const searchTerm = searchBox.value.toLowerCase();
  const selectedDept = filterDept?.value || '';
  const selectedRole = filterRole?.value || '';
  const selectedStatus = filterStatus?.value || '';
  
  const rows = document.querySelectorAll('#userTable tbody .user-row');
  const hasLargeDataset = isUserTableLarge(rows);
  const hasAnyFilter = Boolean(searchTerm || selectedDept || selectedRole || selectedStatus);
  let visibleCount = 0;
  
  rows.forEach(row => {
    let visible = true;

    if (hasLargeDataset && !hasAnyFilter) {
      visible = false;
    }
    
    if (searchTerm) {
      const name = row.dataset.userName || '';
      visible = name.includes(searchTerm);
    }
    
    if (visible && selectedDept) {
      visible = (row.dataset.userDept || '').toLowerCase() === selectedDept.toLowerCase();
    }
    
    if (visible && selectedRole) {
      visible = (row.dataset.userRole || '') === selectedRole;
    }
    
    if (visible && selectedStatus) {
      visible = (row.dataset.userStatus || '') === selectedStatus;
    }
    
    row.style.display = visible ? '' : 'none';
    if (visible) visibleCount++;
  });

  if (searchBox) refreshUserSearchSuggestions(searchTerm, rows);
}

function sortUserTable() {
  const sortBy = document.getElementById('userSortBy')?.value || 'name_asc';
  const tbody = document.querySelector('#userTable tbody');
  if (!tbody) return;
  const rows = Array.from(tbody.querySelectorAll('.user-row'));
  
  rows.sort((a, b) => {
    if (sortBy === 'date_added') {
      const aDate = Date.parse(a.dataset.userCreated || '') || 0;
      const bDate = Date.parse(b.dataset.userCreated || '') || 0;
      return bDate - aDate;
    }
    const aName = a.dataset.userName || '';
    const bName = b.dataset.userName || '';
    return aName.localeCompare(bName);
  });
  
  rows.forEach(row => tbody.appendChild(row));
}

function toggleUserFilterTray() {
  const tray = document.getElementById('userFilterTray');
  if (!tray) return;
  tray.style.display = tray.style.display === 'none' ? 'flex' : 'none';
}

// Add event listeners for search suggestions click elsewhere to hide
document.addEventListener('click', e => {
  if (e.target.id !== 'userSearchBox') {
    const suggestionsList = document.getElementById('userSearchSuggestions');
    if (suggestionsList) suggestionsList.style.display = 'none';
  }
});

function initializeUserTableState() {
  const rows = document.querySelectorAll('#userTable tbody .user-row');
  if (!rows.length) return;
  sortUserTable();
  filterUserTable();
}

// Chief admin password reset modal
function openPasswordResetModal() {
  // Determine if user is chief admin or system admin based on visible button
  const headerActions = document.querySelector('.header-actions');
  const isCorePasswordBtn = headerActions?.querySelector('a[href*="tab=config"]') !== null;
  const isChiefCredentialBtn = headerActions?.querySelector('button[onclick*="openPasswordResetModal"]') !== null;
  
  if (isChiefCredentialBtn && !isCorePasswordBtn) {
    // Chief admin role - open credential reset for counselors
    openModal('chief-credential-reset');
    initializeChiefResetCounselors();
  } else {
    // Regular user role - open own password change
    openModal('password-reset');
  }
}

// Show/hide password input
function togglePasswordInput(inputId, iconId) {
  const input = document.getElementById(inputId);
  const icon = document.getElementById(iconId);
  if (!input) return;
  
  if (input.type === 'password') {
    input.type = 'text';
    icon.classList.remove('fa-eye');
    icon.classList.add('fa-eye-slash');
  } else {
    input.type = 'password';
    icon.classList.remove('fa-eye-slash');
    icon.classList.add('fa-eye');
  }
}

// Chief Admin Credential Reset
let CHIEF_RESET_COUNSELORS = [];

function initializeChiefResetCounselors() {
  // Fetch scoped counselors from the API
  fetch('/api/chief-admin/scoped-counselors')
    .then(r => {
      if (!r.ok) throw new Error('Failed to fetch counselors');
      return r.json();
    })
    .then(data => {
      CHIEF_RESET_COUNSELORS = Array.isArray(data) ? data : [];
    })
    .catch(e => {
      console.error('Error fetching scoped counselors:', e);
      CHIEF_RESET_COUNSELORS = [];
    });
  
  // Clear previous search
  const searchInput = document.getElementById('chiefResetSearch');
  if (searchInput) {
    searchInput.value = '';
    setTimeout(() => searchInput.focus(), 100);
  }
  const selectedEmail = document.getElementById('chiefResetSelectedEmail');
  if (selectedEmail) selectedEmail.value = '';
  const pickedText = document.getElementById('chiefResetPicked');
  if (pickedText) pickedText.textContent = '';
}

function renderChiefResetSuggestions() {
  const input = document.getElementById('chiefResetSearch');
  const panel = document.getElementById('chiefResetSuggestions');
  const selectedEmail = document.getElementById('chiefResetSelectedEmail');
  const pickedText = document.getElementById('chiefResetPicked');
  
  if (!input || !panel || !selectedEmail || !pickedText) return;

  const q = (input.value || '').trim().toLowerCase();
  if (!q) {
    panel.style.display = 'none';
    selectedEmail.value = '';
    pickedText.textContent = '';
    return;
  }

  const matches = CHIEF_RESET_COUNSELORS
    .filter(u => `${u.name} ${u.email} ${u.department}`.toLowerCase().includes(q))
    .slice(0, 20);

  if (!matches.length) {
    panel.style.display = 'block';
    panel.innerHTML = '<div style="padding:10px 12px;color:var(--text-dim);font-size:.85rem;">No matching counselors in your scope.</div>';
    selectedEmail.value = '';
    pickedText.textContent = '';
    return;
  }

  panel.style.display = 'block';
  panel.innerHTML = matches.map((u) => {
    const label = `${u.name} (${u.email}) - ${u.department} Y${u.year_level}`;
    return `<button type="button" class="btn btn-outline btn-sm" style="display:block;width:100%;text-align:left;border:none;border-bottom:1px solid var(--border-light);border-radius:0;padding:10px 12px;cursor:pointer;" data-user-email="${u.email}" data-user-label="${label.replace(/"/g, '&quot;')}">${escapeHtmlInner(label)}</button>`;
  }).join('');

  // Attach click handlers to suggestion buttons
  panel.querySelectorAll('button[data-user-email]').forEach((btn) => {
    btn.addEventListener('mousedown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const email = btn.getAttribute('data-user-email');
      const label = btn.getAttribute('data-user-label');
      chooseChiefResetUser(email, label);
    });
  });

  // Auto-pick exact email match
  const exact = matches.find(u => u.email.toLowerCase() === q);
  if (exact) {
    const label = `${exact.name} (${exact.email}) - ${exact.department} Y${exact.year_level}`;
    chooseChiefResetUser(exact.email, label, true);
  } else {
    selectedEmail.value = '';
    pickedText.textContent = '';
  }
}

function escapeHtmlInner(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function chooseChiefResetUser(email, label, keepOpen) {
  const input = document.getElementById('chiefResetSearch');
  const panel = document.getElementById('chiefResetSuggestions');
  const selectedEmail = document.getElementById('chiefResetSelectedEmail');
  const pickedText = document.getElementById('chiefResetPicked');
  
  if (!input || !panel || !selectedEmail || !pickedText) return;

  input.value = label;
  selectedEmail.value = email;
  pickedText.textContent = `Selected: ${label}`;
  if (!keepOpen) panel.style.display = 'none';
}

function validateChiefResetSelection() {
  const selectedEmail = document.getElementById('chiefResetSelectedEmail');
  const newPwd = document.getElementById('chiefResetNewPassword');
  const confirmPwd = document.getElementById('chiefResetConfirmPassword');
  
  if (!selectedEmail || !selectedEmail.value) {
    alert('Please select a counselor from the suggested list.');
    return false;
  }
  
  if (!newPwd || !confirmPwd || newPwd.value !== confirmPwd.value) {
    alert('Passwords do not match.');
    return false;
  }
  
  if (newPwd.value.length < 6) {
    alert('Password must be at least 6 characters.');
    return false;
  }
  
  return true;
}

// Chief Admin Department-Year Assignment
const chiefScopeState = {};

function getChiefScopeModuleRefs(contextKey = 'create') {
  const suffix = contextKey === 'create' ? '' : `-${contextKey}`;
  return {
    deptInput: document.getElementById(`chiefDeptSelect${suffix}`),
    deptOptions: document.getElementById(`chiefDeptSuggestions${suffix}`),
    yearOptions: document.getElementById(`chiefYearOptions${suffix}`),
    addBtn: document.getElementById(`addChiefScopeBtn${suffix}`),
    scopesWrap: document.getElementById(`chiefScopesList${suffix}`),
    selectedScopes: document.getElementById(`selectedChiefScopes${suffix}`),
  };
}

function initializeChiefScopeModule(contextKey = 'create', initialScopes = []) {
  if (!chiefScopeState[contextKey]) {
    chiefScopeState[contextKey] = { byDepartment: {} };
  }

  const state = chiefScopeState[contextKey];
  state.byDepartment = {};

  (initialScopes || []).forEach((scopeKey) => {
    const [depRaw, yearRaw] = String(scopeKey || '').split('::');
    const dep = String(depRaw || '').trim().toUpperCase();
    const year = Number.parseInt(yearRaw, 10);
    if (!dep || ![1, 2, 3, 4].includes(year)) return;
    if (!state.byDepartment[dep]) state.byDepartment[dep] = [];
    if (!state.byDepartment[dep].includes(year)) state.byDepartment[dep].push(year);
  });

  renderChiefDepartmentOptions(contextKey);
  displayChiefScopes(contextKey);
  updateChiefYearOptions(contextKey);
}

function renderChiefDepartmentOptions(contextKey = 'create') {
  const { deptOptions, deptInput } = getChiefScopeModuleRefs(contextKey);
  if (!deptOptions) return;

  const state = chiefScopeState[contextKey] || { byDepartment: {} };
  const selectedDepartments = new Set(Object.keys(state.byDepartment));
  const allOptions = Array.from(deptOptions.querySelectorAll('option'));

  allOptions.forEach((opt) => {
    const depCode = String(opt.value || '').trim().toUpperCase();
    if (!depCode) return;
    opt.disabled = selectedDepartments.has(depCode);
  });

  if (deptInput) {
    const depCode = String(deptInput.value || '').trim().toUpperCase();
    if (selectedDepartments.has(depCode)) {
      deptInput.value = '';
    }
  }
}

function updateChiefYearOptions(contextKey = 'create') {
  const { deptInput, yearOptions, addBtn } = getChiefScopeModuleRefs(contextKey);
  if (!deptInput || !yearOptions || !addBtn) return;

  const state = chiefScopeState[contextKey] || { byDepartment: {} };
  const selectedDept = String(deptInput.value || '').trim().toUpperCase();
  const existingYears = state.byDepartment[selectedDept] || [];

  if (!selectedDept) {
    yearOptions.innerHTML = '<span style="font-size:.82rem;color:var(--text-dim);">Select department first</span>';
    addBtn.disabled = true;
    return;
  }

  if (existingYears.length > 0) {
    yearOptions.innerHTML = '<span style="font-size:.82rem;color:var(--text-dim);">Department already assigned. Remove it from the list to reassign.</span>';
    addBtn.disabled = true;
    return;
  }

  let html = '';
  for (let yr = 1; yr <= 4; yr++) {
    html += `
      <label style="display:flex;align-items:center;gap:6px;font-size:.84rem;">
        <input type="checkbox" id="chiefYear${yr}-${contextKey}" value="${yr}">
        Year ${yr}
      </label>
    `;
  }

  yearOptions.innerHTML = html;
  addBtn.disabled = false;
}

function addChiefScope(contextKey = 'create') {
  const { deptInput } = getChiefScopeModuleRefs(contextKey);
  if (!deptInput) return;

  const selectedDept = String(deptInput.value || '').trim().toUpperCase();
  if (!selectedDept) {
    alert('Please select a department first.');
    return;
  }

  const selectedYears = [];
  for (let yr = 1; yr <= 4; yr++) {
    const checkbox = document.getElementById(`chiefYear${yr}-${contextKey}`);
    if (checkbox && checkbox.checked) selectedYears.push(yr);
  }

  if (selectedYears.length === 0) {
    alert('Please select at least one year.');
    return;
  }

  if (!chiefScopeState[contextKey]) {
    chiefScopeState[contextKey] = { byDepartment: {} };
  }

  chiefScopeState[contextKey].byDepartment[selectedDept] = selectedYears.sort((a, b) => a - b);

  deptInput.value = '';
  renderChiefDepartmentOptions(contextKey);
  displayChiefScopes(contextKey);
  updateChiefYearOptions(contextKey);
}

function displayChiefScopes(contextKey = 'create') {
  const { scopesWrap, selectedScopes } = getChiefScopeModuleRefs(contextKey);
  if (!scopesWrap || !selectedScopes) return;

  const state = chiefScopeState[contextKey] || { byDepartment: {} };
  const departments = Object.keys(state.byDepartment).sort((a, b) => a.localeCompare(b));

  if (departments.length === 0) {
    scopesWrap.style.display = 'none';
    selectedScopes.innerHTML = '';
    return;
  }

  let html = '';
  departments.forEach((dep) => {
    const years = (state.byDepartment[dep] || []).slice().sort((a, b) => a - b);
    const yearText = years.join(', ');
    const hiddenInputs = years.map((y) => `<input type="hidden" name="chief_scopes" value="${dep}::${y}">`).join('');

    html += `
      <div style="background:rgba(102,126,234,.15);padding:8px 12px;border-radius:16px;font-size:.82rem;display:flex;align-items:center;gap:8px;border:1px solid rgba(102,126,234,.3);">
        <span><strong>${dep}</strong>: ${yearText}</span>
        <button type="button" class="btn btn-sm" style="padding:2px 6px;background:none;border:none;color:var(--text-dim);cursor:pointer;font-size:.8rem;" onclick="removeChiefScope('${contextKey}','${dep}')">
          <i class="fas fa-times"></i>
        </button>
        ${hiddenInputs}
      </div>
    `;
  });

  selectedScopes.innerHTML = html;
  scopesWrap.style.display = 'block';
}

function removeChiefScope(contextKey = 'create', department = '') {
  const dep = String(department || '').trim().toUpperCase();
  if (!chiefScopeState[contextKey] || !dep) return;

  delete chiefScopeState[contextKey].byDepartment[dep];
  renderChiefDepartmentOptions(contextKey);
  displayChiefScopes(contextKey);
  updateChiefYearOptions(contextKey);
}

function bootstrapChiefScopeModules() {
  initializeChiefScopeModule('create', []);

  document.querySelectorAll('.chief-scope-edit-module').forEach((moduleEl) => {
    const key = String(moduleEl.dataset.chiefScopeKey || '').trim();
    if (!key) return;

    let scopes = [];
    try {
      scopes = JSON.parse(moduleEl.dataset.chiefScopes || '[]');
    } catch (e) {
      scopes = [];
    }

    initializeChiefScopeModule(key, scopes);
  });
}

// User role form visibility toggle
function toggleCreateUserFields() {
  const roleSelect = document.getElementById('createUserRole');
  const chiefWrap = document.getElementById('createUserChiefScopeWrap');
  const counselorRow = document.getElementById('createUserCounselorRow');
  const counselorCapacityRow = document.getElementById('createUserCounselorCapacityRow');
  const uploadPermissionWrap = document.getElementById('createUserUploadPermissionWrap');
  const studentUploadWrap = document.getElementById('createUserStudentUploadWrap');
  
  if (!roleSelect) return;
  
  const role = roleSelect.value;
  
  if (chiefWrap) chiefWrap.style.display = role === 'chief_admin' ? 'block' : 'none';
  if (counselorRow) counselorRow.style.display = role === 'counselor' ? 'grid' : 'none';
  if (counselorCapacityRow) counselorCapacityRow.style.display = role === 'counselor' ? 'grid' : 'none';
  if (uploadPermissionWrap) uploadPermissionWrap.style.display = role === 'counselor' ? 'flex' : 'none';
  if (studentUploadWrap) studentUploadWrap.style.display = role === 'counselor' ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', () => {
  toggleCreateUserFields();
  bootstrapChiefScopeModules();
  initializeUserTableState();
});

// Open test view modal from data attribute
function openTestViewModalFromButton(btn) {
  const testId = btn.dataset.testId;
  if (testId) {
    openModal(`test-view-${testId}`);
    // Load test details (optional - if needed for dynamic loading)
  }
}
