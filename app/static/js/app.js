(() => {
  "use strict";

  /* --------------------------------------------------
     State
  -------------------------------------------------- */
  const state = {
    view: "home",
    messages: [], // { role, content, status, reportId, question, failed }
    pendingApproval: null, // { question, messageIndex }
    kbLoaded: false,
    reportsLoaded: false,
  };

  const VIEW_TITLES = {
    home: "Home",
    chat: "Chat",
    "knowledge-base": "Knowledge Base",
    reports: "Saved Reports",
    dashboard: "Dashboard",
    about: "About",
  };

  const KB_ICONS = {
    techniques: '<path d="M6 18 L12 6 L18 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',
    rules: '<path d="M12 3v18M6 7h12M8 7l-4 8a4 4 0 0 0 8 0zM16 7l-4 8a4 4 0 0 0 8 0z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>',
    strategy: '<circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="4" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="0.8" fill="currentColor"/>',
    training: '<path d="M6 12h12M4 9v6M20 9v6M2 10v4M22 10v4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',
    injuries: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><path d="M12 8v5M9.5 10.5h5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    glossary: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
    faq: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="1.6"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.4 2.3c-.7.3-1.2.9-1.2 1.7v.3M12 17v.01" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    default: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  };

  /* --------------------------------------------------
     DOM helpers
  -------------------------------------------------- */
  const $ = (sel, root = document) => root.querySelector(sel);
  const $all = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /** Minimal, dependency-free markdown renderer for the small subset the
   * agent's system prompt actually produces (headings, bold, lists, code,
   * paragraphs). Avoids pulling in an external markdown library. */
  function renderMarkdown(text) {
    const escaped = escapeHtml(text);
    const lines = escaped.split("\n");
    let html = "";
    let inList = false;

    for (const rawLine of lines) {
      const line = rawLine.trim();

      if (/^#{1,3}\s+/.test(line)) {
        if (inList) { html += "</ul>"; inList = false; }
        const level = line.match(/^#+/)[0].length;
        html += `<h${Math.min(level + 1, 3)}>${line.replace(/^#{1,3}\s+/, "")}</h${Math.min(level + 1, 3)}>`;
        continue;
      }

      if (/^[-*]\s+/.test(line)) {
        if (!inList) { html += "<ul>"; inList = true; }
        html += `<li>${inlineMarkdown(line.replace(/^[-*]\s+/, ""))}</li>`;
        continue;
      }

      if (inList) { html += "</ul>"; inList = false; }

      if (line === "") continue;

      html += `<p>${inlineMarkdown(line)}</p>`;
    }

    if (inList) html += "</ul>";
    return html || `<p>${escaped}</p>`;
  }

  function inlineMarkdown(text) {
    return text
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }

  function formatTime(date) {
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function timeAgo(epochSeconds) {
    const diffMs = Date.now() - epochSeconds * 1000;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }

  /* --------------------------------------------------
     Toasts
  -------------------------------------------------- */
  function showToast(message, kind = "default") {
    const stack = $("#toast-stack");
    const toast = document.createElement("div");
    toast.className = `toast ${kind}`;
    toast.textContent = message;
    stack.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 200ms ease";
      setTimeout(() => toast.remove(), 220);
    }, 3200);
  }

  /* --------------------------------------------------
     Ripple effect for buttons
  -------------------------------------------------- */
  document.addEventListener("click", (event) => {
    const btn = event.target.closest(".btn, .btn-send, .btn-new-chat");
    if (!btn) return;
    const rect = btn.getBoundingClientRect();
    const ripple = document.createElement("span");
    const size = Math.max(rect.width, rect.height);
    ripple.className = "ripple";
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${event.clientX - rect.left - size / 2}px`;
    ripple.style.top = `${event.clientY - rect.top - size / 2}px`;
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 500);
  });

  /* --------------------------------------------------
     Theme
  -------------------------------------------------- */
  function initTheme() {
    const stored = localStorage.getItem("judocoach-theme");
    if (stored) document.documentElement.setAttribute("data-theme", stored);
    updateThemeLabel();
  }

  function updateThemeLabel() {
    const current = document.documentElement.getAttribute("data-theme");
    const isDark = current === "dark" ||
      (!current && window.matchMedia("(prefers-color-scheme: dark)").matches);
    $("[data-el='theme-label']").textContent = isDark ? "Dark mode" : "Light mode";
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute("data-theme");
    const isDark = current === "dark" ||
      (!current && window.matchMedia("(prefers-color-scheme: dark)").matches);
    const next = isDark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("judocoach-theme", next);
    updateThemeLabel();
  }

  /* --------------------------------------------------
     Navigation
  -------------------------------------------------- */
  function setView(view) {
    state.view = view;
    $all(".view").forEach((el) => el.classList.remove("active"));
    $(`#view-${view}`).classList.add("active");
    $all(".nav-item").forEach((el) => el.classList.toggle("active", el.dataset.view === view));
    $("[data-el='view-title']").textContent = VIEW_TITLES[view] || "JudoCoach AI";
    $("#sidebar").classList.remove("open");

    if (view === "knowledge-base" && !state.kbLoaded) loadKnowledgeBase();
    if (view === "reports" && !state.reportsLoaded) loadReports();
    if (view === "dashboard") loadDashboard();
  }

  /* --------------------------------------------------
     Status strip
  -------------------------------------------------- */
  function setDot(name, level) {
    const dot = $(`.status-dot[data-status="${name}"]`);
    if (dot) dot.className = `status-dot ${level}`;
  }

  async function refreshStatus() {
    try {
      const health = await fetch("/health");
      setDot("api", health.ok ? "ok" : "error");
    } catch {
      setDot("api", "error");
    }

    try {
      const res = await fetch("/stats");
      if (!res.ok) throw new Error("stats unavailable");
      const data = await res.json();

      setDot("kb", data.documents_indexed > 0 ? "ok" : "warn");
      $("[data-el='kb-status-label']").textContent = `Knowledge Base (${data.documents_indexed})`;

      setDot("index", data.vector_index_available ? "ok" : "warn");

      setDot("model", data.model_name ? "ok" : "warn");
      $("[data-el='model-status-label']").textContent = data.model_name ? `Model: ${data.model_name}` : "Model";
    } catch {
      setDot("kb", "error");
      setDot("index", "error");
      setDot("model", "error");
    }
  }

  /* --------------------------------------------------
     Chat
  -------------------------------------------------- */
  function renderChatEmptyState() {
    const hasMessages = state.messages.length > 0;
    $("#chat-empty").style.display = hasMessages ? "none" : "block";
  }

  function appendMessageEl(message, index) {
    const container = $("#chat-messages");
    const row = document.createElement("div");
    row.className = `message-row ${message.role}`;
    row.dataset.index = index;

    const avatar = document.createElement("div");
    avatar.className = `avatar ${message.role}`;
    avatar.textContent = message.role === "user" ? "You" : "JC";

    const bubble = document.createElement("div");
    bubble.className = "bubble";

    if (message.role === "assistant") {
      if (message.pending) {
        bubble.innerHTML = `<div class="typing-indicator"><span></span><span></span><span></span></div>`;
      } else if (message.failed) {
        bubble.innerHTML = `
          <span class="status-badge failed">Failed</span>
          <p>${escapeHtml(message.content)}</p>
          <span class="meta-time">${formatTime(new Date())}</span>
        `;
      } else {
        const badge = message.status
          ? `<span class="status-badge ${message.status}">${message.status.replace("_", " ")}</span>`
          : "";
        let approvalBtn = "";
        if (message.status === "awaiting_approval") {
          approvalBtn = `<div class="approval-actions"><button class="btn btn-primary" data-action="open-approval" data-index="${index}">Approve &amp; Save</button></div>`;
        }
        bubble.innerHTML = `
          ${badge}
          ${renderMarkdown(message.content)}
          ${approvalBtn}
          <span class="meta-time">${formatTime(new Date())}${message.reportId ? ` · Report ${message.reportId}` : ""}</span>
        `;
      }
    } else {
      bubble.innerHTML = `<p>${escapeHtml(message.content)}</p><span class="meta-time">${formatTime(new Date())}</span>`;
    }

    row.appendChild(avatar);
    row.appendChild(bubble);
    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
    renderChatEmptyState();
  }

  function updateMessageEl(index) {
    const row = $(`.message-row[data-index="${index}"]`);
    if (!row) return;
    row.remove();
    appendMessageEl(state.messages[index], index);
  }

  function validateQuestion(text) {
    return text.trim().length >= 10 && text.trim().length <= 2000;
  }

  /** Even when the API returns status "approved", the two-step draft/approve
   * flow re-runs the agent as a fresh conversation with no memory of the
   * draft — the model can still choose not to call save_report. Rather than
   * trust the status label alone, confirm a report file actually appeared
   * before telling the user it was saved. */
  async function confirmReportWasSaved(beforeTimestamp) {
    try {
      const res = await fetch("/reports");
      const data = await res.json();
      return data.reports.some((r) => r.saved_at > beforeTimestamp);
    } catch {
      return null; // unknown — do not claim success either way
    }
  }

  async function submitQuestion(question, { approve = false, replaceIndex = null } = {}) {
    let assistantIndex = replaceIndex;
    const requestStartedAt = Date.now() / 1000;

    if (replaceIndex === null) {
      state.messages.push({ role: "user", content: question });
      appendMessageEl(state.messages[state.messages.length - 1], state.messages.length - 1);

      state.messages.push({ role: "assistant", pending: true });
      assistantIndex = state.messages.length - 1;
      appendMessageEl(state.messages[assistantIndex], assistantIndex);
    } else {
      state.messages[assistantIndex] = { role: "assistant", pending: true };
      updateMessageEl(assistantIndex);
    }

    try {
      const res = await fetch("/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, require_approval: !approve }),
      });

      if (res.status === 422) {
        const body = await res.json();
        const detail = body.detail?.[0]?.msg || "Please rephrase your question.";
        state.messages[assistantIndex] = { role: "assistant", failed: true, content: detail };
        updateMessageEl(assistantIndex);
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        state.messages[assistantIndex] = {
          role: "assistant",
          failed: true,
          content: body.detail || "Something went wrong reaching JudoCoach AI. Please try again.",
        };
        updateMessageEl(assistantIndex);
        return;
      }

      const data = await res.json();
      state.messages[assistantIndex] = {
        role: "assistant",
        content: data.result,
        status: data.status,
        reportId: data.report_id,
        question,
      };
      updateMessageEl(assistantIndex);

      if (approve && data.status === "approved") {
        const wasSaved = await confirmReportWasSaved(requestStartedAt);
        if (wasSaved === true) {
          showToast("Report saved and audit event recorded.", "success");
          state.reportsLoaded = false;
        } else if (wasSaved === false) {
          showToast("Approved, but the assistant did not save a report this run. Try again.", "error");
        }
      }
    } catch {
      state.messages[assistantIndex] = {
        role: "assistant",
        failed: true,
        content: "Network error reaching JudoCoach AI. Check your connection and try again.",
      };
      updateMessageEl(assistantIndex);
    }
  }

  function initChatForm() {
    const form = $("#chat-form");
    const textarea = $("#chat-input");
    const fieldError = $("#chat-field-error");
    const sendBtn = $("#chat-send");

    textarea.addEventListener("input", () => {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const question = textarea.value.trim();

      if (!validateQuestion(question)) {
        fieldError.classList.add("visible");
        return;
      }
      fieldError.classList.remove("visible");

      sendBtn.disabled = true;
      submitQuestion(question).finally(() => {
        sendBtn.disabled = false;
      });

      textarea.value = "";
      textarea.style.height = "auto";
    });

    document.addEventListener("click", (event) => {
      const approvalBtn = event.target.closest("[data-action='open-approval']");
      if (approvalBtn) {
        const index = Number(approvalBtn.dataset.index);
        state.pendingApproval = { messageIndex: index, question: state.messages[index].question };
        $("#approval-modal").classList.add("open");
      }
    });
  }

  /* --------------------------------------------------
     Approval modal
  -------------------------------------------------- */
  function initApprovalModal() {
    $("[data-action='dismiss-approval']").addEventListener("click", () => {
      $("#approval-modal").classList.remove("open");
      state.pendingApproval = null;
    });

    $("[data-action='confirm-approval']").addEventListener("click", async () => {
      const pending = state.pendingApproval;
      $("#approval-modal").classList.remove("open");
      if (!pending) return;
      await submitQuestion(pending.question, { approve: true, replaceIndex: pending.messageIndex });
      state.pendingApproval = null;
    });
  }

  /* --------------------------------------------------
     Knowledge Base view
  -------------------------------------------------- */
  function iconFor(fileName) {
    const key = Object.keys(KB_ICONS).find((k) => fileName.includes(k));
    return KB_ICONS[key] || KB_ICONS.default;
  }

  async function loadKnowledgeBase() {
    const grid = $("#kb-grid");
    try {
      const res = await fetch("/knowledge-base");
      const data = await res.json();
      state.kbLoaded = true;

      if (!data.documents.length) {
        grid.innerHTML = emptyStateHtml("No documents indexed yet", "Run `python -m app.ingest` to build the knowledge base.");
        return;
      }

      grid.innerHTML = data.documents.map((doc) => `
        <div class="kb-card">
          <div class="kb-icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none">${iconFor(doc.file_name)}</svg></div>
          <h3>${escapeHtml(doc.title)}</h3>
          <p>${escapeHtml(doc.description)}</p>
        </div>
      `).join("");
    } catch {
      grid.innerHTML = errorBannerHtml("Could not load the knowledge base.");
    }
  }

  /* --------------------------------------------------
     Reports view
  -------------------------------------------------- */
  async function loadReports() {
    const list = $("#reports-list");
    try {
      const res = await fetch("/reports");
      const data = await res.json();
      state.reportsLoaded = true;

      if (!data.reports.length) {
        list.innerHTML = emptyStateHtml("No reports saved yet", "Approve a research draft in the Chat view to save your first report.");
        return;
      }

      list.innerHTML = data.reports.map((r) => `
        <div class="report-row" data-action="open-report" data-name="${escapeHtml(r.name)}">
          <div>
            <div class="report-title">${escapeHtml(r.name.replace(/_/g, " "))}</div>
            <div class="report-preview">${escapeHtml(r.preview)}</div>
          </div>
          <div class="report-meta">${r.report_id ? `#${escapeHtml(r.report_id)} · ` : ""}${timeAgo(r.saved_at)}</div>
        </div>
      `).join("");

      $all("[data-action='open-report']").forEach((el) => {
        el.addEventListener("click", () => openReportModal(el.dataset.name));
      });
    } catch {
      list.innerHTML = errorBannerHtml("Could not load saved reports.");
    }
  }

  async function openReportModal(name) {
    try {
      const res = await fetch(`/reports/${encodeURIComponent(name)}`);
      if (!res.ok) throw new Error("not found");
      const data = await res.json();
      $("#report-modal-title").textContent = data.name.replace(/_/g, " ");
      $("#report-modal-content").textContent = data.content;
      $("#report-modal").classList.add("open");
    } catch {
      showToast("Could not open that report.", "error");
    }
  }

  /* --------------------------------------------------
     Dashboard view
  -------------------------------------------------- */
  async function loadDashboard() {
    const statGrid = $("#stat-grid");
    const activityList = $("#activity-list");

    try {
      const res = await fetch("/stats");
      const data = await res.json();

      statGrid.innerHTML = `
        <div class="stat-card">
          <div class="stat-value">${data.documents_indexed}</div>
          <div class="stat-label">Documents Indexed</div>
        </div>
        <div class="stat-card gold">
          <div class="stat-value">${data.reports_saved}</div>
          <div class="stat-label">Reports Saved</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${data.audit_events_logged}</div>
          <div class="stat-label">Audit Events Logged</div>
        </div>
      `;
    } catch {
      statGrid.innerHTML = errorBannerHtml("Could not load dashboard stats.");
    }

    try {
      const res = await fetch("/reports");
      const data = await res.json();

      if (!data.reports.length) {
        activityList.innerHTML = emptyStateHtml("No activity yet", "Saved reports will appear here.");
        return;
      }

      activityList.innerHTML = data.reports.slice(0, 5).map((r) => `
        <div class="activity-row">
          <span class="activity-name">${escapeHtml(r.name.replace(/_/g, " "))}</span>
          <span class="activity-time">${timeAgo(r.saved_at)}</span>
        </div>
      `).join("");
    } catch {
      activityList.innerHTML = errorBannerHtml("Could not load recent activity.");
    }
  }

  /* --------------------------------------------------
     Shared HTML snippets
  -------------------------------------------------- */
  function emptyStateHtml(title, description) {
    return `
      <div class="empty-state">
        <svg width="36" height="36" viewBox="0 0 24 24" fill="none"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(description)}</p>
      </div>
    `;
  }

  function errorBannerHtml(message) {
    return `<div class="error-banner">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 9v4M12 17h.01M10.3 3.9L2.7 17a2 2 0 0 0 1.7 3h15.2a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
      <span>${escapeHtml(message)}</span>
    </div>`;
  }

  /* --------------------------------------------------
     Init
  -------------------------------------------------- */
  function init() {
    initTheme();
    initChatForm();
    initApprovalModal();

    $all(".nav-item").forEach((btn) => {
      btn.addEventListener("click", () => setView(btn.dataset.view));
    });

    $("[data-action='toggle-theme']").addEventListener("click", toggleTheme);
    $("[data-action='toggle-sidebar']").addEventListener("click", () => {
      $("#sidebar").classList.toggle("open");
    });
    $("[data-action='new-chat']").addEventListener("click", () => {
      state.messages = [];
      $("#chat-messages").innerHTML = "";
      $("#chat-messages").appendChild($("#chat-empty"));
      renderChatEmptyState();
      setView("chat");
    });

    $all("[data-action='ask']").forEach((chip) => {
      chip.addEventListener("click", () => {
        setView("chat");
        submitQuestion(chip.dataset.question);
      });
    });

    $("[data-action='close-report-modal']").addEventListener("click", () => {
      $("#report-modal").classList.remove("open");
    });

    document.querySelectorAll(".modal-overlay").forEach((overlay) => {
      overlay.addEventListener("click", (event) => {
        if (event.target === overlay) overlay.classList.remove("open");
      });
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        document.querySelectorAll(".modal-overlay.open").forEach((m) => m.classList.remove("open"));
      }
    });

    refreshStatus();
    setInterval(refreshStatus, 30000);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
