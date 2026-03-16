#!/usr/bin/env python3
"""
MoodSync Browser v2 — UI Chrome-like + connexion compte MoodSync
"""

import sys
import os
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTabWidget, QTabBar,
    QStatusBar, QSizePolicy, QFrame, QProgressBar,
    QMenu, QDialog, QGraphicsDropShadowEffect, QScrollArea,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineCookieStore
)
from PyQt6.QtCore import (
    QUrl, Qt, QSize, QTimer, pyqtSignal, QPoint, QRect
)
from PyQt6.QtGui import (
    QIcon, QFont, QPalette, QColor, QKeySequence,
    QShortcut, QPainter, QBrush, QPen, QCursor
)

HOME_URL    = "https://moodsync.alwaysdata.net"
LOGIN_URL   = "https://moodsync.alwaysdata.net/login.php"
PROFILE_URL = "https://moodsync.alwaysdata.net/profile.php"

C = {
    "chrome_bg":   "#202124",
    "chrome_light":"#35363a",
    "chrome_border":"#3c3c3f",
    "tab_bg":      "#292a2d",
    "tab_active":  "#202124",
    "content_bg":  "#1e1e1e",
    "urlbar_bg":   "#303134",
    "urlbar_focus":"#3c3c3f",
    "text":        "#e8eaed",
    "text_dim":    "#9aa0a6",
    "text_muted":  "#5f6368",
    "accent":      "#8ab4f8",
    "accent_ms":   "#a78bfa",
    "green":       "#81c995",
    "red":         "#f28b82",
    "avatar_bg":   "#4285f4",
}

CHROME_STYLE = f"""
* {{ font-family: 'Segoe UI', system-ui, sans-serif; font-size: 13px; }}
QMainWindow, QWidget#root {{ background: {C['content_bg']}; }}
QTabWidget::pane {{ border: none; background: {C['content_bg']}; margin-top: -1px; }}
QTabBar {{ background: {C['chrome_bg']}; }}
QTabBar::tab {{
    background: {C['tab_bg']}; color: {C['text_dim']};
    padding: 0 12px; height: 34px; min-width: 100px; max-width: 240px;
    border-right: 1px solid {C['chrome_border']};
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-size: 12px; margin-top: 6px;
}}
QTabBar::tab:selected {{
    background: {C['tab_active']}; color: {C['text']};
    margin-top: 4px; height: 36px; border-bottom: none;
}}
QTabBar::tab:hover:!selected {{ background: #2c2d30; color: {C['text']}; }}
QWidget#toolbar {{ background: {C['chrome_bg']}; border-bottom: 1px solid {C['chrome_border']}; }}
QLineEdit#urlbar {{
    background: transparent; border: none;
    color: {C['text']}; font-size: 14px; padding: 6px 0;
    selection-background-color: {C['accent']};
}}
QProgressBar {{ background: transparent; border: none; height: 3px; border-radius: 0; }}
QProgressBar::chunk {{ background: {C['accent']}; border-radius: 0; }}
QStatusBar {{
    background: {C['chrome_bg']}; color: {C['text_dim']};
    font-size: 11px; border-top: 1px solid {C['chrome_border']};
}}
QMenu {{
    background: #2d2e31; border: 1px solid {C['chrome_border']};
    border-radius: 8px; padding: 6px 0; color: {C['text']};
}}
QMenu::item {{ padding: 9px 20px 9px 14px; font-size: 13px; }}
QMenu::item:selected {{ background: {C['chrome_light']}; }}
QMenu::separator {{ height: 1px; background: {C['chrome_border']}; margin: 4px 0; }}
QMenu::item:disabled {{ color: {C['text_muted']}; }}
"""


class AvatarButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(30, 30)
        self._initials = "?"
        self._color = C["text_muted"]
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setToolTip("Compte MoodSync")
        self.setStyleSheet("border: none; background: transparent; padding: 0;")

    def set_user(self, name: str, color: str = None):
        parts = name.strip().split()
        self._initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()
        self._color = color or C["avatar_bg"]
        self.setToolTip(name)
        self.update()

    def set_logged_out(self):
        self._initials = "?"
        self._color = C["text_muted"]
        self.setToolTip("Se connecter")
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(self._color)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(1, 1, 28, 28)
        p.setPen(QColor("#ffffff"))
        p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        p.drawText(QRect(1, 1, 28, 28), Qt.AlignmentFlag.AlignCenter, self._initials)
        p.end()


