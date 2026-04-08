"""
Factory alert script — send failure notifications to ALERT_WEBHOOK_URL.

Called on failure from factory-build.yml.  Posts a structured alert payload
to a configurable webhook (e.g. Slack, Discord, PagerDuty) and optionally
to the MD director webhook for observability.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 2


def _post_webhook(*, url: str, payload: dict, timeout: int = 15) -> None:
    """POST payload to a webhook URL with retries (best-effort)."""
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")

    for attempt in range(_MAX_RETRIES):
        req = urllib.request.Request(url=url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                print(f"[factory_alert] POST {url} → {resp.status}", flush=True)
            return
        except urllib.error.HTTPError as exc:
            if exc.code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY_SECONDS)
                continue
            raise
        except urllib.error.URLError as exc:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY_SECONDS)
                continue
            raise


def main() -> int:
    """Build and POST the alert payload."""
    parser = argparse.ArgumentParser(description="Send factory failure alert to webhook")
    parser.add_argument("--project-id", required=True, help="Project identifier")
    parser.add_argument("--correlation-id", default="", help="End-to-end correlation ID")
    parser.add_argument("--run-id", default="", help="Workflow run ID")
    parser.add_argument("--workflow-url", default="", help="Workflow run URL")
    parser.add_argument("--failure-reason", default="factory-build failed", help="Failure reason")
    parser.add_argument("--error-summary", default="", help="Error summary")
    parser.add_argument(
        "--alert-webhook-url",
        default="",
        help="Webhook URL for alert delivery (env: ALERT_WEBHOOK_URL)",
    )
    args = parser.parse_args()

    alert_url = args.alert_webhook_url.strip() or os.environ.get("ALERT_WEBHOOK_URL", "").strip()

    payload = {
        "project_id": args.project_id.strip(),
        "correlation_id": args.correlation_id.strip(),
        "run_id": args.run_id.strip(),
        "workflow_url": args.workflow_url.strip(),
        "alert_type": "factory_failure",
        "failure_reason": args.failure_reason.strip(),
        "error_summary": args.error_summary.strip(),
        "status": "failed",
    }

    print(f"[factory_alert] Alert payload: {json.dumps(payload, ensure_ascii=True)}", flush=True)

    if not alert_url:
        print("[factory_alert] No ALERT_WEBHOOK_URL configured — skipping.", flush=True)
        return 0

    try:
        _post_webhook(url=alert_url, payload=payload)
        print("[factory_alert] Alert delivered successfully.", flush=True)
    except Exception as exc:
        # Best-effort: don't fail the workflow
        print(f"[factory_alert] Alert delivery failed: {exc}", file=sys.stderr, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
