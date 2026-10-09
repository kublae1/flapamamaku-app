from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

old_setup = '''  function keepSetupStatusVisible() {
    const status = document.getElementById('setup-status-card');
    if (!status) return;
    status.classList.add('system-branding-visible', 'branding-status-always-open', 'is-open');
    status.classList.remove('hidden');
    status.style.display = 'block';
    status.querySelectorAll('.compact-card-body').forEach(body => body.style.display = 'block');
  }
'''
new_setup = '''  function keepSetupStatusVisible() {
    const status = document.getElementById('setup-status-card');
    if (!status) return;
    if (system.classList.contains('system-branding-mode')) {
      status.classList.remove('system-branding-visible', 'branding-status-always-open', 'is-open');
      status.style.setProperty('display', 'none', 'important');
      return;
    }
    status.classList.add('is-open');
    status.classList.remove('hidden');
    status.style.removeProperty('display');
    status.querySelectorAll('.compact-card-body').forEach(body => body.style.display = 'block');
  }
'''
if old_setup not in text:
    raise SystemExit('V7 setup-status function not found')
text = text.replace(old_setup, new_setup, 1)

old_system = '''  function openAndRefreshStatus() {
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
'''
new_system = '''  function openAndRefreshStatus() {
    if (!statusCard) return;
    if (system.classList.contains('system-branding-mode')) {
      statusCard.classList.remove('is-open');
      statusCard.style.setProperty('display', 'none', 'important');
      return;
    }
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
'''
if old_system not in text:
    raise SystemExit('V8 system-status function not found')
text = text.replace(old_system, new_system, 1)

# Add a final invariant so older CSS cannot re-show technical cards in branding mode.
marker = '</style>\n</head>'
final_css = '''\n<style>\n/* ===== Branding Status Exclusion V13 ===== */\n#system.system-branding-mode > #onboarding-card,\n#system.system-branding-mode > #setup-status-card,\n#system.system-branding-mode #system-admin-status-card,\n#system.system-branding-mode #server-migration-card,\n#system.system-branding-mode #club-backup-card,\n#system.system-branding-mode #system-admin-backup-card {\n  display:none !important;\n}\n</style>\n'''
if 'Branding Status Exclusion V13' not in text:
    if marker not in text:
      raise SystemExit('style insertion marker not found')
    text = text.replace(marker, '</style>' + final_css + '</head>', 1)

path.write_text(text, encoding='utf-8')
print('Applied Branding Status Exclusion V13')
