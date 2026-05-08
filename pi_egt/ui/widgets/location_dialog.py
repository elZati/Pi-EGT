from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)

from pi_egt.network.weather import search_location


class LocationDialog(QDialog):
    """
    Search for a city via Open-Meteo geocoding and return the selected location dict.
    Access result via .selected_location after exec_() returns Accepted.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Select Weather Location')
        self.setMinimumWidth(420)
        self.selected_location: dict | None = None
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)

        # Search row
        row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText('City name…')
        self._input.returnPressed.connect(self._search)
        row.addWidget(self._input)
        search_btn = QPushButton('Search')
        search_btn.clicked.connect(self._search)
        row.addWidget(search_btn)
        root.addLayout(row)

        # Status
        self._status = QLabel('')
        self._status.setStyleSheet('color:#888; font-size:10px;')
        root.addWidget(self._status)

        # Results
        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._accept_selection)
        root.addWidget(self._list)

        # OK / Cancel
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_selection)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _search(self) -> None:
        name = self._input.text().strip()
        if not name:
            return
        self._status.setText('Searching…')
        self._list.clear()
        try:
            results = search_location(name)
        except Exception as exc:
            self._status.setText(f'Error: {exc}')
            return

        if not results:
            self._status.setText('No results found.')
            return

        self._status.setText(f'{len(results)} result(s) found.')
        for r in results:
            parts = [r.get('name', '')]
            if r.get('admin1'):
                parts.append(r['admin1'])
            if r.get('country'):
                parts.append(r['country'])
            label = ', '.join(p for p in parts if p)
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, {
                'name': label,
                'lat': float(r['latitude']),
                'lon': float(r['longitude']),
            })
            self._list.addItem(item)

    def _accept_selection(self) -> None:
        item = self._list.currentItem()
        if item:
            self.selected_location = item.data(Qt.UserRole)
            self.accept()
