// ===== Mobile Menu Toggle =====
const menuButton = document.querySelector('[data-menu-toggle]');
const nav = document.querySelector('[data-main-nav]');
menuButton?.addEventListener('click', () => nav?.classList.toggle('open'));

// ===== Location Dialog =====
const locationDialog = document.querySelector('[data-location-dialog]');
document.querySelector('[data-location-button]')?.addEventListener('click', () => locationDialog?.showModal());
document.querySelectorAll('[data-location-close]').forEach((button) => {
  button.addEventListener('click', () => locationDialog?.close());
});

// ===== Flash Message Close =====
document.querySelector('[data-flash-close]')?.addEventListener('click', (event) => {
  event.currentTarget.closest('.flash')?.remove();
});

// ===== Category Carousel =====
(function() {
  const carousel = document.getElementById('categoryCarousel');
  if (!carousel) return;
  
  const prevBtn = document.querySelector('.carousel-prev');
  const nextBtn = document.querySelector('.carousel-next');
  const cardWidth = 180; // card width + gap
  
  function updateArrows() {
    if (prevBtn) {
      prevBtn.classList.toggle('hidden', carousel.scrollLeft <= 10);
    }
    if (nextBtn) {
      const maxScroll = carousel.scrollWidth - carousel.clientWidth;
      nextBtn.classList.toggle('hidden', carousel.scrollLeft >= maxScroll - 10);
    }
  }
  
  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      carousel.scrollBy({ left: -cardWidth * 2, behavior: 'smooth' });
    });
  }
  
  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      carousel.scrollBy({ left: cardWidth * 2, behavior: 'smooth' });
    });
  }
  
  carousel.addEventListener('scroll', updateArrows);
  window.addEventListener('resize', updateArrows);
  updateArrows();
  
  // Optional: Auto-scroll (uncomment if you want)
  /*
  let autoScroll;
  function startAutoScroll() {
    autoScroll = setInterval(() => {
      const maxScroll = carousel.scrollWidth - carousel.clientWidth;
      if (carousel.scrollLeft >= maxScroll - 10) {
        carousel.scrollTo({ left: 0, behavior: 'smooth' });
      } else {
        carousel.scrollBy({ left: cardWidth, behavior: 'smooth' });
      }
    }, 4000);
  }
  startAutoScroll();
  carousel.addEventListener('mouseenter', () => clearInterval(autoScroll));
  carousel.addEventListener('mouseleave', startAutoScroll);
  */
})();