// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
  anchor.addEventListener("click", function (e) {
    e.preventDefault();
    document.querySelector(this.getAttribute("href")).scrollIntoView({
      behavior: "smooth",
    });
  });
});

// Animation on scroll (basic fade-in effect)
const sections = document.querySelectorAll(".section");
const options = {
  threshold: 0.25, // Trigger when 25% of the section is visible
  rootMargin: "0px 0px -100px 0px", // Preload before fully visible
};

// Intersection Observer for section animation
const sectionObserver = new IntersectionObserver((entries, observer) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add("fade-in");
      observer.unobserve(entry.target);
    }
  });
}, options);

sections.forEach((section) => {
  section.classList.add("fade-out"); // Initially hide sections
  sectionObserver.observe(section);
});

// Add a greeting when the Hero button is clicked
const heroButton = document.querySelector(".btn-primary");
if (heroButton) {
  heroButton.addEventListener("click", () => {
    alert("Welcome to BuddyBot! Let’s explore the amazing features!");
  });
}
