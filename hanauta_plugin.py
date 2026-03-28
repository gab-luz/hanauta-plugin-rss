#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

PLUGIN_ROOT = Path(__file__).resolve().parent
RSS_WIDGET_APP = PLUGIN_ROOT / "rss_widget.py"
SERVICE_KEY = "rss_widget"


def _launch_rss_widget(window, api: dict[str, object]) -> None:
    entry_command = api.get("entry_command")
    run_bg = api.get("run_bg")
    command: list[str] = []
    if callable(entry_command):
        try:
            command = list(entry_command(RSS_WIDGET_APP))
        except Exception:
            command = []
    if not command:
        command = ["python3", str(RSS_WIDGET_APP)]
    if callable(run_bg):
        try:
            run_bg(command)
        except Exception:
            pass
    status = getattr(window, "rss_plugin_status", None)
    if isinstance(status, QLabel):
        status.setText("RSS reader launched from plugin.")


def build_rss_service_section(window, api: dict[str, object]) -> QWidget:
    SettingsRow = api["SettingsRow"]
    SwitchButton = api["SwitchButton"]
    ExpandableServiceSection = api["ExpandableServiceSection"]
    material_icon = api["material_icon"]
    icon_path = str(api.get("plugin_icon_path", "")).strip()

    services = window.settings_state.setdefault("services", {})
    service = services.setdefault(
        SERVICE_KEY,
        {
            "enabled": True,
            "show_in_notification_center": False,
            "show_in_bar": False,
        },
    )
    rss_state = window.settings_state.setdefault("rss", {})
    rss_state.setdefault("notify_new_items", True)
    rss_state.setdefault("play_notification_sound", False)

    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)

    display_switch = SwitchButton(bool(service.get("show_in_notification_center", False)))
    display_switch.toggledValue.connect(lambda enabled: window._set_service_notification_visibility(SERVICE_KEY, enabled))
    window.service_display_switches[SERVICE_KEY] = display_switch
    layout.addWidget(
        SettingsRow(
            material_icon("widgets"),
            "Show in notification center",
            "Expose RSS plugin controls in the notification center when available.",
            window.icon_font,
            window.ui_font,
            display_switch,
        )
    )

    bar_switch = SwitchButton(bool(service.get("show_in_bar", False)))
    bar_switch.toggledValue.connect(lambda enabled: window._set_service_bar_visibility(SERVICE_KEY, enabled))
    layout.addWidget(
        SettingsRow(
            material_icon("public"),
            "Show on bar",
            "Show the RSS launcher icon on the bar.",
            window.icon_font,
            window.ui_font,
            bar_switch,
        )
    )

    notify_switch = SwitchButton(bool(rss_state.get("notify_new_items", True)))
    notify_switch.toggledValue.connect(lambda enabled: _set_rss_value(window, "notify_new_items", bool(enabled), "RSS new item notifications updated."))
    layout.addWidget(
        SettingsRow(
            material_icon("notifications"),
            "Notify on new stories",
            "Send desktop notifications when new entries arrive from your feeds.",
            window.icon_font,
            window.ui_font,
            notify_switch,
        )
    )

    sound_switch = SwitchButton(bool(rss_state.get("play_notification_sound", False)))
    sound_switch.toggledValue.connect(
        lambda enabled: _set_rss_value(window, "play_notification_sound", bool(enabled), "RSS notification sound preference saved.")
    )
    layout.addWidget(
        SettingsRow(
            material_icon("volume_up"),
            "Play notification sound",
            "Play a short sound when new RSS entries are detected.",
            window.icon_font,
            window.ui_font,
            sound_switch,
        )
    )

    open_button = QPushButton("Open RSS Reader")
    open_button.setObjectName("secondaryButton")
    open_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    open_button.clicked.connect(lambda: _launch_rss_widget(window, api))
    layout.addWidget(
        SettingsRow(
            material_icon("open_in_new"),
            "Open full app",
            "Launch the plugin RSS reader window.",
            window.icon_font,
            window.ui_font,
            open_button,
        )
    )

    window.rss_plugin_status = QLabel("RSS is now delivered as a plugin.")
    window.rss_plugin_status.setWordWrap(True)
    window.rss_plugin_status.setStyleSheet("color: rgba(246,235,247,0.72);")
    layout.addWidget(window.rss_plugin_status)

    section = ExpandableServiceSection(
        SERVICE_KEY,
        "RSS",
        "Read and track feeds from a decoupled Hanauta plugin.",
        "?",
        window.icon_font,
        window.ui_font,
        content,
        window._service_enabled(SERVICE_KEY),
        lambda enabled: window._set_service_enabled(SERVICE_KEY, enabled),
        icon_path=icon_path,
    )
    window.service_sections[SERVICE_KEY] = section
    return section


def _set_rss_value(window, key: str, value: object, status: str) -> None:
    rss_state = window.settings_state.setdefault("rss", {})
    rss_state[key] = value
    window._save_settings()
    label = getattr(window, "rss_plugin_status", None)
    if isinstance(label, QLabel):
        label.setText(status)


def register_hanauta_plugin() -> dict[str, object]:
    return {
        "id": SERVICE_KEY,
        "name": "RSS",
        "api_min_version": 1,
        "service_sections": [
            {
                "key": SERVICE_KEY,
                "builder": build_rss_service_section,
            }
        ],
    }
