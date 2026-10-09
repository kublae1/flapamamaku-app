from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

# Fix neutral app logo path for login/logout state. The backend exposes the icon
# at the root path; favicon remains a safe fallback.
text = text.replace('src="/static/flapamamaku-icon.png" alt="App-Logo"', 'src="/flapamamaku-icon.png" onerror="this.onerror=null;this.src=\'/favicon.ico\'" alt="App-Logo"')

css_marker = '    /* ===== Centralized Admin Workspace V2 ===== */'
if css_marker not in text:
    css = r'''

    /* ===== Centralized Admin Workspace V2 ===== */
    .workspace-mode-switcher {
      position:sticky;
      top:82px;
      z-index:12;
      display:flex;
      gap:8px;
      align-items:center;
      padding:8px;
      margin:0 0 12px;
      border:1px solid rgba(225,184,85,.16);
      border-radius:12px;
      background:rgba(7,16,23,.94);
      backdrop-filter:blur(12px);
      box-shadow:0 10px 28px rgba(0,0,0,.18);
    }
    .workspace-mode-switcher .workspace-mode-label {
      margin-right:auto;
      padding-left:4px;
      color:rgba(230,236,240,.62);
      font-size:12px;
      font-weight:800;
    }
    .workspace-mode-switcher button {
      border:1px solid rgba(255,255,255,.10);
      background:#111e27;
      color:#e8eef1;
      border-radius:9px;
      padding:8px 12px;
      font-size:12px;
      font-weight:900;
      cursor:pointer;
    }
    .workspace-mode-switcher button.active {
      background:linear-gradient(180deg,rgba(225,184,85,.30),rgba(225,184,85,.14));
      border-color:rgba(225,184,85,.42);
      color:#fff2c8;
    }
    .workspace-pane-hidden { display:none !important; }
    .panel:not(#dashboard) .grid.workspace-single {
      grid-template-columns:minmax(0,1fr) !important;
    }
    .panel:not(#dashboard) .grid.workspace-single > * {
      width:100%;
      max-width:none;
    }
    .panel:not(#dashboard) .grid.workspace-single > form.card,
    .panel:not(#dashboard) .grid.workspace-single > .card,
    .panel:not(#dashboard) .grid.workspace-single > div {
      max-height:calc(100vh - 250px);
      overflow:auto;
      scrollbar-width:thin;
      scrollbar-color:rgba(225,184,85,.36) transparent;
    }
    .panel:not(#dashboard) .grid.workspace-single > form.card {
      padding-bottom:78px;
    }
    .panel:not(#dashboard) .grid.workspace-single > form.card > p:has(.primary) {
      position:sticky;
      bottom:0;
      z-index:6;
      margin:18px -4px -60px;
      padding:12px 4px 4px;
      background:linear-gradient(180deg,rgba(10,20,27,0),rgba(10,20,27,.96) 36%);
    }
    .panel:not(#dashboard) .grid.workspace-single > form.card > p:has(.primary) .primary {
      min-width:180px;
    }
    .panel:not(#dashboard) .workspace-title,
    .panel:not(#dashboard) .preview-heading {
      scroll-margin-top:150px;
    }
    #content.panel .section-switcher {
      position:sticky;
      top:82px;
      z-index:11;
      max-height:92px;
      overflow:auto;
    }
    #content.panel .section-switcher + .workspace-mode-switcher {
      top:142px;
    }
    @media (min-width:981px) {
      .panel:not(#dashboard) { min-height:calc(100vh - 120px); }
      .panel:not(#dashboard) .grid.workspace-single > div > .card {
        margin-bottom:12px;
      }
    }
    @media (max-width:980px) {
      .workspace-mode-switcher,
      #content.panel .section-switcher,
      #content.panel .section-switcher + .workspace-mode-switcher {
        position:static;
      }
      .panel:not(#dashboard) .grid.workspace-single > form.card,
      .panel:not(#dashboard) .grid.workspace-single > .card,
      .panel:not(#dashboard) .grid.workspace-single > div {
        max-height:none;
        overflow:visible;
      }
    }
'''
    text = text.replace('</style>', css + '\n</style>', 1)

