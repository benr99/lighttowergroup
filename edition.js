(function () {
  "use strict";

  function element(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function safeArticleUrl(value) {
    return /^\/insights\/[a-z0-9-]+\.html$/i.test(value || "") ? value : "";
  }

  function articleLink(article, className) {
    var link = element("a", className);
    link.href = safeArticleUrl(article.url) || "/insights.html";
    link.dataset.editionStory = article.slug || "";
    return link;
  }

  function formatDate(value) {
    var date = new Date(String(value || "") + "T12:00:00");
    return isNaN(date.getTime())
      ? String(value || "")
      : date.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  }

  function addMeta(parent, article) {
    var meta = element("div", "edition-meta");
    [
      article.format_label,
      article.franchise && article.franchise.name,
      article.read_time ? article.read_time + " min" : "",
      article.source_count ? article.source_count + " sources" : ""
    ].filter(Boolean).forEach(function (value) {
      meta.appendChild(element("span", "", value));
    });
    parent.appendChild(meta);
  }

  function renderFeature(article) {
    var link = articleLink(article, "edition-feature");
    link.appendChild(element("span", "edition-section-label", article.format_label || "Flagship Analysis"));
    link.appendChild(element("h3", "", article.title));
    link.appendChild(element("p", "", article.subtitle));
    addMeta(link, article);
    return link;
  }

  function renderBrief(article) {
    var link = articleLink(article, "edition-brief");
    link.appendChild(element("span", "edition-section-label", (article.franchise && article.franchise.name) || article.format_label));
    link.appendChild(element("h3", "", article.title));
    link.appendChild(element("p", "", article.subtitle));
    addMeta(link, article);
    return link;
  }

  function renderTapeItem(item) {
    var row = element("li", "edition-tape-item");
    var link = element("a", "", item.title);
    link.href = /^https?:\/\//.test(item.source_url || "") ? item.source_url : "#";
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    row.appendChild(link);
    row.appendChild(element("p", "", item.one_line));
    return row;
  }

  async function postJson(url, payload) {
    var response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    var data = await response.json().catch(function () { return {}; });
    if (!response.ok) throw new Error(data.error || "Request failed");
    return data;
  }

  function bindSubscribe(root) {
    var form = root.querySelector("[data-edition-subscribe]");
    if (!form) return;
    var status = form.querySelector(".edition-form-status");
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      var button = form.querySelector("button");
      button.disabled = true;
      status.textContent = "Adding you to the edition...";
      try {
        await postJson("/.netlify/functions/newsletter-subscribe", {
          email: form.elements.email.value,
          first_name: form.elements.first_name ? form.elements.first_name.value : "",
          website: form.elements.website ? form.elements.website.value : "",
          source: "insights-edition"
        });
        status.textContent = "You are on the list. Watch your inbox.";
        form.reset();
        window.ltgTrack("newsletter_subscribe", { source: "insights-edition" });
      } catch (error) {
        status.textContent = error.message || "Subscription is temporarily unavailable.";
      } finally {
        button.disabled = false;
      }
    });
  }

  function bindPoll(root, prompt) {
    var poll = root.querySelector("[data-edition-poll]");
    if (!poll || !prompt || !Array.isArray(prompt.options)) return;
    poll.replaceChildren();
    prompt.options.forEach(function (option) {
      var button = element("button", "edition-poll-button", option);
      button.type = "button";
      button.addEventListener("click", async function () {
        poll.querySelectorAll("button").forEach(function (item) {
          item.setAttribute("aria-pressed", item === button ? "true" : "false");
        });
        try {
          await postJson("/.netlify/functions/editorial-feedback", {
            feedback_type: "poll",
            prompt_id: prompt.id,
            option: option,
            page_path: window.location.pathname
          });
          window.ltgTrack("editorial_poll_response", { prompt_id: prompt.id, option: option });
        } catch (error) {
          button.setAttribute("aria-pressed", "false");
        }
      });
      poll.appendChild(button);
    });
  }

  function bindReaderPrompt(root, prompt) {
    var form = root.querySelector("[data-edition-feedback]");
    if (!form) return;
    var status = form.querySelector(".edition-form-status");
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      var button = form.querySelector("button");
      button.disabled = true;
      status.textContent = "Sending to the editorial desk...";
      try {
        await postJson("/.netlify/functions/editorial-feedback", {
          feedback_type: "reader_prompt",
          prompt_id: (prompt && prompt.id) || "open-reader-desk",
          comment: form.elements.comment.value,
          page_path: window.location.pathname
        });
        status.textContent = "Received. Thank you for trusting the desk.";
        form.reset();
        window.ltgTrack("editorial_reader_prompt", { prompt_id: (prompt && prompt.id) || "open-reader-desk" });
      } catch (error) {
        status.textContent = error.message || "The reader desk is temporarily unavailable.";
      } finally {
        button.disabled = false;
      }
    });
  }

  function bindStoryTracking(root) {
    root.querySelectorAll("[data-edition-story]").forEach(function (link) {
      link.addEventListener("click", function () {
        window.ltgTrack("edition_story_click", { story_slug: link.dataset.editionStory });
      });
    });
  }

  function renderEdition(root, edition) {
    root.hidden = false;
    root.querySelector("[data-edition-date]").textContent = formatDate(edition.edition_date);
    root.querySelector("[data-edition-dek]").textContent = edition.dek || "";

    var lead = root.querySelector("[data-edition-lead]");
    var secondary = root.querySelector("[data-edition-secondary]");
    lead.replaceChildren();
    secondary.replaceChildren();

    var briefs = Array.isArray(edition.briefs) ? edition.briefs : [];
    if (edition.flagship) lead.appendChild(renderFeature(edition.flagship));

    var briefBox = element("div", "edition-briefs");
    briefBox.appendChild(element("span", "edition-section-label", "The Briefing"));
    briefs.forEach(function (article) { briefBox.appendChild(renderBrief(article)); });
    if (briefs.length) lead.appendChild(briefBox);

    if (edition.culture_signal) {
      var culture = element("div", "edition-culture");
      culture.appendChild(element("span", "edition-section-label", "Culture of Capital"));
      culture.appendChild(renderBrief(edition.culture_signal));
      secondary.appendChild(culture);
    }

    if (edition.data_note) {
      var dataNote = element("div", "edition-culture");
      dataNote.appendChild(element("span", "edition-section-label", "One Chart, One Argument"));
      dataNote.appendChild(renderBrief(edition.data_note));
      secondary.appendChild(dataNote);
    }

    if (Array.isArray(edition.deal_tape) && edition.deal_tape.length) {
      var tape = element("div", "edition-tape");
      tape.appendChild(element("span", "edition-section-label", "Deal Tape"));
      var list = element("ul", "edition-tape-list");
      edition.deal_tape.forEach(function (item) { list.appendChild(renderTapeItem(item)); });
      tape.appendChild(list);
      secondary.appendChild(tape);
    }

    if (!edition.flagship && !briefs.length && !edition.culture_signal && !edition.data_note && !edition.deal_tape.length) {
      lead.appendChild(element(
        "p",
        "edition-empty",
        "Nothing cleared the editorial bar today. That is a feature, not a failure. The next edition will publish when the reporting earns your attention."
      ));
    }

    lead.hidden = false;
    secondary.hidden = secondary.children.length === 0;
    var prompt = edition.reader_prompt || {};
    root.querySelector("[data-edition-question]").textContent = prompt.question || "What should Light Tower investigate next?";
    bindPoll(root, prompt);
    bindReaderPrompt(root, prompt);
    bindSubscribe(root);
    bindStoryTracking(root);
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.getElementById("daily-edition");
    if (!root) return;
    fetch("/latest-edition.json", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("Edition unavailable");
        return response.json();
      })
      .then(function (edition) { renderEdition(root, edition); })
      .catch(function () {
        root.hidden = false;
        root.querySelector("[data-edition-lead]").replaceChildren(
          element("p", "edition-empty", "The curated edition is being prepared.")
        );
        bindSubscribe(root);
      });
  });
})();
