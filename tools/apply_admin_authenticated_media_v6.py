from pathlib import Path

path = Path('backend/static/admin.html')
text = path.read_text(encoding='utf-8')
marker = '/* ===== Authenticated Media + Branding Layout V6 ===== */'
if marker in text:
    raise SystemExit('V6 already applied')

css = r'''

    /* ===== Authenticated Media + Branding Layout V6 ===== */
    .branding-media-grid {
      display:grid;
      grid-template-columns:minmax(260px,1fr) minmax(300px,1fr);
      gap:14px;
      margin:16px 0;
      align-items:start;
    }
    .branding-media-card {
      min-width:0;
      height:100%;
      padding:14px;
      border:1px solid rgba(225,184,85,.16);
      border-radius:12px;
      background:rgba(7,16,23,.48);
    }
    .branding-media-card > :first-child { margin-top:0 !important; }
    .branding-media-card #app-logo-preview,
    .branding-media-card #app-hero-preview { min-height:190px; }
    .branding-media-card #app-logo-image {
      width:min(100%,220px) !important;
      height:auto !important;
      aspect-ratio:1/1;
      margin:0 auto;
    }
    .branding-media-card #app-hero-image {
      width:min(100%,220px) !important;
      max-height:300px;
      margin:0 auto;
    }
    #setup-status-card.branding-status-always-open {
      display:block !important;
      max-height:none !important;
      overflow:visible !important;
    }
    #setup-status-card.branding-status-always-open .compact-card-body {
      display:block !important;
    }
    @media (max-width:860px) {
      .branding-media-grid { grid-template-columns:1fr; }
    }
'''
text = text.replace('</style>', css + '\n</style>', 1)

js = r'''
<script>
/* ===== Authenticated Media + Branding Layout V6 ===== */
(() => {
  const objectUrls = new WeakMap();
  const loading = new WeakSet();

  async function loadProtectedImage(img) {
    if (!(img instanceof HTMLImageElement) || loading.has(img)) return;
    const src = img.getAttribute('src') || '';
    if (!src || src.startsWith('blob:') || src.startsWith('data:')) return;
    let url;
    try { url = new URL(src, window.location.href); } catch (_) { return; }
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return;
    if (!token) return;

    loading.add(img);
    try {
      const response = await fetch(url.href, {
        headers: {Authorization: `Bearer ${token}`},
        cache: 'no-store',
      });
      if (!response.ok) return;
      const blob = await response.blob();
      const previous = objectUrls.get(img);
      if (previous) URL.revokeObjectURL(previous);
      const objectUrl = URL.createObjectURL(blob);
      objectUrls.set(img, objectUrl);
      img.dataset.protectedSource = url.pathname + url.search;
      img.src = objectUrl;
    } catch (error) {
      console.debug('Vorschaubild konnte nicht geladen werden', url.pathname, error);
    } finally {
      loading.delete(img);
    }
  }

  function scanProtectedImages(root = document) {
    if (root instanceof HTMLImageElement) loadProtectedImage(root);
    root.querySelectorAll?.('img').forEach(loadProtectedImage);
  }

  const mediaObserver = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
      if (mutation.type === 'attributes' && mutation.target instanceof HTMLImageElement) {
        loadProtectedImage(mutation.target);
      }
      mutation.addedNodes.forEach(node => {
        if (node instanceof HTMLElement) scanProtectedImages(node);
      });
    });
  });
  mediaObserver.observe(document.documentElement, {subtree:true, childList:true, attributes:true, attributeFilter:['src']});
  scanProtectedImages();

  // A short periodic scan also catches images rendered immediately after login/token changes.
  setInterval(() => {
    if (token) scanProtectedImages(document);
  }, 1500);

  function collectRange(start, end) {
    const nodes = [];
    let node = start;
    while (node) {
      const next = node.nextSibling;
      nodes.push(node);
      if (node === end) break;
      node = next;
    }
    return nodes;
  }

  function arrangeBrandingMedia() {
    const form = document.getElementById('app-config-form');
    if (!form || form.querySelector('.branding-media-grid')) return;

    const logoPreview = document.getElementById('app-logo-preview');
    const heroPreview = document.getElementById('app-hero-preview');
    const logoLabel = Array.from(form.children).find(el =>
      el.tagName === 'LABEL' && el.textContent.trim() === 'Vereinslogo'
    );
    const heroHeading = Array.from(form.children).find(el =>
      el.tagName === 'H3' && el.textContent.trim().startsWith('Startseite / Hauptbild')
    );
    if (!logoLabel || !logoPreview || !heroHeading || !heroPreview) return;

    const grid = document.createElement('div');
    grid.className = 'branding-media-grid';
    const logoCard = document.createElement('div');
    logoCard.className = 'branding-media-card';
    const heroCard = document.createElement('div');
    heroCard.className = 'branding-media-card';

    const separator = heroHeading.previousElementSibling;
    if (separator?.tagName === 'HR') separator.remove();

    const logoNodes = collectRange(logoLabel, logoPreview);
    const heroNodes = collectRange(heroHeading, heroPreview);
    form.insertBefore(grid, logoLabel);
    grid.append(logoCard, heroCard);
    logoNodes.forEach(node => logoCard.appendChild(node));
    heroNodes.forEach(node => heroCard.appendChild(node));
  }

  function keepStatusOpen() {
    const status = document.getElementById('setup-status-card');
    if (!status) return;
    status.classList.add('branding-status-always-open', 'is-open');
    status.classList.remove('hidden');
    status.querySelectorAll('.compact-card-body').forEach(body => body.style.display = 'block');
  }

  function initBrandingLayout() {
    arrangeBrandingMedia();
    keepStatusOpen();
    const brandingButton = document.querySelector('nav button[data-system-target="branding"]');
    brandingButton?.addEventListener('click', () => {
      requestAnimationFrame(() => {
        arrangeBrandingMedia();
        keepStatusOpen();
        scanProtectedImages(document.getElementById('system') || document);
      });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initBrandingLayout, {once:true});
  } else {
    initBrandingLayout();
  }
})();
</script>
'''
text = text.replace('</body>', js + '\n</body>', 1)
path.write_text(text, encoding='utf-8')
print('Applied authenticated media loader and compact branding media layout V6')
