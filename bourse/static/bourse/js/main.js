// Éviter les redéclarations si main.js est chargé plusieurs fois
if (typeof window._mainJsLoaded === 'undefined') {
  window._mainJsLoaded = true;

  // Messages auto-dismiss
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.msg').forEach(msg => {
      setTimeout(() => {
        msg.style.transition = 'opacity 0.4s';
        msg.style.opacity    = '0';
        setTimeout(() => msg.remove(), 400);
      }, 4000);
    });
  });

  // Polling fallback si WebSocket indisponible
  setTimeout(() => {
    const dot = document.querySelector('.ws-dot');
    if (dot && dot.classList.contains('off')) {
      const symboles = [...new Set(
        [...document.querySelectorAll('[data-prix-live]')].map(el => el.dataset.prixLive)
      )];
      if (!symboles.length) return;
      setInterval(async () => {
        for (const sym of symboles) {
          try {
            const resp = await fetch(`/api/prix/${sym}/`);
            const data = await resp.json();
            document.querySelectorAll(`[data-prix-live="${sym}"]`).forEach(el => {
              if (data.prix) el.textContent = parseFloat(data.prix).toFixed(2);
            });
          } catch(e) {}
        }
      }, 30000);
    }
  }, 5000);
}