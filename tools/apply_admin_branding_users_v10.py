from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')
marker = '/* ===== Branding + Users Integration V10 ===== */'
if marker in text:
    print('V10 already applied')
    raise SystemExit(0)

patch = r'''
<style>
/* ===== Branding + Users Integration V10 ===== */
/* Verein & Branding: nur Vereinsdaten/Medien/Module/Benutzer anzeigen. */
#system.system-branding-mode #onboarding-card,
#system.system-branding-mode #setup-status-card,
#system.system-branding-mode #system-admin-status-card,
#system.system-branding-mode #server-migration-card,
#system.system-branding-mode #club-backup-card,
#system.system-branding-mode #system-admin-backup-card {
  display:none !important;
}

/* Einstellungen: Branding und integrierte Benutzerverwaltung ausblenden. */
#system.system-settings-mode #app-config-form,
#system.system-settings-mode .branding-users-integrated {
  display:none !important;
}

#system.system-branding-mode #app-config-form {
  display:block !important;
  width:100% !important;
  max-width:none !important;
  grid-column:1 / -1 !important;
}

#system .branding-users-integrated {
  display:none;
  width:100%;
  max-width:none;
  margin-top:18px;
}
#system.system-branding-mode .branding-users-integrated {
  display:block !important;
}
#system .branding-users-integrated > .grid {
  grid-template-columns:minmax(380px,.95fr) minmax(0,1.05fr) !important;
  gap:18px !important;
}
#system .branding-users-integrated .card {
  max-height:none !important;
  overflow:visible !important;
}

/* Module sind der letzte Inhaltsblock des Branding-Formulars. */
#app-config-form .branding-modules-final {
  margin-top:28px;
  padding-top:22px;
  border-top:1px solid rgba(255,255,255,.12);
}
#app-config-form .branding-modules-final h3 {
  margin:0 0 6px !important;
  color:#f1d48c;
}

@media (max-width:1100px) {
  #system .branding-users-integrated > .grid {
    grid-template-columns:1fr !important;
  }
}
</style>
<script>
(() => {
  const system = document.getElementById('system');
  const form = document.getElementById('app-config-form');
  const users = document.getElementById('users');
  if (!system || !form) return;

  // Eigenen Benutzer/Rollen-Navigationspunkt entfernen. Die bestehende
  // Benutzerverwaltung wird unverändert unten in Verein & Branding genutzt.
  document.querySelectorAll('nav button[data-panel="users"], #users-nav').forEach(button => {
    button.classList.add('hidden');
    button.setAttribute('aria-hidden', 'true');
  });

  if (users && users.parentElement !== system) {
    users.classList.remove('panel', 'active');
    users.classList.add('branding-users-integrated');
    system.appendChild(users);
  } else if (users) {
    users.classList.remove('panel', 'active');
    users.classList.add('branding-users-integrated');
  }

  // Module an das Ende der Branding-Eingaben verschieben. Bestehende Felder,
  // Namen und Event-Logik bleiben dieselben DOM-Knoten.
  const featureList = document.getElementById('club-feature-list');
  if (featureList && !form.querySelector('.branding-modules-final')) {
    let heading = null;
    for (const h3 of form.querySelectorAll('h3')) {
      if ((h3.textContent || '').trim().startsWith('Module dieses Vereins')) {
        heading = h3;
        break;
      }
    }
    const description = heading?.nextElementSibling?.classList?.contains('meta')
      ? heading.nextElementSibling
      : null;
    const wrapper = document.createElement('div');
    wrapper.className = 'branding-modules-final';
    if (heading) wrapper.appendChild(heading);
    if (description) wrapper.appendChild(description);
    wrapper.appendChild(featureList);

    const submitButton = form.querySelector('button[type="submit"]');
    const submitRow = submitButton?.closest('p') || submitButton;
    if (submitRow && submitRow.parentElement === form) {
      form.insertBefore(wrapper, submitRow);
    } else {
      form.appendChild(wrapper);
    }
  }

  function applyMode(mode) {
    if (mode === 'branding') {
      system.classList.add('system-branding-mode');
      system.classList.remove('system-settings-mode');
    } else if (mode === 'settings') {
      system.classList.add('system-settings-mode');
      system.classList.remove('system-branding-mode');
    }
  }

  document.querySelectorAll('[data-system-target="branding"]').forEach(button => {
    button.addEventListener('click', () => window.setTimeout(() => applyMode('branding'), 0));
  });
  document.querySelectorAll('[data-system-target="settings"]').forEach(button => {
    button.addEventListener('click', () => window.setTimeout(() => applyMode('settings'), 0));
  });

  // Falls eine ältere Regel beim Start die falsche Ansicht setzt, am aktiven
  // Navigationsknopf orientieren.
  const activeBranding = document.querySelector('[data-system-target="branding"].active');
  const activeSettings = document.querySelector('[data-system-target="settings"].active');
  if (activeBranding) applyMode('branding');
  else if (activeSettings) applyMode('settings');
})();
</script>
'''

insert_at = text.lower().rfind('</body>')
if insert_at == -1:
    raise SystemExit('Could not find </body>')
text = text[:insert_at] + patch + '\n' + text[insert_at:]
path.write_text(text, encoding='utf-8')
print('Applied Branding + Users Integration V10')
