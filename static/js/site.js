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

const catalogArrival = document.getElementById('id_date_debut');
const catalogDeparture = document.getElementById('id_date_fin');
if (catalogArrival && catalogDeparture) {
  const today = new Date().toISOString().split('T')[0];
  catalogArrival.min = today;
  catalogDeparture.min = catalogArrival.value || today;
  catalogArrival.addEventListener('change', () => {
    catalogDeparture.min = catalogArrival.value || today;
    if (catalogDeparture.value && catalogDeparture.value <= catalogArrival.value) {
      catalogDeparture.value = '';
    }
  });
}

const focusDatesButton = document.querySelector('[data-focus-dates]');
const catalogSearch = document.getElementById('recherche');
if (focusDatesButton && catalogSearch && catalogArrival) {
  focusDatesButton.addEventListener('click', () => {
    catalogSearch.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
    window.setTimeout(() => catalogArrival.focus({ preventScroll: true }), reducedMotion ? 0 : 450);
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
    '.apartments-search',
    '.catalog-heading',
    '.dates-prompt > *',
    '.stay-gallery-heading > *',
    '.catalog-assurance article',
    '.reservations-hero-copy > *',
    '.reservations-hero-visual',
    '.reservation-overview article',
    '.reservation-list-heading > *',
    '.reservation-card',
    '.reservations-empty > *',
    '.reservations-assurance .shell > *',
  ].join(','));
  revealItems.forEach((item, index) => {
    item.classList.add('scroll-reveal');
    const group = item.parentElement;
    const siblings = group ? [...group.children].filter(child => child.matches('.property-card, .feature-grid article, .stat-card, .notification-card, .reservation-card, .reservation-overview article')) : [];
    const position = siblings.indexOf(item);
    if (position >= 0) item.style.setProperty('--reveal-delay', `${Math.min(position, 4) * 90}ms`);
  });

  const imageItems = document.querySelectorAll('.residence-gallery figure, .map-card, .gallery, .stay-gallery-item, .reservation-card-media, .reservations-empty-image');
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

const stayGallery = document.querySelector('.stay-gallery');
const galleryPrevious = document.querySelector('.gallery-control-prev');
const galleryNext = document.querySelector('.gallery-control-next');
const galleryProgress = document.querySelector('.gallery-progress span');

if (stayGallery && galleryPrevious && galleryNext) {
  const updateGallery = () => {
    const maximum = stayGallery.scrollWidth - stayGallery.clientWidth;
    const progress = maximum > 0 ? Math.min(1, Math.max(0, stayGallery.scrollLeft / maximum)) : 0;
    galleryPrevious.disabled = stayGallery.scrollLeft < 8;
    galleryNext.disabled = stayGallery.scrollLeft > maximum - 8;
    if (galleryProgress) galleryProgress.style.transform = `scaleX(${1 + progress * 5})`;
  };

  const moveGallery = direction => {
    const item = stayGallery.querySelector('.stay-gallery-item');
    const distance = item ? item.getBoundingClientRect().width + 16 : stayGallery.clientWidth * .8;
    stayGallery.scrollBy({ left: distance * direction, behavior: reducedMotion ? 'auto' : 'smooth' });
  };

  galleryPrevious.addEventListener('click', () => moveGallery(-1));
  galleryNext.addEventListener('click', () => moveGallery(1));
  stayGallery.addEventListener('scroll', updateGallery, { passive: true });
  window.addEventListener('resize', updateGallery, { passive: true });
  updateGallery();
}
