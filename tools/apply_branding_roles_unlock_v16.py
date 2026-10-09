from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')
marker = '/* ===== Branding Roles Unlock V16 ===== */'
if marker in text:
    raise SystemExit('V16 already applied')

insert = r'''
<style>
/* ===== Branding Roles Unlock V16 ===== */
/* Re-enable the original users/roles UI inside Verein & Branding. */
#system.system-branding-mode #branding-users-host-v11 {
  display:block !important;
  visibility:visible !important;
  opacity:1 !important;
  width:100% !important;
  max-width:none !important;
  max-height:none !important;
  overflow:visible !important;
}
#system.system-branding-mode #branding-users-host-v11 .branding-users-heading,
#system.system-branding-mode #branding-users-host-v11 #users-form,
#system.system-branding-mode #branding-users-host-v11 #users-list,
#system.system-branding-mode #branding-users-host-v11 .card,
#system.system-branding-mode #branding-users-host-v11 .grid {
  display:block !important;
  visibility:visible !important;
  opacity:1 !important;
  max-height:none !important;
  overflow:visible !important;
}
#system.system-branding-mode #branding-users-host-v11 #users-form label,
#system.system-branding-mode #branding-users-host-v11 #users-form select[name="role_key"] {
  display:block !important;
  visibility:visible !important;
}
#system.system-branding-mode #branding-users-host-v11 #users-form select[name="role_key"] {
  width:100% !important;
  min-height:42px !important;
}
#system.system-branding-mode #branding-roles-visible-v15,
#system.system-branding-mode #branding-roles-catalog-v14 {
  display:block !important;
  visibility:visible !important;
  opacity:1 !important;
}
/* Keep the integrated block hidden in Einstellungen. */
#system.system-settings-mode #branding-users-host-v11,
#system.system-settings-mode #branding-roles-visible-v15,
#system.system-settings-mode #branding-roles-catalog-v14 {
  display:none !important;
}
</style>
<script>
(() => {
  async function unlockRoles() {
    const system = document.getElementById('system');
    if (!system?.classList.contains('system-branding-mode')) return;
    const host = document.getElementById('branding-users-host-v11');
    if (host) {
      host.style.setProperty('display','block','important');
      host.style.setProperty('visibility','visible','important');
      host.style.setProperty('opacity','1','important');
      host.style.setProperty('max-height','none','important');
      host.style.setProperty('overflow','visible','important');
    }
    const usersForm = document.getElementById('users-form');
    if (usersForm) {
      usersForm.style.setProperty('display','block','important');
      usersForm.style.setProperty('visibility','visible','important');
      usersForm.style.setProperty('max-height','none','important');
      usersForm.style.setProperty('overflow','visible','important');
    }
    try { if (typeof loadRoles === 'function') await loadRoles(); } catch (e) { console.error('Rollen konnten nicht geladen werden', e); }
    try { if (typeof loadUsers === 'function') await loadUsers(); } catch (e) { console.error('Benutzer konnten nicht geladen werden', e); }
  }

  document.querySelectorAll('nav button[data-system-target="branding"]').forEach(button => {
    button.addEventListener('click', () => {
      setTimeout(unlockRoles, 0);
      setTimeout(unlockRoles, 300);
    });
  });
  setTimeout(unlockRoles, 600);
})();
</script>
'''

text = text.replace('\n</body>\n</html>', insert + '\n</body>\n</html>')
path.write_text(text, encoding='utf-8')
print('Applied Branding Roles Unlock V16')