class AccountPanel(QWidget):
    login_requested   = pyqtSignal()
    logout_requested  = pyqtSignal()
    profile_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setFixedWidth(300)
        self._logged_in = False
        self._username  = ""
        self._email     = ""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setStyleSheet(f"""
            QWidget {{
                background: #2d2e31;
                color: {C['text']};
                border-radius: 12px;
                font-family: 'Segoe UI', sans-serif;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
        self._build()

    def _clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build(self):
        self._clear()
        if self._logged_in:
            # Header gradient
            header = QWidget()
            header.setFixedHeight(100)
            header.setStyleSheet(f"""
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #1a1a2e, stop:1 #2a1a3e);
                border-radius: 12px 12px 0 0;
            """)
            hl = QHBoxLayout(header)
            hl.setContentsMargins(18, 16, 18, 16)
            hl.setSpacing(14)

            # Grand avatar
            av = AvatarButton()
            av.setFixedSize(56, 56)
            av.set_user(self._username, C["accent_ms"])
            av.setStyleSheet(f"""
                border: 2.5px solid {C['accent_ms']};
                border-radius: 28px;
                background: transparent; padding: 0;
            """)
            hl.addWidget(av)

            info = QVBoxLayout()
            info.setSpacing(3)
            lbl_name = QLabel(self._username)
            lbl_name.setStyleSheet(f"color: {C['text']}; font-size: 15px; font-weight: 600; background: transparent; border: none;")
            lbl_site = QLabel("moodsync.alwaysdata.net")
            lbl_site.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; background: transparent; border: none;")
            lbl_badge = QLabel("● Connecté")
            lbl_badge.setStyleSheet(f"color: {C['green']}; font-size: 11px; background: transparent; border: none;")
            info.addWidget(lbl_name)
            info.addWidget(lbl_site)
            info.addWidget(lbl_badge)
            hl.addLayout(info)
            self._layout.addWidget(header)

            # Séparateur
            self._sep()
            for icon, txt, fn in [
                ("👤", "Mon profil",     self.profile_requested.emit),
                ("🎵", "Ouvrir MoodSync", lambda: None),
            ]:
                self._layout.addWidget(self._row(icon, txt, fn))
            self._sep()
            self._layout.addWidget(self._row("🚪", "Se déconnecter", self.logout_requested.emit, danger=True))
            self._pad(8)
        else:
            self._pad(24)
            lbl = QLabel("🎵  MoodSync")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {C['accent_ms']}; font-size: 20px; font-weight: 700; border: none; background: transparent;")
            self._layout.addWidget(lbl)
            self._pad(8)
            sub = QLabel("Connecte-toi pour accéder\nà ton compte MoodSync")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sub.setStyleSheet(f"color: {C['text_dim']}; font-size: 12px; border: none; background: transparent;")
            self._layout.addWidget(sub)
            self._pad(16)

            btn = QPushButton("Se connecter")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C['accent_ms']};
                    color: white; border: none; border-radius: 20px;
                    padding: 10px 24px; font-size: 14px; font-weight: 600;
                    margin: 0 24px;
                }}
                QPushButton:hover {{ background: #9061fd; }}
                QPushButton:pressed {{ background: #6d42e0; }}
            """)
            btn.clicked.connect(self.login_requested.emit)
            btn.clicked.connect(self.close)
            self._layout.addWidget(btn)
            self._pad(20)

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setFixedHeight(1)
        f.setStyleSheet(f"background: {C['chrome_border']}; border: none;")
        self._layout.addWidget(f)

    def _pad(self, h: int):
        sp = QWidget()
        sp.setFixedHeight(h)
        sp.setStyleSheet("background: transparent;")
        self._layout.addWidget(sp)

    def _row(self, icon: str, txt: str, fn, danger=False):
        btn = QPushButton(f"  {icon}   {txt}")
        c = C["red"] if danger else C["text"]
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {c};
                border: none; text-align: left;
                padding: 11px 20px; font-size: 13px;
            }}
            QPushButton:hover {{ background: {C['chrome_light']}; }}
        """)
        btn.clicked.connect(fn)
        btn.clicked.connect(self.close)
        return btn

    def set_logged_in(self, name: str, email: str = ""):
        self._logged_in = True
        self._username  = name
        self._email     = email
        self._build()

    def set_logged_out(self):
        self._logged_in = False
        self._username  = ""
        self._build()

    def show_at(self, pos: QPoint):
        self.adjustSize()
        self.move(pos.x() - self.width() + 8, pos.y() + 4)
        self.show()
        self.raise_()


class SecurityIcon(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_secure(True)

    def set_secure(self, secure: bool):
        self.setText("🔒" if secure else "ℹ️")
        self.setToolTip("HTTPS sécurisé" if secure else "Connexion non sécurisée")


class MoodSyncPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def javaScriptConsoleMessage(self, *a):
        pass

    def createWindow(self, wintype):
        view = BrowserTab(self.parent())
        return view.page()


class BrowserTab(QWebEngineView):
    title_changed   = pyqtSignal(str)
    load_progress_s = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        profile = QWebEngineProfile("moodsync_v2", self)
        profile.setPersistentStoragePath(
            os.path.join(os.path.expanduser("~"), ".moodsync_browser")
        )
        profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
        )
        page = MoodSyncPage(profile, self)
        self.setPage(page)
        s = self.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        self.titleChanged.connect(self.title_changed)
        self.loadProgress.connect(self.load_progress_s)


class TabPage(QWidget):
    def __init__(self, url: str, main_win, parent=None):
        super().__init__(parent)
        self.main_win = main_win
        lo = QVBoxLayout(self)
        lo.setContentsMargins(0, 0, 0, 0)
        lo.setSpacing(0)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        self.progress.setRange(0, 100)
        lo.addWidget(self.progress)
        self.webview = BrowserTab(self)
        lo.addWidget(self.webview)
        self.webview.load_progress_s.connect(self._on_progress)
        self.webview.loadFinished.connect(self._on_loaded)
        self.webview.titleChanged.connect(self._on_title)
        self.webview.urlChanged.connect(self._on_url)
        self.webview.loadFinished.connect(self._check_login)
        self.webview.load(QUrl(url))

    def _on_progress(self, v):
        self.progress.setValue(v)
        self.progress.setVisible(v < 100)

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
            self.main_win._update_urlbar(url)
            self.main_win.update_nav_state()

    def _check_login(self):
        if self.main_win.current_tab() is self:
            js = """
            (function(){
                var s = document.querySelector('[data-username],[data-user-name]');
                if(s) return {name: s.getAttribute('data-username') || s.getAttribute('data-user-name')};
                var u = document.querySelector('.navbar-username,.user-name,#username-display,[class*="username"],[class*="user-name"]');
                if(u && u.textContent.trim()) return {name: u.textContent.trim()};
                var m = document.querySelector('meta[name="user-name"],meta[name="username"]');
                if(m) return {name: m.content};
                return null;
            })()
            """
            self.webview.page().runJavaScript(js, self.main_win._on_js_login)


class MoodSyncBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MoodSync")
        self.resize(1300, 840)
        self._account_panel = None
        self._user_info = {"logged_in": False, "name": ""}
        self._setup_ui()
        self._setup_shortcuts()
        self.new_tab(HOME_URL)
        self._login_timer = QTimer(self)
        self._login_timer.timeout.connect(self._tick_check_login)
        self._login_timer.start(3000)

    def _setup_ui(self):
        self.setStyleSheet(CHROME_STYLE)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        main = QVBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(52)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 7, 8, 7)
        tl.setSpacing(2)

        self.btn_back    = self._mkbtn("←", "Précédent (Alt+←)")
        self.btn_forward = self._mkbtn("→", "Suivant (Alt+→)")
        self.btn_reload  = self._mkbtn("↻", "Recharger (F5)")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_forward.clicked.connect(self._go_forward)
        self.btn_reload.clicked.connect(self._reload)
        for b in (self.btn_back, self.btn_forward, self.btn_reload):
            tl.addWidget(b)
        tl.addSpacing(4)

        # Omnibox
        omni = QWidget()
        omni.setStyleSheet(f"""
            QWidget {{
                background: {C['urlbar_bg']};
                border-radius: 22px;
            }}
            QWidget:focus-within {{
                background: {C['urlbar_focus']};
                outline: 1.5px solid {C['accent']};
            }}
        """)
        ol = QHBoxLayout(omni)
        ol.setContentsMargins(10, 0, 6, 0)
        ol.setSpacing(4)
        self.security_icon = SecurityIcon()
        ol.addWidget(self.security_icon)
        self.urlbar = QLineEdit()
        self.urlbar.setObjectName("urlbar")
        self.urlbar.setPlaceholderText("Chercher ou saisir une URL")
        self.urlbar.returnPressed.connect(self._navigate)
        ol.addWidget(self.urlbar, 1)
        self.btn_bookmark = self._mkbtn("☆", "Ajouter aux favoris", 28)
        ol.addWidget(self.btn_bookmark)
        tl.addWidget(omni, 1)
        tl.addSpacing(6)

        # Droite
        self.avatar_btn = AvatarButton()
        self.avatar_btn.clicked.connect(self._show_account_panel)
        tl.addWidget(self.avatar_btn)
        tl.addSpacing(2)
        self.btn_menu = self._mkbtn("⋮", "Paramètres et plus")
        self.btn_menu.clicked.connect(self._show_chrome_menu)
        tl.addWidget(self.btn_menu)

        main.addWidget(toolbar)

        # ── Tabs ─────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._tab_switched)

        btn_new = QPushButton("+")
        btn_new.setFixedSize(30, 30)
        btn_new.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {C['text_dim']}; font-size: 18px; border-radius: 15px;
            }}
            QPushButton:hover {{ background: {C['chrome_light']}; color: {C['text']}; }}
        """)
        btn_new.clicked.connect(lambda: self.new_tab(HOME_URL))
        self.tabs.setCornerWidget(btn_new, Qt.Corner.TopRightCorner)
        main.addWidget(self.tabs)

        # ── Status bar ───────────────────────────────────────────────────────
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.setFixedHeight(20)
        self.status_url = QLabel("")
        self.status_url.setStyleSheet(f"color: {C['text_dim']}; font-size: 11px; padding-left: 6px;")
        self.statusbar.addWidget(self.status_url, 1)
        self.conn_label = QLabel("Non connecté")
        self.conn_label.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; padding-right: 8px;")
        self.statusbar.addPermanentWidget(self.conn_label)

    def _mkbtn(self, text: str, tip: str, size: int = 34) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setFixedSize(size, size)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: {size//2}px;
                color: {C['text_dim']}; font-size: 16px; padding: 0;
            }}
            QPushButton:hover {{ background: {C['chrome_light']}; color: {C['text']}; }}
            QPushButton:pressed {{ background: #454649; }}
            QPushButton:disabled {{ color: {C['text_muted']}; }}
        """)
        return btn

    # ── Tabs ─────────────────────────────────────────────────────────────────

    def new_tab(self, url: str = HOME_URL):
        page = TabPage(url, self)
        idx  = self.tabs.addTab(page, "Nouveau onglet")
        self.tabs.setCurrentIndex(idx)
        self.urlbar.setText(url)

    def current_tab(self):
        return self.tabs.currentWidget()

    def _close_tab(self, idx: int):
        if self.tabs.count() <= 1:
            self.close()
            return
        w = self.tabs.widget(idx)
        self.tabs.removeTab(idx)
        if w:
            w.deleteLater()

    def _tab_switched(self, idx: int):
        tab = self.tabs.widget(idx)
        if isinstance(tab, TabPage):
            self._update_urlbar(tab.webview.url())
            self.update_nav_state()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _update_urlbar(self, url: QUrl):
        s = url.toString()
        self.urlbar.setText(s)
        self.security_icon.set_secure(s.startswith("https://"))

    def _navigate(self):
        text = self.urlbar.text().strip()
        if not text:
            return
        if text.startswith("http"):
            url = text
        elif "." in text and " " not in text:
            url = "https://" + text
        else:
            url = f"https://www.google.com/search?q={text}"
        if tab := self.current_tab():
            tab.webview.load(QUrl(url))

    def update_nav_state(self):
        if tab := self.current_tab():
            self.btn_back.setEnabled(tab.webview.history().canGoBack())
            self.btn_forward.setEnabled(tab.webview.history().canGoForward())

    def _go_back(self):
        if t := self.current_tab(): t.webview.back()

    def _go_forward(self):
        if t := self.current_tab(): t.webview.forward()

    def _reload(self):
        if t := self.current_tab(): t.webview.reload()

    # ── Compte ────────────────────────────────────────────────────────────────

    def _show_account_panel(self):
        if self._account_panel is None:
            self._account_panel = AccountPanel(self)
            self._account_panel.login_requested.connect(self._do_login)
            self._account_panel.logout_requested.connect(self._do_logout)
            self._account_panel.profile_requested.connect(lambda: self.new_tab(PROFILE_URL))
        if self._user_info["logged_in"]:
            self._account_panel.set_logged_in(self._user_info["name"])
        else:
            self._account_panel.set_logged_out()
        gp = self.avatar_btn.mapToGlobal(self.avatar_btn.rect().bottomRight())
        self._account_panel.show_at(gp)

    def _do_login(self):
        if self._account_panel:
            self._account_panel.close()
        self.new_tab(LOGIN_URL)

    def _do_logout(self):
        self._user_info = {"logged_in": False, "name": ""}
        self.avatar_btn.set_logged_out()
        self._refresh_conn_label()
        if t := self.current_tab():
            t.webview.page().profile().cookieStore().deleteAllCookies()
        self.new_tab(HOME_URL)

    def _tick_check_login(self):
        if t := self.current_tab():
            t._check_login()

    def _on_js_login(self, result):
        if result and isinstance(result, dict) and result.get("name"):
            name = result["name"].strip()
            if name and not self._user_info["logged_in"]:
                self._user_info = {"logged_in": True, "name": name}
                self.avatar_btn.set_user(name, C["accent_ms"])
                self._refresh_conn_label()
        elif not result and self._user_info["logged_in"]:
            tab = self.current_tab()
            if tab:
                host = tab.webview.url().host()
                if "moodsync" not in host and "alwaysdata" not in host:
                    self._user_info = {"logged_in": False, "name": ""}
                    self.avatar_btn.set_logged_out()
                    self._refresh_conn_label()

    def _refresh_conn_label(self):
        if self._user_info["logged_in"]:
            self.conn_label.setText(f"● {self._user_info['name']}")
            self.conn_label.setStyleSheet(f"color: {C['green']}; font-size: 11px; padding-right: 8px;")
        else:
            self.conn_label.setText("Non connecté")
            self.conn_label.setStyleSheet(f"color: {C['text_muted']}; font-size: 11px; padding-right: 8px;")

    # ── Menu ─────────────────────────────────────────────────────────────────

    def _show_chrome_menu(self):
        menu = QMenu(self)
        menu.addAction("Nouvel onglet\tCtrl+T",          lambda: self.new_tab(HOME_URL))
        menu.addSeparator()
        menu.addAction("Zoom +\tCtrl++",                 lambda: self._zoom(1.1))
        menu.addAction("Zoom −\tCtrl+−",                 lambda: self._zoom(0.9))
        menu.addAction("Zoom 100%\tCtrl+0",              self._zoom_reset)
        menu.addSeparator()
        menu.addAction("Outils de développement\tF12",   self._open_devtools)
        menu.addAction("Source de la page\tCtrl+U",      self._view_source)
        menu.addSeparator()
        menu.addAction("Quitter",                        self.close)
        menu.exec(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft()))

    def _zoom(self, f):
        if t := self.current_tab():
            t.webview.setZoomFactor(min(max(t.webview.zoomFactor() * f, 0.25), 5.0))

    def _zoom_reset(self):
        if t := self.current_tab(): t.webview.setZoomFactor(1.0)

    def _open_devtools(self):
        if t := self.current_tab():
            dv = QWebEngineView()
            t.webview.page().setDevToolsPage(dv.page())
            dv.resize(960, 640)
            dv.setWindowTitle("DevTools — MoodSync")
            dv.show()
            self._dv = dv

    def _view_source(self):
        if t := self.current_tab():
            self.new_tab("view-source:" + t.webview.url().toString())

    # ── Raccourcis ────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"),         self, lambda: self.new_tab(HOME_URL))
        QShortcut(QKeySequence("Ctrl+W"),         self, lambda: self._close_tab(self.tabs.currentIndex()))
        QShortcut(QKeySequence("Ctrl+L"),         self, lambda: (self.urlbar.setFocus(), self.urlbar.selectAll()))
        QShortcut(QKeySequence("F5"),             self, self._reload)
        QShortcut(QKeySequence("Ctrl+R"),         self, self._reload)
        QShortcut(QKeySequence("F12"),            self, self._open_devtools)
        QShortcut(QKeySequence("Ctrl+U"),         self, self._view_source)
        QShortcut(QKeySequence("Alt+Left"),       self, self._go_back)
        QShortcut(QKeySequence("Alt+Right"),      self, self._go_forward)
        QShortcut(QKeySequence("Ctrl+Plus"),      self, lambda: self._zoom(1.1))
        QShortcut(QKeySequence("Ctrl+Minus"),     self, lambda: self._zoom(0.9))
        QShortcut(QKeySequence("Ctrl+0"),         self, self._zoom_reset)
        QShortcut(QKeySequence("Ctrl+Tab"),       self, lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex()+1) % self.tabs.count()))
        QShortcut(QKeySequence("Ctrl+Shift+Tab"), self, lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex()-1) % self.tabs.count()))
        QShortcut(QKeySequence("Ctrl+Shift+I"),   self, self._open_devtools)


def main():
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu-driver-bug-workarounds --no-sandbox")
    app = QApplication(sys.argv)
    app.setApplicationName("MoodSync Browser")
    app.setApplicationVersion("2.0")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(C["chrome_bg"]))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(C["text"]))
    palette.setColor(QPalette.ColorRole.Base,            QColor(C["urlbar_bg"]))
    palette.setColor(QPalette.ColorRole.Text,            QColor(C["text"]))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(C["accent"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Button,          QColor(C["chrome_light"]))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(C["text"]))
    app.setPalette(palette)
    win = MoodSyncBrowser()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