js_marker = '/* ===== Centralized Admin Workspace V2 ===== */'
if js_marker not in text:
    js = r'''
<script>
(() => {
  /* ===== Centralized Admin Workspace V2 ===== */
  const panels = Array.from(document.querySelectorAll('#admin-view .panel')).filter(panel => panel.id !== 'dashboard');

  function findGrid(panel) {
    return Array.from(panel.children).find(child => child.classList?.contains('grid')) || null;
  }

  function setWorkspaceMode(panel, mode) {
    const grid = findGrid(panel);
    if (!grid || grid.children.length < 2) return;
    const panes = Array.from(grid.children);
    panel.dataset.workspaceMode = mode;
    grid.classList.toggle('workspace-single', mode !== 'split');
    panes.forEach((pane, index) => {
      const hidden = mode === 'edit' ? index > 0 : mode === 'overview' ? index === 0 : false;
      pane.classList.toggle('workspace-pane-hidden', hidden);
    });
    panel.querySelectorAll('.workspace-mode-switcher button[data-workspace-mode]').forEach(button => {
      button.classList.toggle('active', button.dataset.workspaceMode === mode);
    });
    const activePane = mode === 'edit' ? panes[0] : mode === 'overview' ? panes[1] : null;
    activePane?.scrollTo?.({top: 0, behavior: 'instant'});
  }

  function buildSwitcher(panel) {
    const grid = findGrid(panel);
    if (!grid || grid.children.length < 2 || panel.querySelector(':scope > .workspace-mode-switcher')) return;
    const switcher = document.createElement('div');
    switcher.className = 'workspace-mode-switcher';
    switcher.innerHTML = `
      <span class="workspace-mode-label">Arbeitsbereich</span>
      <button type="button" data-workspace-mode="overview">Übersicht</button>
      <button type="button" data-workspace-mode="edit">Bearbeiten / Neu</button>
      <button type="button" data-workspace-mode="split">Geteilt</button>`;
    const sectionSwitcher = panel.querySelector(':scope > .section-switcher');
    if (sectionSwitcher) sectionSwitcher.insertAdjacentElement('afterend', switcher);
    else grid.insertAdjacentElement('beforebegin', switcher);
    switcher.addEventListener('click', event => {
      const button = event.target.closest('button[data-workspace-mode]');
      if (button) setWorkspaceMode(panel, button.dataset.workspaceMode);
    });
    setWorkspaceMode(panel, 'overview');
  }

  panels.forEach(panel => {
    buildSwitcher(panel);
    panel.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button) return;
      const text = (button.textContent || '').trim().toLowerCase();
      if (/bearbeiten|ändern|neu|hinzufügen|erstellen|hochladen/.test(text)) {
        setTimeout(() => setWorkspaceMode(panel, 'edit'), 0);
      }
      if (/abbrechen|zurück zur übersicht/.test(text)) {
        setTimeout(() => setWorkspaceMode(panel, 'overview'), 0);
      }
    });
  });

  // Quick actions must open the editor pane instead of leaving it hidden.
  document.addEventListener('click', event => {
    const quick = event.target.closest('[data-quick-panel]');
    if (!quick) return;
    const panel = document.getElementById(quick.dataset.quickPanel || '');
    if (panel) setTimeout(() => setWorkspaceMode(panel, 'edit'), 90);
  }, true);

  // When a left navigation item opens a content subsection, start with the
  // compact overview. The existing section routing remains untouched.
  document.querySelectorAll('#admin-view > nav button[data-panel]').forEach(button => {
    button.addEventListener('click', () => {
      const panel = document.getElementById(button.dataset.panel || '');
      if (panel && panel.id !== 'dashboard') {
        setTimeout(() => setWorkspaceMode(panel, 'overview'), 40);
      }
    });
  });
})();
</script>
'''
    text = text.replace('</body>', js + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
