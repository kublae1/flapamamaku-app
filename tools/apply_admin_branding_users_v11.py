from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

# Remove the Benutzer / Rollen navigation entry structurally.
text = text.replace('      <button data-panel="users" data-permission="can_manage_users">Benutzer / Rollen</button>\n', '')

css_marker = '/* ===== Branding Structural Cleanup V11 ===== */'
if css_marker not in text:
    css = r'''

    /* ===== Branding Structural Cleanup V11 ===== */
    #system.system-branding-mode > #onboarding-card,
    #system.system-branding-mode > #setup-status-card,
    #system.system-branding-mode #system-admin-status-card,
    #system.system-branding-mode #server-migration-card,
    #system.system-branding-mode #club-backup-card,
    #system.system-branding-mode #system-admin-backup-card {
      display:none !important;
    }
    #system.system-branding-mode > .grid {
      display:block !important;
      width:100% !important;
      max-width:none !important;
    }
    #system.system-branding-mode > .grid > #app-config-form,
    #system.system-branding-mode > .grid > #branding-users-host-v11 {
      display:block !important;
      width:100% !important;
      max-width:none !important;
      max-height:none !important;
      overflow:visible !important;
    }
    #system.system-settings-mode #branding-users-host-v11 {
      display:none !important;
    }
    #branding-users-host-v11 {
      margin-top:18px;
    }
    #branding-users-host-v11 > .branding-users-heading {
      margin-bottom:12px;
      padding:14px 16px;
      border:1px solid rgba(225,184,85,.24);
      border-radius:14px;
      background:rgba(7,16,23,.58);
    }
    #branding-users-host-v11 > .branding-users-heading h2 {
      margin:0 0 4px;
      color:#f3d887;
    }
    #branding-users-host-v11 #users-form,
    #branding-users-host-v11 .card {
      max-height:none !important;
      overflow:visible !important;
    }
    #app-config-form .branding-modules-bottom-v11 {
      margin-top:24px;
      padding-top:18px;
      border-top:1px solid rgba(255,255,255,.12);
    }
    #app-config-form .branding-modules-bottom-v11 > h3 {
      margin-top:0 !important;
    }
'''
    text = text.replace('</style>', css + '\n</style>', 1)

js_marker = '/* ===== Branding Structural Cleanup V11 ===== */'
if text.count(js_marker) < 2:
    js = r'''

<script>
/* ===== Branding Structural Cleanup V11 ===== */
(() => {
  const system = document.getElementById('system');
  const grid = system?.querySelector(':scope > .grid');
  const brandingForm = document.getElementById('app-config-form');
  const usersPanel = document.getElementById('users');
  if (!system || !grid || !brandingForm) return;

  // Safety: remove any remaining users navigation button even if older markup reappears.
  document.querySelectorAll('nav button[data-panel="users"]').forEach(button => button.remove());

  // Move the existing users/roles UI below the branding form without changing its IDs or handlers.
  let usersHost = document.getElementById('branding-users-host-v11');
  if (!usersHost) {
    usersHost = document.createElement('div');
    usersHost.id = 'branding-users-host-v11';
    usersHost.innerHTML = '<div class="branding-users-heading"><h2>Benutzer / Rollen</h2><p class="meta">Benutzerkonten, Rollen und Berechtigungen dieses Vereins.</p></div>';
    brandingForm.insertAdjacentElement('afterend', usersHost);
  }
  if (usersPanel) {
    while (usersPanel.firstChild) usersHost.appendChild(usersPanel.firstChild);
    usersPanel.classList.remove('active');
    usersPanel.style.display = 'none';
  }

  // Move "Module dieses Vereins" to the actual end of the branding form,
  // immediately before the save button.
  const featureList = document.getElementById('club-feature-list');
  if (featureList) {
    let heading = [...brandingForm.querySelectorAll('h3')]
      .find(h => (h.textContent || '').trim() === 'Module dieses Vereins');
    let intro = null;
    if (heading) {
      const next = heading.nextElementSibling;
      if (next && next.tagName === 'P') intro = next;
    }
    let moduleWrap = brandingForm.querySelector('.branding-modules-bottom-v11');
    if (!moduleWrap) {
      moduleWrap = document.createElement('div');
      moduleWrap.className = 'branding-modules-bottom-v11';
    }
    if (heading) moduleWrap.appendChild(heading);
    if (intro) moduleWrap.appendChild(intro);
    moduleWrap.appendChild(featureList);

    const saveRow = [...brandingForm.querySelectorAll(':scope > p')]
      .reverse()
      .find(p => p.querySelector('button[type="submit"]'));
    if (saveRow) brandingForm.insertBefore(moduleWrap, saveRow);
    else brandingForm.appendChild(moduleWrap);
  }

  const brandingButton = document.querySelector('nav button[data-system-target="branding"]');
  const settingsButton = document.getElementById('system-nav');

  const applyBrandingMode = () => {
    system.classList.add('system-branding-mode');
    system.classList.remove('system-settings-mode');
    usersHost.style.removeProperty('display');
    // Explicitly suppress technical cards despite older !important rules.
    ['onboarding-card','setup-status-card','system-admin-status-card','server-migration-card','club-backup-card','system-admin-backup-card']
      .forEach(id => document.getElementById(id)?.style.setProperty('display','none','important'));
  };

  const clearBrandingOverridesForSettings = () => {
    system.classList.add('system-settings-mode');
    system.classList.remove('system-branding-mode');
    usersHost.style.setProperty('display','none','important');
    ['onboarding-card','setup-status-card','system-admin-status-card','server-migration-card','club-backup-card','system-admin-backup-card']
      .forEach(id => document.getElementById(id)?.style.removeProperty('display'));
  };

  brandingButton?.addEventListener('click', () => setTimeout(applyBrandingMode, 0));
  settingsButton?.addEventListener('click', () => setTimeout(clearBrandingOverridesForSettings, 0));

  // If Branding is already active when this script runs, enforce the clean mode immediately.
  if (brandingButton?.classList.contains('active')) applyBrandingMode();
})();
</script>
'''
    text = text.replace('</body>', js + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
print('Applied Branding Structural Cleanup V11')
