from __future__ import annotations

import sys

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication

from pi_egt import config
from pi_egt.ui.main_window import MainWindow


def _dark_palette() -> QPalette:
    pal = QPalette()
    pal.setColor(QPalette.Window,          QColor('#0d0d1a'))
    pal.setColor(QPalette.WindowText,      QColor('#ffffff'))
    pal.setColor(QPalette.Base,            QColor('#16213e'))
    pal.setColor(QPalette.AlternateBase,   QColor('#0f3460'))
    pal.setColor(QPalette.ToolTipBase,     QColor('#ffffff'))
    pal.setColor(QPalette.ToolTipText,     QColor('#ffffff'))
    pal.setColor(QPalette.Text,            QColor('#ffffff'))
    pal.setColor(QPalette.Button,          QColor('#16213e'))
    pal.setColor(QPalette.ButtonText,      QColor('#ffffff'))
    pal.setColor(QPalette.BrightText,      QColor('#e74c3c'))
    pal.setColor(QPalette.Link,            QColor('#3498db'))
    pal.setColor(QPalette.Highlight,       QColor('#e74c3c'))
    pal.setColor(QPalette.HighlightedText, QColor('#ffffff'))
    # Disabled state
    pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor('#555555'))
    pal.setColor(QPalette.Disabled, QPalette.Text,       QColor('#555555'))
    pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor('#555555'))
    return pal


def main() -> None:
    if '--mock' in sys.argv:
        config.MOCK_SENSORS = True
        sys.argv.remove('--mock')

    app = QApplication(sys.argv)
    app.setApplicationName('Pi-EGT')
    app.setStyle('Fusion')
    app.setPalette(_dark_palette())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
