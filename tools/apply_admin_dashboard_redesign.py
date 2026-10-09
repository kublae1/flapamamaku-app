from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

css = r'''

    /* ===== Admin Dashboard Redesign V1: UI only, existing IDs/API preserved ===== */
    :root {
      --admin-bg: #071017;
      --admin-panel: #0d171f;
      --admin-line: rgba(255,255,255,.11);
      --admin-gold: #e1b855;
      --admin-green: #16b568;
      --admin-red: #ef3e47;
      --admin-blue: #1687ef;
      --admin-purple: #8a42e8;
      --admin-cyan: #0ba6b5;
      --admin-orange: #e39a13;
    }
    body {
      background:
        radial-gradient(circle at 22% 0%, rgba(32,76,111,.18), transparent 31rem),
        radial-gradient(circle at 92% 4%, rgba(199,163,90,.09), transparent 26rem),
        var(--admin-bg);
    }
    header.admin-redesign-header {
      min-height:76px;
      padding:10px 22px;
      background:linear-gradient(90deg,#06111a 0%,#08131b 52%,#050a0e 100%);
      border-bottom:1px solid rgba(225,184,85,.32);
      box-shadow:0 8px 30px rgba(0,0,0,.28);
    }
    .admin-header-brand { display:flex; align-items:center; gap:13px; min-width:0; }
    .admin-header-logo {
      width:52px; height:52px; object-fit:contain; border-radius:12px;
      background:rgba(255,255,255,.05); border:1px solid rgba(225,184,85,.22);
    }
    .admin-header-logo.no-image { display:none; }
    .admin-header-brand h1 { font-size:25px; letter-spacing:.7px; line-height:1; }
    .admin-header-brand small { display:block; margin-top:5px; font-size:12px; letter-spacing:.5px; }
    .admin-header-right { display:flex; align-items:center; gap:18px; margin-left:auto; }
    .admin-system-state { display:flex; align-items:center; gap:8px; color:#d8e0e5; font-size:13px; }
    .admin-system-dot { width:9px; height:9px; border-radius:50%; background:#81909a; box-shadow:0 0 0 4px rgba(129,144,154,.10); }
    .admin-system-dot.online { background:#73d13d; box-shadow:0 0 0 4px rgba(115,209,61,.10); }
    .admin-user-box { display:flex; align-items:center; gap:10px; padding-left:16px; border-left:1px solid var(--admin-line); }
    .admin-user-avatar { width:34px; height:34px; display:grid; place-items:center; border-radius:50%; background:linear-gradient(135deg,#2f3941,#11181d); border:1px solid rgba(255,255,255,.16); }
    .admin-user-copy strong { display:block; font-size:13px; }
    .admin-user-copy span { display:block; margin-top:2px; color:var(--muted); font-size:11px; }
    #logout-button {
      border:1px solid rgba(239,62,71,.42); border-radius:10px; background:rgba(239,62,71,.13);
      color:#ff737a; padding:9px 13px; font-weight:800; cursor:pointer;
    }
    #logout-button:hover { background:rgba(239,62,71,.23); }
    main { max-width:none; margin:0; padding:14px; }
    #admin-view { grid-template-columns:250px minmax(0,1fr); gap:14px; align-items:start; }
    #tenant-context-card { grid-column:1/-1; }
    #tenant-context-card:not(.tenant-switching) { display:none; }
    #admin-view > nav {
      top:90px; height:calc(100vh - 104px); overflow:auto; gap:4px; padding:10px 8px;
      background:linear-gradient(180deg,rgba(10,21,30,.98),rgba(6,14,20,.98));
      border:1px solid rgba(225,184,85,.14); border-radius:14px;
      box-shadow:0 18px 50px rgba(0,0,0,.28);
    }
    #admin-view > nav button {
      position:relative; padding:10px 12px 10px 42px; min-height:39px; border-radius:9px;
      font-size:13px; font-weight:750; color:#d9e0e5;
    }
    #admin-view > nav button::before {
      position:absolute; left:13px; top:50%; transform:translateY(-50%); width:20px; text-align:center;
      font-size:16px; opacity:.92;
    }
    #admin-view > nav button[data-panel="dashboard"]::before { content:'⌂'; }
    #admin-view > nav button[data-panel="news"]::before { content:'▤'; }
    #admin-view > nav button[data-panel="events"]::before { content:'▣'; }
    #admin-view > nav button[data-panel="members"]::before { content:'●'; }
    #admin-view > nav button[data-section-target="gallery"]::before { content:'▧'; }
    #admin-view > nav button[data-section-target="documents"]::before { content:'▱'; }
    #admin-view > nav button[data-section-target="polls"]::before { content:'▥'; }
    #admin-view > nav button[data-section-target="links"]::before { content:'↗'; }
    #admin-view > nav button[data-section-target="sujet"]::before { content:'★'; }
    #admin-view > nav button[data-section-target="archive"]::before { content:'▰'; }
    #admin-view > nav button[data-panel="system"]::before { content:'⚙'; }
    #admin-view > nav button[data-panel="users"]::before { content:'♟'; }
    #admin-view > nav button.active {
      background:linear-gradient(90deg,rgba(225,184,85,.24),rgba(225,184,85,.08));
      color:#fff2c8; border:1px solid rgba(225,184,85,.44);
      box-shadow:inset 3px 0 0 var(--admin-gold);
    }
    #admin-view > nav button:hover { background:rgba(255,255,255,.055); transform:none; }
    .panel { grid-column:2; }
    .card { background:linear-gradient(180deg,var(--admin-panel),#0a141b); border-color:var(--admin-line); border-radius:13px; box-shadow:0 12px 35px rgba(0,0,0,.20); }
    .primary { box-shadow:none; }

    #dashboard { margin:0; }
    .dash-shell { display:grid; gap:12px; }
    .dash-hero {
      min-height:225px; position:relative; overflow:hidden; border:1px solid rgba(225,184,85,.22);
      border-radius:14px; background:
        radial-gradient(circle at 60% 30%,rgba(225,184,85,.14),transparent 28rem),
        linear-gradient(115deg,#101c25 0%,#0b151c 48%,#071017 100%);
    }
    .dash-hero::after {
      content:''; position:absolute; inset:0; pointer-events:none;
      background:linear-gradient(90deg,rgba(4,10,14,.94) 0%,rgba(4,10,14,.72) 36%,rgba(4,10,14,.18) 70%,rgba(4,10,14,.42) 100%);
    }
    .dash-hero-copy { position:relative; z-index:2; max-width:500px; padding:28px 30px; }
    .dash-kicker { color:#f5f1eb; font-size:24px; font-weight:900; margin-bottom:3px; }
    .dash-club-name { color:var(--admin-gold); font-size:35px; line-height:1.02; font-weight:950; letter-spacing:.8px; overflow-wrap:anywhere; }
    .dash-hero-copy p { color:#dce4e9; line-height:1.45; margin:15px 0 0; max-width:390px; }
    .dash-hero-logo {
      position:absolute; right:7%; top:50%; transform:translateY(-50%); z-index:1;
      width:min(34%,390px); height:78%; object-fit:contain; filter:drop-shadow(0 16px 32px rgba(0,0,0,.42)); opacity:.92;
    }
    .dash-stats { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:10px; }
    .dash-stat {
      min-height:78px; display:grid; grid-template-columns:46px minmax(0,1fr); gap:11px; align-items:center;
      padding:10px 12px; border:1px solid var(--admin-line); border-radius:12px;
      background:linear-gradient(135deg,rgba(17,31,41,.96),rgba(9,19,26,.96));
    }
    .dash-stat-icon { width:44px; height:44px; display:grid; place-items:center; border-radius:10px; font-size:20px; font-weight:900; color:white; }
    .dash-stat:nth-child(1) .dash-stat-icon { background:var(--admin-blue); }
    .dash-stat:nth-child(2) .dash-stat-icon { background:var(--admin-green); }
    .dash-stat:nth-child(3) .dash-stat-icon { background:var(--admin-orange); }
    .dash-stat:nth-child(4) .dash-stat-icon { background:var(--admin-purple); }
    .dash-stat:nth-child(5) .dash-stat-icon { background:var(--admin-red); }
    .dash-stat strong { display:block; font-size:26px; line-height:1; }
    .dash-stat span { display:block; margin-top:5px; color:#d2dbe0; font-size:12px; }
    .dash-quick { border:1px solid var(--admin-line); border-radius:12px; background:rgba(12,24,32,.92); padding:10px 12px 12px; }
    .dash-section-title { margin:0 0 8px; color:#f2d17f; font-size:15px; font-weight:900; }
    .dash-quick-grid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:8px; }
    .dash-action { min-height:48px; border:0; border-radius:9px; color:white; font-weight:850; cursor:pointer; padding:8px 9px; box-shadow:inset 0 0 0 1px rgba(255,255,255,.11); transition:filter .15s ease, transform .15s ease; }
    .dash-action:hover { filter:brightness(1.12); transform:translateY(-1px); }
    .dash-action:nth-child(1) { background:#086bc8; }
    .dash-action:nth-child(2) { background:#0d9b58; }
    .dash-action:nth-child(3) { background:#d18a09; }
    .dash-action:nth-child(4) { background:#7533c5; }
    .dash-action:nth-child(5) { background:#c62c34; }
    .dash-action:nth-child(6) { background:#078b98; }
    .dash-bottom { display:grid; grid-template-columns:1.05fr 1.05fr 1.25fr; gap:10px; min-height:265px; }
    .dash-panel { border:1px solid var(--admin-line); border-radius:12px; background:linear-gradient(180deg,#0d1820,#09131a); padding:11px 12px; min-width:0; overflow:hidden; }
    .dash-panel-heading { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:6px; }
    .dash-panel-heading h3 { margin:0; color:#f2d17f; font-size:15px; }
    .dash-panel-heading button { border:0; background:none; color:#68b7ff; font-size:11px; cursor:pointer; font-weight:800; }
    .dash-list { display:grid; gap:5px; }
    .dash-list-item { padding:7px 8px; border:1px solid rgba(255,255,255,.07); border-radius:8px; background:rgba(255,255,255,.025); min-width:0; }
    .dash-list-item strong { display:block; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .dash-list-item span { display:block; margin-top:3px; color:var(--muted); font-size:10px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
    .dash-right-stack { display:grid; grid-template-rows:1fr 1fr; gap:8px; min-height:0; }
    .dash-subgrid { display:grid; grid-template-columns:1fr 1fr; gap:8px; min-height:0; }
    .dash-feature { min-height:0; padding:10px; border-radius:10px; border:1px solid rgba(225,184,85,.18); background:linear-gradient(135deg,rgba(225,184,85,.08),rgba(255,255,255,.018)); }
    .dash-feature strong { display:block; color:#fff; font-size:14px; }
    .dash-feature p { color:var(--muted); font-size:11px; line-height:1.35; margin:6px 0 0; }
    .dash-empty { color:var(--muted); font-size:11px; padding:8px; }

    @media (min-width:1400px) and (min-height:850px) {
      #dashboard.active .dash-shell { height:calc(100vh - 106px); grid-template-rows:225px 78px 74px minmax(0,1fr); }
      #dashboard.active .dash-bottom { min-height:0; }
    }
    @media (max-width:1180px) {
      #admin-view { grid-template-columns:210px minmax(0,1fr); }
      .dash-stats { grid-template-columns:repeat(3,minmax(0,1fr)); }
      .dash-quick-grid { grid-template-columns:repeat(3,minmax(0,1fr)); }
      .dash-bottom { grid-template-columns:1fr 1fr; }
      .dash-right-stack { grid-column:1/-1; grid-template-columns:1fr 1fr; grid-template-rows:none; }
    }
    @media (max-width:980px) {
      header.admin-redesign-header { position:static; }
      .admin-header-right { width:100%; justify-content:flex-end; flex-wrap:wrap; }
      #admin-view { display:block; }
      #admin-view > nav { height:auto; position:static; flex-direction:row; margin-bottom:12px; }
      #admin-view > nav button { width:auto; padding-left:38px; }
      .dash-hero { min-height:205px; }
      .dash-hero-logo { opacity:.45; right:2%; }
      .dash-bottom { grid-template-columns:1fr; }
      .dash-right-stack { grid-column:auto; grid-template-columns:1fr; }
    }
    @media (max-width:680px) {
      header.admin-redesign-header { padding:10px 12px; }
      .admin-header-brand h1 { font-size:20px; }
      .admin-system-state { display:none; }
      .admin-user-copy { display:none; }
      main { padding:8px; }
      .dash-hero-copy { padding:20px; }
      .dash-kicker { font-size:20px; }
      .dash-club-name { font-size:28px; }
      .dash-stats { grid-template-columns:1fr 1fr; }
      .dash-quick-grid { grid-template-columns:1fr 1fr; }
      .dash-subgrid { grid-template-columns:1fr; }
    }
'''

