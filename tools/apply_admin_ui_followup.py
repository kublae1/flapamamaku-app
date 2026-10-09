from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

SUBPAGES = '/* ===== Admin Subpages Redesign V1 ===== */'
LOGIN = '/* ===== Admin Login Redesign V1 ===== */'
RESET = '/* Logged-out header reset */'

if SUBPAGES not in text:
    css = r'''

    /* ===== Admin Subpages Redesign V1 ===== */
    .panel:not(#dashboard) { padding-bottom:24px; }
    .panel:not(#dashboard) > .workspace-title,
    .panel:not(#dashboard) > .preview-heading {
      margin:0 0 12px; padding:14px 16px;
      border:1px solid rgba(225,184,85,.16); border-radius:12px;
      background:linear-gradient(135deg,rgba(225,184,85,.07),rgba(255,255,255,.018));
    }
    .panel:not(#dashboard) > .workspace-title h2,
    .panel:not(#dashboard) > .preview-heading h2 { color:#f2d17f; font-size:22px; }
    .panel:not(#dashboard) .grid {
      grid-template-columns:minmax(390px,.92fr) minmax(500px,1.28fr);
      gap:14px; align-items:start;
    }
    .panel:not(#dashboard) .card {
      margin-bottom:14px; padding:16px; border-radius:12px;
      background:linear-gradient(180deg,#0f1a22 0%,#0a141b 100%);
      border:1px solid rgba(255,255,255,.10); box-shadow:0 10px 30px rgba(0,0,0,.18);
    }
    .panel:not(#dashboard) form.card { position:relative; border-top-color:rgba(225,184,85,.45); }
    .panel:not(#dashboard) form.card::before {
      content:''; position:absolute; left:16px; right:16px; top:0; height:2px;
      border-radius:0 0 6px 6px; background:linear-gradient(90deg,var(--admin-gold),transparent 72%); opacity:.75;
    }
    .panel:not(#dashboard) .card h2 { margin:0 0 12px; font-size:18px; color:#f2d17f; }
    .panel:not(#dashboard) .card h3 { margin:14px 0 8px; font-size:15px; color:#f7e5b0; }
    .panel:not(#dashboard) label { margin:10px 0 5px; font-size:12px; color:#dfe6ea; }
    .panel:not(#dashboard) input,
    .panel:not(#dashboard) textarea,
    .panel:not(#dashboard) select {
      padding:9px 10px; border-radius:9px; background:#081118;
      border-color:rgba(255,255,255,.13); font-size:13px;
    }
    .panel:not(#dashboard) textarea { min-height:96px; }
    .panel:not(#dashboard) input:focus,
    .panel:not(#dashboard) textarea:focus,
    .panel:not(#dashboard) select:focus {
      border-color:rgba(225,184,85,.68); box-shadow:0 0 0 3px rgba(225,184,85,.10);
    }
    .panel:not(#dashboard) .primary {
      background:linear-gradient(180deg,#a21c27,#80131c);
      border:1px solid rgba(255,255,255,.08); border-radius:9px;
      padding:9px 14px; min-height:36px; font-size:12px;
    }
    .panel:not(#dashboard) .actions { gap:6px; margin-top:8px; }
    .panel:not(#dashboard) .actions button { padding:7px 10px; font-size:12px; background:#14222c; }
    .panel:not(#dashboard) .meta { font-size:12px; line-height:1.4; color:rgba(230,236,240,.62); }
    .panel:not(#dashboard) .entry,
    .panel:not(#dashboard) .content-list-card .entry {
      padding:10px 11px; margin:7px 0; border:1px solid rgba(255,255,255,.075);
      border-radius:9px; background:rgba(255,255,255,.025);
    }
    .panel:not(#dashboard) .entry:hover,
    .panel:not(#dashboard) .content-list-card .entry:hover {
      border-color:rgba(225,184,85,.22); background:rgba(225,184,85,.035);
    }
    .panel:not(#dashboard) .entry h3,
    .panel:not(#dashboard) .content-list-card .entry h3 {
      margin:0 0 4px; font-size:14px; color:#f4f7f8;
    }
    .panel:not(#dashboard) .section-switcher {
      gap:6px; margin:0 0 12px; padding:8px; border:1px solid rgba(255,255,255,.08);
      border-radius:11px; background:rgba(8,17,24,.75);
    }
    .panel:not(#dashboard) .section-switcher button {
      padding:7px 10px; font-size:11px; border-radius:8px; background:#111e27;
    }
    .panel:not(#dashboard) .section-switcher button.active {
      background:linear-gradient(180deg,rgba(225,184,85,.30),rgba(225,184,85,.15));
      color:#fff2c8; border-color:rgba(225,184,85,.42);
    }
    .panel:not(#dashboard) .preview-heading { margin-bottom:10px; }
    .panel:not(#dashboard) .preview-heading h2 { font-size:18px; }
    .panel:not(#dashboard) .effective-rights-box {
      margin:14px 0; padding:12px; border-radius:10px; background:#0a141a;
    }
    .panel:not(#dashboard) .effective-rights-grid { gap:8px; margin-top:10px; }
    .panel:not(#dashboard) .effective-right {
      min-height:48px; padding:9px 10px; border-radius:8px; font-size:12px;
    }
    .panel:not(#dashboard) .permission-grid { gap:8px 10px; }
    #content.panel .phone-preview { width:min(100%,300px); border-width:6px; border-radius:26px; margin-bottom:14px; }
    #content.panel .phone-preview-top { padding:12px 10px 10px; font-size:17px; }
    #content.panel .phone-preview-copy { padding:12px 14px 15px; }
    #members.panel #members-list,
    #users.panel #users-list,
    #events.panel #events-list,
    #news.panel #news-list,
    #content.panel #content-list,
    #push.panel #push-history,
    #billing.panel #billing-club-list,
    #billing.panel #billing-invoice-list {
      max-height:calc(100vh - 245px); overflow:auto; padding-right:3px;
      scrollbar-width:thin; scrollbar-color:rgba(225,184,85,.36) transparent;
    }
    @media (max-width:1180px) {
      .panel:not(#dashboard) .grid { grid-template-columns:minmax(320px,.9fr) minmax(0,1.1fr); }
    }
    @media (max-width:980px) {
      .panel:not(#dashboard) .grid { grid-template-columns:1fr; }
      #members.panel #members-list,
      #users.panel #users-list,
      #events.panel #events-list,
      #news.panel #news-list,
      #content.panel #content-list,
      #push.panel #push-history,
      #billing.panel #billing-club-list,
      #billing.panel #billing-invoice-list { max-height:none; overflow:visible; }
    }
'''
    text = text.replace('</style>', css + '\n</style>', 1)

