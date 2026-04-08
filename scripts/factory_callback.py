"""
Factory callback script — POST build result to the Managing Director.

Called as the final step of factory-build.yml on both success and failure.
Posts to the MD /factory/callback endpoint with X-Factory-Secret auth header
and the full result payload including correlation_id.
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


def _post_callback(
    *,
    callback_url: str,
    payload: dict,
    factory_secret: str,
    timeout: int = 30,
) -> None:
    """POST the result payload to the MD callback endpoint with auth."""
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")

    for attempt in range(_MAX_RETRIES):
        req = urllib.request.Request(url=callback_url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if factory_secret:
            req.add_header("X-Factory-Secret", factory_secret)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                print(
                    f"[factory_callback] POST {callback_url} → {resp.status}",
                    flush=True,
                )
            return
        except urllib.error.HTTPError as exc:
            if exc.code in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                print(
                    f"[factory_callback] Retrying ({attempt + 1}/{_MAX_RETRIES}): HTTP {exc.code}",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(_RETRY_DELAY_SECONDS)
                continue
            raise
        except urllib.error.URLError as exc:
            if attempt < _MAX_RETRIES - 1:
                print(
                    f"[factory_callback] Retrying ({attempt + 1}/{_MAX_RETRIES}): {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(_RETRY_DELAY_SECONDS)
                continue
            raise


def main() -> int:
    """Build and POST the callback payload."""
    parser = argparse.ArgumentParser(
        description="POST factory build result to Managing Director callback endpoint"
    )
    parser.add_argument("--project-id", required=True, help="Project identifier")
    parser.add_argument("--correlation-id", default="", help="End-to-end correlation ID")
    parser.add_argument("--callback-url", default="", help="MD callback URL")
    parser.add_argument("--status", required=True, choices=["succeeded", "failed"], help="Build outcome")
    parser.add_argument("--run-id", default="", help="Workflow run ID")
    parser.add_argument("--workflow-url", default="", help="Workflow run URL")
    parser.add_argument("--deploy-url", default="", help="Deployment URL")
    parser.add_argument("--repo-url", default="", help="Repository URL")
    parser.add_argument("--error-summary", default="", help="Error summary for failures")
    parser.add_argument("--error-message", default="", help="Error message for failures")
    parser.add_argument("--completed-at", default="", help="ISO-8601 completion timestamp")
    parser.add_argument("--dry-run", default="false", help="Whether this was a dry run")
    args = parser.parse_args()

    callback_url = args.callback_url.strip()
    correlation_id = args.correlation_id.strip()
    factory_secret = os.environ.get("FACTORY_SECRET", "").strip()

    # Build the callback payload matching FactoryCallbackPayload on the MD side.
    payload: dict = {
        "project_id": args.project_id.strip(),
        "correlation_id": correlation_id,
        "run_id": args.run_id.strip(),
        "status": args.status,
        "deploy_url": args.deploy_url.strip(),
        "repo_url": args.repo_url.strip(),
    }
    # Include optional error fields only when present
    error_msg = args.error_summary.strip() or args.error_message.strip()
    if error_msg:
        payload["error"] = error_msg

    print(f"[factory_callback] Payload: {json.dumps(payload, ensure_ascii=True)}", flush=True)

    if not callback_url:
        print("[factory_callback] No callback_url configured — skipping POST.", flush=True)
        return 0

    if not correlation_id:
        print("[factory_callback] WARNING: No correlation_id — MD may not match this callback.", flush=True)

    try:
        _post_callback(
            callback_url=callback_url,
            payload=payload,
            factory_secret=factory_secret,
        )
        print("[factory_callback] Callback delivered successfully.", flush=True)
    except Exception as exc:
        # Best-effort: log but don't fail the workflow
        print(f"[factory_callback] Callback failed (best-effort): {exc}", file=sys.stderr, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
