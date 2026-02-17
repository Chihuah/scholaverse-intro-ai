/* ============================================
   Scholaverse - App JavaScript
   HTMX config, mobile nav, toast notifications
   ============================================ */

(function () {
  "use strict";

  /* --- Mobile Navigation Toggle --- */
  function initMobileNav() {
    var toggle = document.getElementById("mobile-nav-toggle");
    var menu = document.getElementById("mobile-nav-menu");
    if (!toggle || !menu) return;

    toggle.addEventListener("click", function () {
      var expanded = toggle.getAttribute("aria-expanded") === "true";
      toggle.setAttribute("aria-expanded", String(!expanded));
      menu.classList.toggle("hidden");
    });

    // Close menu when clicking a link
    menu.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        menu.classList.add("hidden");
        toggle.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* --- Toast Notification System --- */
  var toastContainer = null;

  function getToastContainer() {
    if (toastContainer) return toastContainer;
    toastContainer = document.createElement("div");
    toastContainer.className = "toast-container";
    document.body.appendChild(toastContainer);
    return toastContainer;
  }

  function showToast(message, type, duration) {
    type = type || "info";
    duration = duration || 3000;

    var container = getToastContainer();
    var toast = document.createElement("div");
    toast.className = "toast";
    if (type === "success") toast.classList.add("toast-success");
    else if (type === "warning") toast.classList.add("toast-warning");
    else if (type === "error" || type === "danger") toast.classList.add("toast-danger");

    toast.textContent = message;
    container.appendChild(toast);

    // Trigger show animation
    requestAnimationFrame(function () {
      toast.classList.add("show");
    });

    // Auto-dismiss
    setTimeout(function () {
      toast.classList.remove("show");
      setTimeout(function () {
        toast.remove();
      }, 300);
    }, duration);
  }

  // Expose globally
  window.showToast = showToast;

  /* --- HTMX Event Handlers --- */
  function initHTMX() {
    // Show toast on successful HTMX swap with HX-Trigger header
    document.body.addEventListener("showToast", function (evt) {
      var detail = evt.detail || {};
      showToast(detail.message || "Done", detail.type || "success", detail.duration);
    });

    // Handle HTMX errors
    document.body.addEventListener("htmx:responseError", function (evt) {
      var status = evt.detail.xhr ? evt.detail.xhr.status : 0;
      if (status === 401 || status === 403) {
        showToast("Permission denied", "error");
      } else if (status >= 500) {
        showToast("Server error, please try again", "error");
      } else {
        showToast("Request failed", "warning");
      }
    });

    // Loading indicator on HTMX requests
    document.body.addEventListener("htmx:beforeRequest", function (evt) {
      var target = evt.detail.elt;
      if (target && target.classList.contains("pixel-btn")) {
        target.dataset.originalText = target.textContent;
        target.textContent = "...";
        target.disabled = true;
      }
    });

    document.body.addEventListener("htmx:afterRequest", function (evt) {
      var target = evt.detail.elt;
      if (target && target.dataset.originalText) {
        target.textContent = target.dataset.originalText;
        delete target.dataset.originalText;
        target.disabled = false;
      }
    });
  }

  /* --- Highlight Current Nav Link --- */
  function initActiveNav() {
    var path = window.location.pathname;
    document.querySelectorAll(".nav-link").forEach(function (link) {
      var href = link.getAttribute("href");
      if (href === path || (href !== "/" && path.startsWith(href))) {
        link.classList.add("active");
      }
    });
  }

  /* --- Init on DOM Ready --- */
  document.addEventListener("DOMContentLoaded", function () {
    initMobileNav();
    initHTMX();
    initActiveNav();
  });
})();