if 'Admin Dashboard Redesign V1' not in text:
    text = text.replace('  </style>', css + '\n  </style>', 1)

old_header = '''<header>
  <div>
    <h1 id="admin-title">Vereins-App Verwaltung</h1>
    <small id="admin-subtitle">Zentrale Verwaltung für die Inhalte der Vereins-App</small>
  </div>
  <div class="status" id="status">API wird geprüft …</div>
</header>'''
new_header = '''<header class="admin-redesign-header">
  <div class="admin-header-brand">
    <img id="header-club-logo" class="admin-header-logo no-image" alt="Vereinslogo">
    <div>
      <h1 id="admin-title">Vereins-App Verwaltung</h1>
      <small id="admin-subtitle">Zentrale Verwaltung für die Inhalte der Vereins-App</small>
    </div>
  </div>
  <div class="admin-header-right">
    <div class="admin-system-state"><span id="admin-system-dot" class="admin-system-dot"></span><span id="status">API wird geprüft …</span></div>
    <div class="admin-user-box">
      <div class="admin-user-avatar">●</div>
      <div class="admin-user-copy"><strong id="header-user-name">Admin</strong><span>Administration</span></div>
    </div>
    <button id="logout-button" type="button">Abmelden</button>
  </div>
</header>'''
if old_header not in text:
    raise SystemExit('Expected header marker not found')
