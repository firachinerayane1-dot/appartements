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
