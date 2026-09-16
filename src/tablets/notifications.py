"""Desktop/mobile notifications (plyer) with graceful fallback."""
from __future__ import annotations


def send_notification(title: str, message: str, app_name: str = "Tablets") -> bool:
    try:
        from plyer import notification

        notification.notify(
            title=str(title)[:120],
            message=str(message)[:240],
            app_name=app_name,
            timeout=10,
        )
        return True
    except Exception as exc:  # noqa: BLE001 - must never crash the UI
        print(f"[tablets] notification failed: {exc}")
        return False