text = text.replace(old_header, new_header, 1)

old_nav = '''    <nav>
      <button class="active" data-panel="news" data-permission="can_news">News</button>
      <button data-panel="events" data-permission="can_events">Termine</button>
      <button data-panel="members" id="members-nav">Mitglieder</button>
      <button data-panel="users" data-permission="can_manage_users">Benutzer & Rechte</button>
      <button data-panel="content" id="content-nav">Medien & Inhalte</button>
      <button data-panel="push" id="push-nav" data-permission="can_manage_users">Push</button>
      <button data-panel="billing" id="billing-nav">Vereinsabrechnung</button>
      <button data-panel="system" id="system-nav" data-permission="can_manage_settings">Verein & System</button>
      <button id="logout-button">Abmelden</button>
    </nav>'''
new_nav = '''    <nav aria-label="Administration">
      <button class="active" data-panel="dashboard">Dashboard</button>
      <button data-panel="news" data-permission="can_news">News</button>
      <button data-panel="events" data-permission="can_events">Termine</button>
      <button data-panel="members" id="members-nav">Mitglieder</button>
      <button data-panel="content" id="content-nav" data-section-target="gallery">Galerie</button>
      <button data-panel="content" data-section-target="documents">Dokumente</button>
      <button data-panel="content" data-section-target="polls">Umfragen</button>
      <button data-panel="content" data-section-target="links">Links</button>
      <button data-panel="content" data-section-target="sujet">Aktuelles Sujet</button>
      <button data-panel="content" data-section-target="archive">Vergangene Sujets</button>
      <button data-panel="system" id="system-nav" data-permission="can_manage_settings">Einstellungen</button>
      <button data-panel="users" data-permission="can_manage_users">Benutzer / Rollen</button>
      <button data-panel="push" id="push-nav" data-permission="can_manage_users" class="hidden">Push</button>
      <button data-panel="billing" id="billing-nav" class="hidden">Vereinsabrechnung</button>
    </nav>'''
