from pathlib import Path
import re

path = Path('backend/static/admin.html')
html = path.read_text(encoding='utf-8')

# Idempotency guard.
if 'Visual Content Cards V4' in html:
    raise SystemExit(0)

# Reuse exactly the fixed artwork already embedded on the login page.
match = re.search(r'<div class="auth-brand"><img src="([^"]+)"', html)
if not match:
    raise SystemExit('Login artwork not found')
login_art = match.group(1)

# Header: always use the same fixed artwork as the login page.
html = re.sub(
    r'(<img id="header-club-logo" class="admin-header-logo" src=")[^"]+("[^>]*>)',
    lambda m: m.group(1) + login_art + m.group(2),
    html,
    count=1,
)

# Tenant branding must no longer replace the fixed header artwork.
html = html.replace(
    "[qs('#header-club-logo'), qs('#dashboard-club-logo')].forEach(img => {",
    "[qs('#dashboard-club-logo')].forEach(img => {",
)

# Logout should clear only the user name. The fixed header artwork stays untouched.
html = re.sub(
    r"\n\s*const logo = document\.getElementById\('header-club-logo'\);\n\s*if \(logo\) \{\n\s*logo\.src = APP_LOGO;\n\s*logo\.alt = 'App-Logo';\n\s*logo\.classList\.remove\('no-image'\);\n\s*\}",
    "",
    html,
    count=1,
)

css = r'''

    /* ===== Visual Content Cards V4 ===== */
    .admin-header-logo {
      object-fit:cover !important;
      object-position:center !important;
    }
    .visual-entry-card {
      display:grid !important;
      grid-template-columns:118px minmax(0,1fr);
      gap:13px;
      align-items:start;
      padding:10px !important;
      border:1px solid rgba(255,255,255,.085) !important;
      border-radius:12px !important;
      background:linear-gradient(180deg,rgba(255,255,255,.035),rgba(255,255,255,.018)) !important;
      margin:8px 0 !important;
    }
    .visual-entry-thumb {
      width:118px;
      height:88px;
      border-radius:10px;
      overflow:hidden;
      border:1px solid rgba(255,255,255,.10);
      background:#081118;
      display:flex;
      align-items:center;
      justify-content:center;
      color:#f2d17f;
      font-size:25px;
      font-weight:900;
      box-shadow:0 8px 20px rgba(0,0,0,.22);
    }
    .visual-entry-thumb img {
      width:100%;
      height:100%;
      object-fit:cover;
      display:block;
      margin:0 !important;
      border-radius:0 !important;
    }
    .visual-entry-thumb.is-sujet img,
    .visual-entry-thumb.is-archive img { object-position:center top; }
    .visual-entry-body { min-width:0; }
    .visual-entry-body > h3,
    .visual-entry-body > strong:first-child { margin-top:1px !important; }
    .visual-source-image-hidden { display:none !important; }
    .visual-entry-card .actions { margin-top:7px !important; }
    .visual-entry-card .actions button { padding:6px 9px !important; font-size:11px !important; }
    .visual-entry-card .meta { font-size:11px !important; line-height:1.35 !important; }
    .visual-entry-card h3 { font-size:14px !important; line-height:1.25 !important; }
    .visual-entry-card p { margin:4px 0 !important; }
    #news-list,
    #events-list,
    #content-list {
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(330px,1fr));
      gap:9px;
      align-content:start;
    }
    #news-list .visual-entry-card,
    #events-list .visual-entry-card,
    #content-list .visual-entry-card { margin:0 !important; }
    .visual-entry-empty-label {
      padding:5px 7px;
      border-radius:7px;
      background:rgba(225,184,85,.08);
      color:#f2d17f;
      font-size:10px;
      font-weight:900;
      text-transform:uppercase;
      letter-spacing:.5px;
    }
    @media (max-width:760px) {
      #news-list, #events-list, #content-list { grid-template-columns:1fr; }
      .visual-entry-card { grid-template-columns:86px minmax(0,1fr); gap:10px; }
      .visual-entry-thumb { width:86px; height:68px; }
    }
'''
html = html.replace('</style>', css + '\n</style>', 1)

