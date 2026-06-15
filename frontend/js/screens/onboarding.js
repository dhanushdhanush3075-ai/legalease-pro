/**
 * Splash → Onboarding → Terms → Auth flow.
 */
import { $, $$ } from "../ui.js";
import { settings } from "../state.js";

const FLAGS = {
  onboardingDone: "legalease.onboardingDone",
  termsAccepted: "legalease.termsAccepted",
};

let currentSlide = 0;

function showSlide(i) {
  $$(".ob-slide").forEach(s => s.classList.toggle("active", Number(s.dataset.slide) === i));
  $$(".ob-dot").forEach(d => d.classList.toggle("active", Number(d.dataset.dot) === i));
  $("#ob-next").textContent = i === 2 ? "Get Started ✓" : "Next →";
  currentSlide = i;
}

function nextSlide() {
  if (currentSlide < 2) {
    showSlide(currentSlide + 1);
  } else {
    localStorage.setItem(FLAGS.onboardingDone, "true");
    hideOnboarding();
    showTerms();
  }
}

function skipOnboarding() {
  localStorage.setItem(FLAGS.onboardingDone, "true");
  hideOnboarding();
  showTerms();
}

function hideSplash() {
  const splash = $("#splash-screen");
  if (!splash) return;
  splash.classList.add("fade-out");
  setTimeout(() => splash.classList.add("hidden"), 600);
}

function showOnboarding() {
  $("#onboarding-screen").classList.remove("hidden");
  $$(".ob-dot").forEach(d => d.addEventListener("click", () => showSlide(Number(d.dataset.dot))));
  $("#ob-next").addEventListener("click", nextSlide);
  $("#ob-skip").addEventListener("click", skipOnboarding);

  // Swipe support
  let startX = 0;
  const slides = $("#ob-slides");
  slides.addEventListener("touchstart", (e) => { startX = e.touches[0].clientX; }, { passive: true });
  slides.addEventListener("touchend", (e) => {
    const dx = e.changedTouches[0].clientX - startX;
    if (Math.abs(dx) < 50) return;
    if (dx < 0 && currentSlide < 2) showSlide(currentSlide + 1);
    if (dx > 0 && currentSlide > 0) showSlide(currentSlide - 1);
  });
}

function hideOnboarding() {
  $("#onboarding-screen").classList.add("hidden");
}

function showTerms() {
  const screen = $("#terms-screen");
  screen.classList.remove("hidden");
  const accept = $("#t-accept");
  const checks = ["#t-1", "#t-2", "#t-3", "#t-4"].map(s => $(s));
  const update = () => {
    accept.disabled = !checks.every(c => c.checked);
  };
  checks.forEach(c => c.addEventListener("change", update));
  accept.addEventListener("click", () => {
    if (accept.disabled) return;
    localStorage.setItem(FLAGS.termsAccepted, "true");
    screen.classList.add("hidden");
    window.dispatchEvent(new CustomEvent("flow:terms_accepted"));
  });
}

export async function startFlow() {
  // Always show splash briefly
  await new Promise(r => setTimeout(r, 1400));
  hideSplash();
  await new Promise(r => setTimeout(r, 500));

  const onboarded = localStorage.getItem(FLAGS.onboardingDone) === "true";
  const termsAccepted = localStorage.getItem(FLAGS.termsAccepted) === "true";

  if (!onboarded) {
    showOnboarding();
    // resolved by ob-next final click → terms → flow:terms_accepted
    return new Promise(resolve => {
      window.addEventListener("flow:terms_accepted", resolve, { once: true });
    });
  }
  if (!termsAccepted) {
    showTerms();
    return new Promise(resolve => {
      window.addEventListener("flow:terms_accepted", resolve, { once: true });
    });
  }
  // Otherwise jump straight through
}

export function resetFlow() {
  localStorage.removeItem(FLAGS.onboardingDone);
  localStorage.removeItem(FLAGS.termsAccepted);
}
