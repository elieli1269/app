#!/usr/bin/env python3
"""
MoodSync Browser — Navigateur desktop pour MoodSync
Développé avec PyQt6 + QtWebEngine
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTabWidget, QTabBar,
    QStatusBar, QToolBar, QSizePolicy, QFrame, QProgressBar,
    QMenu, QDialog, QTextEdit
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtCore import QUrl, Qt, QSize, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QIcon, QFont, QPalette, QColor, QKeySequence,
    QShortcut, QPixmap, QPainter, QLinearGradient, QBrush
)

# ─── Config ─────────────────────────────────────────────────────────────────

HOME_URL = "https://moodsync.alwaysdata.net"

COLORS = {
    "bg":         "#0f0f13",
    "surface":    "#1a1a22",
    "surface2":   "#22222e",
    "border":     "#2e2e3f",
    "accent":     "#7c5cfc",
    "accent2":    "#a78bfa",
    "accent_glow":"rgba(124,92,252,0.3)",
    "text":       "#e8e6f0",
    "text_dim":   "#8882a0",
    "danger":     "#f87171",
    "success":    "#34d399",
    "tab_active": "#1e1e2c",
}

STYLE = f"""
QMainWindow, QWidget {{
    background: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', 'SF Pro Display', Ubuntu, sans-serif;
}}

/* ── Barre d'onglets ── */
QTabWidget::pane {{
    border: none;
    background: {COLORS['bg']};
}}
QTabBar::tab {{
    background: {COLORS['surface']};
    color: {COLORS['text_dim']};
    padding: 8px 16px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
    min-width: 140px;
    max-width: 220px;
    font-size: 12px;
}}
QTabBar::tab:selected {{
    background: {COLORS['tab_active']};
    color: {COLORS['text']};
    border-bottom: 2px solid {COLORS['accent']};
}}
QTabBar::tab:hover:!selected {{
    background: {COLORS['surface2']};
    color: {COLORS['text']};
}}
QTabBar::close-button {{
    subcontrol-position: right;
}}

/* ── Barre d'adresse ── */
QLineEdit#urlbar {{
    background: {COLORS['surface2']};
    border: 1.5px solid {COLORS['border']};
    border-radius: 20px;
    padding: 6px 16px;
    color: {COLORS['text']};
    font-size: 13px;
    selection-background-color: {COLORS['accent']};
}}
QLineEdit#urlbar:focus {{
    border-color: {COLORS['accent']};
    background: {COLORS['surface']};
}}

/* ── Boutons nav ── */
QPushButton.navbtn {{
    background: {COLORS['surface2']};
    border: none;
    border-radius: 18px;
    color: {COLORS['text']};
    font-size: 16px;
    min-width: 36px;
    min-height: 36px;
    max-width: 36px;
    max-height: 36px;
}}
QPushButton.navbtn:hover {{
    background: {COLORS['border']};
    color: {COLORS['accent2']};
}}
QPushButton.navbtn:pressed {{
    background: {COLORS['accent']};
    color: white;
}}
QPushButton.navbtn:disabled {{
    color: {COLORS['border']};
}}

/* ── Bouton nouvel onglet ── */
QPushButton#newtab {{
    background: transparent;
    border: 1.5px solid {COLORS['border']};
    border-radius: 14px;
    color: {COLORS['text_dim']};
    font-size: 18px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
}}
QPushButton#newtab:hover {{
    background: {COLORS['surface2']};
    border-color: {COLORS['accent']};
    color: {COLORS['accent2']};
}}

/* ── Progress bar ── */
QProgressBar {{
    background: transparent;
    border: none;
    height: 2px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {COLORS['accent']}, stop:1 {COLORS['accent2']});
    border-radius: 1px;
}}

/* ── Status bar ── */
QStatusBar {{
    background: {COLORS['surface']};
    color: {COLORS['text_dim']};
    font-size: 11px;
    border-top: 1px solid {COLORS['border']};
}}

/* ── Menu ── */
QMenu {{
    background: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 4px;
    color: {COLORS['text']};
}}
QMenu::item {{
    padding: 8px 20px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {COLORS['accent']};
    color: white;
}}
QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 4px 0;
}}

