from contextlib import contextmanager
from typing import Optional, Dict, Any
import os

try:
    from opentelemetry import trace  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
    HAS_OTEL = True
except Exception:
    HAS_OTEL = False
    trace = None  # type: ignore

try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore
    from opentelemetry.instrumentation.requests import RequestsInstrumentor  # type: ignore
    HAS_INST = True
except Exception:
    HAS_INST = False

TRACING_ENABLED = os.getenv("TRACING_ENABLED", "0") == "1"

_tracer = None

def setup_tracing():
    global _tracer
    if not TRACING_ENABLED or not HAS_OTEL:
        return
    try:
        provider = TracerProvider()
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if endpoint:
            exporter = OTLPSpanExporter(endpoint=endpoint)
            processor = BatchSpanProcessor(exporter)
            provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("learnlab")
    except Exception:
        _tracer = trace.get_tracer("learnlab") if HAS_OTEL else None

@contextmanager
def span(name: str, attributes: Optional[Dict[str, Any]] = None):
    global _tracer
    if not TRACING_ENABLED or not HAS_OTEL:
        yield None
        return
    if _tracer is None:
        try:
            _tracer = trace.get_tracer("learnlab")
        except Exception:
            yield None
            return
    with _tracer.start_as_current_span(name) as sp:
        if attributes:
            for k, v in attributes.items():
                try:
                    sp.set_attribute(k, v)
                except Exception:
                    pass
        yield sp

app_instrumented = False

def instrument_app(app):
    global app_instrumented
    if not TRACING_ENABLED or not HAS_OTEL or not HAS_INST or app_instrumented:
        return
    try:
        FastAPIInstrumentor.instrument_app(app)
        RequestsInstrumentor().instrument()
        app_instrumented = True
    except Exception:
        pass
