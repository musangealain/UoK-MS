(function () {
  "use strict";

  var SESSION_KEY = "sm_sidebar_expanded_v1";

  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function $all(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function safeParseJSON(raw) {
    try {
      return JSON.parse(raw);
    } catch (e) {
      return null;
    }
  }

  function loadExpanded() {
    var raw = null;
    try {
      raw = sessionStorage.getItem(SESSION_KEY);
    } catch (e) {
      raw = null;
    }
    var parsed = raw ? safeParseJSON(raw) : null;
    return parsed && typeof parsed === "object" ? parsed : {};
  }

  function saveExpanded(state) {
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(state));
    } catch (e) {
      // Ignore
    }
  }

  function setArrow(btn, expanded) {
    // Arrow is an inline SVG and rotates via CSS based on aria-expanded.
  }

  function setExpanded(btn, expanded) {
    btn.setAttribute("aria-expanded", expanded ? "true" : "false");
    setArrow(btn, expanded);
    var panelId = btn.getAttribute("aria-controls");
    if (!panelId) return;
    var panel = document.getElementById(panelId);
    if (!panel) return;
    if (expanded) panel.classList.add("is-open");
    else panel.classList.remove("is-open");
  }

  function collapseOtherGroups(sectionKey, exceptGroupKey) {
    $all(".sm-expand[data-section='" + sectionKey + "']").forEach(function (btn) {
      var groupKey = btn.getAttribute("data-group");
      if (groupKey && groupKey !== exceptGroupKey) setExpanded(btn, false);
    });
  }

  function openGroup(sectionKey, groupKey) {
    var btn = $(".sm-expand[data-section='" + sectionKey + "'][data-group='" + groupKey + "']");
    if (!btn) return;
    collapseOtherGroups(sectionKey, groupKey);
    setExpanded(btn, true);
  }

  function hydrateFromState(state) {
    // Default all closed.
    $all(".sm-expand").forEach(function (btn) {
      setExpanded(btn, false);
    });

    Object.keys(state || {}).forEach(function (sectionKey) {
      var groupKey = state[sectionKey];
      if (!groupKey) return;
      openGroup(sectionKey, groupKey);
    });
  }

  function inferOpenFromActive() {
    // If no session state, open the group that contains the current active leaf (if any).
    // We infer by scanning for active links inside each panel.
    var inferred = {};
    $all(".sm-expand").forEach(function (btn) {
      var sectionKey = btn.getAttribute("data-section");
      var groupKey = btn.getAttribute("data-group");
      var panelId = btn.getAttribute("aria-controls");
      if (!sectionKey || !groupKey || !panelId) return;
      var panel = document.getElementById(panelId);
      if (!panel) return;
      if (panel.querySelector(".sm-sub.active")) {
        inferred[sectionKey] = groupKey;
      }
    });
    return inferred;
  }

  function setupAccordion() {
    var state = loadExpanded();
    var hasState = Object.keys(state).length > 0;
    if (!hasState) state = inferOpenFromActive();

    hydrateFromState(state);
    saveExpanded(state);

    $all(".sm-expand").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var sectionKey = btn.getAttribute("data-section");
        var groupKey = btn.getAttribute("data-group");
        if (!sectionKey || !groupKey) return;

        var expanded = btn.getAttribute("aria-expanded") === "true";
        var nextExpanded = !expanded;

        if (nextExpanded) {
          collapseOtherGroups(sectionKey, groupKey);
        }
        setExpanded(btn, nextExpanded);

        var nextState = loadExpanded();
        nextState[sectionKey] = nextExpanded ? groupKey : null;
        saveExpanded(nextState);
      });

      btn.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          btn.click();
        }
      });
    });
  }

  function setupMobile() {
    var toggle = $(".sidebar-toggle");
    var sidebar = $("#sm-sidebar");
    var overlay = $("[data-sidebar-overlay]");
    if (!toggle || !sidebar || !overlay) return;

    function setOpen(open) {
      sidebar.classList.toggle("is-open", open);
      overlay.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    }

    toggle.addEventListener("click", function () {
      setOpen(!sidebar.classList.contains("is-open"));
    });

    overlay.addEventListener("click", function () {
      setOpen(false);
    });

    window.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setOpen(false);
    });

    // Close after navigation on mobile.
    $all("#sm-sidebar a").forEach(function (a) {
      a.addEventListener("click", function () {
        setOpen(false);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupAccordion();
    setupMobile();
  });
})();
