#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

PLUGIN_ROOT = Path(__file__).resolve().parent
RSS_WIDGET_APP = PLUGIN_ROOT / "rss_widget.py"
SERVICE_KEY = "rss_widget"


def _save_settings(window) -> None:
    module = sys.modules.get(window.__class__.__module__)
    save_function = getattr(module, "save_settings_state", None) if module is not None else None
    if callable(save_function):
        save_function(window.settings_state)
        return
    callback = getattr(window, "_save_settings", None)
    if callable(callback):
        callback()


def _service_state(window) -> dict:
    services = window.settings_state.setdefault("services", {})
    service = services.setdefault(
        SERVICE_KEY,
        {
            "enabled": True,
            "show_in_notification_center": False,
            "show_in_bar": False,
        },
    )
    return service if isinstance(service, dict) else {}


def _rss_state(window) -> dict:
    rss = window.settings_state.setdefault("rss", {})
    if not isinstance(rss, dict):
        rss = {}
        window.settings_state["rss"] = rss
    rss.setdefault("feeds", [])
    rss.setdefault("notify_new_items", True)
    rss.setdefault("play_notification_sound", False)
    rss.setdefault("check_interval_minutes", 15)
    rss.setdefault("item_limit", 10)
    rss.setdefault("opml_source", "")
    rss.setdefault("username", "")
    rss.setdefault("password", "")
    return rss


def _normalized_feeds(rss: dict) -> list[dict[str, str]]:
    feeds = rss.get("feeds", [])
    if not isinstance(feeds, list):
        return []
    normalized: list[dict[str, str]] = []
    for item in feeds:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url", "")).strip()
        if not url:
            continue
        name = str(item.get("name", "")).strip() or url
        normalized.append({"name": name, "url": url})
    return normalized


def _persist_feeds(window, feeds: list[dict[str, str]], status_label: QLabel, message: str) -> None:
    rss = _rss_state(window)
    rss["feeds"] = feeds
    _save_settings(window)
    status_label.setText(message)


