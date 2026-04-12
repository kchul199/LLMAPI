(function () {
  const STATUS_CLASS_MAP = {
    RECEIVED: "status-received",
    QUEUED: "status-queued",
    PROCESSING: "status-processing",
    COMPLETED: "status-completed",
    FAILED: "status-failed",
    TIMEOUT: "status-timeout",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function safeJson(value) {
    try {
      return JSON.stringify(value ?? {}, null, 2);
    } catch (_) {
      return String(value);
    }
  }

  function setText(id, value) {
    const el = byId(id);
    if (el) {
      el.textContent = value ?? "-";
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatDateTime(value) {
    if (!value) {
      return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }
    return date.toLocaleString("ko-KR", {
      timeZone: "Asia/Seoul",
      hour12: false,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function applyStatusBadge(el, status, label) {
    if (!el) {
      return;
    }
    el.className = "status-badge";
    if (status && Object.prototype.hasOwnProperty.call(STATUS_CLASS_MAP, status)) {
      el.classList.add(STATUS_CLASS_MAP[status]);
    } else {
      el.classList.add("status-neutral");
    }
    el.textContent = label || status || "-";
  }

  async function apiFetch(url, options) {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
      },
      ...options,
    });

    let payload = null;
    try {
      payload = await response.json();
    } catch (_) {
      payload = null;
    }

    if (!response.ok) {
      const detail = payload && payload.detail ? payload.detail : payload;
      const err = new Error((detail && detail.error_message) || response.statusText);
      err.status = response.status;
      err.payload = detail || payload || { error_message: response.statusText };
      throw err;
    }

    return {
      status: response.status,
      data: payload,
    };
  }

  async function copyText(value) {
    if (!navigator.clipboard) {
      throw new Error("클립보드를 사용할 수 없습니다.");
    }
    await navigator.clipboard.writeText(value);
  }

  function showBlockMessage(el, message, hiddenWhenEmpty = true) {
    if (!el) {
      return;
    }

    if (!message && hiddenWhenEmpty) {
      el.hidden = true;
      el.textContent = "";
      return;
    }

    el.hidden = false;
    el.textContent = message || "";
  }

  window.UICommon = {
    byId,
    safeJson,
    setText,
    escapeHtml,
    formatDateTime,
    applyStatusBadge,
    apiFetch,
    copyText,
    showBlockMessage,
  };
})();
