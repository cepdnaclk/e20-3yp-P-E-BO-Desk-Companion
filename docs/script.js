// ------------------------------
// Smooth Scroll for Navigation Links with Offset
// ------------------------------
document.querySelectorAll("a.nav-link").forEach((link) => {
  link.addEventListener("click", (e) => {
    const href = link.getAttribute("href");
    if (!href || !href.startsWith("#")) return; // allow external links
    e.preventDefault();
    const target = document.querySelector(href);
    if (!target) return;
    const offset = window.innerWidth < 768 ? 70 : 0; // Adjust offset for mobile
    const targetPosition =
      target.getBoundingClientRect().top + window.scrollY - offset;
    window.scrollTo({ top: targetPosition, behavior: "smooth" });
  });
});

// ------------------------------
// Dark Mode Toggle with Animation + Persistence
// ------------------------------
const toggleDarkMode = () => {
  const body = document.body;
  body.classList.toggle("dark-mode");

  if (body.classList.contains("dark-mode")) {
    localStorage.setItem("theme", "dark");
    body.animate(
      [
        { backgroundColor: "#fff", color: "#000" },
        { backgroundColor: "#121212", color: "#fff" },
      ],
      { duration: 500, easing: "ease-in-out" }
    );
  } else {
    localStorage.setItem("theme", "light");
    body.animate(
      [
        { backgroundColor: "#121212", color: "#fff" },
        { backgroundColor: "#fff", color: "#000" },
      ],
      { duration: 500, easing: "ease-in-out" }
    );
  }
};

document.addEventListener("DOMContentLoaded", () => {
  const theme = localStorage.getItem("theme");
  if (theme === "dark") document.body.classList.add("dark-mode");
});

// ------------------------------
// IntersectionObserver: .animate-on-scroll
// ------------------------------
const animatedElements = document.querySelectorAll(".animate-on-scroll");

const observeElements = new IntersectionObserver(
  (entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("visible");
        observer.unobserve(entry.target);
      }
    });
  },
  { threshold: 0.2 }
);

animatedElements.forEach((el) => observeElements.observe(el));

// Auto-mark .fade-in so it gets observed
document.querySelectorAll(".fade-in").forEach((el) => {
  el.classList.add("animate-on-scroll");
});

// ------------------------------
// Optional GSAP usage if present
// ------------------------------
if (window.gsap) {
  document.querySelectorAll(".animate-gsap").forEach((el) => {
    gsap.fromTo(
      el,
      { opacity: 0, y: 50 },
      {
        opacity: 1,
        y: 0,
        duration: 1,
        scrollTrigger: {
          trigger: el,
          start: "top 80%",
        },
      }
    );
  });
}

// ------------------------------
// Mobile Menu Animation (guarded for nulls)
// ------------------------------
(() => {
  const mobileMenuButton = document.querySelector(".navbar-toggler");
  const navbarMenu = document.querySelector(".navbar-collapse");
  if (!mobileMenuButton || !navbarMenu) return;

  mobileMenuButton.addEventListener("click", () => {
    const showing = navbarMenu.classList.contains("show");
    if (showing) {
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
})();

// ------------------------------
// Responsive description font size
// ------------------------------
const adjustFontSize = () => {
  const descriptions = document.querySelectorAll(".description");
  const isMobile = window.innerWidth < 768;
  descriptions.forEach((desc) => {
    desc.style.fontSize = isMobile ? "14px" : "16px";
  });
};

window.addEventListener("resize", adjustFontSize);
document.addEventListener("DOMContentLoaded", adjustFontSize);

// ------------------------------
// Hero shrink on scroll (guarded)
// ------------------------------
window.addEventListener(
  "scroll",
  () => {
    const hero = document.getElementById("hero");
    if (!hero) return;
    const scrollY = window.scrollY;
    if (scrollY > 50) {
      hero.classList.add("shrink");
    } else {
      hero.classList.remove("shrink");
    }
  },
  { passive: true }
);

// ------------------------------
// Image Modal (single, consistent API)
// HTML must define:
// <div id="imageModal"> <img id="img01"> <div id="caption"></div> ... </div>
// ------------------------------
function openModal(img) {
  const modal = document.getElementById("imageModal");
  const modalImg = document.getElementById("img01");
  const caption = document.getElementById("caption");
  if (!modal || !modalImg) return;

  modal.style.display = "block";
  modalImg.src = img?.src || "";
  if (caption) caption.textContent = img?.alt || "";
}

function closeModal() {
  const modal = document.getElementById("imageModal");
  if (modal) modal.style.display = "none";
}

window.addEventListener("click", (evt) => {
  const modal = document.getElementById("imageModal");
  if (evt.target === modal) closeModal();
});

window.addEventListener("keydown", (evt) => {
  if (evt.key === "Escape") closeModal();
});



document.addEventListener("DOMContentLoaded", () => {
  const scroller = document.querySelector(".scroller");
  const backBtn = document.getElementById("backBtn");
  const nextBtn = document.getElementById("nextBtn");
  if (!scroller || !backBtn || !nextBtn) return;

  // Helper: how far to scroll per click
  const pageSize = () => Math.max(scroller.clientWidth * 0.9, 300);

  // Translate vertical wheel to horizontal scroll (smooth)
  scroller.addEventListener(
    "wheel",
    (evt) => {
      // Only hijack when vertical intent is stronger
      if (Math.abs(evt.deltaY) > Math.abs(evt.deltaX)) {
        evt.preventDefault();
        scroller.scrollBy({ left: evt.deltaY, behavior: "smooth" });
      }
    },
    { passive: false }
  );

  // Prev/Next buttons
  nextBtn.addEventListener("click", () => {
    scroller.scrollBy({ left: pageSize(), behavior: "smooth" });
  });
  backBtn.addEventListener("click", () => {
    scroller.scrollBy({ left: -pageSize(), behavior: "smooth" });
  });

  // Arrow keys when scroller is focused
  scroller.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight")
      scroller.scrollBy({ left: pageSize(), behavior: "smooth" });
    if (e.key === "ArrowLeft")
      scroller.scrollBy({ left: -pageSize(), behavior: "smooth" });
  });
});
document.addEventListener("DOMContentLoaded", () => {
  const scroller = document.getElementById("gallery-scroller");
  const backBtn = document.getElementById("backBtn");
  const nextBtn = document.getElementById("nextBtn");
  if (!scroller) return;

  const page = () => Math.max(scroller.clientWidth * 0.9, 300);

  scroller.addEventListener(
    "wheel",
    (e) => {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();
        scroller.scrollBy({ left: e.deltaY, behavior: "smooth" });
      }
    },
    { passive: false }
  );

  nextBtn?.addEventListener("click", () =>
    scroller.scrollBy({ left: page(), behavior: "smooth" })
  );
  backBtn?.addEventListener("click", () =>
    scroller.scrollBy({ left: -page(), behavior: "smooth" })
  );

  scroller.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight")
      scroller.scrollBy({ left: page(), behavior: "smooth" });
    if (e.key === "ArrowLeft")
      scroller.scrollBy({ left: -page(), behavior: "smooth" });
  });
});