if LOGIN not in text:
    css = r'''

    /* ===== Admin Login Redesign V1 ===== */
    body:has(#auth-view:not(.hidden)),
    body:has(#password-change-view:not(.hidden)) {
      min-height:100vh;
      background:
        radial-gradient(circle at 20% 0%, rgba(36,79,111,.22), transparent 34rem),
        radial-gradient(circle at 86% 10%, rgba(225,184,85,.09), transparent 28rem),
        linear-gradient(180deg,#071017 0%,#050b10 100%);
    }
    body:has(#auth-view:not(.hidden)) main,
    body:has(#password-change-view:not(.hidden)) main {
      min-height:calc(100vh - 76px); display:grid; place-items:center; padding:34px 20px;
    }
    #auth-view.auth-card,
    #password-change-view.auth-card {
      width:min(100%,460px); margin:0; padding:28px; border-radius:18px;
      border:1px solid rgba(225,184,85,.24);
      background:linear-gradient(180deg,rgba(15,27,36,.98),rgba(8,17,23,.98));
      box-shadow:0 28px 80px rgba(0,0,0,.42); position:relative; overflow:hidden;
    }
    #auth-view.auth-card::before,
    #password-change-view.auth-card::before {
      content:''; position:absolute; left:0; right:0; top:0; height:3px;
      background:linear-gradient(90deg,transparent,var(--admin-gold),transparent); opacity:.9;
    }
    .auth-brand { display:flex; flex-direction:column; align-items:center; text-align:center; margin:0 0 22px; }
    .auth-brand img {
      width:92px; height:92px; object-fit:contain; border-radius:20px; padding:8px;
      background:rgba(255,255,255,.035); border:1px solid rgba(225,184,85,.18);
      box-shadow:0 14px 34px rgba(0,0,0,.28);
    }
    .auth-brand strong { margin-top:13px; color:#f2d17f; font-size:19px; letter-spacing:.5px; }
    .auth-brand span { margin-top:4px; color:rgba(230,236,240,.58); font-size:12px; }
    #auth-view h2, #password-change-view h2 { margin:0 0 8px; text-align:center; color:#fff; font-size:24px; }
    #auth-view > p, #password-change-view > p {
      text-align:center; color:rgba(230,236,240,.62); font-size:13px; line-height:1.45; margin:0 0 18px;
    }
    #auth-view label, #password-change-view label { margin:12px 0 6px; font-size:12px; color:#dfe6ea; }
    #auth-view input, #auth-view select, #password-change-view input {
      min-height:44px; padding:10px 12px; border-radius:10px;
      background:#071017; border:1px solid rgba(255,255,255,.13); font-size:14px;
    }
    #auth-view .primary, #password-change-view .primary {
      width:100%; min-height:44px; margin-top:4px; border-radius:10px;
      background:linear-gradient(180deg,#a21c27,#7e131c); font-size:14px; font-weight:900;
    }
    body:has(#auth-view:not(.hidden)) .admin-user-box,
    body:has(#password-change-view:not(.hidden)) .admin-user-box,
    body:has(#auth-view:not(.hidden)) #logout-button,
    body:has(#password-change-view:not(.hidden)) #logout-button { display:none; }
    @media (max-width:680px) {
      body:has(#auth-view:not(.hidden)) main,
      body:has(#password-change-view:not(.hidden)) main { padding:18px 10px; }
      #auth-view.auth-card, #password-change-view.auth-card { padding:22px 18px; border-radius:15px; }
      .auth-brand img { width:78px; height:78px; }
    }
'''
    text = text.replace('</style>', css + '\n</style>', 1)

