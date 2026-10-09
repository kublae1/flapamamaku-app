from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

old = '''      <button data-panel="content" data-section-target="archive">Vergangene Sujets</button>\n      <button data-panel="system" id="system-nav" data-permission="can_manage_settings">Einstellungen</button>'''
new = '''      <button data-panel="content" data-section-target="archive">Vergangene Sujets</button>\n      <button data-panel="system" data-system-target="branding" data-permission="can_manage_settings">Verein &amp; Branding</button>\n      <button data-panel="system" id="system-nav" data-permission="can_manage_settings">Einstellungen</button>'''
if old in text and 'data-system-target="branding"' not in text:
    text = text.replace(old, new, 1)

marker = '/* ===== Direct Branding Navigation V1 ===== */'
if marker not in text:
    js = r'''
<script>
(() => {
  /* ===== Direct Branding Navigation V1 ===== */
  document.querySelectorAll('#admin-view > nav button[data-system-target="branding"]').forEach(button => {
    button.addEventListener('click', () => {
      window.setTimeout(() => {
        const panel = document.getElementById('system');
        const form = document.getElementById('app-config-form');
        if (!panel || !form) return;

        // Centralized workspace: show the edit pane containing the existing
        // club name, colours and logo controls.
        const modeButton = panel.querySelector('.workspace-mode-switcher button[data-workspace-mode="edit"]');
        modeButton?.click();

        form.scrollIntoView({behavior:'smooth', block:'start'});
        form.animate?.([
          {boxShadow:'0 0 0 0 rgba(225,184,85,0)'},
          {boxShadow:'0 0 0 3px rgba(225,184,85,.30)'},
          {boxShadow:'0 0 0 0 rgba(225,184,85,0)'}
        ], {duration:900});
      }, 120);
    });
  });
})();
</script>
'''
    text = text.replace('</body>', js + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
