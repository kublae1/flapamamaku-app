from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')
marker = '/* ===== Branding Layout Fix V7 ===== */'
if marker in text:
    raise SystemExit('Branding Layout Fix V7 already applied')

css = r'''

    /* ===== Branding Layout Fix V7 ===== */
    #system.system-branding-mode > #setup-status-card {
      display:block !important;
      max-height:none !important;
      overflow:visible !important;
    }
    #system.system-branding-mode > #setup-status-card .compact-card-body {
      display:block !important;
    }
    #system.system-branding-mode > .grid.system-branding-visible {
      display:block !important;
      width:100% !important;
      max-width:none !important;
    }
    #system.system-branding-mode > .grid.system-branding-visible > #app-config-form {
      display:block !important;
      width:100% !important;
      max-width:none !important;
      margin:0 !important;
    }
    #system.system-branding-mode > .grid.system-branding-visible > :not(#app-config-form) {
      display:none !important;
    }
    #system.system-branding-mode #app-config-form .branding-media-grid {
      display:grid !important;
      grid-template-columns:minmax(0,1fr) minmax(0,1fr) !important;
      gap:18px !important;
      width:100% !important;
      max-width:none !important;
      align-items:start !important;
    }
    #system.system-branding-mode #app-config-form .branding-media-card {
      width:100% !important;
      min-width:0 !important;
      margin:0 !important;
    }
    @media (max-width:760px) {
      #system.system-branding-mode #app-config-form .branding-media-grid {
        grid-template-columns:1fr !important;
      }
    }
'''

js = r'''

<script>
/* ===== Branding Layout Fix V7 ===== */
(() => {
  const system = document.getElementById('system');
  const form = document.getElementById('app-config-form');
  if (!system || !form) return;

  const findPrevious = (node, predicate) => {
    let current = node?.previousElementSibling || null;
    while (current) {
      if (predicate(current)) return current;
      current = current.previousElementSibling;
    }
    return null;
  };

  const moveRange = (start, end, destination) => {
    if (!start || !end || !destination || start.parentElement !== end.parentElement) return false;
    let node = start;
    while (node) {
      const next = node.nextSibling;
      destination.appendChild(node);
      if (node === end) return true;
      node = next;
    }
    return false;
  };

  function ensureBrandingColumns() {
    const logoInput = form.querySelector('input[name="logo_file"]');
    const heroInput = form.querySelector('input[name="hero_file"]');
    const logoPreview = document.getElementById('app-logo-preview');
    const heroPreview = document.getElementById('app-hero-preview');
    if (!logoInput || !heroInput || !logoPreview || !heroPreview) return;

    let grid = form.querySelector('.branding-media-grid');
    if (!grid) {
      const logoLabel = findPrevious(logoInput, el => el.tagName === 'LABEL' && /Vereinslogo/i.test(el.textContent || ''));
      const heroHeading = findPrevious(heroInput, el => el.tagName === 'H3' && /Hauptbild/i.test(el.textContent || ''));
      if (logoLabel && heroHeading && logoLabel.parentElement === form && heroHeading.parentElement === form) {
        grid = document.createElement('div');
        grid.className = 'branding-media-grid';
        const logoCard = document.createElement('div');
        logoCard.className = 'branding-media-card';
        const heroCard = document.createElement('div');
        heroCard.className = 'branding-media-card';
        form.insertBefore(grid, logoLabel);
        grid.append(logoCard, heroCard);
        moveRange(logoLabel, logoPreview, logoCard);
        moveRange(heroHeading, heroPreview, heroCard);
        const strayHr = grid.previousElementSibling;
        if (strayHr?.tagName === 'HR') strayHr.remove();
      }
    }

    grid = form.querySelector('.branding-media-grid');
    if (grid) {
      grid.style.display = 'grid';
      grid.style.gridTemplateColumns = window.innerWidth <= 760 ? '1fr' : 'minmax(0,1fr) minmax(0,1fr)';
      grid.style.gap = '18px';
      grid.style.width = '100%';
    }
  }

  function keepSetupStatusVisible() {
    const status = document.getElementById('setup-status-card');
    if (!status) return;
    status.classList.add('system-branding-visible', 'branding-status-always-open', 'is-open');
    status.classList.remove('hidden');
    status.style.display = 'block';
    status.querySelectorAll('.compact-card-body').forEach(body => body.style.display = 'block');
  }

  async function refreshBrandingView() {
    ensureBrandingColumns();
    keepSetupStatusVisible();
    if (typeof loadSystem === 'function') {
      try { await loadSystem(); } catch (error) { console.debug('Systemstatus konnte nicht aktualisiert werden', error); }
    }
    ensureBrandingColumns();
    keepSetupStatusVisible();
  }

  document.querySelectorAll('nav button[data-system-target="branding"]').forEach(button => {
    button.addEventListener('click', () => setTimeout(refreshBrandingView, 0));
  });

  window.addEventListener('resize', ensureBrandingColumns);
  setTimeout(() => {
    ensureBrandingColumns();
    keepSetupStatusVisible();
  }, 0);
})();
</script>
'''

text = text.replace('</style>', css + '\n</style>', 1)
text = text.replace('</body>', js + '\n</body>', 1)
path.write_text(text, encoding='utf-8')
print('Applied Branding Layout Fix V7')