/* ── Toolbar ── */
QToolBar {{
    background: {COLORS['surface']};
    border-bottom: 1px solid {COLORS['border']};
    spacing: 4px;
    padding: 4px 8px;
}}

/* ── Frame séparateur ── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {COLORS['border']};
}}
"""


# ─── WebView avec page personnalisée ────────────────────────────────────────

class MoodSyncPage(QWebEnginePage):
    def __init__(self, parent=None):
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        super().__init__(profile, parent)

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        pass  # Silence les logs JS


class BrowserTab(QWebEngineView):
    title_changed = pyqtSignal(str)
    favicon_changed = pyqtSignal(QIcon)
    load_progress = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        page = MoodSyncPage(self)
        self.setPage(page)

        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly, False)

        self.titleChanged.connect(self.title_changed)
        self.iconChanged.connect(self.favicon_changed)
        self.loadProgress.connect(self.load_progress)


# ─── Onglet avec URL bar intégrée ───────────────────────────────────────────

class TabPage(QWidget):
    def __init__(self, url: str, main_win, parent=None):
        super().__init__(parent)
        self.main_win = main_win

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(2)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.webview = BrowserTab(self)
        layout.addWidget(self.webview)

        self.webview.load_progress.connect(self._on_progress)
        self.webview.loadFinished.connect(self._on_loaded)
        self.webview.titleChanged.connect(self._on_title)
        self.webview.urlChanged.connect(self._on_url)

        self.webview.load(QUrl(url))

    def _on_progress(self, val):
        self.progress.setValue(val)
        self.progress.setVisible(val < 100)

    def _on_loaded(self, ok):
        self.progress.setVisible(False)
        self.main_win.update_nav_state()

    def _on_title(self, title):
        idx = self.main_win.tabs.indexOf(self)
        if idx >= 0:
            short = (title[:22] + "…") if len(title) > 24 else title
            self.main_win.tabs.setTabText(idx, short or "Nouvel onglet")
            self.main_win.tabs.setTabToolTip(idx, title)

    def _on_url(self, url):
        if self.main_win.current_tab() is self:
            self.main_win.urlbar.setText(url.toString())
            self.main_win.update_nav_state()


# ─── Fenêtre principale ──────────────────────────────────────────────────────

class MoodSyncBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MoodSync")
        self.resize(1280, 820)
        self._setup_ui()
        self._setup_shortcuts()
        self.new_tab(HOME_URL)

    # ── UI ──────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setStyleSheet(STYLE)
        self.setMinimumSize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(10, 6, 10, 6)
        tl.setSpacing(6)

        # Logo MoodSync
        logo = QLabel("🎵")
        logo.setFont(QFont("", 18))
        logo.setFixedWidth(32)
        tl.addWidget(logo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        tl.addWidget(sep)

        # Boutons navigation
        self.btn_back    = self._nav_btn("‹",  "Précédent (Alt+←)")
        self.btn_forward = self._nav_btn("›",  "Suivant (Alt+→)")
        self.btn_reload  = self._nav_btn("↻",  "Recharger (F5)")
        self.btn_home    = self._nav_btn("⌂",  "Accueil")

        for btn in (self.btn_back, self.btn_forward, self.btn_reload, self.btn_home):
            tl.addWidget(btn)

        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward.clicked.connect(self._go_forward)
        self.btn_reload.clicked.connect(self._reload)
        self.btn_home.clicked.connect(self._go_home)

        tl.addSpacing(4)

        # Barre d'adresse
        self.urlbar = QLineEdit()
        self.urlbar.setObjectName("urlbar")
        self.urlbar.setPlaceholderText("Entrez une URL ou cherchez sur le web…")
        self.urlbar.returnPressed.connect(self._navigate)
        tl.addWidget(self.urlbar, 1)

        tl.addSpacing(4)

        # Boutons droite
        self.btn_mute  = self._nav_btn("🔊", "Couper le son")
        self.btn_devtools = self._nav_btn("🛠", "DevTools (F12)")
        self.btn_menu  = self._nav_btn("⋮",  "Menu")

        self.btn_mute.clicked.connect(self._toggle_mute)
        self.btn_devtools.clicked.connect(self._open_devtools)
        self.btn_menu.clicked.connect(self._show_menu)

        for btn in (self.btn_mute, self.btn_devtools, self.btn_menu):
            tl.addWidget(btn)

        main_layout.addWidget(toolbar)

        # ── Onglets ──────────────────────────────────────────────────────────
        tabs_bar = QWidget()
        tabs_bar.setStyleSheet(f"""
            QWidget {{
                background: {COLORS['bg']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        tabs_layout = QHBoxLayout(tabs_bar)
        tabs_layout.setContentsMargins(8, 0, 8, 0)
        tabs_layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._tab_switched)

        # Bouton "+"
        self.btn_newtab = QPushButton("+")
        self.btn_newtab.setObjectName("newtab")
        self.btn_newtab.setFont(QFont("", 14, QFont.Weight.Bold))
        self.btn_newtab.clicked.connect(lambda: self.new_tab(HOME_URL))
        self.tabs.setCornerWidget(self.btn_newtab, Qt.Corner.TopRightCorner)

        main_layout.addWidget(self.tabs)

        # ── Status bar ───────────────────────────────────────────────────────
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.setFixedHeight(22)

        # Indicateur de connexion
        self.conn_label = QLabel("● MoodSync")
        self.conn_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 11px; padding-right: 8px;")
        self.statusbar.addPermanentWidget(self.conn_label)

        self._muted = False

    def _nav_btn(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "navbtn")
        btn.setToolTip(tooltip)
        btn.setFont(QFont("", 14))
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['surface2']};
                border: none;
                border-radius: 18px;
                color: {COLORS['text']};
                font-size: 15px;
                min-width: 36px; min-height: 36px;
                max-width: 36px; max-height: 36px;
            }}
            QPushButton:hover {{
                background: {COLORS['border']};
                color: {COLORS['accent2']};
            }}
            QPushButton:pressed {{
                background: {COLORS['accent']};
                color: white;
            }}
            QPushButton:disabled {{
                color: {COLORS['border']};
                background: transparent;
            }}
        """)
        return btn

    # ── Onglets ──────────────────────────────────────────────────────────────

    def new_tab(self, url: str = HOME_URL):
        page = TabPage(url, self)
        idx = self.tabs.addTab(page, "Chargement…")
        self.tabs.setCurrentIndex(idx)
        self.urlbar.setText(url)
        self.urlbar.setFocus()

    def current_tab(self) -> TabPage | None:
        return self.tabs.currentWidget()

    def _close_tab(self, idx: int):
        if self.tabs.count() <= 1:
            self.close()
            return
        widget = self.tabs.widget(idx)
        self.tabs.removeTab(idx)
        if widget:
            widget.deleteLater()

    def _tab_switched(self, idx: int):
        tab = self.tabs.widget(idx)
        if isinstance(tab, TabPage):
            url = tab.webview.url().toString()
            self.urlbar.setText(url)
            self.update_nav_state()

    # ── Navigation ───────────────────────────────────────────────────────────

    def _navigate(self):
        text = self.urlbar.text().strip()
        if not text:
            return
        if "." in text and " " not in text and not text.startswith("http"):
            url = "https://" + text
        elif text.startswith("http"):
            url = text
        else:
            url = f"https://www.google.com/search?q={text}"
        tab = self.current_tab()
        if tab:
            tab.webview.load(QUrl(url))

    def _go_back(self):
        if tab := self.current_tab():
            tab.webview.back()

    def _go_forward(self):
        if tab := self.current_tab():
            tab.webview.forward()

    def _reload(self):
        if tab := self.current_tab():
            tab.webview.reload()

    def _go_home(self):
        if tab := self.current_tab():
            tab.webview.load(QUrl(HOME_URL))

    def update_nav_state(self):
        tab = self.current_tab()
        if tab:
            self.btn_back.setEnabled(tab.webview.history().canGoBack())
            self.btn_forward.setEnabled(tab.webview.history().canGoForward())

    # ── Actions ──────────────────────────────────────────────────────────────

    def _toggle_mute(self):
        tab = self.current_tab()
        if not tab:
            return
        self._muted = not self._muted
        tab.webview.page().setAudioMuted(self._muted)
        self.btn_mute.setText("🔇" if self._muted else "🔊")

    def _open_devtools(self):
        tab = self.current_tab()
        if not tab:
            return
        devtools = QWebEngineView()
        tab.webview.page().setDevToolsPage(devtools.page())
        devtools.resize(900, 600)
        devtools.setWindowTitle("DevTools — MoodSync")
        devtools.show()
        self._devtools_win = devtools

    def _show_menu(self):
        menu = QMenu(self)
        menu.addAction("🏠  Accueil MoodSync",      self._go_home)
        menu.addAction("➕  Nouvel onglet",          lambda: self.new_tab(HOME_URL))
        menu.addSeparator()
        menu.addAction("🔍  Zoom +",                 lambda: self._zoom(1.1))
        menu.addAction("🔍  Zoom −",                 lambda: self._zoom(0.9))
        menu.addAction("🔍  Zoom 100%",              lambda: self._zoom_reset())
        menu.addSeparator()
        menu.addAction("📄  Source de la page",      self._view_source)
        menu.addAction("🛠  Outils dev",              self._open_devtools)
        menu.addSeparator()
        menu.addAction("🚪  Quitter",                self.close)
        menu.exec(self.btn_menu.mapToGlobal(
            self.btn_menu.rect().bottomLeft()
        ))

    def _zoom(self, factor: float):
        if tab := self.current_tab():
            cur = tab.webview.zoomFactor()
            tab.webview.setZoomFactor(min(max(cur * factor, 0.25), 5.0))

    def _zoom_reset(self):
        if tab := self.current_tab():
            tab.webview.setZoomFactor(1.0)

    def _view_source(self):
        tab = self.current_tab()
        if not tab:
            return
        url = "view-source:" + tab.webview.url().toString()
        self.new_tab(url)

    # ── Raccourcis ───────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"),       self, lambda: self.new_tab(HOME_URL))
        QShortcut(QKeySequence("Ctrl+W"),       self, lambda: self._close_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Ctrl+L"),       self, lambda: (self.urlbar.setFocus(), self.urlbar.selectAll()))
        QShortcut(QKeySequence("F5"),           self, self._reload)
        QShortcut(QKeySequence("Ctrl+R"),       self, self._reload)
        QShortcut(QKeySequence("F12"),          self, self._open_devtools)
        QShortcut(QKeySequence("Alt+Left"),     self, self._go_back)
        QShortcut(QKeySequence("Alt+Right"),    self, self._go_forward)
        QShortcut(QKeySequence("Ctrl+Plus"),    self, lambda: self._zoom(1.1))
        QShortcut(QKeySequence("Ctrl+Minus"),   self, lambda: self._zoom(0.9))
        QShortcut(QKeySequence("Ctrl+0"),       self, self._zoom_reset)
        QShortcut(QKeySequence("Ctrl+Tab"),     self, self._next_tab)
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, self._prev_tab)

    def _next_tab(self):
        i = self.tabs.currentIndex()
        self.tabs.setCurrentIndex((i + 1) % self.tabs.count())

    def _prev_tab(self):
        i = self.tabs.currentIndex()
        self.tabs.setCurrentIndex((i - 1) % self.tabs.count())

    # ── Drag & Drop URL ──────────────────────────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.new_tab(urls[0].toString())


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    # Nécessaire pour certains GPU sous Linux
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu-driver-bug-workarounds --no-sandbox")

    app = QApplication(sys.argv)
    app.setApplicationName("MoodSync Browser")
    app.setApplicationVersion("1.0")

    # Palette sombre globale
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,       QColor(COLORS["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText,   QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Base,         QColor(COLORS["surface"]))
    palette.setColor(QPalette.ColorRole.Text,         QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Highlight,    QColor(COLORS["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    win = MoodSyncBrowser()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
