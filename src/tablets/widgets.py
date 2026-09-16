"""Custom list items for RecycleView.

MedicationItem is a plain MDBoxLayout with fixed sections
(icon | texts | two action buttons). This intentionally does NOT
subclass KivyMD list items: their internal layout ignores custom
right-side containers, which caused buttons overlapping the text.
"""
from __future__ import annotations

from kivy.clock import Clock
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDIconButton
from kivymd.uix.list import OneLineAvatarIconListItem


class MedicationItem(MDBoxLayout):
    med_id = NumericProperty(-1)
    title = StringProperty("")
    subtitle = StringProperty("")
    status = StringProperty("pending")
    time_text = StringProperty("")
    icon_name = StringProperty("pill")
    icon_color = ListProperty([0.2, 0.45, 0.85, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._long_press = None
        self._pressed = False

    # -- inline buttons (bound in KV) ---------------------------------
    def on_take(self):
        from kivy.app import App

        app = App.get_running_app()
        if self.med_id >= 0 and hasattr(app, "action_take"):
            app.selected_med_id = self.med_id
            if self.status == "taken" and hasattr(app, "action_untake"):
                app.action_untake()
            else:
                app.action_take()

    def on_snooze(self):
        from kivy.app import App

        app = App.get_running_app()
        if self.med_id >= 0 and hasattr(app, "action_skip"):
            app.selected_med_id = self.med_id
            app.action_skip()

    # -- tap = dialog, long-press = edit -------------------------------
    def _on_button(self, x: float, y: float) -> bool:
        for child in self.walk():
            if isinstance(child, MDIconButton) and child.collide_point(x, y):
                return True
        return False

    def _open_dialog(self):
        from kivy.app import App

        app = App.get_running_app()
        if self.med_id >= 0 and hasattr(app, "show_med_dialog"):
            app.show_med_dialog(self.med_id)

    def on_touch_down(self, touch):
        if (
            self.med_id >= 0
            and self.collide_point(*touch.pos)
            and not self._on_button(*touch.pos)
        ):
            self._pressed = True
            if self._long_press:
                self._long_press.cancel()
            self._long_press = Clock.schedule_once(self._on_long_press, 0.8)
        else:
            self._pressed = False
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._long_press:
            self._long_press.cancel()
            self._long_press = None
        was_pressed = self._pressed
        self._pressed = False
        result = super().on_touch_up(touch)
        if was_pressed and self.med_id >= 0 and self.collide_point(*touch.pos):
            try:
                moved = abs(touch.x - touch.opos[0]) + abs(touch.y - touch.opos[1])
            except (AttributeError, IndexError):
                moved = 0
            if moved < 20:
                self._open_dialog()
        return result

    def _on_long_press(self, _dt):
        from kivy.app import App

        self._long_press = None
        self._pressed = False
        app = App.get_running_app()
        if self.med_id >= 0 and hasattr(app, "open_med_for_edit"):
            app.open_med_for_edit(self.med_id)


class MeasurementItem(OneLineAvatarIconListItem):
    meas_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(meas_text=lambda *a: setattr(self, "text", self.meas_text))
