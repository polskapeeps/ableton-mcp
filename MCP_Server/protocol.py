from __future__ import annotations

from typing import Any, Mapping


def success_response(
    object_type: str,
    *,
    object_ref: Mapping[str, Any] | None = None,
    state: Any = None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "error": None,
        "object_type": object_type,
        "object_ref": dict(object_ref or {}),
        "state": state,
    }


def error_response(
    code: str,
    message: str,
    *,
    object_type: str | None = None,
    object_ref: Mapping[str, Any] | None = None,
    state: Any = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": message},
        "object_type": object_type,
        "object_ref": dict(object_ref or {}),
        "state": state,
    }


def normalize_response(response: Any) -> dict[str, Any]:
    if not isinstance(response, dict):
        return success_response("result", state=response)

    if "ok" in response:
        return {
            "ok": bool(response.get("ok")),
            "error": response.get("error"),
            "object_type": response.get("object_type"),
            "object_ref": dict(response.get("object_ref") or {}),
            "state": response.get("state"),
        }

    if response.get("status") == "error":
        return error_response(
            "remote_error",
            str(response.get("message", "Unknown error from Ableton")),
        )

    if response.get("status") == "success":
        return success_response("result", state=response.get("result"))

    return success_response("result", state=response)
