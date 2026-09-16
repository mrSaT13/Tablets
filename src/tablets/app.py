"""Tablets KivyMD application (merged best of tablets.py/2/3)."""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import partial

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import TwoLineAvatarIconListItem, IconLeftWidget

from . import __version__
from .config import get_db_path
from .database import Database
from .doctor import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    LMSTUDIO_BASE_URL,
    LMSTUDIO_DEFAULT_MODEL,
    OLLAMA_MODELS,
    PROVIDERS,
    DoctorError,
    ask_doctor,
    build_offline_answer,
    build_remedies_block,
    check_connection,
    fetch_models,
    provider_defaults,
)
from .drugs import DRUGS, search_drugs, suggest_for_symptoms
from .exporters import export_to_csv, export_to_pdf
from .health import (
    infer_diagnosis_key,
    should_remind,
    temperature_rising,
    pulse_high,
    tip_keys_for_symptoms,
)
from .i18n import LANG
from .kv import KV
from .notifications import send_notification

# Imported for KV viewclass resolution (DO NOT remove).
from . import widgets as _widgets  # noqa: F401
from . import screens as _screens  # noqa: F401


class TabletsApp(MDApp):
    current_theme = StringProperty("Blue")
    current_language = StringProperty("ru")
    is_sick = BooleanProperty(False)
    home_tip = StringProperty("")
    home_ai_tip = StringProperty("")
    tray_enabled = BooleanProperty(False)
    doctor_key_status = StringProperty("")
    doctor_model_name = StringProperty(DEFAULT_MODEL)
    doctor_provider = StringProperty("ollama")
    doctor_base_url = StringProperty(DEFAULT_BASE_URL)

    def __init__(self, db: Database | None = None, **kwargs):
        super().__init__(**kwargs)
        self.db = db or Database(get_db_path())
        self.lang_data: dict = LANG["ru"]
        self.selected_med_id: int | None = None
        self.edit_med_id: int | None = None
        self._dialog: MDDialog | None = None
        self._doctor_symptoms: list[str] = []
        self._ai_tip_key: str | None = None
        self.load_settings()

    # -- i18n / settings ------------------------------------------------
    def tr(self, key: str):
        value = self.lang_data.get(key, key)
        # measurement_types is a nested dict — return as-is.
        return value

    def load_settings(self):
        self.current_theme = self.db.get_setting("theme", "Blue") or "Blue"
        lang = self.db.get_setting("language", "ru") or "ru"
        if lang not in LANG:
            lang = "ru"
        self.current_language = lang
        self.lang_data = LANG[lang]
        self.is_sick = self.db.get_setting("is_sick", "0") == "1"
        self.tray_enabled = self.db.get_setting("tray_enabled", "0") == "1"
        self.doctor_model_name = self.db.get_setting("doctor_model", DEFAULT_MODEL) or DEFAULT_MODEL
        self.doctor_base_url = self.db.get_setting("doctor_base", DEFAULT_BASE_URL) or DEFAULT_BASE_URL
        provider = self.db.get_setting("doctor_provider", "ollama") or "ollama"
        if provider not in PROVIDERS:
            provider = "ollama"
        self.doctor_provider = provider
        has_key = bool(self.db.get_setting("doctor_key", ""))
        self.doctor_key_status = self.tr("settings_doctor_key_set") if has_key else self.tr("settings_doctor_key_empty")
        self._ai_tip_key = None  # settings changed -> AI tips may be re-fetched
        self.home_ai_tip = ""
        self.apply_theme()

    def apply_theme(self):
        palette = "Blue" if self.current_theme == "Blue" else "Pink"
        self.theme_cls.primary_palette = palette
        self.theme_cls.accent_palette = palette

    def _save_setting(self, key: str, value: str):
        self.db.set_setting(key, value)

    # -- build ----------------------------------------------------------
    def build(self):
        self.title = "Tablets"
        self.theme_cls.material_style = "M3"
        return Builder.load_string(KV)

    def on_start(self):
        self.refresh_all()
        Clock.schedule_interval(self.check_reminders, 30)
        Clock.schedule_interval(self.check_trends, 3600)
        Clock.schedule_once(lambda _dt: self._start_tray(), 1.0)

    def on_stop(self):
        try:
            from .tray import stop_tray

            stop_tray()
        except Exception:
            pass

    def _start_tray(self):
        if not self.tray_enabled:
            return
        try:
            from .tray import start_tray

            taken, total = self._today_progress()
            # NOTE: pystray invokes callbacks on its own thread, so hop
            # to Kivy's main thread — direct Window/App calls crash.
            start_tray(on_open=lambda: Clock.schedule_once(
                           lambda _dt: self.show_window()),
                       on_quit=lambda: Clock.schedule_once(
                           lambda _dt: self.quit_from_tray()),
                       taken=taken, total=total,
                       status_text=self.tr("app_name"),
                       open_label=self.tr("tray_open"),
                       quit_label=self.tr("tray_exit"))
        except Exception as exc:
            print(f"[tablets] tray start failed: {exc}")

    def show_window(self):
        try:
            from kivy.core.window import Window

            Window.show()
            try:
                Window.restore()
            except Exception:
                pass
            self._manager().current = "main"
        except Exception as exc:
            print(f"[tablets] show window failed: {exc}")

    def quit_from_tray(self):
        try:
            from .tray import stop_tray

            stop_tray()
        except Exception:
            pass
        self.stop()

    def _today_progress(self) -> tuple[int, int]:
        try:
            meds = self.db.medications_for_today()
        except Exception:
            return 0, 0
        return sum(1 for m in meds if m.get("status") == "taken"), len(meds)

    def _update_progress(self):
        taken, total = self._today_progress()
        try:
            screen = self._manager().get_screen("main")
            if "progress_label" in screen.ids:
                screen.ids.progress_label.text = (
                    self.tr("progress_taken").format(taken=taken, total=total)
                    if total else "")
            if "progress_bar" in screen.ids:
                screen.ids.progress_bar.value = (taken / total) if total else 0
        except Exception:
            pass
        try:
            from .tray import update_tray

            update_tray(taken, total, self.tr("app_name"),
                        self.tr("tray_open"), self.tr("tray_exit"))
        except Exception:
            pass

    def refresh_all(self):
        self.load_home_screen()
        self.load_medications_screen()
        self.load_measurements_screen()
        self.load_symptoms_screen()

    # -- navigation -----------------------------------------------------
    def _manager(self):
        return self.root.ids.screen_manager

    def go_back_to_main(self):
        self._manager().current = "main"
        self.load_home_screen()

    def go_back_to_meas(self):
        self._manager().current = "meas"
        self.load_measurements_screen()

    def go_back_to_symptoms(self):
        self._manager().current = "symptoms"
        self.load_symptoms_screen()

    def go_to_add_med(self):
        self.edit_med_id = None
        screen = self._manager().get_screen("add_med")
        screen.clear_form()
        self._manager().current = "add_med"

    def go_to_add_meas(self):
        screen = self._manager().get_screen("add_meas")
        screen.clear_form()
        self._manager().current = "add_meas"

    def go_to_add_symptoms(self):
        screen = self._manager().get_screen("add_symptoms")
        screen.build_checkboxes()
        self._manager().current = "add_symptoms"

    def go_to_doctor(self):
        self._manager().current = "doctor"

    def go_to_reference(self):
        self.load_reference_screen(query="")
        self._manager().current = "reference"

    def open_med_for_edit(self, med_id: int):
        med = self.db.get_medication(med_id)
        if not med:
            return
        self.edit_med_id = med_id
        screen = self._manager().get_screen("add_med")
        screen.clear_form()
        screen.ids.name.text = med.get("name", "")
        screen.ids.dosage.text = med.get("dosage", "")
        screen.ids.frequency.text = med.get("frequency", "")
        screen.ids.course_days.text = str(med.get("course_days") or "")
        screen.ids.reason.text = med.get("reason", "")
        screen.ids.notes.text = med.get("notes", "")
        screen.set_time(med.get("time", "08:00"))
        days = [int(d) for d in str(med.get("days", "")).split(",")
                if d.strip().isdigit()]
        screen.set_days(days)
        self._manager().current = "add_med"

    # -- list loaders ---------------------------------------------------
    def _status_text(self, status: str) -> str:
        return {"taken": self.tr("taken"), "pending": self.tr("pending"),
                "missed": self.tr("missed")}.get(status, status)

    @staticmethod
    def _status_icon(status: str) -> tuple[str, list]:
        if status == "taken":
            return "check-circle", [0.16, 0.65, 0.27, 1]
        if status == "missed":
            return "close-circle", [0.75, 0.3, 0.3, 1]
        return "pill", [0.2, 0.45, 0.85, 1]

    def load_home_screen(self):
        try:
            screen = self._manager().get_screen("main")
        except Exception:
            return
        items = []
        for med in self.db.medications_for_today():
            subtitle = f"{med['dosage']} • {self._status_text(med['status'])}"\
                       f" • {med['time']}" if med["dosage"] \
                else f"{self._status_text(med['status'])} • {med['time']}"
            items.append({
                "med_id": med["id"],
                "title": med["name"],
                "subtitle": subtitle,
                "status": med["status"],
                "time_text": med["time"],
                "icon_name": self._status_icon(med["status"])[0],
                "icon_color": self._status_icon(med["status"])[1],
            })
        if not items:
            msg = self.tr("no_meds")
            if self.is_sick:
                msg += f" {self.tr('msg_sick_suffix')}"

        symptoms = self.db.recent_symptoms(
            (datetime.now() - timedelta(hours=24)).isoformat())
        tips = [self.tr(k) for k in tip_keys_for_symptoms(symptoms)]
        self.home_tip = "\n".join(sorted(set(tips)))
        try:
            screen.ids.rv.data = items
            screen.ids.tips_label.text = self._tips_text()
            if "empty_label" in screen.ids:
                screen.ids.empty_label.text = msg if not items else ""
        except Exception as exc:
            print(f"[tablets] load_home failed: {exc}")
        self._update_progress()

    def _tips_text(self) -> str:
        parts = []
        if self.home_tip:
            parts += self.home_tip.split("\n")[:2]
        if len(parts) < 2 and self.home_ai_tip:
            parts += self._sentences(self.home_ai_tip)[: 2 - len(parts)]
        text = "\n".join(parts)
        return text if len(text) <= 240 else text[:237] + "..."

    @staticmethod
    def _sentences(text: str) -> list[str]:
        import re

        chunks = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
        return [c for c in chunks if len(c) > 12]

    def maybe_fetch_ai_tips(self, symptoms: list[str]):
        """Fetch 2-3 brief AI tips for current symptoms (cached, background).

        Offline tips always show; AI ones are appended when the backend
        is configured and reachable. Failures are silent (offline stays).
        """
        unique = list(dict.fromkeys(symptoms))
        if not unique:
            self.home_ai_tip = ""
            self._ai_tip_key = None
            return
        provider = self.doctor_provider
        api_key = self.db.get_setting("doctor_key", "")
        if provider == "ollama" and not api_key:
            return  # offline only, no key
        model = self.doctor_model_name
        base = self.doctor_base_url
        key = "|".join([provider, model, base, self.current_language] + sorted(unique))
        if key == self._ai_tip_key:
            return
        self._ai_tip_key = key
        import threading

        lang = self.current_language
        names = [self.tr(f"symptom_{s}") for s in unique]
        if lang == "ru":
            question = (
                "Дай 1-2 коротких совета по одной строке человеку с "
                f"такими симптомами: {', '.join(names)}. "
                "Без диагнозов, дозировок и названий лекарств."
            )
        else:
            question = (
                "Give 1-2 brief one-line tips for a person with these "
                f"symptoms: {', '.join(names)}. "
                "No diagnoses, dosages or drug names."
            )

        def _work():
            try:
                answer = ask_doctor(
                    question, api_key=api_key, model=model, base_url=base,
                    lang=lang, symptom_names=None, provider=provider)
                answer = " ".join(answer.split())[:600]
            except DoctorError:
                return
            Clock.schedule_once(partial(self._show_ai_tips, answer))

        threading.Thread(target=_work, daemon=True).start()

    def _show_ai_tips(self, answer: str, _dt):
        self.home_ai_tip = answer
        try:
            self._manager().get_screen("main").ids.tips_label.text = self._tips_text()
        except Exception:
            pass

    def load_medications_screen(self):
        try:
            screen = self._manager().get_screen("meds")
        except Exception:
            return
        day_names = [self.tr(k) for k in
                     ("mon", "tue", "wed", "thu", "fri", "sat", "sun")]
        items = []
        for med in self.db.list_medications():
            days = [day_names[int(d)] for d in str(med.get("days", "")).split(",")
                    if d.strip().isdigit() and 0 <= int(d.strip()) <= 6]
            subtitle = f"{med.get('dosage') or ''} • {med.get('time', '')}"\
                       f" • {', '.join(days)}".strip(" •")
            items.append({"med_id": med["id"], "title": med.get("name", ""),
                          "subtitle": subtitle, "status": "pending",
                          "time_text": med.get("time", ""),
                          "icon_name": "pill",
                          "icon_color": [0.2, 0.45, 0.85, 1]})
        try:
            screen.ids.rv.data = items
            if "empty_label" in screen.ids:
                screen.ids.empty_label.text = self.tr("no_meds") if not items else ""
        except Exception as exc:
            print(f"[tablets] load_meds failed: {exc}")

    def load_measurements_screen(self):
        try:
            screen = self._manager().get_screen("meas")
        except Exception:
            return
        rows = []
        for mtype, value, ts in self.db.list_measurements():
            try:
                dt = datetime.fromisoformat(ts).strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError):
                dt = str(ts)
            labels = self.tr("measurement_types")
            label = labels.get(mtype, mtype) if isinstance(labels, dict) else mtype
            rows.append({"meas_text": f"{label}: {value} ({dt})"})
        try:
            screen.ids.rv.data = rows
            if "empty_label" in screen.ids:
                screen.ids.empty_label.text = self.tr("no_measurements") if not rows else ""
        except Exception as exc:
            print(f"[tablets] load_meas failed: {exc}")

    def load_symptoms_screen(self):
        try:
            screen = self._manager().get_screen("symptoms")
        except Exception:
            return
        week_ago = (datetime.now() - timedelta(hours=168)).isoformat()
        day_ago = (datetime.now() - timedelta(hours=24)).isoformat()
        symptoms = self.db.recent_symptoms(week_ago)
        recent = set(self.db.recent_symptoms(day_ago))
        unique = list(dict.fromkeys(symptoms))
        container = screen.ids.symptoms_list
        container.clear_widgets()
        for sym in unique:
            item = TwoLineAvatarIconListItem(
                text=self.tr(f"symptom_{sym}"),
                secondary_text=self.tr("msg_today") if sym in recent
                else self.tr("msg_earlier"),
            )
            item.add_widget(IconLeftWidget(icon="alert-circle-outline"))
            container.add_widget(item)
        key = infer_diagnosis_key(symptoms)
        diagnosis = self.tr(f"diagnosis_{key}") if key else self.tr("diagnosis_unknown")
        screen.ids.diagnosis_label.text = f"{self.tr('diagnosis_label')} {diagnosis}"
        self._render_remedies(screen, symptoms)
        self.maybe_fetch_ai_tips(symptoms)
        self.load_home_screen()

    def _drug_display(self, drug: dict) -> tuple[str, str]:
        ru = self.current_language == "ru"
        name = drug["name"] if ru else drug.get("name_en", drug["name"])
        desc = drug["desc"] if ru else drug.get("desc_en", drug["desc"])
        return name, desc

    def _render_remedies(self, screen, symptoms: list[str]):
        try:
            remedies_box = screen.ids.remedies_list
        except KeyError:
            return
        remedies_box.clear_widgets()
        if not symptoms:
            try:
                screen.ids.remedies_urgent.text = ""
            except KeyError:
                pass
            item = TwoLineAvatarIconListItem(
                text=self.tr("remedies_empty"),
                secondary_text=self.tr("remedies_disclaimer"),
            )
            item.add_widget(IconLeftWidget(icon="information-outline"))
            remedies_box.add_widget(item)
            return
        suggestions, urgent = suggest_for_symptoms(list(dict.fromkeys(symptoms)))
        try:
            screen.ids.remedies_urgent.text = self.tr("remedies_urgent") if urgent else ""
        except KeyError:
            pass
        if not suggestions:
            item = TwoLineAvatarIconListItem(
                text=self.tr("remedies_empty"),
                secondary_text=self.tr("remedies_disclaimer"),
            )
            item.add_widget(IconLeftWidget(icon="information-outline"))
            remedies_box.add_widget(item)
            return
        for drug in suggestions:
            name, desc = self._drug_display(drug)
            matched = ", ".join(self.tr(f"symptom_{s}") for s in drug.get("matched", []))
            is_remedy = drug.get("kind", "remedy") == "remedy"
            item = TwoLineAvatarIconListItem(
                text=name,
                secondary_text=f"{matched} — {desc[:90]}",
                on_release=partial(self.show_drug_dialog, drug["id"]),
            )
            item.add_widget(IconLeftWidget(
                icon="pill" if is_remedy else "information-outline"))
            remedies_box.add_widget(item)

    def show_drug_dialog(self, drug_id: str, *args):
        drug = next((d for d in DRUGS if d["id"] == drug_id), None)
        if not drug:
            return
        name, desc = self._drug_display(drug)
        cat = drug["category"] if self.current_language == "ru" else drug.get("category_en", "")
        self._close_dialog()
        if drug.get("kind", "remedy") == "remedy":
            buttons = [
                MDFlatButton(text=self.tr("remedies_add"),
                             on_release=lambda *_: self.add_remedy_to_meds(drug_id)),
                MDFlatButton(text=self.tr("cancel"),
                             on_release=lambda *_: self._close_dialog()),
            ]
        else:
            buttons = [
                MDFlatButton(text=self.tr("got_it"),
                             on_release=lambda *_: self._close_dialog()),
            ]
        self._dialog = MDDialog(
            title=name,
            text=f"{cat}\n\n{desc}\n\n(i) {self.tr('remedies_disclaimer')}",
            buttons=buttons,
        )
        self._dialog.open()
        if drug.get("wiki"):
            self._enrich_drug_dialog(drug["wiki"])

    def _enrich_drug_dialog(self, wiki_title: str):
        """Append a Wikipedia RU summary to the open dialog (cached)."""
        import threading

        base_text = ""
        try:
            base_text = self._dialog.text if self._dialog else ""
        except Exception:
            return

        def _work():
            try:
                from .wiki import fetch_summary_ru

                extract, _url = fetch_summary_ru(wiki_title)
            except Exception:
                return
            if extract:
                Clock.schedule_once(
                    partial(self._update_drug_dialog,
                            f"{base_text}\n\nWikipedia (CC BY-SA): {extract[:400]}"))

        threading.Thread(target=_work, daemon=True).start()

    def _update_drug_dialog(self, text: str, _dt):
        try:
            if self._dialog:
                self._dialog.text = text
        except Exception:
            pass

    def add_remedy_to_meds(self, drug_id: str, *args):
        drug = next((d for d in DRUGS if d["id"] == drug_id), None)
        self._close_dialog()
        if not drug or drug.get("kind", "remedy") != "remedy":
            return
        self.db.add_medication(
            name=drug["name"] if self.current_language == "ru" else drug.get("name_en", drug["name"]),
            dosage="",
            time="08:00",
            days="0,1,2,3,4,5,6",
            notes=(drug["desc"] if self.current_language == "ru" else drug.get("desc_en", ""))[:200],
        )
        toast(self.tr("remedies_added"))
        self.load_home_screen()
        self.load_medications_screen()

    # -- reference ------------------------------------------------------
    def load_reference_screen(self, query: str = ""):
        try:
            screen = self._manager().get_screen("reference")
        except Exception:
            return
        container = screen.ids.ref_list
        container.clear_widgets()
        found = search_drugs(query or "")
        found.sort(key=lambda d: 0 if d.get("kind", "remedy") == "remedy" else 1)
        for drug in found:
            name, desc = self._drug_display(drug)
            is_remedy = drug.get("kind", "remedy") == "remedy"
            item = TwoLineAvatarIconListItem(
                text=name,
                secondary_text=desc[:110],
                on_release=partial(self.show_drug_dialog, drug["id"]),
            )
            item.add_widget(IconLeftWidget(
                icon="pill" if is_remedy else "information-outline"))
            container.add_widget(item)

    # -- doctor (AI) ----------------------------------------------------
    def ask_doctor_from_form(self, screen):
        question = screen.ids.question.text.strip()
        symptoms = self.db.recent_symptoms(
            (datetime.now() - timedelta(hours=168)).isoformat())
        names = [self.tr(f"symptom_{s}") for s in dict.fromkeys(symptoms)]
        provider = self.db.get_setting("doctor_provider", "ollama") or "ollama"
        api_key = self.db.get_setting("doctor_key", "")
        if not question and not symptoms:
            screen.ids.answer_label.text = self.tr("doctor_no_key")
            self._doctor_symptoms = []
            self._render_doctor_remedies()
            return
        if provider == "ollama" and not api_key:
            screen.ids.answer_label.text = (
                f"{self.tr('doctor_need_key')}\n\n"
                f"{build_offline_answer(symptoms, self.tr)}"
            )
            self._doctor_symptoms = symptoms
            self._render_doctor_remedies()
            return
        screen.ids.answer_label.text = self.tr("doctor_thinking")
        screen.ids.question.text = ""
        try:
            screen.ids.doctor_remedies.clear_widgets()
        except (KeyError, AttributeError):
            pass
        self._doctor_symptoms = symptoms
        import threading

        def _work():
            model = self.db.get_setting("doctor_model", DEFAULT_MODEL) or DEFAULT_MODEL
            base = self.db.get_setting("doctor_base", DEFAULT_BASE_URL) or DEFAULT_BASE_URL
            try:
                answer = ask_doctor(
                    question, api_key=api_key, model=model, base_url=base,
                    lang=self.current_language, symptom_names=names,
                    provider=provider)
                if symptoms:
                    answer += "\n\n---\n" + build_remedies_block(symptoms, self.tr)
            except DoctorError:
                offline = build_offline_answer(symptoms, self.tr)
                answer = f"[!] {self.tr('doctor_offline')}\n\n{offline}"
            Clock.schedule_once(partial(self._show_doctor_answer, answer))

        threading.Thread(target=_work, daemon=True).start()

    def _show_doctor_answer(self, answer: str, _dt):
        try:
            self._manager().get_screen("doctor").ids.answer_label.text = answer
        except Exception:
            pass
        self._render_doctor_remedies()

    def _render_doctor_remedies(self):
        """Clickable remedy cards under the answer (each opens add dialog)."""
        try:
            screen = self._manager().get_screen("doctor")
            box = screen.ids.doctor_remedies
        except (KeyError, AttributeError, Exception):
            return
        box.clear_widgets()
        symptoms = list(dict.fromkeys(self._doctor_symptoms))
        if not symptoms:
            return
        suggestions, _urgent = suggest_for_symptoms(symptoms)
        for drug in suggestions:
            name, desc = self._drug_display(drug)
            matched = ", ".join(self.tr(f"symptom_{s}") for s in drug.get("matched", []))
            is_remedy = drug.get("kind", "remedy") == "remedy"
            item = TwoLineAvatarIconListItem(
                text=f"+ {name}" if is_remedy else name,
                secondary_text=f"{matched} — {desc[:90]}",
                on_release=partial(self.show_drug_dialog, drug["id"]),
            )
            item.add_widget(IconLeftWidget(
                icon="pill" if is_remedy else "information-outline"))
            box.add_widget(item)

    def _text_field_dialog(self, title: str, current: str, hint: str, on_save):
        from kivymd.uix.textfield import MDTextField

        self._close_dialog()
        field = MDTextField(text=current or "", hint_text=hint, mode="rectangle")
        self._dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=field,
            buttons=[
                MDFlatButton(text=self.tr("save"),
                             on_release=lambda *_: (on_save(field.text.strip()), self._close_dialog())),
                MDFlatButton(text=self.tr("cancel"),
                             on_release=lambda *_: self._close_dialog()),
            ],
        )
        self._dialog.open()

    def _list_dialog(self, title: str, options: list[tuple[str, str]], on_pick):
        """Simple single-choice dialog. options = [(key, label)]."""
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.list import OneLineListItem

        self._close_dialog()
        box = MDBoxLayout(orientation="vertical", adaptive_height=True,
                          spacing="4dp", padding="4dp")
        for key, label in options:
            item = OneLineListItem(
                text=label,
                on_release=partial(self._pick_from_dialog, on_pick, key),
            )
            box.add_widget(item)
        self._dialog = MDDialog(
            title=title,
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text=self.tr("cancel"),
                             on_release=lambda *_: self._close_dialog()),
            ],
        )
        self._dialog.open()

    def _pick_from_dialog(self, on_pick, key: str, *args):
        self._close_dialog()
        on_pick(key)

    # -- doctor provider / model / key / server -------------------------
    def doctor_provider_label(self) -> str:
        return self.tr(f"provider_{self.doctor_provider}")

    def edit_doctor_provider(self):
        self._list_dialog(
            self.tr("settings_doctor_provider"),
            [("ollama", self.tr("provider_ollama")),
             ("lmstudio", self.tr("provider_lmstudio"))],
            self._save_doctor_provider,
        )

    def _save_doctor_provider(self, provider: str):
        self.db.set_setting("doctor_provider", provider)
        base, model = provider_defaults(provider)
        self.db.set_setting("doctor_base", base)
        self.db.set_setting("doctor_model", model)
        self.load_settings()
        toast(self.tr("doctor_provider_changed").format(self.tr(f"provider_{provider}")))

    def edit_doctor_key(self):
        self._text_field_dialog(
            self.tr("settings_doctor_key"),
            "",
            self.tr("settings_doctor_key"),
            self._save_doctor_key,
        )

    def _save_doctor_key(self, value: str):
        self.db.set_setting("doctor_key", value)
        self.load_settings()

    def edit_doctor_base(self):
        from .doctor import DEFAULT_BASE_URL as _default

        current = self.db.get_setting("doctor_base", _default) or _default
        self._text_field_dialog(
            self.tr("settings_doctor_base"),
            current,
            "http://localhost:1234",
            self._save_doctor_base,
        )

    def _save_doctor_base(self, value: str):
        self.db.set_setting("doctor_base", value or DEFAULT_BASE_URL)
        self.load_settings()

    def edit_doctor_model(self):
        provider = self.doctor_provider
        if provider == "lmstudio":
            current = self.doctor_model_name
            models = [current] if current else list(LMSTUDIO_DEFAULT_MODEL and [LMSTUDIO_DEFAULT_MODEL] or [])
            options = [(m, m) for m in dict.fromkeys(models)]
            options.append(("__refresh__", self.tr('doctor_refresh_models')))
            options.append(("__custom__", self.tr('doctor_custom_model')))
        else:
            options = [(m, m + (" *" if m == self.doctor_model_name else ""))
                       for m in OLLAMA_MODELS]
            if self.doctor_model_name not in OLLAMA_MODELS:
                options.insert(0, (self.doctor_model_name,
                                   f"{self.doctor_model_name} *"))
            options.append(("__custom__", self.tr('doctor_custom_model')))
        self._list_dialog(self.tr("doctor_models_title"), options,
                          self._pick_doctor_model)

    def _pick_doctor_model(self, key: str):
        if key == "__custom__":
            self._text_field_dialog(
                self.tr("settings_doctor_model"),
                self.doctor_model_name,
                "llama3.2:1b",
                self._save_doctor_model,
            )
        elif key == "__refresh__":
            self.refresh_doctor_models()
        else:
            self._save_doctor_model(key)

    def _save_doctor_model(self, value: str):
        self.db.set_setting("doctor_model", value or DEFAULT_MODEL)
        self.load_settings()

    def refresh_doctor_models(self):
        import threading

        base = self.db.get_setting("doctor_base", "") or LMSTUDIO_BASE_URL
        key = self.db.get_setting("doctor_key", "")

        def _work():
            try:
                models = fetch_models(base, key)
                if not models:
                    raise DoctorError("empty list")
                if self.doctor_model_name not in models:
                    self.db.set_setting("doctor_model", models[0])
                    self.load_settings()
                msg = self.tr("doctor_models_updated").format(len(models))
            except DoctorError as exc:
                msg = self.tr("doctor_models_failed").format(exc)
            Clock.schedule_once(lambda _dt: toast(msg))

        threading.Thread(target=_work, daemon=True).start()

    def test_doctor_connection(self):
        import threading

        provider = self.doctor_provider
        base = self.db.get_setting("doctor_base", "") or DEFAULT_BASE_URL
        key = self.db.get_setting("doctor_key", "")
        model = self.doctor_model_name

        def _work():
            try:
                check_connection(provider, base, key, model)
                msg = self.tr("doctor_test_ok")
            except DoctorError as exc:
                msg = self.tr("doctor_test_fail").format(exc)
            Clock.schedule_once(lambda _dt: toast(msg))

        threading.Thread(target=_work, daemon=True).start()

    # -- medication dialog (replaces fragile fake-caller dropdown) ------
    def _close_dialog(self, *args):
        if self._dialog:
            try:
                self._dialog.dismiss()
            except Exception:
                pass
            self._dialog = None

    def show_med_dialog(self, med_id: int):
        med = self.db.get_medication(med_id)
        if not med:
            return
        self.selected_med_id = med_id
        self._close_dialog()
        self._dialog = MDDialog(
            title=self.tr("medication_action").format(med.get("name", "")),
            buttons=[
                MDFlatButton(text=self.tr("take"),
                             on_release=lambda *_: self.action_take()),
                MDFlatButton(text=self.tr("skip"),
                             on_release=lambda *_: self.action_skip()),
                MDFlatButton(text=self.tr("edit"),
                             on_release=lambda *_: self.action_edit()),
                MDFlatButton(text=self.tr("delete"),
                             on_release=lambda *_: self.action_delete()),
                MDFlatButton(text=self.tr("cancel"),
                             on_release=lambda *_: self._close_dialog()),
            ],
        )
        self._dialog.open()

    def action_take(self, *args):
        if self.selected_med_id is not None and self.selected_med_id >= 0:
            self.db.mark_taken(self.selected_med_id)
        self._close_dialog()
        self.load_home_screen()
        self.load_medications_screen()

    def action_untake(self, *args):
        if self.selected_med_id is not None and self.selected_med_id >= 0:
            self.db.unmark(self.selected_med_id)
            toast(self.tr("msg_untaken"))
        self._close_dialog()
        self.load_home_screen()
        self.load_medications_screen()

    def action_skip(self, *args):
        if self.selected_med_id is not None and self.selected_med_id >= 0:
            self.db.mark_skipped(self.selected_med_id)
        self._close_dialog()
        self.load_home_screen()
        self.load_medications_screen()

    def action_edit(self, *args):
        med_id = self.selected_med_id
        self._close_dialog()
        if med_id is not None and med_id >= 0:
            self.open_med_for_edit(med_id)

    def action_delete(self, *args):
        if self.selected_med_id is not None and self.selected_med_id >= 0:
            self.db.delete_medication(self.selected_med_id)
        self._close_dialog()
        self.load_home_screen()
        self.load_medications_screen()

    # -- form saves -----------------------------------------------------
    def save_medication_from_form(self, screen) -> None:
        name = screen.ids.name.text.strip()
        dosage = screen.ids.dosage.text.strip()
        days = ",".join(str(i) for i, v in enumerate(screen.selected_days) if v)
        if not name or not days:
            toast(self.tr("msg_fill_name_days"))
            return
        payload = {
            "name": name,
            "dosage": dosage,
            "time": screen.time_text,
            "days": days,
            "frequency": screen.ids.frequency.text.strip(),
            "course_days": screen.ids.course_days.text.strip(),
            "reason": screen.ids.reason.text.strip(),
            "notes": screen.ids.notes.text.strip(),
        }
        if self.edit_med_id:
            self.db.update_medication(self.edit_med_id, **payload)
            self.edit_med_id = None
        else:
            self.db.add_medication(**payload)
        toast(self.tr("msg_med_saved"))
        self.load_home_screen()
        self.load_medications_screen()
        self.go_back_to_main()

    def save_measurement_from_form(self, screen) -> None:
        value = screen.ids.value.text.strip()
        if not screen.internal_type or not value:
            toast(self.tr("msg_fill_type_value"))
            return
        self.db.add_measurement(screen.internal_type, value)
        toast(self.tr("msg_meas_saved"))
        self.load_measurements_screen()
        self.load_home_screen()
        self.go_back_to_meas()

    def save_symptoms_from_form(self, screen) -> None:
        selected = screen.selected_keys()
        if not selected:
            toast(self.tr("msg_sym_select_one"))
            return
        self.db.add_symptoms(selected)
        toast(self.tr("msg_sym_saved"))
        self.load_symptoms_screen()
        self.load_home_screen()
        self.go_back_to_symptoms()

    def clear_all_symptoms(self):
        self.db.clear_symptoms()
        self.load_symptoms_screen()
        self.load_home_screen()
        toast(self.tr("msg_sym_cleared"))

    # -- reminders & trends (fixed logic) -------------------------------
    def check_reminders(self, _dt):
        now = datetime.now()
        for med in self.db.medications_for_today(now):
            scheduled = med.get("datetime")
            if scheduled and should_remind(med["status"], scheduled, now):
                send_notification(
                    self.tr("notification_title").format(med["name"]),
                    self.tr("notification_text").format(med["dosage"] or "—"),
                    app_name=self.tr("app_name"),
                )

    def check_trends(self, _dt):
        now = datetime.now()
        temps = self.db.measurement_values(
            "temperature", (now - timedelta(days=3)).isoformat())
        pulses = self.db.measurement_values(
            "pulse", (now - timedelta(days=2)).isoformat())
        if temperature_rising(temps):
            send_notification(self.tr("health_trend_title"),
                              self.tr("trend_temp_rising"),
                              app_name=self.tr("app_name"))
        if pulse_high(pulses):
            send_notification(self.tr("health_trend_title"),
                              self.tr("trend_pulse_high"),
                              app_name=self.tr("app_name"))

    # -- settings -------------------------------------------------------
    def toggle_sick_status(self):
        self.is_sick = not self.is_sick
        self._save_setting("is_sick", "1" if self.is_sick else "0")
        self.load_home_screen()

    def toggle_tray(self):
        self.tray_enabled = not self.tray_enabled
        self._save_setting("tray_enabled", "1" if self.tray_enabled else "0")
        if self.tray_enabled:
            self._start_tray()
        else:
            try:
                from .tray import stop_tray

                stop_tray()
            except Exception:
                pass

    def show_about(self):
        self._close_dialog()
        text = (
            f"{self.tr('about_version')}: {__version__}\n"
            f"{self.tr('about_author')}: mrSaT13\n"
            "GitHub: github.com/mrSaT13/Tablets\n"
            f"{self.tr('about_license')}: MIT\n\n"
            f"(i) {self.tr('about_disclaimer')}"
        )
        self._dialog = MDDialog(
            title=f"{self.tr('app_name')}",
            text=text,
            buttons=[
                MDFlatButton(text=self.tr("cancel"),
                             on_release=lambda *_: self._close_dialog()),
            ],
        )
        self._dialog.open()

    def toggle_theme(self):
        self.current_theme = "Pink" if self.current_theme == "Blue" else "Blue"
        self._save_setting("theme", self.current_theme)
        self.apply_theme()

    def toggle_language(self):
        self.current_language = "en" if self.current_language == "ru" else "ru"
        self.lang_data = LANG[self.current_language]
        self._save_setting("language", self.current_language)
        has_key = bool(self.db.get_setting("doctor_key", ""))
        self.doctor_key_status = self.tr("settings_doctor_key_set") if has_key else self.tr("settings_doctor_key_empty")
        self.home_ai_tip = ""
        self._ai_tip_key = None  # refetch AI tips in the new language
        # Re-render day buttons + symptom checkboxes in the new language.
        try:
            self._manager().get_screen("add_med").refresh_days()
            self._manager().get_screen("add_symptoms").build_checkboxes()
        except Exception:
            pass
        self.refresh_all()

    # -- export ---------------------------------------------------------
    def export_to_csv(self):
        try:
            paths = export_to_csv(self.db)
            toast(self.tr("msg_csv_done").format(str(paths[0].parent)))
        except Exception as exc:  # noqa: BLE001
            toast(self.tr("msg_csv_error").format(exc))

    def export_to_pdf(self):
        try:
            path = export_to_pdf(self.db, self.tr)
            toast(self.tr("msg_pdf_done").format(str(path)))
        except Exception as exc:  # noqa: BLE001
            toast(self.tr("msg_pdf_error").format(exc))


def main() -> None:
    TabletsApp().run()


if __name__ == "__main__":
    main()
