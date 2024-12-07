// Initialize AOS (Animate On Scroll)
AOS.init({
  duration: 1200,  // Duration of the animation
  easing: 'ease-in-out',  // Easing type for the animation
});

// Smooth Scroll for links
document.querySelectorAll('.scrollto').forEach(anchor => {
  anchor.addEventListener('click', function (e) {
    e.preventDefault();
    document.querySelector(this.getAttribute('href')).scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  });
});

// Activate mobile navigation toggle
const mobileNavToggle = document.querySelector('.mobile-nav-toggle');
const navbar = document.getElementById('navbar');
mobileNavToggle.addEventListener('click', () => {
  navbar.classList.toggle('navbar-mobile');
});

// Close the mobile menu when a link is clicked
document.querySelectorAll('#navbar .nav-link').forEach(link => {
  link.addEventListener('click', () => {
    if (navbar.classList.contains('navbar-mobile')) {
      navbar.classList.remove('navbar-mobile');
    }
  });
});

// Scroll to top button visibility
const scrollTopBtn = document.querySelector('.back-to-top');
window.addEventListener('scroll', () => {
  if (window.scrollY > 100) {
    scrollTopBtn.classList.add('active');
  } else {
    scrollTopBtn.classList.remove('active');
  }
});

// Show back-to-top button when scrolled down
scrollTopBtn.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// Example of smooth fade-in effect for elements as they come into view
window.addEventListener('load', () => {
  // Add your custom functionality here if needed
});
