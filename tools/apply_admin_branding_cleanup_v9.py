from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

css_marker = '/* ===== Branding Cleanup V9 ===== */'
if css_marker not in text:
    css = r'''

    /* ===== Branding Cleanup V9 ===== */
    /* Branding: only the actual branding form. No onboarding/setup/system cards. */
    #system.system-branding-mode > #onboarding-card,
    #system.system-branding-mode > #setup-status-card {
      display:none !important;
    }
    #system.system-branding-mode > .grid.system-branding-visible,
    #system.system-branding-mode > .grid {
      display:block !important;
      width:100% !important;
      max-width:none !important;
    }
    #system.system-branding-mode > .grid > * {
      display:none !important;
    }
    #system.system-branding-mode > .grid > #app-config-form {
      display:block !important;
      width:100% !important;
      max-width:none !important;
      max-height:none !important;
      overflow:visible !important;
    }

    /* Settings: keep technical cards visible, but not the branding form. */
    #system.system-settings-mode > .grid.system-branding-visible,
    #system.system-settings-mode > .grid {
      display:grid !important;
      grid-template-columns:repeat(2,minmax(0,1fr)) !important;
      gap:14px !important;
      width:100% !important;
    }
    #system.system-settings-mode > .grid > #app-config-form {
      display:none !important;
    }
    #system.system-settings-mode > .grid > .card:not(.hidden) {
      display:block !important;
    }
    #system.system-settings-mode > #onboarding-card:not(.hidden),
    #system.system-settings-mode > #setup-status-card:not(.hidden) {
      display:block !important;
    }

    .branding-modules-bottom {
      margin-top:22px;
      padding-top:18px;
      border-top:1px solid rgba(255,255,255,.10);
    }
    .branding-modules-bottom > h3 { margin-top:0 !important; }

    @media (max-width:980px) {
      #system.system-settings-mode > .grid.system-branding-visible,
      #system.system-settings-mode > .grid {
        grid-template-columns:1fr !important;
      }
    }
'''
    text = text.replace('</style>', css + '\n</style>', 1)

js_marker = '/* ===== Branding Cleanup V9 ===== */'
if text.count(js_marker) < 2:
    js = r'''

<script>
/* ===== Branding Cleanup V9 ===== */
(() => {
  const system = document.getElementById('system');
  const form = document.getElementById('app-config-form');
  if (!system || !form) return;

  function moveModulesToBottom() {
    if (form.querySelector('.branding-modules-bottom')) return;
    const featureList = document.getElementById('club-feature-list');
    if (!featureList) return;
    const heading = Array.from(form.children).find(el =>
      el.tagName === 'H3' && el.textContent.trim() === 'Module dieses Vereins'
    );
    if (!heading) return;
    const note = heading.nextElementSibling;
    const wrapper = document.createElement('section');
    wrapper.className = 'branding-modules-bottom';
    wrapper.appendChild(heading);
    if (note && note.classList.contains('meta')) wrapper.appendChild(note);
    wrapper.appendChild(featureList);

    const submit = Array.from(form.children).find(el =>
      el.tagName === 'P' && el.querySelector('button[type="submit"]')
    );
    if (submit) form.insertBefore(wrapper, submit);
    else form.appendChild(wrapper);
  }

  function setMode(mode) {
    const branding = mode === 'branding';
    system.classList.toggle('system-branding-mode', branding);
    system.classList.toggle('system-settings-mode', !branding);
    moveModulesToBottom();
  }

  document.querySelectorAll('nav button[data-system-target="branding"]').forEach(btn => {
    btn.addEventListener('click', () => requestAnimationFrame(() => setMode('branding')));
  });
  document.getElementById('system-nav')?.addEventListener('click', () => {
    requestAnimationFrame(() => setMode('settings'));
  });

  moveModulesToBottom();
})();
</script>
'''
    text = text.replace('</body>', js + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
