"""
OpenTelemetry tracing setup for UTOS Trading Engine.

Provides distributed tracing for HTTP requests, async tasks, and
key flows (order placement, grid cycle, recovery sequence).

Traces are exported to Jaeger or Grafana Tempo via OTLP.
"""

from typing import Optional

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_tracer: Optional[object] = None
_telemetry_initialized = False


def init_telemetry(app=None) -> None:
    """Initialize OpenTelemetry instrumentation.

    This sets up:
    - FastAPI auto-instrumentation (HTTP request spans)
    - Async context propagation
    - OTLP exporter (configurable via env)

    Gracefully degrades if opentelemetry packages are not installed.
    """
    global _tracer, _telemetry_initialized

    if _telemetry_initialized:
        return

    _telemetry_initialized = True

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({
            "service.name": "utos-backend",
            "service.version": settings.VERSION,
            "deployment.environment": settings.APP_ENV,
        })

        provider = TracerProvider(resource=resource)

        otlp_endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT if hasattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT") else "http://localhost:4317"

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("utos")

        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("OpenTelemetry FastAPI instrumentation enabled", extra={"otlp_endpoint": otlp_endpoint})
        else:
            logger.info("OpenTelemetry tracer initialized (no app to instrument)")

    except ImportError:
        logger.warning(
            "OpenTelemetry packages not installed — tracing disabled. "
            "Install: pip install opentelemetry-distro opentelemetry-exporter-otlp "
            "opentelemetry-instrumentation-fastapi"
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"OpenTelemetry initialization failed: {exc}")


def get_tracer():
    """Return the configured tracer, or None if not initialized."""
    if _tracer is None:
        from opentelemetry import trace
        return trace.get_tracer("utos")
    return _tracer


def shutdown_telemetry() -> None:
    """Shut down telemetry and flush pending spans."""
    global _tracer, _telemetry_initialized

    if not _telemetry_initialized:
        return

    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
            logger.info("OpenTelemetry tracer shut down")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"OpenTelemetry shutdown failed: {exc}")

    _tracer = None
    _telemetry_initialized = False
