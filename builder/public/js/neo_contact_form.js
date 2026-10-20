/* //// Neoffice — added file (no upstream equivalent): the single runtime behind every contact form of
   //// a generated site — the Jinja include (templates/includes/contact_form.html) and the block
   //// templates an owner drops in the editor (builder_block_template/contact_form_*).
   ////
   //// Why one file. The stock endpoint mailed the visitor's own text back to any address typed in the
   //// form and filed the message last: a site's domain sent about 2,500 spam mails in six days and its
   //// owner received nothing (neoffice-maintenance#1593). The defence — a signed token taken when the
   //// page loads, a minimum delay before sending, a field only a script fills, the message stored
   //// before any mail is attempted — now lives in ONE place. Spread over each form's own markup, the
   //// next template added beside them would ship without it.
   ////
   //// A form opts in with data-neo-contact. Everything else is markup the owner may edit freely:
   //// any field whose name the endpoint does not know is folded into the message as "Label: value",
   //// so a template may ask whatever questions it likes without a change on the server.
   ////
   ////
   //// A form kept as data (templates/includes/site_form.html, a Site Form of the theme) also carries
   //// data-neo-form="<identifier>": its answers then travel as data, one entry for each question of the form
   //// ({form, answers}), and the token comes with the name of the field only a script is shown. The forms
   //// written before them keep their eight names and the folding of the other questions into the message.
   ////
   //// To remove: nothing to remove, there is no upstream counterpart. */
