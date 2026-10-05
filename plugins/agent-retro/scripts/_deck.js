(() => {
  const deck = document.getElementById('deck'), slides = [...deck.querySelectorAll('.slide')];
  if (!slides.length) return;
  const prog = document.getElementById('progress'), reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  slides.forEach(() => { const s = document.createElement('span'); s.appendChild(document.createElement('i')); prog.appendChild(s); });
  const segs = [...prog.children];
  slides.forEach((s, i) => { if (i > 0) s.classList.add('armed'); });
  slides[0].classList.add('in');
  document.querySelectorAll('.tryb').forEach(box => {
    const b = document.createElement('button'); b.type = 'button'; b.textContent = 'Copy';
    b.addEventListener('click', ev => { ev.stopPropagation(); const code = box.querySelector('code');
      const sel = () => { const r = document.createRange(); r.selectNodeContents(code); const s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = 'Selected'; };
      try { navigator.clipboard.writeText(code.textContent).then(() => { b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy', 1500); }, sel); } catch (_) { sel(); } });
    box.appendChild(b);
  });
  document.querySelectorAll('.checks button').forEach(b => b.addEventListener('click', ev => { ev.stopPropagation();
    const on = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', on); b.closest('li').classList.toggle('done', on); }));
  const fmt = n => Math.round(n).toLocaleString('en-US');
  const countUp = el => { if (reduce || el.dataset.done) return; el.dataset.done = 1;
    const target = +el.dataset.count, t0 = performance.now(), dur = target > 1e6 ? 1800 : 1100;
    const step = t => { const p = Math.min(1, (t - t0) / dur), k = 1 - Math.pow(1 - p, 4); el.textContent = fmt(target * k); if (p < 1) requestAnimationFrame(step); else el.textContent = fmt(target); };
    requestAnimationFrame(step); };
  const confetti = cv => { if (reduce || cv.dataset.done) return; cv.dataset.done = 1;
    const ctx = cv.getContext('2d'), dpr = devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight; cv.width = W * dpr; cv.height = H * dpr; ctx.scale(dpr, dpr);
    const cols = ['#ff4fae', '#1f6fd1', '#11a768', '#ff6b35', '#1d1b3f'];
    const ps = Array.from({ length: 160 }, () => ({ x: W / 2, y: H * .42, vx: (Math.random() - .5) * 16, vy: -Math.random() * 15 - 4, s: Math.random() * 8 + 5, r: Math.random() * 6, vr: (Math.random() - .5) * .3, c: cols[Math.random() * cols.length | 0], o: Math.random() < .35 }));
    const t0 = performance.now();
    const tick = t => { ctx.clearRect(0, 0, W, H);
      for (const p of ps) { p.vy += .38; p.vx *= .99; p.x += p.vx; p.y += p.vy; p.r += p.vr; ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.fillStyle = p.c;
        if (p.o) { ctx.beginPath(); ctx.arc(0, 0, p.s / 2, 0, 7); ctx.fill(); } else ctx.fillRect(-p.s / 2, -p.s / 4, p.s, p.s / 2); ctx.restore(); }
      if (t - t0 < 4200) requestAnimationFrame(tick); else ctx.clearRect(0, 0, W, H); };
    requestAnimationFrame(tick); };
  let cur = 0;
  const setActive = i => { cur = i; const s = slides[i]; s.classList.add('in'); s.querySelectorAll('[data-count]').forEach(countUp);
    const cv = s.querySelector('.confetti'); if (cv) setTimeout(() => confetti(cv), 350);
    document.documentElement.style.setProperty('--pfg', s.dataset.fg); segs.forEach((g, j) => g.classList.toggle('done', j <= i)); };
  const io = new IntersectionObserver(es => es.forEach(x => { if (x.isIntersecting) setActive(slides.indexOf(x.target)); }), { root: deck, rootMargin: '-45% 0px -45% 0px', threshold: 0 });
  slides.forEach(s => io.observe(s)); setActive(0);
  // fallback: whenever scrolling settles, activate the slide under the middle of the screen
  let settle; const check = () => { const mid = innerHeight / 2;
    const i = slides.findIndex(s => { const r = s.getBoundingClientRect(); return r.top <= mid && r.bottom >= mid; });
    if (i >= 0 && (i !== cur || !slides[i].classList.contains('in'))) setActive(i); };
  deck.addEventListener('scroll', () => { clearTimeout(settle); settle = setTimeout(check, 90); }, { passive: true });
  const go = i => { i = Math.max(0, Math.min(slides.length - 1, i)); deck.scrollTo({ top: slides[i].offsetTop, behavior: reduce ? 'auto' : 'smooth' }); };
  document.getElementById('next').onclick = () => go(cur + 1); document.getElementById('prev').onclick = () => go(cur - 1);
  addEventListener('keydown', ev => {
    if (ev.defaultPrevented || ev.altKey || ev.ctrlKey || ev.metaKey ||
        (ev.target instanceof Element && ev.target.closest('button, a, input, textarea, select, [contenteditable]'))) return;
    if (['ArrowDown', 'ArrowRight', 'PageDown', ' '].includes(ev.key)) { ev.preventDefault(); go(cur + 1); }
    else if (['ArrowUp', 'ArrowLeft', 'PageUp'].includes(ev.key)) { ev.preventDefault(); go(cur - 1); } });
  deck.addEventListener('click', ev => { if (ev.target.closest('button, a, q, .quote, .tryb')) return; const x = ev.clientX / innerWidth; if (x > .72) go(cur + 1); else if (x < .28) go(cur - 1); });
})();
