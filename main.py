import time
import uuid
from typing import Callable, Awaitable

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

ALLOWED_ORIGIN = "https://dash-n41kz3.example.com"
STUDENT_EMAIL = "24f2006633@ds.study.iitm.ac.in"

api = FastAPI(title="TDS GA2 CORS Metrics API")


@api.get("/stats")
def get_stats(values: str = Query(..., description="Comma-separated integers")):
    """Calculate descriptive statistics from the current request's values."""
    try:
        parts = values.split(",")
        if not values.strip() or any(not part.strip() for part in parts):
            raise ValueError("empty value")
        numbers = [int(part.strip()) for part in parts]
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="values must be a comma-separated list of integers",
        )

    total = sum(numbers)
    return {
        "email": STUDENT_EMAIL,
        "count": len(numbers),
        "sum": total,
        "min": min(numbers),
        "max": max(numbers),
        "mean": total / len(numbers),
    }


# Configure exact-origin CORS. There is intentionally no wildcard origin.
cors_app: ASGIApp = CORSMiddleware(
    app=api,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=False,
    max_age=600,
)


class RequiredResponseHeaders:
    """Add the required headers to every HTTP response, including preflights/errors."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        request_id = str(uuid.uuid4()).encode("ascii")

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                elapsed = max(0.0, time.perf_counter() - started)
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id))
                headers.append((b"x-process-time", f"{elapsed:.6f}".encode("ascii")))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


# Keep this outermost so it adds headers to normal responses and CORS preflight responses.
app = RequiredResponseHeaders(cors_app)
