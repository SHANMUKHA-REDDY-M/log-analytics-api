from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "api_request_count_total",
    "Total number of HTTP requests processed",
    ["method", "endpoint", "http_status"],
)

REQUEST_LATENCY = Histogram(
    "api_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)

LOGS_INGESTED = Counter(
    "api_logs_ingested_total",
    "Total number of log records successfully saved",
    ["service_name"],
)
