(function () {
  const {
    byId,
    apiFetch,
    safeJson,
    setText,
    showBlockMessage,
    applyStatusBadge,
    copyText,
  } = window.UICommon;

  let lastResponseJson = "{}";
  let polling = false;

  function readCheckedValues(name) {
    return Array.from(document.querySelectorAll(`input[name="${name}"]:checked`)).map((el) => el.value);
  }

  function getRadioValue(name) {
    const node = document.querySelector(`input[name="${name}"]:checked`);
    return node ? node.value : "both";
  }

  function setButtonsDisabled(disabled) {
    ["btn-sync", "btn-async", "btn-sample", "btn-reset"].forEach((id) => {
      const btn = byId(id);
      if (btn) {
        btn.disabled = disabled;
      }
    });
  }

  function generateRequestId() {
    const timestamp = new Date().toISOString().replace(/[-:.TZ]/g, "").slice(0, 14);
    return `req_${timestamp}`;
  }

  function validatePayload(payload) {
    if (!payload.source_system || payload.source_system.trim().length === 0) {
      return "source_system은 필수입니다.";
    }
    if (!payload.client_request_id || payload.client_request_id.trim().length === 0) {
      return "client_request_id는 필수입니다.";
    }
    if (!payload.text || payload.text.trim().length === 0) {
      return "text는 필수입니다.";
    }
    if (!payload.tasks || payload.tasks.length === 0) {
      return "tasks를 최소 1개 이상 선택해야 합니다.";
    }
    return null;
  }

  function collectPayload() {
    return {
      source_system: byId("source_system").value.trim(),
      client_request_id: byId("client_request_id").value.trim(),
      text: byId("text").value.trim(),
      tasks: readCheckedValues("tasks"),
      target_speakers: getRadioValue("target_speakers"),
      options: {
        language: "ko",
        prompt_version: byId("prompt_version").value.trim() || "v1.1",
      },
    };
  }

  function setMeta({ requestUid = "-", traceId = "-", jobId = "-", httpStatus = "-", mode = "-", pollingText = "-" }) {
    setText("meta-request-uid", requestUid);
    setText("meta-trace-id", traceId);
    setText("meta-job-id", jobId);
    setText("meta-http-status", String(httpStatus));
    setText("meta-mode", mode);
    setText("meta-polling", pollingText);
  }

  function renderResponse(httpStatus, mode, data) {
    const status = data && data.status ? data.status : "-";
    applyStatusBadge(byId("response-status-badge"), status, status);
    setMeta({
      requestUid: data && data.request_uid ? data.request_uid : "-",
      traceId: data && data.trace_id ? data.trace_id : "-",
      jobId: data && data.job_id ? data.job_id : "-",
      httpStatus,
      mode,
      pollingText: polling ? "running" : "-",
    });

    showBlockMessage(byId("response-error"), "", true);
    lastResponseJson = safeJson(data);
    byId("response-json").textContent = lastResponseJson;
  }

  function renderError(error, mode) {
    const payload = error && error.payload ? error.payload : {};
    const message = [
      `HTTP ${error.status || "-"}`,
      payload.error_code ? `error_code: ${payload.error_code}` : null,
      payload.error_message ? `error_message: ${payload.error_message}` : error.message,
    ]
      .filter(Boolean)
      .join("\n");

    applyStatusBadge(byId("response-status-badge"), "FAILED", "FAILED");
    setMeta({
      requestUid: payload.request_uid || "-",
      traceId: payload.trace_id || "-",
      jobId: payload.job_id || "-",
      httpStatus: error.status || "-",
      mode,
      pollingText: polling ? "running" : "-",
    });

    showBlockMessage(byId("response-error"), message, false);
    lastResponseJson = safeJson(payload);
    byId("response-json").textContent = lastResponseJson;
  }

  async function runSync() {
    const payload = collectPayload();
    const errorMessage = validatePayload(payload);
    showBlockMessage(byId("form-error"), errorMessage, true);
    if (errorMessage) {
      return;
    }

    setButtonsDisabled(true);
    try {
      const { status, data } = await apiFetch("/ui/api/analyze", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderResponse(status, "sync", data);
    } catch (error) {
      renderError(error, "sync");
    } finally {
      setButtonsDisabled(false);
    }
  }

  async function pollAsync(jobId) {
    polling = true;
    const maxAttempts = 60;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      setMeta({ pollingText: `${attempt}/${maxAttempts}` });
      try {
        const { status, data } = await apiFetch(`/ui/api/analyze/async/${encodeURIComponent(jobId)}`);
        renderResponse(status, "async", data);

        if (["COMPLETED", "FAILED", "TIMEOUT"].includes(data.status)) {
          polling = false;
          setMeta({
            requestUid: data.request_uid || "-",
            traceId: data.trace_id || "-",
            jobId: data.job_id || "-",
            httpStatus: status,
            mode: "async",
            pollingText: "done",
          });
          return;
        }
      } catch (error) {
        polling = false;
        renderError(error, "async");
        return;
      }

      await new Promise((resolve) => {
        setTimeout(resolve, 2000);
      });
    }

    polling = false;
    showBlockMessage(byId("response-error"), "비동기 폴링 시간(2분)을 초과했습니다.", false);
    setMeta({ pollingText: "timeout" });
  }

  async function runAsync() {
    const payload = collectPayload();
    const errorMessage = validatePayload(payload);
    showBlockMessage(byId("form-error"), errorMessage, true);
    if (errorMessage) {
      return;
    }

    setButtonsDisabled(true);
    try {
      const { status, data } = await apiFetch("/ui/api/analyze/async", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderResponse(status, "async", data);
      if (data.job_id) {
        await pollAsync(data.job_id);
      }
    } catch (error) {
      renderError(error, "async");
    } finally {
      setButtonsDisabled(false);
    }
  }

  function fillSample() {
    byId("source_system").value = "qa-admin";
    byId("client_request_id").value = generateRequestId();
    byId("text").value = "고객: 배송이 늦어요. 상담원: 확인 후 안내드릴게요.";
    byId("prompt_version").value = "v1.1";

    Array.from(document.querySelectorAll('input[name="tasks"]')).forEach((el) => {
      el.checked = ["summary", "sentiment"].includes(el.value);
    });
    document.querySelector('input[name="target_speakers"][value="both"]').checked = true;
  }

  function prefillFromQuery() {
    const query = new URLSearchParams(window.location.search);
    const sourceSystem = query.get("source_system");
    const clientRequestId = query.get("client_request_id");
    const text = query.get("text");
    const targetSpeakers = query.get("target_speakers");
    const promptVersion = query.get("prompt_version");
    const tasks = query.get("tasks");

    if (sourceSystem) byId("source_system").value = sourceSystem;
    if (clientRequestId) byId("client_request_id").value = clientRequestId;
    if (text) byId("text").value = text;
    if (promptVersion) byId("prompt_version").value = promptVersion;

    if (targetSpeakers) {
      const radio = document.querySelector(`input[name="target_speakers"][value="${targetSpeakers}"]`);
      if (radio) radio.checked = true;
    }

    if (tasks) {
      const taskSet = new Set(tasks.split(",").map((x) => x.trim()).filter(Boolean));
      Array.from(document.querySelectorAll('input[name="tasks"]')).forEach((el) => {
        el.checked = taskSet.has(el.value);
      });
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    prefillFromQuery();

    if (!byId("client_request_id").value) {
      byId("client_request_id").value = generateRequestId();
    }

    byId("btn-sync").addEventListener("click", runSync);
    byId("btn-async").addEventListener("click", runAsync);
    byId("btn-sample").addEventListener("click", fillSample);
    byId("btn-copy-json").addEventListener("click", async () => {
      try {
        await copyText(lastResponseJson);
        showBlockMessage(byId("response-error"), "JSON이 클립보드에 복사되었습니다.", false);
      } catch (error) {
        showBlockMessage(byId("response-error"), error.message, false);
      }
    });

    byId("analyze-form").addEventListener("reset", () => {
      window.setTimeout(() => {
        byId("client_request_id").value = generateRequestId();
        applyStatusBadge(byId("response-status-badge"), null, "대기");
        setMeta({});
        showBlockMessage(byId("response-error"), "", true);
        byId("response-json").textContent = "{}";
        lastResponseJson = "{}";
      }, 0);
    });
  });
})();
