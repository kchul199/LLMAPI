(function () {
  const { apiFetch, setText, formatDateTime, applyStatusBadge, byId } = window.UICommon;

  async function loadHealth() {
    const badge = byId("health-overall");
    try {
      const { data } = await apiFetch("/ui/api/health");
      const isHealthy = data.status === "healthy";
      applyStatusBadge(badge, isHealthy ? "COMPLETED" : "FAILED", isHealthy ? "healthy" : "degraded");
      setText("health-mysql", data.checks.mysql);
      setText("health-redis", data.checks.redis);
      setText("health-llmapi", data.checks.llmapi);
    } catch (error) {
      applyStatusBadge(badge, "FAILED", "error");
      setText("health-mysql", "error");
      setText("health-redis", "error");
      setText("health-llmapi", "error");
      console.error(error);
    }
  }

  async function loadSummary() {
    const tbody = byId("recent-failed-body");

    try {
      const { data } = await apiFetch("/ui/api/dashboard-summary");

      setText("summary-date", data.date);
      setText("metric-total", String(data.total_requests_today));
      setText("metric-failed", String(data.failed_today));
      setText("metric-latency", data.avg_latency_ms == null ? "-" : String(data.avg_latency_ms));

      const statuses = ["RECEIVED", "QUEUED", "PROCESSING", "COMPLETED", "FAILED", "TIMEOUT"];
      statuses.forEach((status) => {
        setText(`count-${status}`, String(data.status_counts[status] || 0));
      });

      if (!data.recent_failed.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="empty">최근 실패 건이 없습니다.</td></tr>';
        return;
      }

      tbody.innerHTML = data.recent_failed
        .map(
          (row) => `
          <tr>
            <td class="mono"><a href="/ui/history/${row.request_uid}">${row.request_uid}</a></td>
            <td>${row.source_system}</td>
            <td><span class="status-badge ${statusClass(row.status)}">${row.status}</span></td>
            <td>${row.error_code || "-"}</td>
            <td>${formatDateTime(row.updated_at)}</td>
          </tr>
        `,
        )
        .join("");
    } catch (error) {
      tbody.innerHTML = '<tr><td colspan="5" class="empty">요약 정보를 불러오지 못했습니다.</td></tr>';
      console.error(error);
    }
  }

  function statusClass(status) {
    const map = {
      RECEIVED: "status-received",
      QUEUED: "status-queued",
      PROCESSING: "status-processing",
      COMPLETED: "status-completed",
      FAILED: "status-failed",
      TIMEOUT: "status-timeout",
    };
    return map[status] || "status-neutral";
  }

  document.addEventListener("DOMContentLoaded", async () => {
    await Promise.all([loadHealth(), loadSummary()]);
  });
})();