if old_nav not in text:
    raise SystemExit('Expected nav marker not found')
text = text.replace(old_nav, new_nav, 1)

dashboard = r'''    <section id="dashboard" class="panel active">
      <div class="dash-shell">
        <div class="dash-hero">
          <div class="dash-hero-copy">
            <div class="dash-kicker">Willkommen</div>
            <div class="dash-club-name" id="dashboard-club-name">Verein</div>
            <p>Schön, dass du da bist. Hier verwaltest du alle Inhalte deines Vereins schnell, einfach und übersichtlich.</p>
          </div>
          <img id="dashboard-club-logo" class="dash-hero-logo hidden" alt="Vereinslogo">
        </div>
        <div class="dash-stats">
          <div class="dash-stat"><div class="dash-stat-icon">●</div><div><strong id="dash-members-count">–</strong><span>Mitglieder</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">▣</div><div><strong id="dash-events-count">–</strong><span>nächste Termine</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">?</div><div><strong id="dash-polls-count">–</strong><span>aktive Umfragen</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">▧</div><div><strong id="dash-gallery-count">–</strong><span>Galerie-Inhalte</span></div></div>
          <div class="dash-stat"><div class="dash-stat-icon">▱</div><div><strong id="dash-documents-count">–</strong><span>Dokumente</span></div></div>
        </div>
        <div class="dash-quick">
          <div class="dash-section-title">Schnellzugriffe</div>
          <div class="dash-quick-grid">
            <button class="dash-action" type="button" data-quick-panel="news" data-quick-new="news-new-button">News erstellen</button>
            <button class="dash-action" type="button" data-quick-panel="events">Termin erstellen</button>
            <button class="dash-action" type="button" data-quick-panel="members" data-quick-new="member-new-button">Mitglied hinzufügen</button>
            <button class="dash-action" type="button" data-quick-panel="content" data-quick-section="gallery">Bilder hochladen</button>
            <button class="dash-action" type="button" data-quick-panel="content" data-quick-section="documents">Dokument hochladen</button>
            <button class="dash-action" type="button" data-quick-panel="content" data-quick-section="polls">Umfrage erstellen</button>
          </div>
        </div>
        <div class="dash-bottom">
          <div class="dash-panel">
            <div class="dash-panel-heading"><h3>Letzte News</h3><button type="button" data-dash-open="news">Alle News →</button></div>
            <div id="dash-news-list" class="dash-list"><div class="dash-empty">News werden geladen …</div></div>
          </div>
          <div class="dash-panel">
            <div class="dash-panel-heading"><h3>Nächste Termine</h3><button type="button" data-dash-open="events">Alle Termine →</button></div>
            <div id="dash-events-list" class="dash-list"><div class="dash-empty">Termine werden geladen …</div></div>
          </div>
          <div class="dash-right-stack">
            <div class="dash-feature">
              <div class="dash-panel-heading"><h3>Aktuelles Sujet</h3><button type="button" data-dash-section="sujet">Bearbeiten →</button></div>
              <strong id="dash-sujet-title">Noch kein Sujet geladen</strong>
              <p id="dash-sujet-copy">Der vorhandene Sujet-Bereich wird hier kompakt zusammengefasst.</p>
            </div>
            <div class="dash-subgrid">
              <div class="dash-panel">
                <div class="dash-panel-heading"><h3>Galerie</h3><button type="button" data-dash-section="gallery">Öffnen →</button></div>
                <div id="dash-gallery-list" class="dash-list"><div class="dash-empty">Galerie wird geladen …</div></div>
              </div>
              <div class="dash-panel">
                <div class="dash-panel-heading"><h3>Dokumente</h3><button type="button" data-dash-section="documents">Öffnen →</button></div>
                <div id="dash-documents-list" class="dash-list"><div class="dash-empty">Dokumente werden geladen …</div></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

'''
marker = '    <section id="news" class="panel active">'
if marker not in text:
    raise SystemExit('Expected news panel marker not found')