def _refresh_feed_list(feed_list: QListWidget, feeds: list[dict[str, str]]) -> None:
    feed_list.clear()
    for feed in feeds:
        name = str(feed.get("name", "")).strip()
        url = str(feed.get("url", "")).strip()
        item = QListWidgetItem(f"{name}\n{url}")
        item.setData(Qt.ItemDataRole.UserRole, {"name": name, "url": url})
        feed_list.addItem(item)


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

    service = _service_state(window)
    rss = _rss_state(window)
    feeds = _normalized_feeds(rss)

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

    notify_switch = SwitchButton(bool(rss.get("notify_new_items", True)))
    notify_switch.toggledValue.connect(lambda enabled: _set_rss_value(window, "notify_new_items", bool(enabled), status_label, "RSS notifications updated."))
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

    sound_switch = SwitchButton(bool(rss.get("play_notification_sound", False)))
    sound_switch.toggledValue.connect(
        lambda enabled: _set_rss_value(window, "play_notification_sound", bool(enabled), status_label, "RSS sound preference saved.")
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

    interval_spin = QSpinBox()
    interval_spin.setRange(5, 180)
    interval_spin.setValue(int(rss.get("check_interval_minutes", 15) or 15))
    interval_spin.valueChanged.connect(
        lambda value: _set_rss_value(window, "check_interval_minutes", int(value), status_label, f"RSS refresh interval: {int(value)} minute(s).")
    )
    layout.addWidget(
        SettingsRow(
            material_icon("schedule"),
            "Refresh interval (min)",
            "How often feed updates are checked.",
            window.icon_font,
            window.ui_font,
            interval_spin,
        )
    )

    item_limit_spin = QSpinBox()
    item_limit_spin.setRange(3, 50)
    item_limit_spin.setValue(int(rss.get("item_limit", 10) or 10))
    item_limit_spin.valueChanged.connect(
        lambda value: _set_rss_value(window, "item_limit", int(value), status_label, f"RSS item limit: {int(value)}.")
    )
    layout.addWidget(
        SettingsRow(
            material_icon("list"),
            "Maximum stories",
            "How many stories should be shown in RSS views.",
            window.icon_font,
            window.ui_font,
            item_limit_spin,
        )
    )

    feed_name = QLineEdit()
    feed_name.setPlaceholderText("Feed display name (optional)")
    feed_url = QLineEdit()
    feed_url.setPlaceholderText("https://example.com/feed.xml")

    feed_list = QListWidget()
    feed_list.setObjectName("rssFeedList")
    feed_list.setMinimumHeight(200)
    feed_list.setStyleSheet(
        """
        QListWidget#rssFeedList {
            background-color: rgba(24, 28, 36, 0.94);
            border: 1px solid rgba(140, 152, 178, 0.34);
            border-radius: 12px;
            color: rgba(241, 244, 255, 0.96);
            padding: 4px;
        }
        QListWidget#rssFeedList::item {
            background-color: rgba(34, 40, 52, 0.88);
            border: 1px solid rgba(140, 152, 178, 0.24);
            border-radius: 9px;
            padding: 8px;
            margin: 4px;
        }
        QListWidget#rssFeedList::item:selected {
            background-color: rgba(87, 129, 255, 0.28);
            border: 1px solid rgba(122, 160, 255, 0.68);
        }
        """
    )
    _refresh_feed_list(feed_list, feeds)

    action_row = QHBoxLayout()
    action_row.setContentsMargins(0, 0, 0, 0)
    action_row.setSpacing(8)

    add_button = QPushButton("Add feed")
    add_button.setObjectName("secondaryButton")
    add_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    action_row.addWidget(add_button)

    clear_form_button = QPushButton("Clear form")
    clear_form_button.setObjectName("secondaryButton")
    clear_form_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    action_row.addWidget(clear_form_button)

    remove_button = QPushButton("Remove selected")
    remove_button.setObjectName("secondaryButton")
    remove_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    action_row.addWidget(remove_button)

    move_up_button = QPushButton("Move up")
    move_up_button.setObjectName("secondaryButton")
    move_up_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    action_row.addWidget(move_up_button)

    move_down_button = QPushButton("Move down")
    move_down_button.setObjectName("secondaryButton")
    move_down_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    action_row.addWidget(move_down_button)

    form_wrap = QWidget()
    form_layout = QVBoxLayout(form_wrap)
    form_layout.setContentsMargins(0, 0, 0, 0)
    form_layout.setSpacing(8)
    form_layout.addWidget(feed_name)
    form_layout.addWidget(feed_url)
    form_layout.addLayout(action_row)
    layout.addWidget(form_wrap)
    layout.addWidget(feed_list)

    bulk_urls = QTextEdit()
    bulk_urls.setPlaceholderText("Paste one URL per line (or comma-separated) to import feeds in bulk.")
    bulk_urls.setFixedHeight(90)
    import_button = QPushButton("Import URLs in bulk")
    import_button.setObjectName("secondaryButton")
    import_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    layout.addWidget(bulk_urls)
    layout.addWidget(import_button)

    opml_input = QLineEdit(str(rss.get("opml_source", "")).strip())
    opml_input.setPlaceholderText("Optional OPML source URL")
    opml_input.editingFinished.connect(
        lambda: _set_rss_value(window, "opml_source", opml_input.text().strip(), status_label, "OPML source updated.")
    )
    layout.addWidget(
        SettingsRow(
            material_icon("link"),
            "OPML source",
            "Optional remote OPML URL for syncing feeds.",
            window.icon_font,
            window.ui_font,
            opml_input,
        )
    )

    username_input = QLineEdit(str(rss.get("username", "")).strip())
    username_input.setPlaceholderText("Optional username")
    password_input = QLineEdit(str(rss.get("password", "")))
    password_input.setPlaceholderText("Optional password")
    password_input.setEchoMode(QLineEdit.EchoMode.Password)

    def save_credentials() -> None:
        _set_rss_value(window, "username", username_input.text().strip(), status_label, "RSS credentials updated.")
        _set_rss_value(window, "password", password_input.text(), status_label, "RSS credentials updated.")

    username_input.editingFinished.connect(save_credentials)
    password_input.editingFinished.connect(save_credentials)
    creds_wrap = QWidget()
    creds_layout = QVBoxLayout(creds_wrap)
    creds_layout.setContentsMargins(0, 0, 0, 0)
    creds_layout.setSpacing(8)
    creds_layout.addWidget(username_input)
    creds_layout.addWidget(password_input)
    layout.addWidget(
        SettingsRow(
            material_icon("key"),
            "Feed credentials",
            "Used for authenticated feeds and OPML endpoints.",
            window.icon_font,
            window.ui_font,
            creds_wrap,
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

    status_label = QLabel("RSS plugin is ready. Add feeds below.")
    status_label.setWordWrap(True)
    status_label.setStyleSheet("color: rgba(246,235,247,0.72);")
    window.rss_plugin_status = status_label
    layout.addWidget(status_label)

    def _current_feeds() -> list[dict[str, str]]:
        return _normalized_feeds(_rss_state(window))

    def _reload_with_selection(selected_index: int = -1) -> None:
        rows = _current_feeds()
        _refresh_feed_list(feed_list, rows)
        if selected_index >= 0 and selected_index < feed_list.count():
            feed_list.setCurrentRow(selected_index)

    def _clear_form() -> None:
        feed_name.clear()
        feed_url.clear()
        feed_list.clearSelection()
        add_button.setText("Add feed")

    def _select_feed(item: QListWidgetItem | None) -> None:
        if item is None:
            return
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict):
            return
        feed_name.setText(str(payload.get("name", "")).strip())
        feed_url.setText(str(payload.get("url", "")).strip())
        add_button.setText("Update feed")

    def _upsert_feed() -> None:
        url = feed_url.text().strip()
        name = feed_name.text().strip() or url
        if not url:
            status_label.setText("Feed URL is required.")
            return
        rows = _current_feeds()
        selected = feed_list.currentRow()
        existing_index = -1
        for idx, row in enumerate(rows):
            if str(row.get("url", "")).strip() == url:
                existing_index = idx
                break
        target_index = selected if 0 <= selected < len(rows) else existing_index
        payload = {"name": name, "url": url}
        if 0 <= target_index < len(rows):
            rows[target_index] = payload
            _persist_feeds(window, rows, status_label, f"Updated feed: {name}")
            _reload_with_selection(target_index)
        else:
            rows.append(payload)
            _persist_feeds(window, rows, status_label, f"Added feed: {name}")
            _reload_with_selection(len(rows) - 1)
        _clear_form()

    def _remove_selected() -> None:
        selected = feed_list.currentRow()
        rows = _current_feeds()
        if selected < 0 or selected >= len(rows):
            status_label.setText("Select a feed to remove.")
            return
        removed = rows.pop(selected)
        _persist_feeds(window, rows, status_label, f"Removed feed: {removed.get('name', 'Feed')}")
        _reload_with_selection(min(selected, len(rows) - 1))

    def _move_selected(step: int) -> None:
        selected = feed_list.currentRow()
        rows = _current_feeds()
        target = selected + step
        if selected < 0 or selected >= len(rows) or target < 0 or target >= len(rows):
            return
        rows[selected], rows[target] = rows[target], rows[selected]
        _persist_feeds(window, rows, status_label, "Feed order updated.")
        _reload_with_selection(target)

    def _import_bulk() -> None:
        raw = bulk_urls.toPlainText().strip()
        if not raw:
            status_label.setText("Paste at least one URL to import.")
            return
        tokens = [token.strip() for chunk in raw.splitlines() for token in chunk.split(",")]
        urls = [token for token in tokens if token]
        if not urls:
            status_label.setText("No valid URLs found in bulk input.")
            return
        rows = _current_feeds()
        existing = {str(row.get("url", "")).strip() for row in rows}
        added = 0
        for url in urls:
            if url in existing:
                continue
            rows.append({"name": url, "url": url})
            existing.add(url)
            added += 1
        _persist_feeds(window, rows, status_label, f"Imported {added} new feed(s).")
        _reload_with_selection(feed_list.count() - 1)
        bulk_urls.clear()

    feed_list.currentItemChanged.connect(_select_feed)
    add_button.clicked.connect(_upsert_feed)
    clear_form_button.clicked.connect(_clear_form)
    remove_button.clicked.connect(_remove_selected)
    move_up_button.clicked.connect(lambda: _move_selected(-1))
    move_down_button.clicked.connect(lambda: _move_selected(1))
    import_button.clicked.connect(_import_bulk)

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


def _set_rss_value(window, key: str, value: object, status_label: QLabel, message: str) -> None:
    rss = _rss_state(window)
    rss[key] = value
    _save_settings(window)
    status_label.setText(message)


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
