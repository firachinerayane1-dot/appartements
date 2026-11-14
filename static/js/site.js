const toggle = document.querySelector('.nav-toggle');
const nav = document.querySelector('.main-nav');
if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!open));
    nav.classList.toggle('is-open', !open);
  });
}
const dismissToast = toast => {
  if (!toast || toast.classList.contains('is-closing')) return;
  toast.classList.add('is-closing');
  window.setTimeout(() => toast.remove(), 250);
};
document.querySelectorAll('.toast').forEach(toast => {
  const button = toast.querySelector('button');
  if (button) button.addEventListener('click', () => dismissToast(toast));
  window.setTimeout(() => dismissToast(toast), 2000);
});

const dayAfter = value => {
  if (!value) return '';
  const date = new Date(`${value}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + 1);
  return date.toISOString().split('T')[0];
};
const arrival = document.getElementById('home-arrivee');
const departure = document.getElementById('home-depart');
if (arrival && departure) {
  const today = new Date().toISOString().split('T')[0];
  arrival.min = today;
  departure.min = arrival.value ? dayAfter(arrival.value) : dayAfter(today);
  arrival.addEventListener('change', () => {
    departure.min = dayAfter(arrival.value || today);
    if (departure.value && departure.value <= arrival.value) departure.value = '';
  });
}

const catalogArrival = document.getElementById('id_date_debut');
const catalogDeparture = document.getElementById('id_date_fin');
if (catalogArrival && catalogDeparture && !document.body.classList.contains('admin-workspace')) {
  const today = new Date().toISOString().split('T')[0];
  catalogArrival.min = today;
  catalogDeparture.min = dayAfter(catalogArrival.value || today);
  catalogArrival.addEventListener('change', () => {
    catalogDeparture.min = dayAfter(catalogArrival.value || today);
    if (catalogDeparture.value && catalogDeparture.value <= catalogArrival.value) {
      catalogDeparture.value = '';
    }
  });

  const priceSummary = document.getElementById('booking-price-summary');
  const liveSummary = document.getElementById('booking-live-summary');
  const liveNights = document.getElementById('booking-live-nights');
  const liveTotal = document.getElementById('booking-live-total');
  const totalRow = document.getElementById('booking-total-row');
  const totalValue = document.getElementById('booking-total-value');
  const updateBookingTotal = () => {
    if (!priceSummary) return;
    const mobileTotal = document.getElementById('mobile-booking-total');
    if (liveSummary) liveSummary.hidden = true;
    if (totalRow) totalRow.hidden = true;
    if (mobileTotal) mobileTotal.textContent = `${priceSummary.dataset.nightlyRate} MAD / nuit`;
    if (!catalogArrival.value || !catalogDeparture.value) return;
    const start = new Date(`${catalogArrival.value}T00:00:00Z`);
    const end = new Date(`${catalogDeparture.value}T00:00:00Z`);
    const nights = Math.round((end - start) / 86400000);
    if (!Number.isFinite(nights) || nights <= 0) return;
    const rate = Number(priceSummary.dataset.nightlyRate.replace(',', '.'));
    const total = new Intl.NumberFormat('fr-FR', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(rate * nights);
    if (mobileTotal) mobileTotal.textContent = `${total} MAD`;
    if (liveSummary && liveNights && liveTotal) {
      liveNights.textContent = `${nights} nuit${nights > 1 ? 's' : ''}`;
      liveTotal.textContent = `Total du séjour : ${total} MAD`;
      liveSummary.hidden = false;
    }
    if (totalRow && totalValue) {
      totalRow.querySelector('dt').textContent = `Total du séjour · ${nights} nuit${nights > 1 ? 's' : ''}`;
      totalValue.textContent = `${total} MAD`;
      totalRow.hidden = false;
    }
  };
  catalogArrival.addEventListener('change', updateBookingTotal);
  catalogDeparture.addEventListener('change', updateBookingTotal);
  updateBookingTotal();
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
    '.stay-gallery-heading > *',
    '.catalog-assurance article',
    '.reservations-hero-copy > *',
    '.reservations-hero-visual',
    '.reservation-overview article',
    '.reservation-list-heading > *',
    '.reservation-card',
    '.reservations-empty > *',
    '.reservations-assurance .shell > *',
    '.booking-hero-content > *',
    '.booking-confirm-card > *',
    '.booking-property-card',
    '.reservation-detail-heading > *',
    '.reservation-progress li',
    '.reservation-stay-card',
    '.reservation-information-card',
    '.reservation-action-card > *',
    '.policies-hero-content > *',
    '.policies-document-heading > *',
    '.policy-group',
    '.policy-list article',
    '.policies-accept-card > *',
  ].join(','));
  revealItems.forEach((item, index) => {
    item.classList.add('scroll-reveal');
    const group = item.parentElement;
    const siblings = group ? [...group.children].filter(child => child.matches('.property-card, .feature-grid article, .stat-card, .notification-card, .reservation-card, .reservation-overview article')) : [];
    const position = siblings.indexOf(item);
    if (position >= 0) item.style.setProperty('--reveal-delay', `${Math.min(position, 4) * 30}ms`);
  });

  const imageItems = document.querySelectorAll('.residence-gallery figure, .map-card, .gallery, .stay-gallery-item, .reservation-card-media, .reservations-empty-image, .booking-property-image, .reservation-stay-image');
  imageItems.forEach((item, index) => {
    item.classList.add('image-reveal');
    item.style.setProperty('--reveal-delay', `${Math.min(index, 4) * 25}ms`);
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

// Garder les valeurs des boutons nommés dans la requête native du formulaire.
const pendingForms = new Map();
const submissionStatus = document.createElement('p');
submissionStatus.className = 'sr-only';
submissionStatus.setAttribute('role', 'status');
document.body.append(submissionStatus);
document.addEventListener('submit', event => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || event.defaultPrevented || form.method === 'dialog') return;
  if (pendingForms.has(form)) {
    event.preventDefault();
    return;
  }
  const buttons = [...form.elements].filter(element =>
    (element instanceof HTMLButtonElement || element instanceof HTMLInputElement) &&
    element.type === 'submit' && !element.disabled
  );
  const originals = buttons.map(button => ({
    button, html: button.innerHTML, ariaDisabled: button.getAttribute('aria-disabled'),
  }));
  pendingForms.set(form, { originals, busy: form.getAttribute('aria-busy') });
  form.setAttribute('aria-busy', 'true');
  buttons.forEach(button => {
    button.setAttribute('aria-disabled', 'true');
    if (button instanceof HTMLButtonElement) {
      button.innerHTML = '<span class="submission-spinner" aria-hidden="true"></span><span>Envoi en cours…</span>';
    }
  });
  submissionStatus.textContent = 'Envoi en cours, veuillez patienter…';
});
window.addEventListener('pageshow', () => {
  pendingForms.forEach(({ originals, busy }, form) => {
    if (busy === null) form.removeAttribute('aria-busy');
    else form.setAttribute('aria-busy', busy);
    originals.forEach(({ button, html, ariaDisabled }) => {
      button.innerHTML = html;
      if (ariaDisabled === null) button.removeAttribute('aria-disabled');
      else button.setAttribute('aria-disabled', ariaDisabled);
    });
  });
  pendingForms.clear();
  submissionStatus.textContent = '';
});

const mobileBookingBar = document.querySelector('.mobile-booking-bar');
if (mobileBookingBar && 'ResizeObserver' in window) {
  new ResizeObserver(() => {
    document.documentElement.style.setProperty('--booking-bar-height', `${mobileBookingBar.getBoundingClientRect().height}px`);
  }).observe(mobileBookingBar);
}