text = text.replace(marker, dashboard + '    <section id="news" class="panel">', 1)

script = r'''
<script>
(() => {
  const qs = (s, r=document) => r.querySelector(s);
  const qsa = (s, r=document) => Array.from(r.querySelectorAll(s));
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));

  function openPanel(panel, section=null) {
    const navButton = qsa('#admin-view > nav button[data-panel]').find(btn => btn.dataset.panel === panel && (!section || btn.dataset.sectionTarget === section)) || qs(`#admin-view > nav button[data-panel="${panel}"]`);
    navButton?.click();
    if (section) setTimeout(() => selectContentSection(section), 30);
  }
  function selectContentSection(section) {
    qs(`#content-section-switcher button[data-section="${section}"]`)?.click();
    const filter = qs('#content-filter');
    if (filter) { filter.value = section; filter.dispatchEvent(new Event('change', {bubbles:true})); }
    const select = qs('#content-form select[name="section"]');
    if (select) { select.value = section; select.dispatchEvent(new Event('change', {bubbles:true})); }
  }

  qsa('#admin-view > nav button[data-section-target]').forEach(btn => btn.addEventListener('click', () => setTimeout(() => selectContentSection(btn.dataset.sectionTarget), 30)));
  qsa('[data-quick-panel]').forEach(btn => btn.addEventListener('click', () => {
    openPanel(btn.dataset.quickPanel, btn.dataset.quickSection || null);
    if (btn.dataset.quickNew) setTimeout(() => qs(`#${btn.dataset.quickNew}`)?.click(), 80);
  }));
  qsa('[data-dash-open]').forEach(btn => btn.addEventListener('click', () => openPanel(btn.dataset.dashOpen)));
  qsa('[data-dash-section]').forEach(btn => btn.addEventListener('click', () => openPanel('content', btn.dataset.dashSection)));

  const authForm = qs('#auth-form');
  authForm?.addEventListener('submit', () => {
    const username = authForm.elements.username?.value?.trim();
    if (username) sessionStorage.setItem('flap-admin-username', username);
  }, true);

  function cleanEntryText(entry) {
    const clone = entry.cloneNode(true);
    qsa('button,.actions,input,select,textarea', clone).forEach(el => el.remove());
    return (clone.textContent || '').replace(/\s+/g,' ').trim();
  }
  const entryTitle = entry => qs('h3,strong', entry)?.textContent?.trim() || cleanEntryText(entry).slice(0,70) || 'Eintrag';
  function renderList(targetId, entries, max=4) {
    const target = qs(`#${targetId}`);
    if (!target) return;
    const selected = entries.slice(0,max);
    if (!selected.length) { target.innerHTML = '<div class="dash-empty">Noch keine Einträge vorhanden.</div>'; return; }
    target.innerHTML = selected.map(entry => {
      const title = entryTitle(entry);
      const detail = cleanEntryText(entry).replace(title,'').trim().slice(0,90);
      return `<div class="dash-list-item"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>`;
    }).join('');
  }
  function contentEntriesFor(label) {
    const needle = label.toLowerCase();
    return qsa('#content-list .entry').filter(entry => cleanEntryText(entry).toLowerCase().includes(needle));
  }

  function syncBranding() {
    const tenantName = qs('#tenant-context-name')?.textContent?.trim();
    if (tenantName && !tenantName.includes('geladen')) {
      if (qs('#dashboard-club-name')) qs('#dashboard-club-name').textContent = tenantName;
      if (qs('#admin-title')) qs('#admin-title').textContent = tenantName;
    }
    const sourceLogo = qs('#tenant-context-logo');
    const src = sourceLogo?.getAttribute('src') || '';
    [qs('#header-club-logo'), qs('#dashboard-club-logo')].forEach(img => {
      if (!img || !src) return;
      if (img.getAttribute('src') !== src) img.setAttribute('src', src);
      img.classList.remove('no-image','hidden');
    });
    const username = sessionStorage.getItem('flap-admin-username');
    if (username && qs('#header-user-name')) qs('#header-user-name').textContent = username;
    const status = qs('#status')?.textContent?.toLowerCase() || '';
    qs('#admin-system-dot')?.classList.toggle('online', /ok|online|bereit|verbunden|erreichbar/.test(status));
    const switchWrap = qs('#tenant-switch-wrap');
    const tenantCard = qs('#tenant-context-card');
    if (tenantCard && switchWrap) tenantCard.classList.toggle('tenant-switching', !switchWrap.classList.contains('hidden'));
  }

  function syncDashboard() {
    syncBranding();
    const news = qsa('#news-list .entry');
    const events = qsa('#events-list .entry');
    const members = qsa('#members-list .entry');
    const polls = contentEntriesFor('umfrage');
    const gallery = contentEntriesFor('galerie');
    const documents = contentEntriesFor('dokument');
    const sujet = contentEntriesFor('sujet');
    const setCount = (id, value) => { const el = qs(`#${id}`); if (el) el.textContent = String(value); };
    setCount('dash-members-count', members.length);
    setCount('dash-events-count', events.length);
    setCount('dash-polls-count', polls.length);
    setCount('dash-gallery-count', gallery.length);
    setCount('dash-documents-count', documents.length);
    renderList('dash-news-list', news, 4);
    renderList('dash-events-list', events, 4);
    renderList('dash-gallery-list', gallery, 3);
    renderList('dash-documents-list', documents, 3);
    if (sujet[0]) {
      const title = entryTitle(sujet[0]);
      const copy = cleanEntryText(sujet[0]).replace(title,'').trim();
      if (qs('#dash-sujet-title')) qs('#dash-sujet-title').textContent = title;
      if (qs('#dash-sujet-copy')) qs('#dash-sujet-copy').textContent = copy.slice(0,150) || 'Aktuelles Sujet bearbeiten und ergänzen.';
    }
  }

  const observer = new MutationObserver(syncDashboard);
  ['news-list','events-list','members-list','content-list','tenant-context-name','tenant-context-logo','status','tenant-switch-wrap'].forEach(id => {
    const el = qs(`#${id}`);
    if (el) observer.observe(el,{childList:true,subtree:true,attributes:true,characterData:true});
  });
  syncDashboard();
  setTimeout(syncDashboard, 400);
  setTimeout(syncDashboard, 1200);
})();
</script>
'''
if 'flap-admin-username' not in text:
    text = text.replace('</body>', script + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
print('Admin dashboard redesign applied successfully.')
