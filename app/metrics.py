from prometheus_client import Counter, Histogram

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "status"]
)

WEBHOOK_OUTCOMES = Counter(
    "webhook_requests_total",
    "Webhook processing outcomes",
    ["result"]
)

LATENCY = Histogram(
    "request_latency_ms",
    "Request latency in ms",
    buckets=[100, 500, float("inf")]
)