from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')
marker = '/* ===== Branding Roles Catalog V14 ===== */'
if marker in text:
    raise SystemExit(0)

patch = r'''
<style>
/* ===== Branding Roles Catalog V14 ===== */
#branding-roles-catalog-v14 {
  margin:16px 0 18px;
  padding:16px;
  border:1px solid rgba(225,184,85,.22);
  border-radius:14px;
  background:rgba(7,16,23,.58);
}
#branding-roles-catalog-v14 h3 { margin:0 0 5px; color:#f3d887; }
#branding-roles-catalog-v14 .roles-catalog-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
  margin-top:12px;
}
#branding-roles-catalog-v14 .role-catalog-card {
  padding:12px 13px;
  border:1px solid rgba(255,255,255,.10);
  border-radius:11px;
  background:rgba(255,255,255,.025);
}
#branding-roles-catalog-v14 .role-catalog-card strong { display:block; color:#fff; margin-bottom:7px; }
#branding-roles-catalog-v14 .role-permission-tags { display:flex; flex-wrap:wrap; gap:5px; }
#branding-roles-catalog-v14 .role-permission-tag {
  display:inline-block;
  padding:4px 7px;
  border-radius:999px;
  font-size:10px;
  font-weight:800;
  background:rgba(22,135,239,.13);
  border:1px solid rgba(22,135,239,.25);
  color:#a9d4ff;
}
#branding-roles-catalog-v14 .role-permission-none { color:var(--muted); font-size:11px; }
@media (max-width:900px) {
  #branding-roles-catalog-v14 .roles-catalog-grid { grid-template-columns:1fr; }
}
</style>
<script>
(() => {
  const permissionLabels = {
    can_news:'News', can_events:'Termine', can_members:'Mitglieder',
    can_documents:'Dokumente', can_photos:'Fotos/Inhalte', can_gallery_upload:'Galerie-Upload',
    can_polls:'Umfragen', can_links:'Links', can_contact:'Kontakt', can_about:'Über uns',
    can_admin_page:'PC-Admin', can_manage_settings:'Verein & Branding', can_manage_users:'Benutzer/Rollen'
  };

  function ensureCatalogHost() {
    const host = document.getElementById('branding-users-host-v11') || document.querySelector('.branding-users-integrated');
    if (!host) return null;
    let catalog = document.getElementById('branding-roles-catalog-v14');
    if (!catalog) {
      catalog = document.createElement('section');
      catalog.id = 'branding-roles-catalog-v14';
      catalog.innerHTML = '<h3>Rollen</h3><p class="meta">Vorhandene Rollen und deren Standardrechte.</p><div class="roles-catalog-grid"></div>';
      const heading = host.querySelector('.branding-users-heading');
      if (heading) heading.insertAdjacentElement('afterend', catalog);
      else host.prepend(catalog);
    }
    return catalog;
  }

  function renderRolesCatalog() {
    const catalog = ensureCatalogHost();
    if (!catalog) return;
    const grid = catalog.querySelector('.roles-catalog-grid');
    const roles = Array.isArray(window.roleDefinitions) ? window.roleDefinitions : (typeof roleDefinitions !== 'undefined' ? roleDefinitions : []);
    grid.innerHTML = '';
    if (!roles.length) {
      grid.innerHTML = '<p class="meta">Rollen werden geladen …</p>';
      return;
    }
    roles.forEach(role => {
      const permissions = role.permissions || {};
      const enabled = Object.entries(permissions).filter(([, value]) => value === true);
      const card = document.createElement('div');
      card.className = 'role-catalog-card';
      const tags = enabled.length
        ? enabled.map(([key]) => `<span class="role-permission-tag">${permissionLabels[key] || key}</span>`).join('')
        : '<span class="role-permission-none">Keine Verwaltungsrechte</span>';
      card.innerHTML = `<strong>${role.label || role.key}</strong><div class="role-permission-tags">${tags}</div>`;
      grid.appendChild(card);
    });
  }

  async function refreshBrandingUsersRoles() {
    if (!currentUser?.can_manage_users) return;
    try { if (typeof loadRoles === 'function') await loadRoles(); } catch (error) { console.error('Rollen konnten nicht geladen werden:', error); }
    try { if (typeof loadUsers === 'function') await loadUsers(); } catch (error) { console.error('Benutzer konnten nicht geladen werden:', error); }
    renderRolesCatalog();
  }

  document.querySelectorAll('nav button[data-system-target="branding"]').forEach(button => {
    button.addEventListener('click', () => setTimeout(refreshBrandingUsersRoles, 0));
  });

  const timer = setInterval(() => {
    if (!currentUser?.can_manage_users) return;
    const roles = (typeof roleDefinitions !== 'undefined' ? roleDefinitions : []);
    if (roles?.length) {
      renderRolesCatalog();
      clearInterval(timer);
    }
  }, 400);
  setTimeout(() => clearInterval(timer), 8000);
})();
</script>
'''

text = text.replace('</body>', patch + '\n</body>', 1)
path.write_text(text, encoding='utf-8')
