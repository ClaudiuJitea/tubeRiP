from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from tuberip.main_window import MainWindow
from tuberip.theme import app_icon, apply_theme


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv if argv is None else argv)
    app = QApplication(args)
    app.setApplicationName("tubeRiP")
    app.setOrganizationName("tubeRiP")
    app.setWindowIcon(app_icon())
    apply_theme(app)
    window = MainWindow()
    window.show()
    if len(args) > 1:
        window.download_page.set_urls("\n".join(args[1:]))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
