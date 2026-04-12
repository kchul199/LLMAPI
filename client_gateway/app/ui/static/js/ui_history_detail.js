(function () {
  const { byId, apiFetch, safeJson, formatDateTime, applyStatusBadge } = window.UICommon;

  function renderBasic(request) {
    const basic = byId("detail-basic");
    const keys = [
      ["request_uid", request.request_uid],
      ["source_system", request.source_system],
      ["client_request_id", request.client_request_id],
      ["trace_id", request.trace_id],
      ["mode", request.mode],
      ["status", request.status],
      ["prompt_version", request.prompt_version || "-"],
      ["created_at", formatDateTime(request.created_at)],
      ["updated_at", formatDateTime(request.updated_at)],
    ];

    basic.innerHTML = keys
      .map(([key, value]) => `<dt>${key}</dt><dd class="mono">${value == null ? "-" : value}</dd>`)
      .join("");
  }

  function renderTimeline(items) {
    const timeline = byId("detail-timeline");
    if (!items || !items.length) {
      timeline.innerHTML = '<li><div class="line-meta">상태 전이 이력이 없습니다.</div></li>';
      return;
    }

    timeline.innerHTML = items
      .map(
        (row) => `
        <li>
          <div class="line-title">
            <span class="mono">${row.prev_status || "-"}</span>
            <span>→</span>
            <span class="mono">${row.new_status}</span>
          </div>
          <div class="line-meta">${formatDateTime(row.changed_at)}</div>
          <div class="line-meta">${row.reason_code || ""} ${row.reason_message || ""}</div>
        </li>
      `,
      )
      .join("");
  }

  function setRetestLink(request) {
    const link = byId("btn-retest");
    const params = new URLSearchParams();

    if (request.source_system) params.set("source_system", request.source_system);
    if (request.client_request_id) params.set("client_request_id", `${request.client_request_id}_retry`);
    if (request.text_masked) params.set("text", request.text_masked);
    if (request.target_speakers) params.set("target_speakers", request.target_speakers);
    if (request.prompt_version) params.set("prompt_version", request.prompt_version);
    if (Array.isArray(request.tasks) && request.tasks.length > 0) {
      params.set("tasks", request.tasks.join(","));
    }

    link.href = `/ui/test?${params.toString()}`;
  }

  async function loadDetail() {
    const root = byId("detail-root");
    const requestUid = root ? root.dataset.requestUid : "";
    if (!requestUid) {
      return;
    }

    try {
      const { data } = await apiFetch(`/ui/api/requests/${encodeURIComponent(requestUid)}`);

      const request = data.request || {};
      const errorText = [request.error_code, request.error_message].filter(Boolean).join(" / ");

      applyStatusBadge(byId("detail-status"), request.status, request.status || "-");
      renderBasic(request);
      renderTimeline(data.status_history || []);
      byId("detail-request").textContent = safeJson(request);
      byId("detail-result").textContent = safeJson(data.result || {});
      byId("detail-error").textContent = errorText || "오류 없음";
      setRetestLink(request);
    } catch (error) {
      applyStatusBadge(byId("detail-status"), "FAILED", "ERROR");
      byId("detail-basic").innerHTML = "<dt>message</dt><dd>요청 상세를 불러오지 못했습니다.</dd>";
      byId("detail-request").textContent = "{}";
      byId("detail-result").textContent = "{}";
      byId("detail-timeline").innerHTML = '<li><div class="line-meta">로딩 실패</div></li>';
      byId("detail-error").textContent = error.message;
      console.error(error);
    }
  }

  document.addEventListener("DOMContentLoaded", loadDetail);
})();
