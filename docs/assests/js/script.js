// Initialize AOS (Animate On Scroll) for animations when elements come into view
AOS.init({
  duration: 1200, // Duration of the animation (in milliseconds)
  easing: "ease-in-out", // Easing function for the animation
});

// Smooth Scroll for navigation links
document.querySelectorAll(".scrollto").forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault(); // Prevent the default anchor link behavior
    document.querySelector(this.getAttribute("href")).scrollIntoView({
      behavior: "smooth", // Smooth scrolling behavior
      block: "start", // Align the target section to the top
    });
  });
});

// Mobile Navigation Toggle (Hamburger Menu)
const mobileNavToggle = document.querySelector(".mobile-nav-toggle");
const navbar = document.getElementById("navbar");
mobileNavToggle.addEventListener("click", () => {
  navbar.classList.toggle("navbar-mobile"); // Toggle the 'navbar-mobile' class to show/hide the menu
});

// Close the mobile menu when a link is clicked
document.querySelectorAll("#navbar .nav-link").forEach((link) => {
  link.addEventListener("click", () => {
    if (navbar.classList.contains("navbar-mobile")) {
      navbar.classList.remove("navbar-mobile"); // Close the mobile menu when a link is clicked
    }
  });
});

// Scroll to top button visibility based on scroll position
const scrollTopBtn = document.querySelector(".back-to-top");
window.addEventListener("scroll", () => {
  if (window.scrollY > 100) {
    scrollTopBtn.classList.add("active"); // Show the back-to-top button when the user scrolls down 100px
  } else {
    scrollTopBtn.classList.remove("active"); // Hide the button if scrolled back to top
  }
});

// Scroll to top when the button is clicked
scrollTopBtn.addEventListener("click", () => {
  window.scrollTo({ top: 0, behavior: "smooth" }); // Smoothly scroll back to the top
});

// Example of smooth fade-in effect for elements as they come into view
window.addEventListener("load", () => {
  // Any additional custom functionality can be added here
});
