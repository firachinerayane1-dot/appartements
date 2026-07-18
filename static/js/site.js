const toggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.main-nav');
if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!open));
    nav.classList.toggle('is-open', !open);
  });
}
document.querySelectorAll('.toast button').forEach(button => {
  button.addEventListener('click', () => button.closest('.toast').remove());
});
const arrival = document.getElementById('home-arrivee');
const departure = document.getElementById('home-depart');
if (arrival && departure) {
  const today = new Date().toISOString().split('T')[0];
  arrival.min = today;
  departure.min = today;
  arrival.addEventListener('change', () => {
    departure.min = arrival.value;
    if (departure.value && departure.value <= arrival.value) departure.value = '';
  });
}

/* Animations déclenchées au défilement. La classe motion-ready évite de
   masquer du contenu lorsque JavaScript n'est pas disponible. */
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (!reducedMotion && 'IntersectionObserver' in window) {
  document.documentElement.classList.add('motion-ready');

  const revealItems = document.querySelectorAll([
    '.section-heading',
    '.residence-intro',
    '.location-copy',
    '.page-heading',
    '.property-card',
    '.feature-grid article',
    '.stat-card',
    '.notification-card',
    '.cta-panel > *',
  ].join(','));
  revealItems.forEach((item, index) => {
    item.classList.add('scroll-reveal');
    const group = item.parentElement;
    const siblings = group ? [...group.children].filter(child => child.matches('.property-card, .feature-grid article, .stat-card, .notification-card')) : [];
    const position = siblings.indexOf(item);
    if (position >= 0) item.style.setProperty('--reveal-delay', `${Math.min(position, 4) * 90}ms`);
  });

  const imageItems = document.querySelectorAll('.residence-gallery figure, .map-card, .gallery');
  imageItems.forEach((item, index) => {
    item.classList.add('image-reveal');
    item.style.setProperty('--reveal-delay', `${Math.min(index, 4) * 80}ms`);
  });

  const observer = new IntersectionObserver((entries, activeObserver) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      activeObserver.unobserve(entry.target);
    });
  }, { threshold: 0.05, rootMargin: '0px 0px -2% 0px' });

  document.querySelectorAll('.scroll-reveal, .image-reveal').forEach(item => observer.observe(item));
}
