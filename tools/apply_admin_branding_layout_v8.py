from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')
marker = '/* ===== Branding Settings Repair V8 ===== */'
if marker in text:
    raise SystemExit(0)

style = r'''

    /* ===== Branding Settings Repair V8 ===== */
    #system.system-branding-mode .system-branding-visible.grid,
    #system.system-settings-mode .system-branding-visible.grid {
      display:grid !important;
      grid-template-columns:minmax(0,1fr) !important;
      width:100% !important;
      max-width:none !important;
    }
    #system.system-branding-mode #app-config-form {
      display:block !important;
      width:100% !important;
      max-width:none !important;
      max-height:none !important;
      overflow:visible !important;
    }
    #system.system-settings-mode #app-config-form {
      display:none !important;
    }
    #system #system-admin-status-card {
      width:100% !important;
      max-width:none !important;
      max-height:none !important;
      overflow:visible !important;
      grid-column:1 / -1 !important;
    }
    #system #system-admin-status-card.is-open > .compact-card-body,
    #system #system-admin-status-card .compact-card-body {
      display:block !important;
    }
    #app-config-form .branding-media-grid-v8 {
      display:grid !important;
      grid-template-columns:minmax(0,1fr) minmax(0,1fr) !important;
      gap:18px !important;
      width:100% !important;
      margin:18px 0 !important;
      align-items:start !important;
    }
    #app-config-form .branding-media-card-v8 {
      min-width:0;
      padding:16px;
      border:1px solid rgba(225,184,85,.18);
      border-radius:14px;
      background:rgba(7,16,23,.52);
    }
    #app-config-form .branding-media-card-v8 > :first-child {
      margin-top:0 !important;
    }
    #app-config-form .branding-media-card-v8 #app-logo-image {
      width:min(100%,240px) !important;
      height:auto !important;
      aspect-ratio:1/1 !important;
      object-fit:cover !important;
      margin:0 auto !important;
    }
    #app-config-form .branding-media-card-v8 #app-hero-image {
      width:min(100%,260px) !important;
      height:auto !important;
      max-height:360px !important;
      object-fit:contain !important;
      margin:0 auto !important;
    }
    @media (max-width:900px) {
      #app-config-form .branding-media-grid-v8 {
        grid-template-columns:1fr !important;
      }
    }
'''

