// Unbox Learning site: mobile menu, playable demo cards, contact form.
(function () {
  // Where contact-form submissions go. Leave empty to fall back to opening the visitor's email app.
  // Any endpoint that accepts a JSON POST works (for example a Formspree form URL).
  var FORM_ENDPOINT = "";
  var CONTACT_EMAIL = "hello@unboxlearning.in";

  // ---------- mobile menu
  var nav = document.querySelector(".nav");
  var menuBtn = document.querySelector(".menu-btn");
  if (nav && menuBtn) {
    menuBtn.addEventListener("click", function () {
      var open = nav.classList.toggle("open");
      menuBtn.setAttribute("aria-expanded", open ? "true" : "false");
      menuBtn.textContent = open ? "Close" : "Menu";
    });
  }

  // ---------- true / false time-attack card
  var tf = document.getElementById("tf");
  if (tf) {
    var items = [
      { s: "France's debt was far higher than Britain's.", t: false, why: "Its debt wasn't the highest. Messy taxes and blocked reforms were the real problem." },
      { s: "Tax farmers kept a cut of the taxes they collected.", t: true, why: "Private collectors took their share first, so the treasury got less." },
      { s: "Nobles and the Church paid most of the taxes.", t: false, why: "They had many exemptions. Ordinary people carried most of the burden." },
      { s: "Regional parlements could block new tax laws.", t: true, why: "They refused to register reforms, so change stalled." }
    ];
    var i = 0, score = 0, xp = 0, answered = false, timerId = null, left = 10, results = [];
    var stmt = document.getElementById("stmt"), fb = document.getElementById("fb"), dots = document.getElementById("dots");
    var timer = document.getElementById("timer"), prog = document.getElementById("prog"), xpEl = document.getElementById("xp");
    var again = document.getElementById("again");
    var renderDots = function () {
      dots.innerHTML = "";
      items.forEach(function (_, k) { var d = document.createElement("span"); if (results[k] === true) d.className = "ok"; if (results[k] === false) d.className = "no"; dots.appendChild(d); });
    };
    var tick = function () { left -= 0.1; timer.style.width = Math.max(0, left * 10) + "%"; if (left <= 0) answer(null); };
    var show = function () {
      answered = false; left = 10; timer.style.width = "100%"; fb.textContent = ""; fb.className = "fb";
      stmt.textContent = items[i].s; tf.hidden = false;
      clearInterval(timerId); timerId = setInterval(tick, 100);
    };
    var answer = function (v) {
      if (answered) return; answered = true; clearInterval(timerId);
      var it = items[i], ok = v === it.t;
      results[i] = ok; if (ok) { score++; xp += 10; }
      xpEl.textContent = "★ " + xp;
      fb.className = "fb " + (ok ? "ok" : "no");
      fb.textContent = (v === null ? "Time's up. " : ok ? "Yes! " : "Not quite. ") + (it.t ? "True" : "False") + ". " + it.why;
      prog.style.width = ((i + 1) / items.length * 100) + "%";
      renderDots();
      setTimeout(function () {
        i++;
        if (i < items.length) { show(); return; }
        tf.hidden = true;
        stmt.textContent = score + " / " + items.length + " right · +" + xp + " XP";
        fb.className = "fb ok";
        fb.textContent = score === items.length ? "Perfect round. That's how a streak starts." : "The ones you missed go into your memory deck for tomorrow.";
        again.hidden = false;
      }, 2200);
    };
    tf.addEventListener("click", function (e) { var b = e.target.closest("button"); if (b) answer(b.getAttribute("data-v") === "true"); });
    again.addEventListener("click", function () { i = 0; score = 0; xp = 0; results = []; xpEl.textContent = "★ 0"; prog.style.width = "0"; again.hidden = true; renderDots(); show(); });
    renderDots();
    // The card rests in a readable state; the timer starts only when the card is in view.
    var started = false;
    var stage = tf.closest("section") || tf;
    if ("IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (en) { if (en.isIntersecting && !started) { started = true; show(); io.disconnect(); } });
      }, { threshold: 0.5 });
      io.observe(stage);
    } else { show(); }
  }

  // ---------- put-in-order card
  var order = document.getElementById("order");
  if (order) {
    var correct = JSON.parse(order.getAttribute("data-answer"));
    var buttons = Array.prototype.slice.call(order.querySelectorAll("button"));
    var picked = [];
    var ofb = document.getElementById("order-fb"), oreset = document.getElementById("order-reset");
    var paint = function () {
      buttons.forEach(function (b) {
        var k = picked.indexOf(b.getAttribute("data-id"));
        b.querySelector(".pos").textContent = k >= 0 ? String(k + 1) : "";
        b.classList.toggle("placed", k >= 0);
      });
    };
    order.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b || b.disabled) return;
      var id = b.getAttribute("data-id"), k = picked.indexOf(id);
      if (k >= 0) picked.splice(k, 1); else picked.push(id);
      paint();
      if (picked.length === correct.length) {
        var right = 0;
        buttons.forEach(function (btn) {
          var pos = picked.indexOf(btn.getAttribute("data-id")), ok = correct[pos] === btn.getAttribute("data-id");
          if (ok) right++;
          btn.classList.add(ok ? "right" : "wrong"); btn.disabled = true;
        });
        ofb.className = "fb " + (right === correct.length ? "ok" : "no");
        ofb.textContent = right === correct.length
          ? "All in order. Water evaporates, condenses into clouds, falls as rain, then runs off or soaks in and returns to the sea."
          : right + " of " + correct.length + " in the right place. Evaporation comes first: the sun turns water into vapour before any cloud can form.";
        oreset.hidden = false;
      }
    });
    oreset.addEventListener("click", function () {
      picked = []; buttons.forEach(function (b) { b.disabled = false; b.classList.remove("right", "wrong"); });
      ofb.className = "fb"; ofb.textContent = ""; oreset.hidden = true; paint();
    });
  }

  // ---------- contact form
  var form = document.getElementById("contact-form");
  if (form) {
    var status = document.getElementById("form-status");
    var params = new URLSearchParams(location.search);
    var topic = params.get("topic");
    if (topic && form.topic) {
      Array.prototype.forEach.call(form.topic.options, function (o) { if (o.value === topic) form.topic.value = topic; });
    }
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }
      var data = {};
      new FormData(form).forEach(function (v, k) { data[k] = v; });
      if (data.website) return; // honeypot: bots fill hidden fields
      var done = function (ok, msg) { status.hidden = false; status.className = "form-status " + (ok ? "ok" : "no"); status.textContent = msg; };
      if (FORM_ENDPOINT) {
        var btn = form.querySelector("button[type=submit]"); btn.disabled = true;
        fetch(FORM_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(data) })
          .then(function (r) {
            if (!r.ok) throw new Error(String(r.status));
            done(true, "Thanks, " + (data.name || "there") + ". We'll reply to " + data.email + " within two working days.");
            form.reset();
          })
          .catch(function () { done(false, "That didn't send. Please email us at " + CONTACT_EMAIL + " instead."); })
          .then(function () { btn.disabled = false; });
        return;
      }
      var body = "Name: " + data.name + "\nEmail: " + data.email + "\nOrganisation: " + (data.org || "-") + "\nTopic: " + data.topic + "\n\n" + data.message;
      location.href = "mailto:" + CONTACT_EMAIL + "?subject=" + encodeURIComponent("Unbox Learning: " + data.topic) + "&body=" + encodeURIComponent(body);
      done(true, "Your email app should open with the message ready to send. If it doesn't, write to " + CONTACT_EMAIL + ".");
    });
  }
})();
