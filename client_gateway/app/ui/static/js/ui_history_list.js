(function () {
  const { byId, apiFetch, formatDateTime } = window.UICommon;

  const state = {
    page: 1,
    size: 20,
    total: 0,
  };

  function toIsoStringOrNull(value) {
    if (!value) {
      return null;
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date.toISOString();
  }

  function buildQuery() {
    const sourceSystem = byId("filter-source-system").value.trim();
    const status = byId("filter-status").value;
    const fromValue = toIsoStringOrNull(byId("filter-from").value);
    const toValue = toIsoStringOrNull(byId("filter-to").value);
    const size = Number.parseInt(byId("filter-size").value, 10) || 20;

    state.size = size;

    const params = new URLSearchParams();
    params.set("page", String(state.page));
    params.set("size", String(size));

    if (sourceSystem) params.set("source_system", sourceSystem);
    if (status) params.set("status", status);
    if (fromValue) params.set("from", fromValue);
    if (toValue) params.set("to", toValue);

    return params;
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

  function updatePager() {
    const prev = byId("history-prev");
    const next = byId("history-next");

    prev.disabled = state.page <= 1;
    next.disabled = state.page * state.size >= state.total;
    byId("history-page-info").textContent = `page ${state.page}`;
  }

  function renderRows(payload) {
    const tbody = byId("history-body");

    if (!payload.items.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">조건에 맞는 요청이 없습니다.</td></tr>';
      byId("history-summary").textContent = `total ${payload.total}건`;
      return;
    }

    tbody.innerHTML = payload.items
      .map(
        (row) => `
        <tr>
          <td>${formatDateTime(row.created_at)}</td>
          <td class="mono">${row.request_uid}</td>
          <td>${row.source_system}</td>
          <td class="mono">${row.client_request_id}</td>
          <td><span class="status-badge ${statusClass(row.status)}">${row.status}</span></td>
          <td>${formatDateTime(row.updated_at)}</td>
          <td><a href="/ui/history/${row.request_uid}">상세</a></td>
        </tr>
      `,
      )
      .join("");

    byId("history-summary").textContent = `total ${payload.total}건`;
  }

  async function loadHistory() {
    const tbody = byId("history-body");
    tbody.innerHTML = '<tr><td colspan="7" class="empty">조회중...</td></tr>';

    try {
      const query = buildQuery();
      const { data } = await apiFetch(`/ui/api/requests?${query.toString()}`);
      state.total = data.total;
      renderRows(data);
      updatePager();
    } catch (error) {
      tbody.innerHTML = '<tr><td colspan="7" class="empty">조회에 실패했습니다. 다시 시도해 주세요.</td></tr>';
      byId("history-summary").textContent = "조회 실패";
      console.error(error);
    }
  }

  function resetFilters() {
    byId("filter-source-system").value = "";
    byId("filter-status").value = "";
    byId("filter-from").value = "";
    byId("filter-to").value = "";
    byId("filter-size").value = "20";
    state.page = 1;
    loadHistory();
  }

  document.addEventListener("DOMContentLoaded", () => {
    byId("history-filter-form").addEventListener("submit", (event) => {
      event.preventDefault();
      state.page = 1;
      loadHistory();
    });

    byId("btn-search-reset").addEventListener("click", resetFilters);

    byId("history-prev").addEventListener("click", () => {
      if (state.page > 1) {
        state.page -= 1;
        loadHistory();
      }
    });

    byId("history-next").addEventListener("click", () => {
      if (state.page * state.size < state.total) {
        state.page += 1;
        loadHistory();
      }
    });

    loadHistory();
  });
})();
