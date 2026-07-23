"use strict";

const body = document.body;
const contrastButton = document.getElementById("contrast-toggle");
const pathwayButton = document.getElementById("pathway-details-toggle");
const pathwayDetails = document.getElementById("pathway-details");
const decisionButton = document.getElementById("review-decision");
const requestDataButton = document.getElementById("request-data");
const decisionDialog = document.getElementById("decision-dialog");
const confirmReviewButton = document.getElementById("confirm-review");
const reviewNote = document.getElementById("review-note");
const liveRegion = document.getElementById("dialog-region");

const STORAGE_KEY = "provider-assessment-prototype-contrast";

function readContrastPreference() {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "high";
  } catch (_error) {
    return false;
  }
}

function saveContrastPreference(enabled) {
  try {
    window.localStorage.setItem(STORAGE_KEY, enabled ? "high" : "standard");
  } catch (_error) {
    // The interface remains functional when storage is unavailable.
  }
}

function setContrast(enabled) {
  body.classList.toggle("high-contrast", enabled);
  contrastButton.setAttribute("aria-pressed", String(enabled));
  contrastButton.textContent = enabled ? "التباين القياسي" : "تباين مرتفع";
  saveContrastPreference(enabled);
}

function showToast(message) {
  const previous = liveRegion.querySelector(".toast");
  if (previous) {
    previous.remove();
  }

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute("role", "status");
  toast.textContent = message;
  liveRegion.appendChild(toast);

  window.setTimeout(() => {
    toast.remove();
  }, 6000);
}

function togglePathwayDetails() {
  const willOpen = pathwayDetails.hidden;
  pathwayDetails.hidden = !willOpen;
  pathwayButton.setAttribute("aria-expanded", String(willOpen));
  pathwayButton.textContent = willOpen ? "إخفاء قواعد المسار" : "عرض قواعد المسار";
  if (willOpen) {
    pathwayDetails.focus({ preventScroll: true });
  }
}

function openDecisionDialog() {
  if (typeof decisionDialog.showModal === "function") {
    decisionDialog.showModal();
    return;
  }
  decisionDialog.setAttribute("open", "");
}

function validateDecisionReview(event) {
  const form = decisionDialog.querySelector("form");
  const requiredChecks = Array.from(form.querySelectorAll('input[name="review"]'));
  const allChecked = requiredChecks.every((checkbox) => checkbox.checked);
  const noteComplete = reviewNote.value.trim().length >= 10;

  if (!allChecked || !noteComplete) {
    event.preventDefault();
    if (!allChecked) {
      requiredChecks.find((checkbox) => !checkbox.checked)?.focus();
      showToast("يجب مراجعة جميع عناصر القائمة قبل تسجيل التأكيد التجريبي.");
      return;
    }
    reviewNote.focus();
    showToast("أدخل ملاحظة مراجعة واضحة من عشرة أحرف على الأقل.");
    return;
  }

  window.setTimeout(() => {
    showToast("سُجلت مراجعة تجريبية محليًا. لم ينفذ أي انتقال أو حفظ سريري.");
    form.reset();
  }, 0);
}

function updateActiveNavigation(event) {
  const link = event.target.closest("a[href^='#']");
  if (!link) {
    return;
  }

  document.querySelectorAll(".sidebar a").forEach((item) => {
    item.classList.remove("active");
    item.removeAttribute("aria-current");
  });
  link.classList.add("active");
  link.setAttribute("aria-current", "page");
}

setContrast(readContrastPreference());

contrastButton.addEventListener("click", () => {
  setContrast(!body.classList.contains("high-contrast"));
});

pathwayButton.addEventListener("click", togglePathwayDetails);
decisionButton.addEventListener("click", openDecisionDialog);
confirmReviewButton.addEventListener("click", validateDecisionReview);

requestDataButton.addEventListener("click", () => {
  showToast("طلب تجريبي: الملاحظة المباشرة، الأداة الأكاديمية المرخصة، والملف الوظيفي ما تزال ناقصة.");
});

document.querySelector(".sidebar").addEventListener("click", updateActiveNavigation);

decisionDialog.addEventListener("close", () => {
  decisionButton.focus();
});
