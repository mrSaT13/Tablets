"""KV layout for Tablets. Targets KivyMD 1.2 (MDTopAppBar API)."""
from __future__ import annotations

KV = '''
#:import dp kivy.metrics.dp
#:import MDNavigationLayout kivymd.uix.navigationdrawer.MDNavigationLayout
#:import MDNavigationDrawer kivymd.uix.navigationdrawer.MDNavigationDrawer
#:import OneLineIconListItem kivymd.uix.list.OneLineIconListItem
#:import TwoLineAvatarIconListItem kivymd.uix.list.TwoLineAvatarIconListItem
#:import OneLineAvatarIconListItem kivymd.uix.list.OneLineAvatarIconListItem
#:import IconLeftWidget kivymd.uix.list.IconLeftWidget
#:import MDIconButton kivymd.uix.button.MDIconButton
#:import MDRaisedButton kivymd.uix.button.MDRaisedButton
#:import MDRectangleFlatButton kivymd.uix.button.MDRectangleFlatButton
#:import MDFloatingActionButton kivymd.uix.button.MDFloatingActionButton
#:import MDTopAppBar kivymd.uix.toolbar.MDTopAppBar
#:import MDList kivymd.uix.list.MDList
#:import MDIcon kivymd.uix.label.MDIcon
#:import ProgressBar kivy.uix.progressbar.ProgressBar

<MedicationItem>:
    orientation: "horizontal"
    adaptive_height: True
    padding: dp(12), dp(10), dp(4), dp(10)
    spacing: dp(8)
    MDIcon:
        icon: root.icon_name
        theme_text_color: "Custom"
        text_color: root.icon_color
        size_hint: None, None
        size: dp(40), dp(40)
        pos_hint: {"center_y": .5}
    MDBoxLayout:
        orientation: "vertical"
        adaptive_height: True
        spacing: dp(2)
        pos_hint: {"center_y": .5}
        MDLabel:
            text: root.title
            size_hint_y: None
            height: self.texture_size[1]
            shorten: True
            shorten_from: "right"
        MDLabel:
            text: root.subtitle
            theme_text_color: "Secondary"
            font_style: "Caption"
            size_hint_y: None
            height: self.texture_size[1]
            shorten: True
            shorten_from: "right"
    MDIconButton:
        icon: "check-circle-outline"
        theme_text_color: "Custom"
        text_color: 0.16, 0.65, 0.27, 1
        pos_hint: {"center_y": .5}
        on_release: root.on_take()
    MDIconButton:
        icon: "clock-outline"
        theme_text_color: "Custom"
        text_color: 0.55, 0.55, 0.55, 1
        pos_hint: {"center_y": .5}
        on_release: root.on_snooze()

<MeasurementItem>:
    text: root.meas_text
    IconLeftWidget:
        icon: "chart-line"

<MainScreen>:
    name: "main"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.96, 0.97, 1, 1
        MDTopAppBar:
            title: app.tr('home')
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            elevation: 4
        MDBoxLayout:
            orientation: "vertical"
            padding: dp(12)
            spacing: dp(8)
            MDLabel:
                text: app.tr('tips')
                font_style: "Subtitle2"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: self.texture_size[1] if (app.home_tip or app.home_ai_tip) else 0
                opacity: 1 if (app.home_tip or app.home_ai_tip) else 0
            MDBoxLayout:
                size_hint_y: None
                height: dp(28)
                spacing: dp(8)
                MDLabel:
                    id: progress_label
                    text: ""
                    theme_text_color: "Secondary"
                    size_hint_x: None
                    width: dp(110)
                ProgressBar:
                    id: progress_bar
                    max: 1
                    value: 0
            MDLabel:
                id: empty_label
                text: ""
                halign: "center"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: self.texture_size[1] if self.text else 0
            RecycleView:
                id: rv
                viewclass: 'MedicationItem'
                RecycleBoxLayout:
                    default_size: None, dp(76)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(4)
            MDLabel:
                id: tips_label
                text: app.home_tip
                halign: "center"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: self.texture_size[1] if self.text else 0
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.94, "y": 0.04}
        on_release: app.go_to_add_med()

<MedicationsScreen>:
    name: "meds"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.96, 0.97, 1, 1
        MDTopAppBar:
            title: app.tr('medications')
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            elevation: 4
        MDBoxLayout:
            padding: dp(12)
            spacing: dp(8)
            orientation: "vertical"
            MDLabel:
                id: empty_label
                text: ""
                halign: "center"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: self.texture_size[1] if self.text else 0
            RecycleView:
                id: rv
                viewclass: 'MedicationItem'
                RecycleBoxLayout:
                    default_size: None, dp(76)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(4)
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.94, "y": 0.04}
        on_release: app.go_to_add_med()

<MeasurementsScreen>:
    name: "meas"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.96, 0.97, 1, 1
        MDTopAppBar:
            title: app.tr('measurements')
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            elevation: 4
        MDBoxLayout:
            padding: dp(12)
            spacing: dp(8)
            orientation: "vertical"
            MDLabel:
                id: empty_label
                text: ""
                halign: "center"
                theme_text_color: "Secondary"
                size_hint_y: None
                height: self.texture_size[1] if self.text else 0
            RecycleView:
                id: rv
                viewclass: 'MeasurementItem'
                RecycleBoxLayout:
                    default_size: None, dp(64)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(4)
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.94, "y": 0.04}
        on_release: app.go_to_add_meas()

<SymptomsScreen>:
    name: "symptoms"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.96, 0.97, 1, 1
        MDTopAppBar:
            title: app.tr('symptoms')
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            elevation: 4
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: dp(8)
                spacing: dp(4)
                MDList:
                    id: symptoms_list
                    size_hint_y: None
                    height: self.minimum_height
                MDLabel:
                    id: diagnosis_label
                    text: ""
                    halign: "center"
                    theme_text_color: "Primary"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1] if self.text else 0
                    padding: [dp(12), dp(8), dp(12), dp(8)]
                MDLabel:
                    text: app.tr('remedies_title')
                    font_style: "Subtitle2"
                    theme_text_color: "Secondary"
                    size_hint_y: None
                    height: self.texture_size[1]
                MDLabel:
                    id: remedies_urgent
                    text: ""
                    halign: "center"
                    theme_text_color: "Error"
                    bold: True
                    size_hint_y: None
                    height: self.texture_size[1] if self.text else 0
                MDList:
                    id: remedies_list
                    size_hint_y: None
                    height: self.minimum_height
                MDLabel:
                    text: app.tr('remedies_disclaimer')
                    halign: "center"
                    theme_text_color: "Secondary"
                    font_style: "Caption"
                    size_hint_y: None
                    height: self.texture_size[1]
                    text_size: self.width, None
                Widget:
                    size_hint_y: None
                    height: dp(72)
        MDBoxLayout:
            size_hint_y: None
            height: dp(56)
            padding: [dp(12), dp(6), dp(12), dp(6)]
            spacing: dp(8)
            MDRaisedButton:
                text: app.tr('clear_symptoms')
                md_bg_color: 0.78, 0.2, 0.2, 1
                on_release: app.clear_all_symptoms()
            MDRaisedButton:
                text: app.tr('doctor_title')
                on_release: app.go_to_doctor()
    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.94, "y": 0.04}
        on_release: app.go_to_add_symptoms()

<DoctorScreen>:
    name: "doctor"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.96, 0.97, 1, 1
        MDTopAppBar:
            title: app.tr('doctor_title')
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            elevation: 4
        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                adaptive_height: True
                padding: dp(12)
                spacing: dp(8)
                MDLabel:
                    text: app.tr('doctor_disclaimer')
                    halign: "center"
                    theme_text_color: "Secondary"
                    font_style: "Caption"
                    size_hint_y: None
                    height: self.texture_size[1]
                    text_size: self.width, None
                MDLabel:
                    id: answer_label
                    text: ""
                    halign: "left"
                    size_hint_y: None
                    height: self.texture_size[1] if self.text else 0
                    text_size: self.width, None
                MDList:
                    id: doctor_remedies
                    size_hint_y: None
                    height: self.minimum_height
        MDBoxLayout:
            size_hint_y: None
            height: dp(64)
            padding: [dp(12), dp(8), dp(12), dp(8)]
            spacing: dp(8)
            MDTextField:
                id: question
                hint_text: app.tr('doctor_hint')
                mode: "rectangle"
                multiline: False
                on_text_validate: root.ask()
            MDRaisedButton:
                text: app.tr('doctor_send')
                size_hint_x: None
                width: dp(100)
                on_release: root.ask()

<ReferenceScreen>:
    name: "reference"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.96, 0.97, 1, 1
        MDTopAppBar:
            title: app.tr('reference_title')
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            elevation: 4
        MDBoxLayout:
            size_hint_y: None
            height: dp(64)
            padding: [dp(12), dp(8), dp(12), dp(0)]
            MDTextField:
                id: search
                hint_text: app.tr('reference_search')
                mode: "rectangle"
                on_text: root.on_search(self.text)
        ScrollView:
            MDList:
                id: ref_list
                padding: dp(8)
                spacing: dp(4)
        MDLabel:
            text: app.tr('remedies_disclaimer')
            halign: "center"
            theme_text_color: "Secondary"
            font_style: "Caption"
            size_hint_y: None
            height: dp(28)

<SettingsScreen>:
    name: "settings"
    MDBoxLayout:
        orientation: "vertical"
        md_bg_color: 0.96, 0.97, 1, 1
        MDTopAppBar:
            title: app.tr('settings')
            left_action_items: [["menu", lambda x: app.root.ids.nav_drawer.set_state("open")]]
            elevation: 4
        ScrollView:
            MDList:
                padding: dp(8)
                spacing: dp(4)
                TwoLineAvatarIconListItem:
                    text: app.tr('status')
                    secondary_text: app.tr('is_sick') if app.is_sick else app.tr('not_sick')
                    on_release: app.toggle_sick_status()
                    IconLeftWidget:
                        icon: "emoticon-sad" if app.is_sick else "emoticon-happy"
                TwoLineAvatarIconListItem:
                    text: app.tr('settings_tray')
                    secondary_text: app.tr('tray_on') if app.tray_enabled else app.tr('tray_off')
                    on_release: app.toggle_tray()
                    IconLeftWidget:
                        icon: "tray"
                TwoLineAvatarIconListItem:
                    text: app.tr('theme')
                    secondary_text: app.current_theme
                    on_release: app.toggle_theme()
                    IconLeftWidget:
                        icon: "palette"
                TwoLineAvatarIconListItem:
                    text: app.tr('language')
                    secondary_text: app.current_language
                    on_release: app.toggle_language()
                    IconLeftWidget:
                        icon: "translate"
                OneLineAvatarIconListItem:
                    text: app.tr('export_csv')
                    on_release: app.export_to_csv()
                    IconLeftWidget:
                        icon: "file-export"
                OneLineAvatarIconListItem:
                    text: app.tr('export_pdf')
                    on_release: app.export_to_pdf()
                    IconLeftWidget:
                        icon: "file-pdf-box"
                TwoLineAvatarIconListItem:
                    text: app.tr('settings_doctor_provider')
                    secondary_text: app.doctor_provider_label()
                    on_release: app.edit_doctor_provider()
                    IconLeftWidget:
                        icon: "server-network"
                TwoLineAvatarIconListItem:
                    text: app.tr('settings_doctor_key')
                    secondary_text: app.doctor_key_status
                    on_release: app.edit_doctor_key()
                    IconLeftWidget:
                        icon: "key"
                TwoLineAvatarIconListItem:
                    text: app.tr('settings_doctor_model')
                    secondary_text: app.doctor_model_name
                    on_release: app.edit_doctor_model()
                    IconLeftWidget:
                        icon: "robot"
                TwoLineAvatarIconListItem:
                    text: app.tr('settings_doctor_base')
                    secondary_text: app.doctor_base_url
                    on_release: app.edit_doctor_base()
                    IconLeftWidget:
                        icon: "lan"
                OneLineAvatarIconListItem:
                    text: app.tr('doctor_test')
                    on_release: app.test_doctor_connection()
                    IconLeftWidget:
                        icon: "lan-check"
                OneLineAvatarIconListItem:
                    text: app.tr('about_title')
                    on_release: app.show_about()
                    IconLeftWidget:
                        icon: "information-outline"

<AddMedicationScreen>:
    name: 'add_med'
    ScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(16)
            spacing: dp(10)
            size_hint_y: None
            height: self.minimum_height
            md_bg_color: 0.98, 0.98, 1, 1
            MDTopAppBar:
                title: app.tr('add_med')
                left_action_items: [["arrow-left", lambda x: app.go_back_to_main()]]
                elevation: 2
            MDTextField:
                id: name
                hint_text: app.tr('name')
                mode: "rectangle"
                on_text: root.on_name_text(self.text)
            MDTextField:
                id: dosage
                hint_text: app.tr('dosage')
                mode: "rectangle"
            MDLabel:
                text: app.tr('time')
                size_hint_y: None
                height: dp(22)
                theme_text_color: "Secondary"
            BoxLayout:
                size_hint_y: None
                height: dp(40)
                spacing: dp(6)
                MDRectangleFlatButton:
                    text: app.tr('morning')
                    on_release: root.set_time("08:00")
                MDRectangleFlatButton:
                    text: app.tr('afternoon')
                    on_release: root.set_time("12:00")
                MDRectangleFlatButton:
                    text: app.tr('evening')
                    on_release: root.set_time("20:00")
            MDRectangleFlatButton:
                text: root.time_text
                size_hint_y: None
                height: dp(48)
                on_release: root.show_time_picker()
            MDLabel:
                text: app.tr('days')
                size_hint_y: None
                height: dp(22)
                theme_text_color: "Secondary"
            BoxLayout:
                id: days_box
                size_hint_y: None
                height: dp(44)
                spacing: dp(6)
            MDTextField:
                id: frequency
                hint_text: app.tr('frequency')
                mode: "rectangle"
            MDTextField:
                id: course_days
                hint_text: app.tr('course_days')
                input_filter: 'int'
                mode: "rectangle"
            MDTextField:
                id: reason
                hint_text: app.tr('reason')
                mode: "rectangle"
            MDTextField:
                id: notes
                hint_text: app.tr('notes')
                multiline: True
                mode: "rectangle"
            MDRaisedButton:
                text: app.tr('save')
                pos_hint: {'center_x': 0.5}
                size_hint_y: None
                height: dp(48)
                on_release: root.save_medication()

<AddMeasurementScreen>:
    name: 'add_meas'
    ScrollView:
        MDBoxLayout:
            orientation: 'vertical'
            padding: dp(20)
            spacing: dp(14)
            size_hint_y: None
            height: self.minimum_height
            md_bg_color: 0.98, 0.98, 1, 1
            MDTopAppBar:
                title: app.tr('add_meas')
                left_action_items: [["arrow-left", lambda x: app.go_back_to_meas()]]
                elevation: 2
            MDTextField:
                id: type_spinner
                hint_text: app.tr('type')
                readonly: True
                mode: "rectangle"
                on_focus: root.open_type_menu() if self.focus else None
            MDTextField:
                id: value
                hint_text: app.tr('value')
                mode: "rectangle"
            MDRaisedButton:
                text: app.tr('save')
                pos_hint: {'center_x': 0.5}
                size_hint_y: None
                height: dp(48)
                on_release: root.save_measurement()

<AddSymptomsScreen>:
    name: 'add_symptoms'
    MDBoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(12)
        md_bg_color: 0.98, 0.98, 1, 1
        MDTopAppBar:
            title: app.tr('add_symptom')
            left_action_items: [["arrow-left", lambda x: app.go_back_to_symptoms()]]
            elevation: 2
        MDTextField:
            id: symptom_search
            hint_text: app.tr('symptom_search')
            mode: "rectangle"
            size_hint_y: None
            height: dp(48)
            on_text: root.on_search(self.text)
        ScrollView:
            MDGridLayout:
                id: symptom_grid
                cols: 1
                spacing: dp(6)
                size_hint_y: None
                height: self.minimum_height
        MDRaisedButton:
            text: app.tr('save')
            pos_hint: {'center_x': 0.5}
            size_hint_y: None
            height: dp(48)
            on_release: root.save_symptoms()

MDNavigationLayout:
    ScreenManager:
        id: screen_manager
        MainScreen:
        MedicationsScreen:
        MeasurementsScreen:
        SymptomsScreen:
        DoctorScreen:
        ReferenceScreen:
        SettingsScreen:
        AddMedicationScreen:
        AddMeasurementScreen:
        AddSymptomsScreen:
    MDNavigationDrawer:
        id: nav_drawer
        BoxLayout:
            orientation: "vertical"
            padding: "8dp"
            spacing: "8dp"
            MDLabel:
                text: "Tablets"
                font_style: "H6"
                size_hint_y: None
                height: self.texture_size[1]
                padding: ["12dp", "16dp", "0dp", "8dp"]
            ScrollView:
                MDList:
                    OneLineIconListItem:
                        text: app.tr('home')
                        on_release:
                            screen_manager.current = "main"
                            nav_drawer.set_state("close")
                        IconLeftWidget:
                            icon: "home"
                    OneLineIconListItem:
                        text: app.tr('medications')
                        on_release:
                            screen_manager.current = "meds"
                            nav_drawer.set_state("close")
                        IconLeftWidget:
                            icon: "pill"
                    OneLineIconListItem:
                        text: app.tr('measurements')
                        on_release:
                            screen_manager.current = "meas"
                            nav_drawer.set_state("close")
                        IconLeftWidget:
                            icon: "chart-line"
                    OneLineIconListItem:
                        text: app.tr('symptoms')
                        on_release:
                            screen_manager.current = "symptoms"
                            nav_drawer.set_state("close")
                        IconLeftWidget:
                            icon: "alert-circle-outline"
                    OneLineIconListItem:
                        text: app.tr('doctor_title')
                        on_release:
                            screen_manager.current = "doctor"
                            nav_drawer.set_state("close")
                        IconLeftWidget:
                            icon: "stethoscope"
                    OneLineIconListItem:
                        text: app.tr('reference_title')
                        on_release:
                            screen_manager.current = "reference"
                            nav_drawer.set_state("close")
                        IconLeftWidget:
                            icon: "book-open-variant"
                    OneLineIconListItem:
                        text: app.tr('settings')
                        on_release:
                            screen_manager.current = "settings"
                            nav_drawer.set_state("close")
                        IconLeftWidget:
                            icon: "cog"
'''
