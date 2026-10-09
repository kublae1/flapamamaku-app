from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

# 1) Render real images already present in existing data for News and Members.
old = '''      ${resource === "news" && item.image_url ? `<div class="meta">Foto gespeichert</div>` : ""}
      ${resource === "members" && item.photo_url ? '<div class="meta">Mitgliederfoto gespeichert</div>' : ""}
'''
new = '''      ${resource === "news" && item.image_url ? `<img class="visual-source-media" src="${cacheBustUrl(item.image_url)}" alt="News-Vorschaubild" loading="lazy">` : ""}
      ${resource === "members" && item.photo_url ? `<img class="visual-source-media visual-member-photo" src="${cacheBustUrl(item.photo_url)}" alt="Mitgliederfoto" loading="lazy">` : ""}
'''
if old not in text:
    raise SystemExit('generic media marker not found')
text = text.replace(old, new, 1)

# 2) Render first stored image for content entries (Sujet, Archiv, Galerie, etc.).
old = '''      ${item.image_urls?.length ? `<div class="meta">✓ ${item.image_urls.length} Bilder gespeichert</div>` : '<div class="meta">Keine Bilder</div>'}
'''
new = '''      ${item.image_urls?.length ? `<img class="visual-source-media" src="${cacheBustUrl(item.image_urls[0])}" alt="${contentLabels[item.section] || item.section} Vorschaubild" loading="lazy"><div class="meta">✓ ${item.image_urls.length} Bilder gespeichert</div>` : '<div class="meta">Keine Bilder</div>'}
'''
if old not in text:
    raise SystemExit('content media marker not found')
text = text.replace(old, new, 1)

# 3) Extend visual cards to Members and style portraits.
text = text.replace("    'content-list': {kind:'content', glyph:'▦', label:'Inhalt'},\n", "    'content-list': {kind:'content', glyph:'▦', label:'Inhalt'},\n    'members-list': {kind:'members', glyph:'●', label:'Mitglied'},\n", 1)
text = text.replace('''    #news-list,\n    #events-list,\n    #content-list {\n''', '''    #news-list,\n    #events-list,\n    #content-list,\n    #members-list {\n''', 1)
text = text.replace('''    #news-list .visual-entry-card,\n    #events-list .visual-entry-card,\n    #content-list .visual-entry-card { margin:0 !important; }\n''', '''    #news-list .visual-entry-card,\n    #events-list .visual-entry-card,\n    #content-list .visual-entry-card,\n    #members-list .visual-entry-card { margin:0 !important; }\n''', 1)
text = text.replace('''      #news-list, #events-list, #content-list { grid-template-columns:1fr; }\n''', '''      #news-list, #events-list, #content-list, #members-list { grid-template-columns:1fr; }\n''', 1)

css = r'''

    /* ===== Visual Media V5 ===== */
    .visual-source-media { max-width:100%; height:auto; display:block; border-radius:10px; }
    .visual-entry-thumb.is-members { width:82px; height:82px; border-radius:50%; }
    .visual-entry-thumb.is-members img { object-fit:cover; object-position:center; }
    #members-list { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:9px; align-content:start; }
    #members-list .visual-entry-card { grid-template-columns:82px minmax(0,1fr); align-items:center; }
    #members-list .visual-entry-body { align-self:center; }
    #system.system-branding-mode > * { display:none !important; }
    #system.system-branding-mode .system-branding-visible { display:block !important; }
    #system.system-branding-mode .system-branding-visible.grid { display:grid !important; }
    #system.system-settings-mode .system-branding-visible { display:none !important; }
'''
if '/* ===== Visual Media V5 ===== */' not in text:
    text = text.replace('</style>', css + '\n</style>', 1)

js = r'''
<script>
/* ===== System Branding Split V5 ===== */
(() => {
  const system = document.getElementById('system');
  const appForm = document.getElementById('app-config-form');
  if (!system || !appForm) return;

  const brandingGrid = appForm.parentElement;
  if (brandingGrid) brandingGrid.classList.add('system-branding-visible');
  appForm.classList.add('system-branding-visible');

  function setMode(mode) {
    system.classList.toggle('system-branding-mode', mode === 'branding');
    system.classList.toggle('system-settings-mode', mode !== 'branding');
    if (mode === 'branding') {
      if (brandingGrid) brandingGrid.classList.add('system-branding-visible');
      appForm.classList.add('system-branding-visible');
      setTimeout(() => appForm.scrollIntoView({block:'start'}), 0);
    }
  }

  document.querySelectorAll('nav button[data-system-target="branding"]').forEach(btn => {
    btn.addEventListener('click', () => setMode('branding'));
  });
  document.getElementById('system-nav')?.addEventListener('click', () => setMode('settings'));
  setMode('settings');
})();
</script>
'''
if '/* ===== System Branding Split V5 ===== */' not in text:
    text = text.replace('</body>', js + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
print('Applied visual media thumbnails, member portraits and branding/settings split.')
