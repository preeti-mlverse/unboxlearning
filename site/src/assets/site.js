// UnboxEd site: mobile menu, playable demo cards, contact form.
(function () {
  // Where contact-form submissions go. Leave empty to fall back to opening the visitor's email app.
  // Any endpoint that accepts a JSON POST works (for example a Formspree form URL).
  var FORM_ENDPOINT = "";
  var CONTACT_EMAIL = "preeti.agrawal@lightbulblabs.tech";
  window.UNBOX = Object.assign(window.UNBOX || {}, { FORM_ENDPOINT: FORM_ENDPOINT, CONTACT_EMAIL: CONTACT_EMAIL });

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
      fb.textContent = (v === null ? "Time's up. " : ok ? "Yes! " : "Almost. Here's what you're missing: ") + (it.t ? "True" : "False") + ". " + it.why;
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
      location.href = "mailto:" + CONTACT_EMAIL + "?subject=" + encodeURIComponent("UnboxEd: " + data.topic) + "&body=" + encodeURIComponent(body);
      done(true, "Your email app should open with the message ready to send. If it doesn't, write to " + CONTACT_EMAIL + ".");
    });
  }
})();

// ---------- hands-on labs, tutor, voice, try-the-engine
(function () {
  var $ = function (root, sel) { return root.querySelector(sel); };

  // Physics: a = F / m, and the cart rolls faster with more force
  document.querySelectorAll('[data-lab="physics"]').forEach(function (lab) {
    var range = $(lab, "input"), out = $(lab, "output"), read = $(lab, ".lab-read"), cart = $(lab, ".cart");
    var update = function () {
      var f = Number(range.value), a = f / 2;
      out.textContent = f + " N";
      read.innerHTML = "a = F ÷ m = " + f + " ÷ 2 = <b>" + (a % 1 ? a.toFixed(1) : a) + " m/s²</b>";
      cart.classList.remove("go"); void cart.offsetWidth;
      cart.style.setProperty("--dur", Math.sqrt(8 / a).toFixed(2) + "s");
      cart.classList.add("go");
    };
    range.addEventListener("input", update);
    range.addEventListener("change", update);
  });

  // Biology: build the cell, then learn what each part does
  var FACTS = { membrane: "Membrane: the cell's border. It decides what gets in and out.", nucleus: "Nucleus: holds the DNA, the cell's instructions.",
    mito: "Mitochondria: release energy from food so the cell can work.", ribo: "Ribosomes: tiny builders that make proteins." };
  document.querySelectorAll('[data-lab="biology"]').forEach(function (lab) {
    var stage = $(lab, ".cell-stage"), read = $(lab, ".lab-read"), placed = {};
    var place = function (org) {
      if (!FACTS[org] || placed[org]) return;
      placed[org] = true;
      if (org === "membrane") $(lab, ".membrane").setAttribute("stroke-dasharray", "0");
      else $(lab, ".org-" + org).setAttribute("opacity", "1");
      $(lab, '[data-org="' + org + '"]').classList.add("done");
      read.textContent = Object.keys(placed).length === 4 ? "You built a cell. Now every part has a job you can picture." : FACTS[org];
    };
    lab.querySelectorAll(".org-chips button").forEach(function (b) {
      b.addEventListener("click", function () { place(b.getAttribute("data-org")); });
      b.addEventListener("dragstart", function (e) { e.dataTransfer.setData("text/plain", b.getAttribute("data-org")); });
    });
    stage.addEventListener("dragover", function (e) { e.preventDefault(); stage.classList.add("over"); });
    stage.addEventListener("dragleave", function () { stage.classList.remove("over"); });
    stage.addEventListener("drop", function (e) { e.preventDefault(); stage.classList.remove("over"); place(e.dataTransfer.getData("text/plain")); });
  });

  // Economics: quantity demanded falls as price rises (Q = 100 - 0.8P)
  document.querySelectorAll('[data-lab="economics"]').forEach(function (lab) {
    var range = $(lab, "input"), out = $(lab, "output"), read = $(lab, ".lab-read");
    var pt = $(lab, ".dg-pt"), v = $(lab, ".dg-v"), h = $(lab, ".dg-h");
    var update = function () {
      var p = Number(range.value), q = Math.round(100 - 0.8 * p), t = (p - 10) / 80;
      var x = 220 - 180 * t, y = 104 - 86 * t;
      pt.setAttribute("cx", x); pt.setAttribute("cy", y);
      v.setAttribute("x1", x); v.setAttribute("x2", x); v.setAttribute("y1", y);
      h.setAttribute("y1", y); h.setAttribute("y2", y); h.setAttribute("x2", x);
      out.textContent = "₹" + p;
      read.innerHTML = "At ₹" + p + " a cup, the stall sells <b>" + q + " cups</b> a day." + (p >= 70 ? " Too pricey: people walk past." : p <= 20 ? " Cheap, so the queue grows." : "");
    };
    range.addEventListener("input", update);
    update();
  });

  // Language: a tiny scripted conversation with a Spanish café owner
  var SCRIPT = {
    start: [["Un café con leche, por favor.", "coffee"], ["¿Qué me recomienda?", "recommend"]],
    coffee: { them: "¡Perfecto! ¿Algo más?", en: "Perfect! Anything else?", next: [["No, gracias. ¿Cuánto es?", "price"]] },
    recommend: { them: "Le recomiendo los churros con chocolate.", en: "I recommend the churros with chocolate.", next: [["Sí, unos churros, por favor.", "churros"]] },
    price: { them: "Son dos euros. ¡Que aproveche!", en: "That's two euros. Enjoy!", end: "¡Muy bien! You ordered and asked the price, all in Spanish." },
    churros: { them: "¡Marchando! Son tres euros.", en: "Coming right up! That's three euros.", end: "¡Muy bien! You asked for advice and ordered, all in Spanish." }
  };
  document.querySelectorAll('[data-lab="language"]').forEach(function (lab) {
    var log = $(lab, ".chat-mini"), box = $(lab, ".lab-choices");
    var bubble = function (cls, text, small) {
      var p = document.createElement("p"); p.className = "bub " + cls; p.textContent = text;
      if (small) { var s = document.createElement("small"); s.textContent = small; p.appendChild(s); }
      log.appendChild(p); log.scrollTop = log.scrollHeight;
    };
    var choices = function (list) {
      box.innerHTML = "";
      list.forEach(function (c) {
        var b = document.createElement("button"); b.type = "button"; b.textContent = c[0];
        b.addEventListener("click", function () {
          bubble("me", c[0]);
          var step = SCRIPT[c[1]];
          setTimeout(function () {
            bubble("them", step.them, step.en);
            if (step.next) choices(step.next);
            else {
              box.innerHTML = "";
              var done = document.createElement("p"); done.className = "lab-read"; done.textContent = step.end; box.appendChild(done);
              var again = document.createElement("button"); again.type = "button"; again.textContent = "Start again";
              again.addEventListener("click", function () { log.innerHTML = ""; bubble("them", "¡Hola! ¿Qué te pongo?", "Hi! What can I get you?"); choices(SCRIPT.start); });
              box.appendChild(again);
            }
          }, 450);
        });
        box.appendChild(b);
      });
    };
    choices(SCRIPT.start);
  });

  // Business: choose a response to an unhappy customer
  var REPLIES = {
    good: ["picked-good", "Strong. You apologised, owned it and fixed it. People remember how a problem was handled."],
    mid: ["picked-bad", "Almost. Here's what you're missing: an explanation isn't an apology. Acknowledge the wait first, then fix it."],
    bad: ["picked-bad", "That usually makes it worse. Acknowledge the problem before anything else."]
  };
  document.querySelectorAll('[data-lab="business"]').forEach(function (lab) {
    var read = $(lab, ".lab-read");
    lab.querySelectorAll("[data-q]").forEach(function (b) {
      b.addEventListener("click", function () {
        lab.querySelectorAll("[data-q]").forEach(function (o) { o.classList.remove("picked-good", "picked-bad"); });
        var r = REPLIES[b.getAttribute("data-q")];
        b.classList.add(r[0]); read.textContent = r[1];
      });
    });
  });

  // AI: a toy spam filter (logistic score over three features)
  document.querySelectorAll('[data-lab="ai"]').forEach(function (lab) {
    var range = $(lab, "input[type=range]"), out = $(lab, "output"), bar = $(lab, ".meter i"), lbl = $(lab, ".meter-lbl b"), subj = $(lab, ".subj-line");
    var free = $(lab, '[data-f="free"]'), stranger = $(lab, '[data-f="stranger"]');
    var update = function () {
      var z = -2.35 + 0.35 * Number(range.value) + (free.checked ? 2.2 : 0) + (stranger.checked ? 1.4 : 0);
      var p = Math.round(100 / (1 + Math.exp(-z)));
      out.textContent = range.value;
      subj.textContent = free.checked ? "FREE!!! Claim your prize now" : "Your invoice for March";
      bar.style.width = p + "%";
      bar.style.background = p < 40 ? "#1E9E78" : p < 70 ? "#F2B900" : "#E65F45";
      lbl.textContent = p + "% · " + (p < 50 ? "goes to Inbox" : "goes to Spam");
    };
    [range, free, stranger].forEach(function (el) { el.addEventListener("input", update); el.addEventListener("change", update); });
    update();
  });

  // Tutor: the learner's choice gets a reply that teaches rather than tells, plus what the tutor noticed
  var TUTOR = {
    water: ["Good thinking: water matters, and it's in every cell. But most of a tree's dry weight is carbon. Where could carbon come from?", "Hint 1 of 2 · answer not given away", ""],
    air: ["Yes! Leaves take in carbon dioxide and, with sunlight, build it into sugar and then wood. Most of a tree is made from air.", "Mastery · photosynthesis 42% → 61%", "ok"],
    show: ["Here's the setup: about 90 kg of dried soil, a 2.3 kg willow, and only rainwater for five years. Predict the result before you look.", "Opening the simulation · card 8", ""]
  };
  document.querySelectorAll(".convo").forEach(function (convo) {
    var log = $(convo, ".convo-log");
    convo.querySelectorAll("[data-t]").forEach(function (b) {
      b.addEventListener("click", function () {
        if (b.getAttribute("aria-pressed") === "true") return;
        b.setAttribute("aria-pressed", "true");
        var me = document.createElement("p"); me.className = "msg me"; me.innerHTML = '<span class="who">Learner</span>'; me.appendChild(document.createTextNode(b.textContent));
        log.appendChild(me);
        setTimeout(function () {
          var r = TUTOR[b.getAttribute("data-t")];
          var ai = document.createElement("p"); ai.className = "msg ai"; ai.innerHTML = '<span class="who">Tutor</span>'; ai.appendChild(document.createTextNode(r[0]));
          var note = document.createElement("p"); note.className = "tnote " + r[2]; note.textContent = r[1];
          log.appendChild(ai); log.appendChild(note);
        }, 450);
      });
    });
  });

  // Voice: read the tutor's line aloud where the browser can
  if ("speechSynthesis" in window) {
    document.querySelectorAll(".speak[data-say]").forEach(function (b) {
      b.hidden = false;
      b.addEventListener("click", function () {
        speechSynthesis.cancel();
        var u = new SpeechSynthesisUtterance(b.getAttribute("data-say")); u.lang = "en-IN"; u.rate = 0.95;
        speechSynthesis.speak(u);
      });
    });
  }

  // Try the engine: take a file or link and show what happens next, or a real example
  var tryBox = document.querySelector(".try-box");
  if (tryBox) {
    var result = document.getElementById("try-result"), drop = document.getElementById("try-drop");
    var file = document.getElementById("try-file"), url = document.getElementById("try-url");
    var show = function (html) { result.innerHTML = html; result.hidden = false; };
    var esc = function (s) { return s.replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    var received = function (name) {
      show('<h3>Got it: ' + esc(name) + '</h3><p>UnboxEd is in early access, so we unbox your first source with you. Send it to us and we\'ll show you what it becomes within two working days.</p>' +
        '<a class="btn btn-violet btn-sm" href="/contact/?topic=demo&amp;source=' + encodeURIComponent(name) + '">Send it to us →</a>');
    };
    file.addEventListener("change", function () { if (file.files[0]) received(file.files[0].name); });
    drop.addEventListener("dragover", function (e) { e.preventDefault(); drop.classList.add("over"); });
    drop.addEventListener("dragleave", function () { drop.classList.remove("over"); });
    drop.addEventListener("drop", function (e) { e.preventDefault(); drop.classList.remove("over"); if (e.dataTransfer.files[0]) received(e.dataTransfer.files[0].name); });
    document.getElementById("try-go").addEventListener("click", function () {
      var v = url.value.trim();
      if (!v) { url.focus(); return; }
      received(v);
    });
    url.addEventListener("keydown", function (e) { if (e.key === "Enter") document.getElementById("try-go").click(); });
    document.getElementById("try-example").addEventListener("click", function () {
      show('<p class="eyebrow v">A real example</p><h3>"Water cycle" encyclopedia article → 20-minute course</h3>' +
        '<div class="row"><span>15 sections in</span><span>4 modules out</span><span>48 cards</span><span>0 flagged</span><span>narrated</span></div>' +
        '<ol><li>Where Earth\'s water sits</li><li>How a drop journeys</li><li>How people change the cycle</li><li>Water in your city</li></ol>' +
        '<a class="btn btn-violet btn-sm" href="/demo/#order-game">Play a card from it →</a>');
    });
  }

  // Contact: carry the source from "try the engine" into the message
  var msg = document.getElementById("f-msg"), src = new URLSearchParams(location.search).get("source");
  if (msg && src && !msg.value) msg.value = "I'd like to see what UnboxEd makes from: " + src + "\n\n";
})();

// ---------- home hero: the phone cycles through what a learner sees, lighting the matching capability tags
(function () {
  var out = document.querySelector(".hv-out");
  if (!out) return;
  var screens = Array.prototype.slice.call(out.querySelectorAll(".scr"));
  var dots = Array.prototype.slice.call(out.querySelectorAll(".ph-dots i"));
  var tags = Array.prototype.slice.call(out.querySelectorAll(".tag"));
  var bar = out.querySelector(".ph-bar i");
  var i = 0, paused = false;
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var show = function (n) {
    screens.forEach(function (s, k) { s.classList.toggle("on", k === n); });
    dots.forEach(function (d, k) { d.classList.toggle("on", k === n); });
    var key = screens[n].getAttribute("data-k");
    tags.forEach(function (t) { t.classList.toggle("lit", t.getAttribute("data-for") === key); });
    if (bar) bar.style.width = ((n + 1) / screens.length * 100) + "%";
  };
  out.addEventListener("mouseenter", function () { paused = true; });
  out.addEventListener("mouseleave", function () { paused = false; });
  show(0);
  setTimeout(function () {
    setInterval(function () {
      if (paused || document.hidden) return;
      i = (i + 1) % screens.length;
      show(i);
    }, reduce ? 6500 : 3600);
  }, reduce ? 0 : 2600);
})();

// ---------- sign up / log in
// The forms talk to the UnboxEd API (window.UNBOX.AUTH_API, set per environment by build.py). The session comes back
// as HttpOnly cookies, then the visitor is sent into the app (window.UNBOX.APP_URL). Passwords only ever go to the API.
(function () {
  var CFG = window.UNBOX || {};
  var AUTH_API = (CFG.AUTH_API || "").replace(/\/$/, "");
  var APP_URL = (CFG.APP_URL || "").replace(/\/$/, "");
  var CONTACT_EMAIL = CFG.CONTACT_EMAIL || "preeti.agrawal@lightbulblabs.tech";
  var esc = function (s) { return String(s).replace(/[<>&"]/g, function (c) { return { "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;" }[c]; }); };
  var post = function (path, data) {
    return fetch(AUTH_API + path, { method: "POST", credentials: "include", headers: { "Content-Type": "application/json", Accept: "application/json" },
                                    body: JSON.stringify(data) })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (body) {
          if (r.ok) return body;
          var e = new Error((body.error && body.error.message) || "Something went wrong.");
          e.code = body.error && body.error.code;
          e.fields = (body.error && body.error.details && body.error.details.fields) || {};
          throw e;
        });
      }, function () {
        var e = new Error("We couldn't reach UnboxEd. Check your connection and try again.");
        e.code = "NETWORK"; e.fields = {};
        throw e;
      });
  };
  var invalid = function (el, bad) { el.setAttribute("aria-invalid", bad ? "true" : "false"); return bad; };
  var signedIn = /(?:^|;\s*)ub_signed_in=1/.test(document.cookie);

  // Already signed in (the app shares the cookie): turn "Log in" into a way back to the app.
  if (signedIn && APP_URL) {
    document.querySelectorAll('a[href="/login/"]').forEach(function (a) { a.href = APP_URL + "/"; a.textContent = "Go to my dashboard"; });
    document.querySelectorAll('header a[href="/signup/"]').forEach(function (a) { a.hidden = true; });
  }

  document.querySelectorAll(".show-pass").forEach(function (b) {
    b.addEventListener("click", function () {
      var input = b.parentNode.querySelector("input");
      var show = input.type === "password";
      input.type = show ? "text" : "password";
      b.textContent = show ? "Hide" : "Show";
      b.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  // ----- sign up
  var form = document.getElementById("signup-form");
  if (form) {
    var steps = form.querySelectorAll(".step"), marks = document.querySelectorAll(".auth-steps li");
    var go = function (n) {
      steps.forEach(function (s) { s.hidden = s.getAttribute("data-step") !== String(n); });
      marks.forEach(function (m) { var k = Number(m.getAttribute("data-s")); m.classList.toggle("on", k === n); m.classList.toggle("done", k < n); });
      var first = form.querySelector('.step[data-step="' + n + '"] input, .step[data-step="' + n + '"] a');
      if (first && n > 1) first.focus();
    };
    var role = function () { var r = form.querySelector('input[name="role"]:checked'); return r ? r.value : ""; };
    var orgWrap = document.getElementById("org-wrap");
    var syncOrg = function () { orgWrap.hidden = role() === "learner"; };
    form.querySelectorAll('input[name="role"]').forEach(function (r) {
      r.addEventListener("change", function () { document.getElementById("err-role").hidden = true; syncOrg(); });
    });
    // /signup/?role=educator (from "For educators" and similar pages) preselects the role
    var preset = (new URLSearchParams(location.search).get("role") || "").replace(/[^a-z]/g, "");
    var presetInput = preset && form.querySelector('input[name="role"][value="' + preset + '"]');
    if (presetInput) { presetInput.checked = true; syncOrg(); }
    form.querySelector("[data-next]").addEventListener("click", function () {
      if (!role()) { document.getElementById("err-role").hidden = false; return; }
      go(2);
    });
    form.querySelector("[data-back]").addEventListener("click", function () { go(1); });

    var pass = document.getElementById("s-pass"), meter = form.querySelector(".meter-pass i"), hint = document.getElementById("pass-hint");
    pass.addEventListener("input", function () {
      var v = pass.value, score = 0;
      if (v.length >= 8) score++;
      if (v.length >= 12) score++;
      if (/[a-z]/i.test(v) && /\d/.test(v)) score++;
      if (/[^a-z0-9]/i.test(v)) score++;
      var lv = [["0%", "#E2DDF5", "At least 8 characters. Mix letters and numbers."], ["30%", "#D8453A", "Too easy to guess."],
        ["55%", "#F2B900", "Getting there. Add numbers or symbols."], ["80%", "#1E9E78", "Strong password."], ["100%", "#1E9E78", "Very strong password."]][v ? Math.max(1, score) : 0];
      meter.style.width = lv[0]; meter.style.background = lv[1]; hint.textContent = lv[2];
    });

    var FIELD = { name: "s-name", email: "s-email", phone: "s-phone", org: "s-org", password: "s-pass", agree: "s-agree" };
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var err = document.getElementById("err-details"), msgs = [];
      var name = document.getElementById("s-name"), email = document.getElementById("s-email"), phone = document.getElementById("s-phone");
      var org = document.getElementById("s-org"), agree = document.getElementById("s-agree");
      var needsOrg = ["school", "ngo", "organization"].indexOf(role()) >= 0;
      phone.value = phone.value.replace(/\D/g, "").slice(-10);
      if (invalid(name, name.value.trim().length < 2)) msgs.push("your full name");
      if (invalid(email, !email.validity.valid || !email.value)) msgs.push("a valid email");
      if (invalid(phone, !!phone.value && !/^[6-9]\d{9}$/.test(phone.value))) msgs.push("a 10-digit Indian mobile number (or leave it empty)");
      if (invalid(org, needsOrg && org.value.trim().length < 2)) msgs.push("your organisation's name");
      if (invalid(pass, pass.value.length < 8 || !/[a-z]/i.test(pass.value) || !/\d/.test(pass.value))) msgs.push("a password of at least 8 characters with letters and numbers");
      if (!agree.checked) msgs.push("agreement to the Terms and Privacy policy");
      if (msgs.length) { err.textContent = "Please add " + msgs.join(", ") + "."; err.hidden = false; return; }
      err.hidden = true;
      var data = { role: role(), name: name.value.trim(), email: email.value.trim(), phone: phone.value || null,
                   org: role() === "learner" ? null : (org.value.trim() || null), language: document.getElementById("s-lang").value,
                   password: pass.value, agree: true };
      var btn = form.querySelector('button[type="submit"]');
      if (!AUTH_API) {
        err.textContent = "Accounts aren't open on this copy of the site. Please email " + CONTACT_EMAIL + ".";
        err.hidden = false;
        return;
      }
      btn.disabled = true;
      post("/auth/signup", data).then(function (r) {
        document.getElementById("done-title").textContent = "Welcome, " + data.name.split(" ")[0] + "!";
        document.getElementById("done-copy").textContent = "Your account is ready. We've emailed you a link to confirm your address. Taking you in now…";
        var cta = document.querySelector(".done-step .hero-cta");
        if (cta) cta.innerHTML = '<a class="btn btn-primary" href="' + esc(r.redirect_to) + '">Open UnboxEd →</a>';
        go(3);
        setTimeout(function () { location.href = r.redirect_to; }, 1400);
      }).catch(function (x) {
        var keys = Object.keys(x.fields || {});
        keys.forEach(function (k) { var el = document.getElementById(FIELD[k]); if (el) invalid(el, true); });
        err.textContent = keys.length ? keys.map(function (k) { return x.fields[k]; }).join(" ") : x.message;
        if (x.code === "EMAIL_TAKEN") { invalid(email, true); err.innerHTML = esc(x.message) + ' <a href="/login/">Log in</a>'; }
        err.hidden = false;
        btn.disabled = false;
      });
    });
  }

  // ----- log in and password reset
  var login = document.getElementById("login-form"), reset = document.getElementById("reset-form");
  if (login) {
    var status = function (el, ok, msg) { el.hidden = false; el.className = "form-status " + (ok ? "ok" : "no"); el.innerHTML = msg; };
    document.getElementById("to-reset").addEventListener("click", function () { login.hidden = true; reset.hidden = false; document.getElementById("r-email").focus(); });
    document.getElementById("to-login").addEventListener("click", function () { reset.hidden = true; login.hidden = false; document.getElementById("l-id").focus(); });
    login.addEventListener("submit", function (e) {
      e.preventDefault();
      var id = document.getElementById("l-id"), pw = document.getElementById("l-pass"), st = document.getElementById("login-status");
      var bad = invalid(id, !id.value.trim()) | invalid(pw, !pw.value);
      if (bad) { status(st, false, "Enter your email or mobile and your password."); return; }
      if (!AUTH_API) { status(st, false, "Log-in isn't available on this copy of the site."); return; }
      var btn = login.querySelector('button[type="submit"]');
      btn.disabled = true;
      post("/auth/login", { identifier: id.value.trim(), password: pw.value, remember: login.remember.checked })
        .then(function (r) { status(st, true, "Welcome back. Opening UnboxEd…"); location.href = r.redirect_to || APP_URL; })
        .catch(function (x) { status(st, false, esc(x.message)); btn.disabled = false; });
    });
    reset.addEventListener("submit", function (e) {
      e.preventDefault();
      var em = document.getElementById("r-email"), st = document.getElementById("reset-status");
      if (invalid(em, !em.value || !em.validity.valid)) { status(st, false, "Enter the email you signed up with."); return; }
      var done = function () { status(st, true, "If an account exists for " + esc(em.value) + ", a reset link is on its way. Check your inbox."); };
      if (!AUTH_API) { done(); return; }
      post("/auth/forgot-password", { email: em.value.trim() }).then(done, function (x) {
        if (x.code === "RATE_LIMITED" || x.code === "NETWORK") status(st, false, esc(x.message)); else done();
      });
    });
  }
})();

// ---------- hands-on labs: a 3D deck that keeps sliding, one card after another
(function () {
  document.querySelectorAll(".labs.deck").forEach(function (deck) {
    var sec = deck.closest("section");
    var cards = Array.prototype.slice.call(deck.querySelectorAll(".lab"));
    var tabs = Array.prototype.slice.call(sec.querySelectorAll(".lab-tabs [data-go]"));
    var count = sec.querySelector(".deck-count b");
    var n = cards.length, cur = 0, timer = null, lastPlay = 0, started = false;
    var DUR = 4500;   // time on each card
    var HOLD = 8000;  // after someone uses a card's controls, wait this long before sliding on
    var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

    var fit = function () {
      var h = 0;
      cards.forEach(function (c) { h = Math.max(h, c.offsetHeight); });
      deck.style.setProperty("--deck-h", (h + 40) + "px");
    };
    var runBar = function (ms) {
      tabs.forEach(function (t) { t.classList.remove("run"); });
      if (reduce || !tabs[cur]) return;
      void tabs[cur].offsetWidth;
      tabs[cur].style.setProperty("--dur", ms + "ms");
      tabs[cur].classList.add("run");
    };
    var layout = function () {
      cards.forEach(function (c, k) {
        var d = ((k - cur) % n + n) % n;
        if (d > n / 2) d -= n;
        c.setAttribute("data-pos", String(d));
        c.setAttribute("aria-hidden", d === 0 ? "false" : "true");
        c.querySelectorAll("button, input").forEach(function (el) { el.tabIndex = d === 0 ? 0 : -1; });
      });
      tabs.forEach(function (t, k) { t.setAttribute("aria-selected", k === cur ? "true" : "false"); t.tabIndex = k === cur ? 0 : -1; });
      if (count) count.textContent = String(cur + 1).padStart(2, "0");
    };
    var schedule = function (ms) {
      clearTimeout(timer);
      if (reduce || !started) return;
      runBar(ms);
      timer = setTimeout(tick, ms);
    };
    var tick = function () {
      var wait = HOLD - (Date.now() - lastPlay);
      if (document.hidden) { schedule(DUR); return; }
      if (wait > 0) { schedule(wait); return; }   // someone is playing with this card: let them finish
      cur = (cur + 1) % n; layout(); schedule(DUR);
    };
    var go = function (k) { cur = ((k % n) + n) % n; lastPlay = 0; layout(); schedule(DUR); };

    tabs.forEach(function (t, k) {
      t.addEventListener("click", function () { go(k); });
      t.addEventListener("keydown", function (e) {
        if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); go(cur + (e.key === "ArrowRight" ? 1 : -1)); tabs[cur].focus(); }
      });
    });
    sec.querySelectorAll(".deck-btn").forEach(function (b) {
      b.addEventListener("click", function () { go(cur + Number(b.getAttribute("data-step"))); });
    });
    cards.forEach(function (c, k) {
      c.addEventListener("click", function () { if (c.getAttribute("data-pos") !== "0") go(k); }, true);
      var played = function () { if (c.getAttribute("data-pos") === "0") { lastPlay = Date.now(); schedule(HOLD); } };
      c.addEventListener("input", played);
      c.addEventListener("change", played);
      c.addEventListener("click", function (e) { if (e.target.closest("button, input, label")) played(); });
    });
    var x0 = null;
    deck.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; }, { passive: true });
    deck.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0; x0 = null;
      if (Math.abs(dx) > 50) go(cur + (dx < 0 ? 1 : -1));
    });

    layout(); fit();
    window.addEventListener("resize", fit);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
    // slide from the moment the page loads, so the deck is always in motion
    started = true;
    schedule(DUR);
  });
})();
