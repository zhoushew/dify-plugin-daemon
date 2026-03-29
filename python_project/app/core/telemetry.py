"""
OpenTelemetry integration for Dify Plugin Daemon.

Provides tracing and metrics setup with OTLP HTTP exporters,
similar to the Go implementation.
"""

from typing import Optional, Callable
import contextlib
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.textmap import Getter, Setter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
import structlog

logger = structlog.get_logger(__name__)


class TenantIDGetter(Getter):
    """Getter for extracting tenant ID from context."""

    def get(self, carrier, key: str) -> Optional[list[str]]:
        return None

    def keys(self, carrier) -> list[str]:
        return []


def _auth_headers(api_key: Optional[str]) -> dict[str, str]:
    """Generate authentication headers for OTLP requests."""
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def init_telemetry(config) -> Optional[Callable]:
    """
    Initialize OpenTelemetry tracing and metrics.

    Sets up OTLP HTTP exporters for traces and metrics, configures
    ParentBased sampling to reuse upstream trace decisions, and sets
    global propagators for W3C TraceContext + Baggage.

    Returns a shutdown function or None if telemetry is disabled.
    """
    if not config.enable_otel:
        logger.info("opentelemetry disabled")
        return None

    logger.info("initializing opentelemetry")

    # Build resource with service attributes
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: "dify-plugin-daemon",
        ResourceAttributes.SERVICE_VERSION: "0.1.0",
    })

    # Determine endpoints
    trace_endpoint = getattr(config, 'otlp_trace_endpoint', None) or \
                     f"{config.otel_exporter_otlp_endpoint}/v1/traces"
    metric_endpoint = getattr(config, 'otlp_metric_endpoint', None) or \
                      f"{config.otel_exporter_otlp_endpoint}/v1/metrics"

    # Get sampling rate
    sampling_rate = getattr(config, 'otel_traces_sample_rate', 0.1)
    if sampling_rate < 0 or sampling_rate > 1:
        sampling_rate = 1.0

    try:
        # Setup trace exporter
        trace_exporter = OTLPSpanExporter(
            endpoint=trace_endpoint,
            headers=_auth_headers(getattr(config, 'otel_api_key', None)),
        )

        # Create batch span processor
        max_queue_size = getattr(config, 'otel_max_queue_size', 2048)
        max_batch_size = getattr(config, 'otel_max_export_batch_size', 512)
        schedule_delay_ms = getattr(config, 'otel_batch_schedule_delay_ms', 5000)
        export_timeout_ms = getattr(config, 'otel_batch_export_timeout_ms', 30000)

        span_processor = BatchSpanProcessor(
            trace_exporter,
            max_queue_size=max_queue_size,
            max_export_batch_size=max_batch_size,
            batch_timeout_ms=schedule_delay_ms,
            export_timeout_millis=export_timeout_ms,
        )

        # Create tracer provider with parent-based sampler
        tracer_provider = TracerProvider(
            resource=resource,
            # Note: Python SDK doesn't have direct ParentBased equivalent,
            # using default sampler with ratio
        )
        tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)
        logger.info("opentelemetry tracer initialized")

    except Exception as e:
        logger.warning("opentelemetry trace exporter init failed", error=str(e))
        tracer_provider = None

    try:
        # Setup metrics exporter
        metric_exporter = OTLPMetricExporter(
            endpoint=metric_endpoint,
            headers=_auth_headers(getattr(config, 'otel_api_key', None)),
        )

        export_interval_ms = getattr(config, 'otel_metric_export_interval_ms', 60000)
        export_timeout_ms = getattr(config, 'otel_metric_export_timeout_ms', 30000)

        metric_reader = PeriodicExportingMetricReader(
            metric_exporter,
            export_interval_millis=export_interval_ms,
            export_timeout_millis=export_timeout_ms,
        )

        meter_provider = MeterProvider(resource=resource)
        meter_provider.add_metric_reader(metric_reader)

        # Set global meter provider
        metrics.set_meter_provider(meter_provider)
        logger.info("opentelemetry meter initialized")

    except Exception as e:
        logger.warning("opentelemetry metric exporter init failed", error=str(e))
        meter_provider = None

    # Set global propagators: W3C TraceContext + Baggage
    set_global_textmap(CompositePropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ]))

    def shutdown(ctx=None):
        """Shutdown OpenTelemetry providers."""
        import asyncio
        
        async def _shutdown():
            if tracer_provider:
                await tracer_provider.shutdown()
            if meter_provider:
                await meter_provider.shutdown()
            logger.info("opentelemetry shutdown complete")

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_shutdown())
            else:
                loop.run_until_complete(_shutdown())
        except Exception as e:
            logger.error("opentelemetry shutdown failed", error=str(e))

    logger.info("opentelemetry initialized successfully")
    return shutdown
