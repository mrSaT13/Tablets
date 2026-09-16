"""Windows system-tray icon with daily intake progress.

Optional: works only if ``pystray`` + ``Pillow`` are installed
(Windows default). On other platforms or without pystray every
function is a silent no-op — the app must never crash because
of the tray.
"""
from __future__ import annotations

import threading

_icon = None
_thread = None
_callbacks: dict = {}


def _make_image(taken: int, total: int):
    from PIL import Image, ImageDraw

    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if total > 0 and taken >= total:
        color = (22, 163, 74, 255)  # green — all taken
    else:
        color = (37, 99, 235, 255)  # blue — pending
    draw.ellipse([4, 4, size - 4, size - 4], fill=color)
    label = f"{taken}/{total}" if total else "T"
    # Centered text (default bitmap font is always available).
    bbox = draw.textbbox((0, 0), label)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) / 2, (size - h) / 2 - 1), label,
              fill=(255, 255, 255, 255))
    return img


def _build_menu(status_text: str, open_label: str = "Open",
                quit_label: str = "Exit"):
    import pystray

    return pystray.Menu(
        pystray.MenuItem(status_text, None, enabled=False),
        pystray.MenuItem(
            open_label, lambda *_: _callbacks.get("on_open", lambda: None)(),
            default=True),
        pystray.MenuItem(
            quit_label, lambda icon, _item: _callbacks.get("on_quit", lambda: None)()),
    )


def start_tray(*, on_open, on_quit, taken: int = 0, total: int = 0,
               status_text: str = "Tablets",
               open_label: str = "Open", quit_label: str = "Exit") -> bool:
    """Start the tray icon in a daemon thread. Returns True if started."""
    global _icon, _thread
    if _icon is not None:
        return True
    try:
        import pystray  # noqa: F401
    except Exception as exc:
        print(f"[tablets] tray disabled (no pystray): {exc}")
        return False
    _callbacks["on_open"] = on_open
    _callbacks["on_quit"] = on_quit

    def _run():
        global _icon
        try:
            import pystray

            _icon = pystray.Icon(
                "tablets",
                _make_image(taken, total),
                title=f"{status_text}: {taken}/{total}",
                menu=_build_menu(f"{status_text}: {taken}/{total}",
                                 open_label, quit_label),
            )
            _icon.run()
        except Exception as exc:
            print(f"[tablets] tray error: {exc}")
            _icon = None

    _thread = threading.Thread(target=_run, daemon=True)
    _thread.start()
    return True


def update_tray(taken: int, total: int, status_text: str = "Tablets",
                open_label: str = "Open", quit_label: str = "Exit") -> None:
    if _icon is None:
        return
    try:
        _icon.icon = _make_image(taken, total)
        _icon.title = f"{status_text}: {taken}/{total}"
        _icon.menu = _build_menu(f"{status_text}: {taken}/{total}",
                                 open_label, quit_label)
        try:
            _icon.update_menu()
        except Exception:
            pass
    except Exception as exc:
        print(f"[tablets] tray update failed: {exc}")


def stop_tray() -> None:
    global _icon
    if _icon is None:
        return
    try:
        _icon.stop()
    except Exception:
        pass
    _icon = None
