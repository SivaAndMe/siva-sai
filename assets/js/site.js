/* Publication filtering + active nav highlighting. No dependencies. */

(function () {
  "use strict";

  /* --------------------------------------------------- email reveal ----- *
   * The address is never written into the markup. It is held here as
   * shifted character codes and assembled only when a visitor clicks, so
   * address harvesters reading the HTML source find nothing to take.       */

  var MAIL = [138, 128, 141, 120, 69, 138, 120, 128, 87, 133, 140, 138,
              69, 124, 123, 140, 69, 138, 126];
  var SHIFT = 23;

  function buildAddress() {
    var out = "";
    for (var i = 0; i < MAIL.length; i++) {
      out += String.fromCharCode(MAIL[i] - SHIFT);
    }
    return out;
  }

  Array.prototype.slice
    .call(document.querySelectorAll("[data-mail]"))
    .forEach(function (btn) {
      btn.addEventListener("click", function () {
        var address = buildAddress();
        var link = document.createElement("a");
        link.href = "ma" + "ilto:" + address;
        link.className = btn.className;
        link.textContent = address;

        var icon = btn.querySelector("i");
        if (icon) link.insertBefore(icon.cloneNode(true), link.firstChild);

        btn.parentNode.replaceChild(link, btn);
        link.focus();
      });
    });

  /* ------------------------------------------------ scholar metrics ---- *
   * The numbers in the markup are the fallback and are always correct as of
   * the last successful refresh. This upgrades them from a cached JSON file
   * that a scheduled job rewrites. Scholar itself is never contacted from
   * the browser: it sends no CORS header, so that request cannot succeed.
   * Any failure here leaves the served markup exactly as it is.            */

  function paintStats(data) {
    if (!data || typeof data !== "object") return;

    Array.prototype.slice
      .call(document.querySelectorAll("[data-stat]"))
      .forEach(function (el) {
        var value = data[el.getAttribute("data-stat")];
        if (typeof value !== "number" || !isFinite(value) || value <= 0) return;
        el.textContent = value.toLocaleString("en-US");
      });

    var stamp = document.querySelector("[data-stat-updated]");
    if (stamp && typeof data.updated === "string") {
      var parts = data.updated.split("-");
      var when = new Date(Date.UTC(+parts[0], +parts[1] - 1, +parts[2]));
      if (!isNaN(when.getTime())) {
        stamp.textContent = when.toLocaleDateString("en-GB", {
          month: "long", year: "numeric", timeZone: "UTC"
        });
        stamp.setAttribute("datetime", data.updated);
      }
    }
  }

  if (typeof fetch === "function") {
    fetch("assets/data/scholar.json", { cache: "no-cache" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(paintStats)
      .catch(function () { /* keep the numbers already in the markup */ });
  }

  /* ------------------------------------------------ publication filter -- */
  var chips = Array.prototype.slice.call(
    document.querySelectorAll(".pub-toolbar .chip")
  );
  var pubs = Array.prototype.slice.call(document.querySelectorAll(".pub"));
  var empty = document.getElementById("pubEmpty");

  function applyFilter(area) {
    var shown = 0;

    pubs.forEach(function (pub) {
      var areas = (pub.getAttribute("data-area") || "").split(/\s+/);
      var match = area === "all" || areas.indexOf(area) !== -1;
      pub.hidden = !match;
      if (match) shown++;
    });

    /* the first visible row owns the "no top rule" treatment */
    var first = true;
    pubs.forEach(function (pub) {
      if (pub.hidden) return;
      pub.style.borderTop = first ? "0" : "";
      pub.style.paddingTop = first ? "0" : "";
      first = false;
    });

    if (empty) empty.hidden = shown !== 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      chips.forEach(function (c) {
        c.setAttribute("aria-pressed", String(c === chip));
      });
      applyFilter(chip.getAttribute("data-filter"));
    });
  });

  /* ------------------------------------------------------- active nav -- */
  var navLinks = Array.prototype.slice.call(
    document.querySelectorAll('.nav__links a[href^="#"]')
  );
  var sections = navLinks
    .map(function (link) {
      return document.querySelector(link.getAttribute("href"));
    })
    .filter(Boolean);

  if ("IntersectionObserver" in window && sections.length) {
    var visible = new Set();

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) visible.add(entry.target.id);
          else visible.delete(entry.target.id);
        });

        var current = null;
        for (var i = 0; i < sections.length; i++) {
          if (visible.has(sections[i].id)) {
            current = sections[i].id;
            break;
          }
        }

        navLinks.forEach(function (link) {
          var on = current && link.getAttribute("href") === "#" + current;
          if (on) link.setAttribute("aria-current", "true");
          else link.removeAttribute("aria-current");
        });
      },
      { rootMargin: "-30% 0px -55% 0px", threshold: 0 }
    );

    sections.forEach(function (section) {
      observer.observe(section);
    });
  }
})();
