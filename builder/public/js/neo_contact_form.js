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
   //// To remove: nothing to remove, there is no upstream counterpart. */
(function () {
  // The eight names neoffice_theme.website_messages.submit knows. Anything else is a question of
  // this template's own, and travels inside the message.
  var KNOWN_FIELDS = [
    "full_name",
    "sender",
    "phone",
    "subject",
    "message",
    "consent",
    "website",
    "token",
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
    var token = { value: "", at: 0 };

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
    var fetchToken = function () {
      return fetch(tokenUrl, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then(function (response) {
          if (!response.ok) throw new Error(String(response.status));
          return response.json();
        })
        .then(function (json) {
          token = { value: (json && json.message) || "", at: Date.now() };
          return token.value;
        })
        .catch(function () {
          token = { value: "", at: 0 };
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
          });
          return post(action, body).then(function (response) {
            if (response.status === 404)
              return post(legacyAction, legacyBody(form));
            return response;
          });
        })
        .then(function (response) {
          if (response.status === 429) throw new Error("429");
          if (!response.ok) throw new Error(String(response.status));
          form.reset();
          if (steps.length > 1) show(1);
          if (status) {
            status.textContent = text(form, "sent");
            status.classList.remove("is-error");
          }
          fetchToken();
        })
        .catch(function (error) {
          if (!status) return;
          status.textContent =
            error && error.message === "429"
              ? text(form, "throttled")
              : text(form, "failed");
          status.classList.add("is-error");
        })
        .finally(function () {
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
