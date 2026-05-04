// Hero image parallax effect
const heroImage = document.querySelector('.hero-image');
if (heroImage) {
  window.addEventListener('scroll', () => {
    const scrolled = window.scrollY;
    heroImage.style.transform = `translateY(${scrolled * 0.08}px) scale(1.01)`;
  });
}

// Animate fade-in on scroll for cards
function animateOnScroll() {
  const elements = document.querySelectorAll('.feature-card, .scooter-card, .testimonial-card');
  const trigger = window.innerHeight * 0.92;
  elements.forEach((el, i) => {
    const rect = el.getBoundingClientRect();
    if (rect.top < trigger) {
      el.style.opacity = 1;
      el.style.transform = 'translateY(0)';
      el.style.transition = `opacity 0.5s ${0.1 + i * 0.08}s, transform 0.5s ${0.1 + i * 0.08}s`;
    }
  });
}
window.addEventListener('scroll', animateOnScroll);
window.addEventListener('DOMContentLoaded', () => {
  // Initial state for cards
  document.querySelectorAll('.feature-card, .scooter-card, .testimonial-card').forEach((el) => {
    el.style.opacity = 0;
    el.style.transform = 'translateY(32px)';
  });
  animateOnScroll();
});

// Button micro-interaction
document.querySelectorAll('.btn').forEach(btn => {
  btn.addEventListener('mousedown', () => {
    btn.style.transform += ' scale(0.97)';
  });
  btn.addEventListener('mouseup', () => {
    btn.style.transform = btn.style.transform.replace(' scale(0.97)', '');
  });
  btn.addEventListener('mouseleave', () => {
    btn.style.transform = btn.style.transform.replace(' scale(0.97)', '');
  });
});

// Navbar shadow on scroll
const navbar = document.querySelector('.navbar');
if (navbar) {
  window.addEventListener('scroll', () => {
    if (window.scrollY > 24) {
      navbar.style.boxShadow = '0 4px 24px rgba(0,0,0,0.08)';
      navbar.style.background = 'rgba(255,255,255,0.92)';
    } else {
      navbar.style.boxShadow = '0 2px 16px rgba(0,0,0,0.04)';
      navbar.style.background = 'rgba(255,255,255,0.75)';
    }
  });
}