script = r'''
<script>
/* ===== Branding Settings Repair V8 ===== */
(() => {
  const system = document.getElementById('system');
  const form = document.getElementById('app-config-form');
  const statusCard = document.getElementById('system-admin-status-card');
  if (!system || !form) return;

  const systemGrid = form.parentElement;

  function moveRangeToCard(start, end, card) {
    if (!start || !end) return false;
    const parent = start.parentNode;
    if (!parent || end.parentNode !== parent) return false;
    let node = start;
    while (node) {
      const next = node.nextSibling;
      card.appendChild(node);
      if (node === end) break;
      node = next;
    }
    return true;
  }

  function rebuildMediaRow() {
    if (form.querySelector('.branding-media-grid-v8')) return;

    const logoInput = form.querySelector('input[name="logo_file"]');
    const heroInput = form.querySelector('input[name="hero_file"]');
    const logoPreview = document.getElementById('app-logo-preview');
    const heroPreview = document.getElementById('app-hero-preview');
    const logoLabel = [...form.querySelectorAll('label')]
      .find(el => el.textContent.trim() === 'Vereinslogo');
    const heroHeading = [...form.querySelectorAll('h3')]
      .find(el => el.textContent.trim().startsWith('Startseite / Hauptbild'));
    if (!logoInput || !heroInput || !logoPreview || !heroPreview || !logoLabel || !heroHeading) return;

    // Remove empty/obsolete media wrappers left by earlier UI-only attempts.
    form.querySelectorAll('.branding-media-grid').forEach(old => {
      if (!old.contains(logoInput) && !old.contains(heroInput)) old.remove();
    });

    const logoCard = document.createElement('div');
    logoCard.className = 'branding-media-card-v8';
    const heroCard = document.createElement('div');
    heroCard.className = 'branding-media-card-v8';
    const row = document.createElement('div');
    row.className = 'branding-media-grid-v8';

    // Insert the new row immediately before the first branding-media control.
    const insertionAnchor = logoLabel.closest('.branding-media-card') || logoLabel;
    const anchorParent = insertionAnchor.parentNode;
    if (!anchorParent) return;
    anchorParent.insertBefore(row, insertionAnchor);
    row.append(logoCard, heroCard);

    // Prefer moving the existing contiguous blocks so labels, help text and buttons stay intact.
    const logoStart = logoLabel;
    const logoEnd = logoPreview;
    if (!moveRangeToCard(logoStart, logoEnd, logoCard)) {
      [logoLabel, logoInput, logoInput.nextElementSibling, logoPreview]
        .filter(Boolean)
        .forEach(node => logoCard.appendChild(node));
    }

    const heroStart = heroHeading;
    const heroEnd = heroPreview;
    if (!moveRangeToCard(heroStart, heroEnd, heroCard)) {
      [heroHeading, heroHeading.nextElementSibling, heroInput, heroInput.nextElementSibling, heroPreview]
        .filter(Boolean)
        .forEach(node => heroCard.appendChild(node));
    }

    // Remove old now-empty wrappers/separators.
    form.querySelectorAll('.branding-media-grid, .branding-media-card').forEach(old => {
      if (!old.querySelector('input, img, button, label, h3')) old.remove();
    });
    form.querySelectorAll('hr').forEach(hr => {
      if (!hr.nextElementSibling || hr.nextElementSibling === row) hr.remove();
    });
  }

  function openAndRefreshStatus() {
    if (!statusCard) return;
    if (currentUser?.can_manage_users === false) return;
    statusCard.classList.remove('hidden');
    statusCard.classList.add('is-open');
    statusCard.style.setProperty('display', 'block', 'important');
    statusCard.style.setProperty('max-height', 'none', 'important');
    statusCard.style.setProperty('overflow', 'visible', 'important');
    statusCard.querySelectorAll('.compact-card-body').forEach(body => {
      body.style.setProperty('display', 'block', 'important');
    });
  }

  async function refreshSystemData() {
    try {
      if (typeof loadSystem === 'function') await loadSystem();
    } catch (error) {
      console.debug('Systemstatus konnte nicht aktualisiert werden', error);
    }
    openAndRefreshStatus();
  }

  function showBranding() {
    system.classList.add('system-branding-mode');
    system.classList.remove('system-settings-mode');
    if (systemGrid) {
      systemGrid.classList.add('system-branding-visible');
      systemGrid.style.setProperty('display', 'grid', 'important');
      systemGrid.style.setProperty('grid-template-columns', 'minmax(0,1fr)', 'important');
      systemGrid.style.setProperty('width', '100%', 'important');
    }
    form.classList.add('system-branding-visible');
    form.style.setProperty('display', 'block', 'important');
    form.style.setProperty('width', '100%', 'important');
    form.style.setProperty('max-width', 'none', 'important');
    system.querySelectorAll('.workspace-pane-hidden').forEach(el => el.classList.remove('workspace-pane-hidden'));
    rebuildMediaRow();
    openAndRefreshStatus();
    void refreshSystemData();
  }

  function showSettings() {
    system.classList.remove('system-branding-mode');
    system.classList.add('system-settings-mode');
    system.querySelectorAll('.workspace-pane-hidden').forEach(el => el.classList.remove('workspace-pane-hidden'));
    if (systemGrid) {
      systemGrid.classList.add('system-branding-visible');
      systemGrid.style.setProperty('display', 'grid', 'important');
      systemGrid.style.setProperty('grid-template-columns', 'minmax(0,1fr)', 'important');
      systemGrid.style.setProperty('width', '100%', 'important');
    }
    form.style.setProperty('display', 'none', 'important');
    openAndRefreshStatus();
    void refreshSystemData();
  }

  // Keep status before the branding form so it is immediately visible in both modes.
  if (systemGrid && statusCard && statusCard.parentElement === systemGrid) {
    systemGrid.insertBefore(statusCard, form);
  }

  document.querySelectorAll('nav button[data-system-target="branding"]').forEach(button => {
    button.addEventListener('click', () => setTimeout(showBranding, 0));
  });
  document.getElementById('system-nav')?.addEventListener('click', () => setTimeout(showSettings, 0));
  document.getElementById('system-refresh')?.addEventListener('click', () => setTimeout(openAndRefreshStatus, 0));

  // Repair the DOM once after all prior UI scripts have initialized.
  setTimeout(() => {
    rebuildMediaRow();
    openAndRefreshStatus();
  }, 250);
})();
</script>
'''

text = text.replace('</style>', style + '\n</style>', 1)
text = text.replace('</body>', script + '\n</body>', 1)
path.write_text(text, encoding='utf-8')
