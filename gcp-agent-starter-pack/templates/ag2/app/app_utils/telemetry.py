"""Telemetry setup for OpenTelemetry tracing on Google Cloud."""

import os


def setup_telemetry() -> None:
    """Initialize OpenTelemetry tracing for Google Cloud.

    This sets up tracing to export to Google Cloud Trace when running
    on Cloud Run. Locally, tracing is disabled by default.
    """
    # Only enable telemetry in Cloud Run (when K_SERVICE is set)
    if not os.getenv("K_SERVICE"):
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider()
        processor = BatchSpanProcessor(CloudTraceSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
    except ImportError:
        # Telemetry dependencies not installed, skip setup
        pass
