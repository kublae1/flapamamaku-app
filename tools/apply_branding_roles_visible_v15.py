from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')
marker = '/* ===== Branding Roles Visible V15 ===== */'
if marker in text:
    raise SystemExit('V15 already applied')

block = r'''
<style>
/* ===== Branding Roles Visible V15 ===== */
#branding-roles-visible-v15 {
  display:none;
  width:100%;
  margin:18px 0;
  padding:16px;
  border:1px solid rgba(225,184,85,.24);
  border-radius:14px;
  background:rgba(7,16,23,.62);
}
#system.system-branding-mode #branding-roles-visible-v15 { display:block !important; }
#branding-roles-visible-v15 h3 { margin:0 0 5px; color:#f3d887; }
#branding-roles-visible-v15 .roles-v15-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
  margin-top:12px;
}
#branding-roles-visible-v15 .role-v15-card {
  padding:12px 13px;
  border:1px solid rgba(255,255,255,.10);
  border-radius:11px;
  background:rgba(255,255,255,.025);
}
#branding-roles-visible-v15 .role-v15-card strong { display:block; margin-bottom:7px; color:#fff; }
#branding-roles-visible-v15 .role-v15-tags { display:flex; flex-wrap:wrap; gap:5px; }
#branding-roles-visible-v15 .role-v15-tag {
  padding:4px 7px;
  border-radius:999px;
  font-size:10px;
  font-weight:800;
  background:rgba(22,135,239,.13);
  border:1px solid rgba(22,135,239,.25);
  color:#a9d4ff;
}
#branding-roles-visible-v15 .role-v15-none { color:var(--muted); font-size:11px; }
@media (max-width:900px) {
  #branding-roles-visible-v15 .roles-v15-grid { grid-template-columns:1fr; }
}
</style>
<script>
(() => {
  const staticRoles = [
    {key:'member', label:'Mitglied'},
    {key:'editor', label:'Redaktion'},
    {key:'board', label:'Vorstand'},
    {key:'club_manager', label:'Vereinsverwaltung'},
  ];
  const permissionLabels = {
    can_news:'News', can_events:'Termine', can_members:'Mitglieder',
    can_documents:'Dokumente', can_photos:'Fotos/Inhalte', can_gallery_upload:'Galerie-Upload',
    can_polls:'Umfragen', can_links:'Links', can_contact:'Kontakt', can_about:'Über uns',
    can_admin_page:'PC-Admin', can_manage_settings:'Verein & Branding', can_manage_users:'Benutzer/Rollen'
  };

  function ensureVisibleHost() {
    const system = document.getElementById('system');
    const brandingForm = document.getElementById('app-config-form');
    if (!system || !brandingForm) return null;
    let box = document.getElementById('branding-roles-visible-v15');
    if (!box) {
      box = document.createElement('section');
      box.id = 'branding-roles-visible-v15';
      box.innerHTML = '<h3>Rollen</h3><p class="meta">Vorhandene Rollen dieses Vereins.</p><div class="roles-v15-grid"></div>';
      const usersHost = document.getElementById('branding-users-host-v11');
      if (usersHost?.parentElement) usersHost.parentElement.insertBefore(box, usersHost);
      else brandingForm.insertAdjacentElement('afterend', box);
    }
    return box;
  }

  function currentRoles() {
    try {
      if (typeof roleDefinitions !== 'undefined' && Array.isArray(roleDefinitions) && roleDefinitions.length) {
        return staticRoles.map(base => roleDefinitions.find(role => role.key === base.key) || base);
      }
    } catch (_) {}
    return staticRoles;
  }

  function render() {
    const box = ensureVisibleHost();
    if (!box) return;
    const grid = box.querySelector('.roles-v15-grid');
    grid.innerHTML = '';
    currentRoles().forEach(role => {
      const card = document.createElement('div');
      card.className = 'role-v15-card';
      const permissions = role.permissions || {};
      const enabled = Object.entries(permissions).filter(([, value]) => value === true);
      const tags = enabled.length
        ? enabled.map(([key]) => `<span class="role-v15-tag">${permissionLabels[key] || key}</span>`).join('')
        : '<span class="role-v15-none">Standardrolle ohne Verwaltungsrechte</span>';
      card.innerHTML = `<strong>${role.label || role.key}</strong><div class="role-v15-tags">${tags}</div>`;
      grid.appendChild(card);
    });
  }

  async function refresh() {
    render();
    if (currentUser?.can_manage_users) {
      try { if (typeof loadRoles === 'function') await loadRoles(); } catch (error) { console.error('Rollen konnten nicht geladen werden:', error); }
      try { if (typeof loadUsers === 'function') await loadUsers(); } catch (error) { console.error('Benutzer konnten nicht geladen werden:', error); }
      render();
    }
  }

  document.querySelectorAll('nav button[data-system-target="branding"]').forEach(button => {
    button.addEventListener('click', () => setTimeout(refresh, 0));
  });

  setTimeout(render, 0);
  setTimeout(render, 600);
})();
</script>
'''

text = text.replace('\n</body>', '\n' + block + '\n</body>')
path.write_text(text, encoding='utf-8')
print('Applied V15 visible roles block')
