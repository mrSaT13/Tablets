"""Screen classes. Heavy logic lives in TabletsApp, screens stay thin."""
from __future__ import annotations

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRectangleFlatButton
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDTimePicker


class MainScreen(Screen):
    pass


class MedicationsScreen(Screen):
    pass


class MeasurementsScreen(Screen):
    pass


class SymptomsScreen(Screen):
    pass


class DoctorScreen(Screen):
    def ask(self):
        from kivy.app import App

        App.get_running_app().ask_doctor_from_form(self)


class ReferenceScreen(Screen):
    def on_pre_enter(self, *args):
        from kivy.app import App

        App.get_running_app().load_reference_screen(query="")

    def on_search(self, query: str):
        from kivy.app import App

        App.get_running_app().load_reference_screen(query=query)


class SettingsScreen(Screen):
    pass


class AddMedicationScreen(Screen):
    time_text = StringProperty("08:00")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_days: list[bool] = [False] * 7
        self._drug_menu = None
        Clock.schedule_once(lambda *_: self.refresh_days(), 0.2)

    def on_pre_leave(self, *args):
        self._dismiss_drug_menu()

    def refresh_days(self):
        from kivy.app import App

        app = App.get_running_app()
        box = self.ids.get("days_box")
        if box is None:
            return
        box.clear_widgets()
        keys = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        for i, key in enumerate(keys):
            label = app.tr(key) if hasattr(app, "tr") else key
            selected = self.selected_days[i]
            btn = MDRectangleFlatButton(
                text=label,
                size_hint=(None, None),
                width=dp(52),
                height=dp(38),
            )
            # Selected day is highlighted via colors.
            if selected:
                btn.md_bg_color = (0.2, 0.6, 1, 1)
                btn.text_color = (1, 1, 1, 1)
            btn.bind(on_release=lambda _b, idx=i: self.toggle_day(idx))
            box.add_widget(btn)

    def toggle_day(self, idx: int):
        self.selected_days[idx] = not self.selected_days[idx]
        self.refresh_days()

    def set_time(self, time_str: str):
        self.time_text = time_str

    def set_days(self, days: list[int]):
        self.selected_days = [i in days for i in range(7)]
        self.refresh_days()

    def clear_form(self):
        for field in ("name", "dosage", "frequency", "course_days", "reason", "notes"):
            if field in self.ids:
                self.ids[field].text = ""
        self.time_text = "08:00"
        self.set_days([])

    def show_time_picker(self):
        picker = MDTimePicker()
        picker.bind(time=self._on_picker_time)
        picker.open()

    def _on_picker_time(self, _instance, time):
        self.time_text = time.strftime("%H:%M")

    def save_medication(self):
        from kivy.app import App

        self._dismiss_drug_menu()
        app = App.get_running_app()
        app.save_medication_from_form(self)

    # -- drug autocomplete --------------------------------------------
    def _dismiss_drug_menu(self):
        if self._drug_menu:
            try:
                self._drug_menu.dismiss()
            except Exception:
                pass
            self._drug_menu = None

    def on_name_text(self, text: str):
        """Show reference matches while the user types a drug name."""
        from kivy.app import App

        self._dismiss_drug_menu()
        field = self.ids.get("name")
        if field is None or not field.focus:
            return
        query = (text or "").strip()
        if len(query) < 2:
            return
        try:
            from .drugs import search_drugs

            matches = search_drugs(query)[:6]
        except Exception:
            return
        if not matches:
            return
        app = App.get_running_app()
        ru = getattr(app, "current_language", "ru") == "ru"
        items = [
            {
                "text": d["name"] if ru else d.get("name_en", d["name"]),
                "on_release": lambda x=d: self.pick_drug(x),
            }
            for d in matches
        ]
        self._drug_menu = MDDropdownMenu(
            caller=field,
            items=items,
            width_mult=6,
        )
        self._drug_menu.open()

    def pick_drug(self, drug: dict):
        from kivy.app import App

        self._dismiss_drug_menu()
        app = App.get_running_app()
        ru = getattr(app, "current_language", "ru") == "ru"
        self.ids.name.text = drug["name"] if ru else drug.get("name_en", drug["name"])
        desc = drug["desc"] if ru else drug.get("desc_en", drug["desc"])
        if "notes" in self.ids and not self.ids.notes.text.strip():
            self.ids.notes.text = desc[:200]


class AddMeasurementScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.internal_type: str | None = None
        self._menu = None

    def type_labels(self) -> dict[str, str]:
        """Return {internal_key: localized label}."""
        from kivy.app import App

        app = App.get_running_app()
        mapping = app.tr("measurement_types")
        return dict(mapping) if isinstance(mapping, dict) else {}

    def open_type_menu(self):
        labels = self.type_labels()
        if not labels:
            return
        if self._menu:
            try:
                self._menu.dismiss()
            except Exception:
                pass
        items = [
            {
                "text": label,
                "on_release": lambda x=key: self.set_type(x),
            }
            for key, label in labels.items()
        ]
        self._menu = MDDropdownMenu(
            caller=self.ids.type_spinner,
            items=items,
            width_mult=6,
        )
        self._menu.open()

    def set_type(self, internal_key: str):
        self.internal_type = internal_key
        self.ids.type_spinner.text = self.type_labels().get(internal_key, internal_key)
        if self._menu:
            try:
                self._menu.dismiss()
            except Exception:
                pass

    def clear_form(self):
        self.internal_type = None
        if "type_spinner" in self.ids:
            self.ids.type_spinner.text = ""
        if "value" in self.ids:
            self.ids.value.text = ""

    def save_measurement(self):
        from kivy.app import App

        App.get_running_app().save_measurement_from_form(self)


class AddSymptomsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._selected: set[str] = set()
        Clock.schedule_once(lambda *_: self.build_checkboxes(), 0.3)

    def on_pre_enter(self, *args):
        self._selected.clear()
        search = self.ids.get("symptom_search")
        if search is not None:
            search.text = ""
        self.build_checkboxes()

    def on_search(self, query: str):
        self.build_checkboxes(query or "")

    def _track(self, checkbox, active: bool):
        key = getattr(checkbox, "symptom_key", None)
        if not key:
            return
        if active:
            self._selected.add(key)
        else:
            self._selected.discard(key)

    def build_checkboxes(self, filter_text: str = ""):
        from kivy.app import App

        from .i18n import ALL_SYMPTOMS

        app = App.get_running_app()
        container = self.ids.get("symptom_grid")
        if container is None:
            return
        query = (filter_text or "").strip().lower()
        container.clear_widgets()
        for sym in ALL_SYMPTOMS:
            label_text = app.tr(f"symptom_{sym}") if hasattr(app, "tr") else sym
            if query and query not in label_text.lower():
                continue
            row = MDBoxLayout(adaptive_height=True, spacing=dp(8))
            checkbox = MDCheckbox(size_hint=(None, None), size=(dp(48), dp(48)))
            checkbox.symptom_key = sym  # type: ignore[attr-defined]
            checkbox.active = sym in self._selected
            checkbox.bind(active=lambda cb, val: self._track(cb, val))
            label = MDLabel(
                text=label_text,
                size_hint_y=None,
                height=dp(48),
                valign="middle",
            )
            row.add_widget(checkbox)
            row.add_widget(label)
            container.add_widget(row)

    def selected_keys(self) -> list[str]:
        return sorted(self._selected)

    def save_symptoms(self):
        from kivy.app import App

        App.get_running_app().save_symptoms_from_form(self)
