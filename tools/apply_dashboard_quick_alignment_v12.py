from pathlib import Path

p = Path('backend/static/admin.html')
s = p.read_text(encoding='utf-8')

old_stats = '''        <div class="dash-stats">
          <div class="dash-stat"><div class="dash-stat-icon">●</div><div><strong id="dash-members-count">–</strong><span>Mitglieder</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">▣</div><div><strong id="dash-events-count">–</strong><span>nächste Termine</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">?</div><div><strong id="dash-polls-count">–</strong><span>aktive Umfragen</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">▧</div><div><strong id="dash-gallery-count">–</strong><span>Galerie-Inhalte</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">▱</div><div><strong id="dash-documents-count">–</strong><span>Dokumente</span></div></div>
        </div>'''
new_stats = '''        <div class="dash-stats">
          <div class="dash-stat" data-dash-category="news"><div class="dash-stat-icon">▤</div><div><strong id="dash-news-count">–</strong><span>News</span></div></div>
          <div class="dash-stat" data-dash-category="events"><div class="dash-stat-icon">▣</div><div><strong id="dash-events-count">–</strong><span>nächste Termine</span></div></div>
          <div class="dash-stat" data-dash-category="members"><div class="dash-stat-icon">●</div><div><strong id="dash-members-count">–</strong><span>Mitglieder</span></div></div>
          <div class="dash-stat" data-dash-category="polls"><div class="dash-stat-icon">?</div><div><strong id="dash-polls-count">–</strong><span>aktive Umfragen</span></div></div>
          <div class="dash-stat" data-dash-category="gallery"><div class="dash-stat-icon">▧</div><div><strong id="dash-gallery-count">–</strong><span>Galerie-Inhalte</span></div></div>
          <div class="dash-stat" data-dash-category="documents"><div class="dash-stat-icon">▱</div><div><strong id="dash-documents-count">–</strong><span>Dokumente</span></div></div>
        </div>'''
if old_stats not in s:
    raise SystemExit('dashboard stats block not found')
s = s.replace(old_stats, new_stats, 1)

old_quick = '''          <div class="dash-quick-grid">
            <button class="dash-action" type="button" data-quick-panel="news" data-quick-new="news-new-button">News erstellen</button>
            <button class="dash-action" type="button" data-quick-panel="events">Termin erstellen</button>
            <button class="dash-action" type="button" data-quick-panel="members" data-quick-new="member-new-button">Mitglied hinzufügen</button>
            <button class="dash-action" type="button" data-quick-panel="content" data-quick-section="gallery">Bilder hochladen</button>
            <button class="dash-action" type="button" data-quick-panel="content" data-quick-section="documents">Dokument hochladen</button>
            <button class="dash-action" type="button" data-quick-panel="content" data-quick-section="polls">Umfrage erstellen</button>
          </div>'''
new_quick = '''          <div class="dash-quick-grid">
            <button class="dash-action" type="button" data-dash-category="news" data-quick-panel="news" data-quick-new="news-new-button">News erstellen</button>
            <button class="dash-action" type="button" data-dash-category="events" data-quick-panel="events">Termin erstellen</button>
            <button class="dash-action" type="button" data-dash-category="members" data-quick-panel="members" data-quick-new="member-new-button">Mitglied hinzufügen</button>
            <button class="dash-action" type="button" data-dash-category="polls" data-quick-panel="content" data-quick-section="polls">Umfrage erstellen</button>
            <button class="dash-action" type="button" data-dash-category="gallery" data-quick-panel="content" data-quick-section="gallery">Bilder hochladen</button>
            <button class="dash-action" type="button" data-dash-category="documents" data-quick-panel="content" data-quick-section="documents">Dokument hochladen</button>
          </div>'''
if old_quick not in s:
    raise SystemExit('dashboard quick block not found')
s = s.replace(old_quick, new_quick, 1)

# Append final CSS overrides so old nth-child colors cannot create mismatches.
css = '''\n<style>\n/* ===== Dashboard Pair Alignment V12 ===== */\n.dash-stats { grid-template-columns:repeat(6,minmax(0,1fr)) !important; }\n.dash-stat[data-dash-category="news"] .dash-stat-icon,\n.dash-action[data-dash-category="news"] { background:var(--admin-cyan) !important; }\n.dash-stat[data-dash-category="events"] .dash-stat-icon,\n.dash-action[data-dash-category="events"] { background:var(--admin-green) !important; }\n.dash-stat[data-dash-category="members"] .dash-stat-icon,\n.dash-action[data-dash-category="members"] { background:var(--admin-blue) !important; }\n.dash-stat[data-dash-category="polls"] .dash-stat-icon,\n.dash-action[data-dash-category="polls"] { background:var(--admin-orange) !important; }\n.dash-stat[data-dash-category="gallery"] .dash-stat-icon,\n.dash-action[data-dash-category="gallery"] { background:var(--admin-purple) !important; }\n.dash-stat[data-dash-category="documents"] .dash-stat-icon,\n.dash-action[data-dash-category="documents"] { background:var(--admin-red) !important; }\n@media (max-width:1180px) { .dash-stats { grid-template-columns:repeat(3,minmax(0,1fr)) !important; } }\n@media (max-width:720px) { .dash-stats { grid-template-columns:repeat(2,minmax(0,1fr)) !important; } }\n</style>\n'''
s = s.replace('</head>', css + '</head>', 1)

# Keep News count synced from the already-rendered News list; no API/backend change.
js = '''\n<script>\n/* ===== Dashboard News Count V12 ===== */\n(() => {\n  const updateNewsCount = () => {\n    const out = document.getElementById('dash-news-count');\n    const list = document.getElementById('news-list');\n    if (!out || !list) return;\n    const entries = [...list.children].filter(el =>\n      !el.classList.contains('dash-empty') &&\n      !el.classList.contains('meta') &&\n      el.tagName !== 'STYLE' && el.tagName !== 'SCRIPT'\n    );\n    out.textContent = String(entries.length);\n  };\n  const list = document.getElementById('news-list');\n  if (list) {\n    new MutationObserver(updateNewsCount).observe(list, {childList:true, subtree:false});\n    updateNewsCount();\n  }\n})();\n</script>\n'''
s = s.replace('</body>', js + '</body>', 1)

p.write_text(s, encoding='utf-8')
print('Applied dashboard paired colors/order and News count V12')
