// ── Count-up numbers: add data-countup="24.2" to any element ──
document.querySelectorAll('[data-countup]').forEach(el => {
  const target = parseFloat(el.getAttribute('data-countup'));
  const decimals = el.getAttribute('data-countup').includes('.') ? 1 : 0;
  const suffix = el.getAttribute('data-suffix') || '';
  let started = false;

  const run = () => {
    if (started) return;
    started = true;
    const duration = 800;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = (eased * target).toFixed(decimals) + suffix;
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = target.toFixed(decimals) + suffix;
    };
    requestAnimationFrame(tick);
  };

  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) run(); });
  }, { threshold: 0.3 });
  obs.observe(el);
});

// ── Radial progress rings: add data-radial="72" (percent) to an SVG circle.fill ──
document.querySelectorAll('.radial-svg .fill').forEach(circle => {
  const pct = parseFloat(circle.getAttribute('data-radial')) || 0;
  const r = parseFloat(circle.getAttribute('r'));
  const circumference = 2 * Math.PI * r;
  circle.style.strokeDasharray = circumference;
  circle.style.strokeDashoffset = circumference;
  requestAnimationFrame(() => {
    circle.style.strokeDashoffset = circumference - (pct / 100) * circumference;
  });
});

// ── Live network canvas: <canvas id="liveNetwork" data-nodes="24" data-active="3"> ──
window.addEventListener('load', function () {
  const canvas = document.getElementById('liveNetwork');
  if (!canvas) return;

  const totalNodes = Math.min(parseInt(canvas.dataset.nodes || '0', 10), 40);
  const activeCount = Math.min(parseInt(canvas.dataset.active || '0', 10), totalNodes);

  if (totalNodes < 3) {
    canvas.style.display = 'none';
    const msg = document.createElement('p');
    msg.style.cssText = 'color: var(--muted); font-size: 13px; text-align: center; padding: 40px 0; margin: 0;';
    msg.textContent = 'Live network appears once the club has a few more members.';
    canvas.parentElement.appendChild(msg);
    return;
  }

  const ctx = canvas.getContext('2d');
  let W, H;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    W = rect.width;
    H = rect.height;
    canvas.width = W * devicePixelRatio;
    canvas.height = H * devicePixelRatio;
    ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  }
  resize();
  window.addEventListener('resize', resize);

  const style = getComputedStyle(document.documentElement);
  const accent = style.getPropertyValue('--hc-red').trim() || '#ec3750';
  const accentActive = style.getPropertyValue('--hc-green').trim() || '#33d6a6';

  const pts = Array.from({ length: totalNodes }, (_, i) => ({
    x: Math.random() * W,
    y: Math.random() * H,
    vx: (Math.random() - 0.5) * 0.3,
    vy: (Math.random() - 0.5) * 0.3,
    active: i < activeCount,
  }));

  function hexToRgba(hex, a) {
    const h = hex.replace('#', '');
    const r = parseInt(h.substring(0, 2), 16);
    const g = parseInt(h.substring(2, 4), 16);
    const b = parseInt(h.substring(4, 6), 16);
    return `rgba(${r},${g},${b},${a})`;
  }

  function tick() {
    ctx.clearRect(0, 0, W, H);
    pts.forEach(p => {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > W) p.vx *= -1;
      if (p.y < 0 || p.y > H) p.vy *= -1;
    });
    const maxDist = Math.min(W, H) * 0.55;
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const d = Math.hypot(pts[i].x - pts[j].x, pts[i].y - pts[j].y);
        if (d < maxDist) {
          ctx.strokeStyle = hexToRgba(accent, (1 - d / maxDist) * 0.3);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.stroke();
        }
      }
    }
    pts.forEach(p => {
      ctx.fillStyle = p.active ? accentActive : accent;
      ctx.globalAlpha = p.active ? 1 : 0.6;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.active ? 4 : 3, 0, 7);
      ctx.fill();
      ctx.globalAlpha = 1;
    });
    requestAnimationFrame(tick);
  }
  tick();
});