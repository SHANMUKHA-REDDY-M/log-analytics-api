import os
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _configure_provider(service_name: str) -> None:
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
            }
        )
    )
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        exporter = OTLPSpanExporter(
            endpoint=endpoint,
            insecure=os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "false").lower()
            == "true",
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def setup_api_telemetry(app: Any, service_name: str = "log-analytics-api") -> None:
    if trace.get_tracer_provider().__class__.__name__ == "ProxyTracerProvider":
        _configure_provider(service_name)
    LoggingInstrumentor().instrument(set_logging_format=True)
    SQLAlchemyInstrumentor().instrument(enable_commenter=True)
    RedisInstrumentor().instrument()
    FastAPIInstrumentor.instrument_app(app)


def setup_worker_telemetry(
    service_name: str = "log-analytics-celery-worker",
) -> None:
    if trace.get_tracer_provider().__class__.__name__ == "ProxyTracerProvider":
        _configure_provider(service_name)
    CeleryInstrumentor().instrument()
