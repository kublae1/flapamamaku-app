from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')

# Ensure all neutral app-logo fallbacks use the actually exposed root route.
text = text.replace("const APP_LOGO = '/static/flapamamaku-icon.png';", "const APP_LOGO = '/flapamamaku-icon.png';")
text = text.replace('src="/static/flapamamaku-icon.png"', 'src="/flapamamaku-icon.png"')

css_marker = '/* ===== Published Content Preview V1 ===== */'
if css_marker not in text:
    css = r'''

    /* ===== Published Content Preview V1 ===== */
    .entry-preview-button {
      border:1px solid rgba(225,184,85,.30) !important;
      background:rgba(225,184,85,.08) !important;
      color:#f2d17f !important;
    }
    .published-preview-modal {
      position:fixed;
      inset:0;
      z-index:3000;
      display:none;
      align-items:center;
      justify-content:center;
      padding:22px;
      background:rgba(0,0,0,.78);
      backdrop-filter:blur(8px);
    }
    .published-preview-modal.open { display:flex; }
    .published-preview-shell {
      width:min(100%,980px);
      max-height:92vh;
      display:grid;
      grid-template-columns:minmax(0,1fr) 360px;
      overflow:hidden;
      border:1px solid rgba(225,184,85,.28);
      border-radius:20px;
      background:#071017;
      box-shadow:0 30px 100px rgba(0,0,0,.55);
    }
    .published-preview-main {
      min-width:0;
      padding:22px;
      overflow:auto;
    }
    .published-preview-topbar {
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
      margin-bottom:16px;
      padding-bottom:12px;
      border-bottom:1px solid rgba(255,255,255,.08);
    }
    .published-preview-topbar strong {
      color:#f2d17f;
      font-size:18px;
    }
    .published-preview-close {
      border:1px solid rgba(255,255,255,.12);
      background:#14222c;
      color:white;
      border-radius:9px;
      padding:8px 12px;
      cursor:pointer;
      font-weight:800;
    }
    .published-preview-content {
      color:#e8eef1;
      line-height:1.55;
    }
    .published-preview-content .actions,
    .published-preview-content button,
    .published-preview-content input,
    .published-preview-content select,
    .published-preview-content textarea { display:none !important; }
    .published-preview-content img {
      max-width:100%;
      height:auto;
      border-radius:12px;
      display:block;
      margin:12px auto;
    }
    .published-preview-content a {
      color:#f2d17f;
      word-break:break-word;
    }
    .published-preview-phone {
      background:linear-gradient(180deg,#0d1820,#081118);
      border-left:1px solid rgba(255,255,255,.08);
      padding:20px;
      overflow:auto;
    }
    .published-preview-phone-frame {
      width:100%;
      min-height:560px;
      border:7px solid #020405;
      border-radius:32px;
      overflow:hidden;
      background:#111315;
      box-shadow:0 18px 45px rgba(0,0,0,.42);
    }
    .published-preview-phone-head {
      padding:18px 14px 14px;
      text-align:center;
      background:#061018;
      color:#f2d17f;
      font-weight:900;
      letter-spacing:.5px;
    }
    .published-preview-phone-body {
      padding:16px;
      color:#f2f5f6;
    }
    .published-preview-phone-body h3 {
      margin:0 0 10px;
      font-size:20px;
      color:white;
    }
    .published-preview-phone-body .preview-phone-meta {
      margin-bottom:12px;
      color:rgba(230,236,240,.58);
      font-size:12px;
    }
    .published-preview-phone-body .preview-phone-copy {
      white-space:pre-wrap;
      line-height:1.5;
      font-size:14px;
    }
    .published-preview-phone-body img {
      width:100%;
      height:auto;
      border-radius:10px;
      margin:0 0 14px;
    }
    @media (max-width:820px) {
      .published-preview-shell { grid-template-columns:1fr; }
      .published-preview-phone { display:none; }
    }
'''
    text = text.replace('</style>', css + '\n</style>', 1)