brand = '<div class="auth-brand"><img src="/static/flapamamaku-icon.png" alt="App-Logo"><strong>Vereins-App Administration</strong><span>Sichere Vereinsverwaltung</span></div>'
auth_marker = '<section id="auth-view" class="card auth-card">'
if brand not in text and auth_marker in text:
    text = text.replace(auth_marker, auth_marker + '\n    ' + brand, 1)

pwd_marker = '<section id="password-change-view" class="card auth-card hidden">'
if pwd_marker in text:
    start = text.find(pwd_marker)
    if 'auth-brand' not in text[start:start+500]:
        text = text.replace(pwd_marker, pwd_marker + '\n    ' + brand, 1)

text = text.replace(
    '<img id="header-club-logo" class="admin-header-logo no-image" alt="Vereinslogo">',
    '<img id="header-club-logo" class="admin-header-logo" src="/static/flapamamaku-icon.png" alt="App-Logo">'
)
text = text.replace(
    '<div class="admin-user-copy"><strong id="header-user-name">Admin</strong><span>Administration</span></div>',
    '<div class="admin-user-copy"><strong id="header-user-name"></strong><span>Administration</span></div>'
)

if RESET not in text:
    script = r'''
<script>
/* Logged-out header reset */
(function () {
  const APP_LOGO = '/static/flapamamaku-icon.png';
  function resetLoggedOutHeader() {
    const userName = document.getElementById('header-user-name');
    if (userName) userName.textContent = '';
    const logo = document.getElementById('header-club-logo');
    if (logo) {
      logo.src = APP_LOGO;
      logo.alt = 'App-Logo';
      logo.classList.remove('no-image');
    }
  }
  const logoutButton = document.getElementById('logout-button');
  if (logoutButton) logoutButton.addEventListener('click', () => window.setTimeout(resetLoggedOutHeader, 0));
  const adminView = document.getElementById('admin-view');
  if (adminView) {
    const observer = new MutationObserver(() => {
      if (adminView.classList.contains('hidden')) resetLoggedOutHeader();
    });
    observer.observe(adminView, {attributes:true, attributeFilter:['class']});
    if (adminView.classList.contains('hidden')) resetLoggedOutHeader();
  }
})();
</script>
'''
    text = text.replace('</body>', script + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