(function () {
  // The names neoffice_theme.website_messages.submit knows: the eight of the plain form, and the four a form kept
  // as data adds (form, answers, elapsed, captcha). Anything else is a question of this template's own, and
  // travels inside the message.
  var KNOWN_FIELDS = [
    "full_name",
    "sender",
    "phone",
    "subject",
    "message",
    "consent",
    "website",
    "token",
    "form",
    "answers",
    "elapsed",
    "captcha",
  ];

  var SUBMIT_URL = "/api/method/neoffice_theme.website_messages.submit";
  var TOKEN_URL = "/api/method/neoffice_theme.website_messages.issue_token";
  // an instance whose theme predates the endpoint (404) falls back on the stock URL, which the theme
  // overrides as soon as it is up to date
  var LEGACY_URL = "/api/method/frappe.www.contact.send_message";

  var TOKEN_FRESH_MS = 20 * 60 * 1000;
  var TOKEN_MIN_AGE_MS = 4000; // the server holds back an answer that comes faster than a human could

  // Fallbacks only: a template says these in the site's own language, through data attributes.
  var TEXT = {
    sent: "Thank you, your message has been sent.",
    failed:
      "Your message could not be sent. Please check your email address and try again.",
    throttled: "Too many messages have been sent. Please try again later.",
    nameLabel: "Name",
    phoneLabel: "Phone",
    consentLabel: "Consent given",
  };

  var text = function (form, key) {
    return form.dataset[key] || TEXT[key];
  };

  // //// Neoffice — the field a bot fills and a visitor never sees. Put here rather than in each
  // //// template: a template whose author forgets the styling would show it to everyone. Off screen
  // //// on purpose, not display:none — a bot that reads the markup without running scripts has to
  // //// believe it is a real field.
  var hideHoneypots = function () {
    if (document.getElementById("neo-contact-form-style")) return;
    var style = document.createElement("style");
    style.id = "neo-contact-form-style";
    style.textContent =
      "[data-neo-honeypot]{position:absolute!important;left:-9999px!important;top:auto!important;" +
      "width:1px!important;height:1px!important;overflow:hidden!important}";
    document.head.appendChild(style);
  };

  var value = function (form, name) {
    var control = form.elements.namedItem(name);
    return control && control.value ? control.value.trim() : "";
  };

  var checkedConsent = function (form) {
    var consent = form.elements.namedItem("consent");
    return consent && consent.checked ? consent.value : "";
  };

  // What to call a question in the message the owner reads: what the template says it is, else the
  // label tied to the field, else the label around it, else its placeholder, else its own name.
  var labelOf = function (control, form) {
    if (control.dataset.label) return control.dataset.label;
    if (control.id) {
      var tied = form.querySelector('label[for="' + control.id + '"]');
      if (tied && tied.textContent.trim()) return tied.textContent.trim();
    }
    var around = control.closest("label");
    if (around && around.textContent.trim()) return around.textContent.trim();
    return (
      control.getAttribute("placeholder") ||
      control.getAttribute("aria-label") ||
      control.name
    );
  };

  var answerOf = function (control) {
    if (control.tagName === "SELECT") {
      var option = control.selectedOptions && control.selectedOptions[0];
      // what the visitor read, not the value behind it
      return option ? option.text.trim() : "";
    }
    if (control.type === "checkbox" || control.type === "radio") {
      return control.checked ? control.value || "yes" : "";
    }
    return control.value ? control.value.trim() : "";
  };

  // Every question this template asks beyond the eight the endpoint knows, in the order the visitor
  // met them. Several checkboxes sharing a name answer on one line.
  var extraAnswers = function (form) {
    var lines = [];
    var byLabel = {};
    var order = [];
    Array.prototype.forEach.call(form.elements, function (control) {
      if (!control.name || KNOWN_FIELDS.indexOf(control.name) !== -1) return;
      if (control.type === "hidden" || control.disabled) return;
      var answer = answerOf(control);
      if (!answer) return;
      var label = labelOf(control, form);
      if (byLabel[label] === undefined) {
        byLabel[label] = answer;
        order.push(label);
      } else {
        byLabel[label] += ", " + answer;
      }
    });
    order.forEach(function (label) {
      // a question already ending in ? or : takes no colon of its own
      lines.push(
        label + (/[?:]\s*$/.test(label) ? " " : ": ") + byLabel[label],
      );
    });
    return lines;
  };

  var messageWithAnswers = function (form) {
    var answers = extraAnswers(form);
    var written = value(form, "message");
    return answers.length ? answers.join("\n") + "\n\n" + written : written;
  };

  // The stock endpoint takes sender, subject and message only: the name, the phone, the consent and
  // the template's own questions all go at the top of the message.
  var legacyBody = function (form) {
    var head = [];
    if (value(form, "full_name"))
      head.push(text(form, "nameLabel") + ": " + value(form, "full_name"));
    if (value(form, "phone"))
      head.push(text(form, "phoneLabel") + ": " + value(form, "phone"));
    if (checkedConsent(form))
      head.push(text(form, "consentLabel") + ": " + checkedConsent(form));
    head = head.concat(extraAnswers(form));
    return new URLSearchParams({
      sender: value(form, "sender"),
      subject: value(form, "subject"),
      message:
        (head.length ? head.join("\n") + "\n\n" : "") + value(form, "message"),
    });
  };

  // The answers of a form kept as data: one entry for each name a control has, by what the control is. A
  // question of several choices (checkboxes sharing a name) answers with a list, a single box (the consent)
  // with true; the field only a script is shown is not an answer.
  var answersOf = function (form) {
    var answers = {};
    var groups = {};
    Array.prototype.forEach.call(form.elements, function (control) {
      if (!control.name || control.disabled || control.type === "hidden")
        return;
      if (control.type === "submit" || control.type === "button") return;
      if (control.hasAttribute("data-neo-honeypot")) return;
      (groups[control.name] = groups[control.name] || []).push(control);
    });
    Object.keys(groups).forEach(function (name) {
      var controls = groups[name];
      var first = controls[0];
      if (first.type === "checkbox") {
        var ticked = controls
          .filter(function (c) {
            return c.checked;
          })
          .map(function (c) {
            return c.value;
          });
        if (controls.length > 1) {
          if (ticked.length) answers[name] = ticked;
        } else if (ticked.length) {
          answers[name] = true;
        }
      } else if (first.type === "radio") {
        var picked = controls.filter(function (c) {
          return c.checked;
        })[0];
        if (picked) answers[name] = picked.value;
      } else if (first.value && first.value.trim()) {
        answers[name] = first.value.trim();
      }
    });
    return answers;
  };

  // The sentence the server gave for a refusal (frappe puts it in _server_messages), "" when there is none.
  var sentenceOf = function (response) {
    return response
      .json()
      .then(function (json) {
        var messages = JSON.parse((json && json._server_messages) || "[]");
        var first = messages.length ? JSON.parse(messages[0]) : null;
        return (first && first.message) || "";
      })
      .catch(function () {
        return "";
      });
  };

  // //// Neoffice — Cloudflare Turnstile, off unless the site switched it on with its keys: captcha_config answers
  // //// with the PUBLIC key only then, and nothing otherwise. Loaded once per page. A check that cannot be drawn
  // //// (Cloudflare blocked, the script failed) leaves the form usable: the message goes without it and the server
  // //// holds it back for the owner to look at, instead of turning the visitor away.
  var CAPTCHA_URL =
    "/api/method/neoffice_theme.website_messages.captcha_config";
  var captchaKey = null;
  var turnstileLoading = null;
  var siteCaptchaKey = function () {
    if (!captchaKey) {
      captchaKey = fetch(CAPTCHA_URL, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then(function (response) {
          return response.ok ? response.json() : {};
        })
        .then(function (json) {
          return (
            (json && json.message && json.message.turnstile_site_key) || ""
          );
        })
        .catch(function () {
          return "";
        });
    }
    return captchaKey;
  };
  var loadTurnstile = function () {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    if (!turnstileLoading) {
      turnstileLoading = new Promise(function (resolve, reject) {
        var script = document.createElement("script");
        script.src =
          "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        script.async = true;
        script.onload = function () {
          resolve(window.turnstile);
        };
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }
    return turnstileLoading;
  };
  // The check, drawn above the send button; null when the site has none or it cannot be drawn.
  var mountCaptcha = function (form, button) {
    return siteCaptchaKey()
      .then(function (key) {
        if (!key) return null;
        return loadTurnstile().then(function (turnstile) {
          var box = document.createElement("div");
          box.className = "builder-contact-form__captcha";
          var parent = button && button.parentNode ? button.parentNode : form;
          parent.insertBefore(box, button || null);
          var id = turnstile.render(box, { sitekey: key });
          return {
            value: function () {
              return turnstile.getResponse(id) || "";
            },
            reset: function () {
              turnstile.reset(id);
            },
          };
        });
      })
      .catch(function () {
        return null;
      });
  };

  var post = function (url, body) {
    var headers = { Accept: "application/json" };
    if (window.frappe && window.frappe.csrf_token)
      headers["X-Frappe-CSRF-Token"] = window.frappe.csrf_token;
    return fetch(url, {
      method: "POST",
      body: body,
      headers: headers,
      credentials: "same-origin",
    });
  };

  var bind = function (form) {
    form.setAttribute("data-bound", "1");

    var status = form.querySelector(
      "[data-neo-status], .builder-contact-form__status",
    );
    var button = form.querySelector('button[type="submit"]');
    var tokenUrl = form.dataset.tokenUrl || TOKEN_URL;
    var action = form.getAttribute("action") || SUBMIT_URL;
    var legacyAction = form.dataset.legacyAction || LEGACY_URL;
    var siteForm = form.dataset.neoForm || "";
    var captcha = null;
    mountCaptcha(form, button).then(function (widget) {
      captcha = widget;
    });
    var token = { value: "", at: 0, decoy: "" };
    // when the visitor first touched the form: a script posting at once has no such moment to report
    var touched = 0;
    var touch = function () {
      if (!touched) touched = Date.now();
    };
    ["keydown", "pointerdown", "input", "change"].forEach(function (type) {
      form.addEventListener(type, touch, true);
    });

    // //// Neoffice — the steps are an enhancement: without JavaScript every step shows and the
    // //// form posts in one go, so a visitor is never stuck on a page that cannot go forward.
    var steps = Array.prototype.slice
      .call(form.querySelectorAll("[data-step]"))
      .sort(function (a, b) {
        return Number(a.dataset.step) - Number(b.dataset.step);
      });
    var at = 1;

    var show = function (number) {
      at = number;
      steps.forEach(function (step) {
        step.hidden = Number(step.dataset.step) !== number;
      });
      form.querySelectorAll("[data-step-now]").forEach(function (el) {
        el.textContent = String(number);
      });
      var first = steps[number - 1].querySelector(
        "input:not([type=hidden]), textarea, select",
      );
      if (first && number > 1) first.focus();
    };

    var stepIsValid = function (index) {
      var controls = steps[index].querySelectorAll("input, textarea, select");
      for (var i = 0; i < controls.length; i++) {
        if (!controls[i].checkValidity()) {
          controls[i].reportValidity();
          return false;
        }
      }
      return true;
    };

    if (steps.length > 1) {
      form
        .querySelectorAll("[data-step-next], [data-step-back], [data-progress]")
        .forEach(function (el) {
          el.hidden = false;
        });
      form.querySelectorAll("[data-step-total]").forEach(function (el) {
        el.textContent = String(steps.length);
      });
      show(1);
      // delegated, so a template may put its own Next and Back inside each step
      form.addEventListener("click", function (event) {
        var target = event.target instanceof Element ? event.target : null;
        if (!target) return;
        if (target.closest("[data-step-next]")) {
          if (stepIsValid(at - 1)) show(Math.min(at + 1, steps.length));
        } else if (target.closest("[data-step-back]")) {
          show(Math.max(at - 1, 1));
        }
      });
    }

    // The signed token the server asks for: taken when the page loads, renewed when it has aged.
    // //// Neoffice — the field only a script is shown carries a name the server chose for this token, and
    // //// is added once the token is taken: a bot that reads the markup finds no such field to learn.
    var setDecoy = function (name) {
      var old = form.querySelector("[data-neo-honeypot][data-neo-decoy]");
      if (old) old.remove();
      if (!name) return;
      var decoy = document.createElement("input");
      decoy.type = "text";
      decoy.name = name;
      decoy.tabIndex = -1;
      decoy.autocomplete = "off";
      decoy.setAttribute("aria-hidden", "true");
      decoy.setAttribute("data-neo-honeypot", "1");
      decoy.setAttribute("data-neo-decoy", "1");
      form.appendChild(decoy);
    };

    var fetchToken = function () {
      var url = siteForm
        ? tokenUrl +
          (tokenUrl.indexOf("?") === -1 ? "?" : "&") +
          "form=" +
          encodeURIComponent(siteForm)
        : tokenUrl;
      return fetch(url, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then(function (response) {
          if (!response.ok) throw new Error(String(response.status));
          return response.json();
        })
        .then(function (json) {
          // a string for the forms written before the forms kept as data, an object for these
          var issued = (json && json.message) || "";
          if (typeof issued !== "object") issued = { token: issued, decoy: "" };
          token = {
            value: issued.token || "",
            at: Date.now(),
            decoy: issued.decoy || "",
          };
          setDecoy(token.decoy);
          return token.value;
        })
        .catch(function () {
          token = { value: "", at: 0, decoy: "" };
          setDecoy("");
          return "";
        });
    };
    var readyToken = function () {
      var fresh =
        token.value && Date.now() - token.at < TOKEN_FRESH_MS
          ? Promise.resolve(token.value)
          : fetchToken();
      return fresh.then(function (ready) {
        var wait = ready
          ? Math.max(0, TOKEN_MIN_AGE_MS - (Date.now() - token.at))
          : 0;
        return new Promise(function (resolve) {
          setTimeout(function () {
            resolve(ready);
          }, wait);
        });
      });
    };
    fetchToken();

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      if (button) button.disabled = true;
      readyToken()
        .then(function (ready) {
          // a form kept as data sends its answers as data, to the one entry point
          if (siteForm) {
            if (!ready) throw new Error("token");
            var data = new URLSearchParams({
              form: siteForm,
              answers: JSON.stringify(answersOf(form)),
              token: ready,
              elapsed: String(touched ? Date.now() - touched : 0),
              captcha: captcha ? captcha.value() : "",
            });
            var decoy = form.querySelector("[data-neo-decoy]");
            if (token.decoy) data.set(token.decoy, decoy ? decoy.value : "");
            return post(action, data);
          }
          if (!ready) return post(legacyAction, legacyBody(form));
          var body = new URLSearchParams({
            full_name: value(form, "full_name"),
            sender: value(form, "sender"),
            phone: value(form, "phone"),
            subject: value(form, "subject"),
            message: messageWithAnswers(form),
            consent: checkedConsent(form),
            token: ready,
            website: value(form, "website"),
            captcha: captcha ? captcha.value() : "",
          });
          return post(action, body).then(function (response) {
            if (response.status === 404)
              return post(legacyAction, legacyBody(form));
            return response;
          });
        })
        .then(function (response) {
          if (response.status === 429) throw new Error("429");
          if (!response.ok) {
            var failure = new Error(String(response.status));
            failure.response = response;
            throw failure;
          }
          form.reset();
          touched = 0;
          if (steps.length > 1) show(1);
          if (status) {
            status.textContent = text(form, "sent");
            status.classList.remove("is-error");
          }
          fetchToken();
        })
        .catch(function (error) {
          // a token serves one message: the next try needs a new one, sent or not
          if (siteForm) fetchToken();
          if (!status) return;
          // the server says what to correct (a required question, a choice that is not offered)
          var sentence =
            siteForm && error && error.response
              ? sentenceOf(error.response)
              : Promise.resolve("");
          return sentence.then(function (said) {
            status.textContent =
              error && error.message === "429"
                ? text(form, "throttled")
                : said || text(form, "failed");
            status.classList.add("is-error");
          });
        })
        .finally(function () {
          // a Turnstile answer serves once
          if (captcha) captcha.reset();
          if (status) status.hidden = false;
          if (button) button.disabled = false;
        });
    });
  };

  // //// Neoffice — the form in a window (the include's contact_dialog, and the "in a window" block
  // //// template). The first window of the page answers #contact: its own button, any link to
  // //// #contact on the page, and a visit to the page's #contact from elsewhere. Closing it takes
  // //// #contact off the address, so a reload does not open it again.
  var bindDialog = function (dialog) {
    dialog.setAttribute("data-bound", "1");
    var open = function () {
      if (dialog.open) return;
      var status = dialog.querySelector(
        "[data-neo-status], .builder-contact-form__status",
      );
      if (status) status.hidden = true;
      // the window focuses its first control, the close button: no keyboard springs up on a phone
      dialog.showModal();
    };
    var isContactLink = function (link) {
      if (!link || !link.getAttribute("href")) return false;
      var url = new URL(link.getAttribute("href"), window.location.href);
      return (
        url.hash === "#contact" &&
        url.origin === window.location.origin &&
        url.pathname === window.location.pathname
      );
    };
    document.addEventListener(
      "click",
      function (event) {
        var target = event.target instanceof Element ? event.target : null;
        if (!target) return;
        if (target.closest("[data-contact-open]")) {
          open();
          return;
        }
        var link = target.closest("a[href]");
        if (isContactLink(link)) {
          event.preventDefault();
          open();
        }
      },
      true,
    );
    var close = dialog.querySelector("[data-contact-close]");
    if (close)
      close.addEventListener("click", function () {
        dialog.close();
      });
    // a click on the backdrop lands on the dialog itself, outside its panel
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", function () {
      if (window.location.hash === "#contact") {
        history.replaceState(
          null,
          "",
          window.location.pathname + window.location.search,
        );
      }
    });
    window.addEventListener("hashchange", function () {
      if (window.location.hash === "#contact") open();
    });
    if (window.location.hash === "#contact") open();
  };

  // One listener per form and per window, however many times this runs: a page may carry the form
  // twice (a window and a section of its own), and a block may arrive after the page has loaded.
  var scan = function () {
    var forms = document.querySelectorAll(
      "form[data-neo-contact]:not([data-bound]), .builder-contact-form form:not([data-bound])",
    );
    if (forms.length) hideHoneypots();
    forms.forEach(bind);
    document
      .querySelectorAll(
        "dialog[data-neo-contact-dialog]:not([data-bound]), .builder-contact-form__dialog:not([data-bound])",
      )
      .forEach(function (dialog) {
        if (typeof dialog.showModal === "function") bindDialog(dialog);
      });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", scan);
  } else {
    scan();
  }
  // a form the owner's own script, or the editor's preview, puts on the page later
  window.neoContactForm = { scan: scan };
})();
