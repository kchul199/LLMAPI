CREATE TABLE IF NOT EXISTS client_analysis_request (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_uid CHAR(36) NOT NULL,
    source_system VARCHAR(64) NOT NULL,
    client_request_id VARCHAR(100) NOT NULL,
    trace_id VARCHAR(64) NOT NULL,
    mode ENUM('sync','async') NOT NULL,
    status ENUM('RECEIVED','QUEUED','PROCESSING','COMPLETED','FAILED','TIMEOUT') NOT NULL DEFAULT 'RECEIVED',

    text_masked LONGTEXT NOT NULL,
    text_sha256 CHAR(64) NOT NULL,
    tasks JSON NOT NULL,
    target_speakers ENUM('agent','customer','both') NOT NULL DEFAULT 'both',
    prompt_version VARCHAR(32) NULL,

    llmapi_request_id VARCHAR(100) NULL,
    llmapi_http_status SMALLINT UNSIGNED NULL,
    retry_count TINYINT UNSIGNED NOT NULL DEFAULT 0,

    error_code VARCHAR(64) NULL,
    error_message VARCHAR(500) NULL,

    received_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    queued_at DATETIME(3) NULL,
    started_at DATETIME(3) NULL,
    completed_at DATETIME(3) NULL,

    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    updated_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),

    UNIQUE KEY uk_request_uid (request_uid),
    UNIQUE KEY uk_source_client_request (source_system, client_request_id),
    KEY idx_llmapi_request_id (llmapi_request_id),
    KEY idx_status_created (status, created_at),
    KEY idx_trace_id (trace_id),
    KEY idx_received_at (received_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS client_analysis_result (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_id BIGINT UNSIGNED NOT NULL,
    result_status ENUM('SUCCESS','FAIL') NOT NULL DEFAULT 'SUCCESS',
    summary TEXT NULL,
    sentiment VARCHAR(32) NULL,
    category VARCHAR(64) NULL,
    result_json JSON NOT NULL,
    usage_total_tokens INT UNSIGNED NOT NULL DEFAULT 0,
    usage_latency_ms INT UNSIGNED NOT NULL DEFAULT 0,
    llm_model VARCHAR(128) NULL,
    is_fallback TINYINT(1) NOT NULL DEFAULT 0,
    prompt_version_applied VARCHAR(32) NULL,
    created_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_result_request
      FOREIGN KEY (request_id) REFERENCES client_analysis_request(id)
      ON DELETE CASCADE,

    UNIQUE KEY uk_request_result (request_id),
    KEY idx_result_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS client_analysis_status_history (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    request_id BIGINT UNSIGNED NOT NULL,
    prev_status ENUM('RECEIVED','QUEUED','PROCESSING','COMPLETED','FAILED','TIMEOUT') NULL,
    new_status ENUM('RECEIVED','QUEUED','PROCESSING','COMPLETED','FAILED','TIMEOUT') NOT NULL,
    reason_code VARCHAR(64) NULL,
    reason_message VARCHAR(500) NULL,
    actor VARCHAR(32) NOT NULL DEFAULT 'system',
    changed_at DATETIME(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),

    CONSTRAINT fk_status_request
      FOREIGN KEY (request_id) REFERENCES client_analysis_request(id)
      ON DELETE CASCADE,

    KEY idx_status_req_changed (request_id, changed_at),
    KEY idx_status_new_changed (new_status, changed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
