// Initialize AOS for animations
AOS.init({
  duration: 1000,
  easing: "ease-in-out",
  once: true,
});

// Scroll to Top Button functionality
const scrollTopBtn = document.querySelector(".back-to-top");
window.addEventListener("scroll", () => {
  if (window.scrollY > 100) {
    scrollTopBtn.classList.add("active");
  } else {
    scrollTopBtn.classList.remove("active");
  }
});

scrollTopBtn.addEventListener("click", () => {
  window.scrollTo({ top: 0, behavior: "smooth" });
});
