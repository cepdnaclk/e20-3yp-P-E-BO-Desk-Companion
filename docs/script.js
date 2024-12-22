// Smooth Scroll for Navigation Links with Offset
document.querySelectorAll("a.nav-link").forEach((link) => {
  link.addEventListener("click", function (e) {
    e.preventDefault();
    const target = document.querySelector(this.getAttribute("href"));
    if (target) {
      const offset = window.innerWidth < 768 ? 70 : 0; // Adjust offset for mobile
      const targetPosition =
        target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top: targetPosition, behavior: "smooth" });
    }
  });
});

// Dark Mode Toggle with Animation
const toggleDarkMode = () => {
  const body = document.body;
  body.classList.toggle("dark-mode");

  if (body.classList.contains("dark-mode")) {
    localStorage.setItem("theme", "dark");

    // Add a fade-in effect for dark mode
    body.animate(
      [
        { backgroundColor: "#fff", color: "#000" }, // From light
        { backgroundColor: "#121212", color: "#fff" }, // To dark
      ],
      { duration: 500, easing: "ease-in-out" }
    );
  } else {
    localStorage.setItem("theme", "light");

    // Add a fade-out effect for light mode
    body.animate(
      [
        { backgroundColor: "#121212", color: "#fff" }, // From dark
        { backgroundColor: "#fff", color: "#000" }, // To light
      ],
      { duration: 500, easing: "ease-in-out" }
    );
  }
};

// Persist Dark Mode
document.addEventListener("DOMContentLoaded", () => {
  const theme = localStorage.getItem("theme");
  if (theme === "dark") {
    document.body.classList.add("dark-mode");
  }
});

// Scroll Animation for Elements on Scroll
const animatedElements = document.querySelectorAll(".animate-on-scroll");

const observeElements = new IntersectionObserver(
  (entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible"); // Trigger animation
        observer.unobserve(entry.target); // Stop observing once animated
      }
    });
  },
  { threshold: 0.2 } // Trigger when 20% of the element is visible
);

animatedElements.forEach((element) => observeElements.observe(element));

// Example: Adding animation classes dynamically
document.querySelectorAll(".fade-in").forEach((el) => {
  el.classList.add("animate-on-scroll"); // Ensure it's observed
});

// Example for adding animations using GSAP (optional)
if (window.gsap) {
  document.querySelectorAll(".animate-gsap").forEach((el) => {
    gsap.fromTo(
      el,
      { opacity: 0, y: 50 }, // Start state
      {
        opacity: 1,
        y: 0,
        duration: 1,
        scrollTrigger: {
          trigger: el,
          start: "top 80%", // Trigger animation when 80% of the viewport height
        },
      }
    );
  });
}

// Mobile Menu Animation
const mobileMenuButton = document.querySelector(".navbar-toggler");
const navbarMenu = document.querySelector(".navbar-collapse");

mobileMenuButton.addEventListener("click", () => {
  if (navbarMenu.classList.contains("show")) {
    navbarMenu.animate(
      [
        { opacity: 1, transform: "translateY(0)" },
        { opacity: 0, transform: "translateY(-10px)" },
      ],
      { duration: 300, easing: "ease-in-out" }
    );
  } else {
    navbarMenu.animate(
      [
        { opacity: 0, transform: "translateY(-10px)" },
        { opacity: 1, transform: "translateY(0)" },
      ],
      { duration: 300, easing: "ease-in-out" }
    );
  }
});
const adjustFontSize = () => {
  const descriptions = document.querySelectorAll(".description");
  const isMobile = window.innerWidth < 768;

  descriptions.forEach((desc) => {
    if (isMobile) {
      desc.style.fontSize = "14px"; // Smaller font for mobile
    } else {
      desc.style.fontSize = "16px"; // Default size for larger screens
    }
  });
};

window.addEventListener("resize", adjustFontSize);
document.addEventListener("DOMContentLoaded", adjustFontSize);
// Add scroll event listener
window.addEventListener("scroll", () => {
  const hero = document.getElementById("hero");
  const scrollY = window.scrollY;

  if (scrollY > 50) {
    hero.classList.add("shrink");
  } else {
    hero.classList.remove("shrink");
  }
});