js_marker = '/* ===== Published Content Preview V1 ===== */'
if js_marker not in text:
    js = r'''
<script>
(() => {
  /* ===== Published Content Preview V1 ===== */
  const previewSources = [
    ['news-list', 'News'],
    ['events-list', 'Termine'],
    ['members-list', 'Mitglieder'],
    ['content-list', 'Veröffentlichter Inhalt']
  ];

  const modal = document.createElement('div');
  modal.className = 'published-preview-modal';
  modal.innerHTML = `
    <div class="published-preview-shell" role="dialog" aria-modal="true" aria-label="Vorschau">
      <div class="published-preview-main">
        <div class="published-preview-topbar">
          <strong id="published-preview-heading">Vorschau</strong>
          <button type="button" class="published-preview-close">Schliessen</button>
        </div>
        <div id="published-preview-content" class="published-preview-content"></div>
      </div>
      <aside class="published-preview-phone">
        <div class="published-preview-phone-frame">
          <div class="published-preview-phone-head" id="published-preview-app-name">Vereins-App</div>
          <div class="published-preview-phone-body" id="published-preview-phone-body"></div>
        </div>
      </aside>
    </div>`;
  document.body.appendChild(modal);

  const closePreview = () => modal.classList.remove('open');
  modal.querySelector('.published-preview-close')?.addEventListener('click', closePreview);
  modal.addEventListener('click', event => { if (event.target === modal) closePreview(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closePreview(); });

  function plainText(node) {
    const clone = node.cloneNode(true);
    clone.querySelectorAll('button,.actions,input,select,textarea').forEach(el => el.remove());
    return (clone.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function titleOf(entry) {
    return entry.querySelector('h1,h2,h3,strong')?.textContent?.trim() || plainText(entry).slice(0,80) || 'Vorschau';
  }

  function previewEntry(entry, sectionLabel) {
    const clean = entry.cloneNode(true);
    clean.querySelectorAll('button,.actions,input,select,textarea').forEach(el => el.remove());
    clean.removeAttribute('draggable');

    const title = titleOf(entry);
    const allText = plainText(entry);
    const detail = allText.replace(title, '').trim();
    const image = clean.querySelector('img');
    const imageHtml = image ? `<img src="${image.getAttribute('src') || ''}" alt="">` : '';
    const tenantName = document.getElementById('tenant-context-name')?.textContent?.trim() || 'Vereins-App';

    document.getElementById('published-preview-heading').textContent = `${sectionLabel} · Vorschau`;
    document.getElementById('published-preview-content').innerHTML = clean.outerHTML;
    document.getElementById('published-preview-app-name').textContent = tenantName;
    document.getElementById('published-preview-phone-body').innerHTML = `
      ${imageHtml}
      <div class="preview-phone-meta">${sectionLabel}</div>
      <h3>${escapePreviewHtml(title)}</h3>
      <div class="preview-phone-copy">${escapePreviewHtml(detail)}</div>`;
    modal.classList.add('open');
  }

  function escapePreviewHtml(value) {
    return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  }

  function enhanceList(list, sectionLabel) {
    if (!list) return;
    list.querySelectorAll('.entry').forEach(entry => {
      if (entry.dataset.previewReady === '1') return;
      entry.dataset.previewReady = '1';
      let actions = entry.querySelector('.actions');
      if (!actions) {
        actions = document.createElement('div');
        actions.className = 'actions';
        entry.appendChild(actions);
      }
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'entry-preview-button';
      button.textContent = 'Vorschau';
      button.addEventListener('click', event => {
        event.preventDefault();
        event.stopPropagation();
        previewEntry(entry, sectionLabel);
      });
      actions.prepend(button);
    });
  }

  function enhanceAll() {
    previewSources.forEach(([id, label]) => enhanceList(document.getElementById(id), label));
  }

  const observer = new MutationObserver(enhanceAll);
  previewSources.forEach(([id]) => {
    const list = document.getElementById(id);
    if (list) observer.observe(list, {childList:true, subtree:true});
  });
  enhanceAll();
  setTimeout(enhanceAll, 500);
  setTimeout(enhanceAll, 1500);
})();
</script>
'''
    text = text.replace('</body>', js + '\n</body>', 1)

path.write_text(text, encoding='utf-8')