js = r'''

<script>
/* ===== Visual Content Cards V4 ===== */
(() => {
  const listConfig = {
    'news-list': {kind:'news', glyph:'▤', label:'News'},
    'events-list': {kind:'events', glyph:'◫', label:'Termin'},
    'content-list': {kind:'content', glyph:'▦', label:'Inhalt'},
  };

  function detectKind(entry, fallback) {
    const text = (entry.textContent || '').toLowerCase();
    if (text.includes('sujet')) return {kind:'sujet', glyph:'◉', label:'Sujet'};
    if (text.includes('archiv') || text.includes('vergangen')) return {kind:'archive', glyph:'◉', label:'Archiv'};
    if (text.includes('galerie') || text.includes('foto')) return {kind:'gallery', glyph:'▦', label:'Galerie'};
    if (text.includes('dokument')) return {kind:'documents', glyph:'▱', label:'Dokument'};
    if (text.includes('umfrage')) return {kind:'polls', glyph:'?', label:'Umfrage'};
    if (text.includes('link')) return {kind:'links', glyph:'↗', label:'Link'};
    return fallback;
  }

  function enhanceEntry(entry, fallback) {
    if (!(entry instanceof HTMLElement)) return;
    if (entry.classList.contains('visual-entry-card')) {
      const source = Array.from(entry.querySelectorAll('img')).find(img => !img.closest('.visual-entry-thumb') && !img.classList.contains('visual-source-image-hidden'));
      if (source && !entry.querySelector('.visual-entry-thumb img')) {
        const thumb = entry.querySelector('.visual-entry-thumb');
        if (thumb) {
          thumb.innerHTML = '';
          const clone = source.cloneNode(true);
          clone.removeAttribute('id');
          clone.classList.remove('visual-source-image-hidden');
          thumb.appendChild(clone);
          source.classList.add('visual-source-image-hidden');
        }
      }
      return;
    }

    const info = detectKind(entry, fallback);
    entry.classList.add('visual-entry-card');

    const thumb = document.createElement('div');
    thumb.className = `visual-entry-thumb is-${info.kind}`;
    const source = Array.from(entry.querySelectorAll('img')).find(img => !img.closest('.actions'));
    if (source) {
      const clone = source.cloneNode(true);
      clone.removeAttribute('id');
      thumb.appendChild(clone);
      source.classList.add('visual-source-image-hidden');
    } else {
      const badge = document.createElement('span');
      badge.className = 'visual-entry-empty-label';
      badge.textContent = info.label;
      thumb.appendChild(badge);
    }

    const body = document.createElement('div');
    body.className = 'visual-entry-body';
    while (entry.firstChild) body.appendChild(entry.firstChild);
    entry.appendChild(thumb);
    entry.appendChild(body);
  }

  function enhanceList(id) {
    const root = document.getElementById(id);
    if (!root) return;
    const fallback = listConfig[id];
    root.querySelectorAll(':scope > .entry').forEach(entry => enhanceEntry(entry, fallback));
  }

  function refresh() {
    Object.keys(listConfig).forEach(enhanceList);
  }

  Object.keys(listConfig).forEach(id => {
    const root = document.getElementById(id);
    if (!root) return;
    new MutationObserver(() => requestAnimationFrame(() => enhanceList(id))).observe(root, {
      childList:true,
      subtree:true,
      attributes:true,
      attributeFilter:['src']
    });
  });

  refresh();
  setTimeout(refresh, 350);
  setTimeout(refresh, 1000);
})();
</script>
'''
html = html.replace('</body>', js + '\n</body>', 1)

path.write_text(html, encoding='utf-8')
