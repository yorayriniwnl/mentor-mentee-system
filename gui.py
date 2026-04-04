"""
gui.py — KIIT-portal-styled Tkinter interface for the Menor Mentee Portal.

Colour scheme:
    Header bg     #060B16
    Accent cyan   #0EA5E9
    Accent cyan   #22D3EE
    Card surface  #111827
    App bg        #030712
    Warning amber #3A2F12 / #FDE68A
    Text light    #E5E7EB
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from typing import Optional
import json
import os
import shutil
import ctypes

import auth
import analytics
import booking
import feedback as fb
import matching
import messaging

try:
    from PIL import Image, ImageOps, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ──────────────────────────── Palette ────────────────────────────
HEADER_BG  = "#060B16"
NAVY       = "#93C5FD"
BLUE       = "#0EA5E9"
TAB_BLUE   = "#0369A1"
LIGHT_BLUE = "#1F2937"
BG         = "#030712"
WHITE      = "#111827"
BORDER     = "#334155"
TEXT       = "#E5E7EB"
MUTED      = "#94A3B8"
WARN_BG    = "#3A2F12"
WARN_FG    = "#FDE68A"
SUCCESS    = "#10B981"
DANGER     = "#F43F5E"
LINK       = "#22D3EE"
GOLD       = "#1E293B"
LIGHT_GOLD = "#050B18"

FONT_TITLE  = ("Segoe UI", 20, "bold")
FONT_HEADER = ("Segoe UI", 15, "bold")
FONT_BODY   = ("Segoe UI", 12)
FONT_SMALL  = ("Segoe UI", 11)
FONT_LABEL  = ("Segoe UI", 12, "bold")
PROFILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _hex_to_rgb(hex_color: str):
    color = hex_color.strip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def _shade(hex_color: str, factor: float) -> str:
    """Lighten (factor>0) or darken (factor<0) a hex color."""
    r, g, b = _hex_to_rgb(hex_color)
    if factor >= 0:
        r = int(r + (255 - r) * factor)
        g = int(g + (255 - g) * factor)
        b = int(b + (255 - b) * factor)
    else:
        r = int(r * (1 + factor))
        g = int(g * (1 + factor))
        b = int(b * (1 + factor))
    return _rgb_to_hex((max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))


def _animate_panel_entry(widget, start_color="#22D3EE", end_color=BORDER, steps=10, delay=18):
    """Subtle border fade-in animation for cards and panels."""
    try:
        s = _hex_to_rgb(start_color)
        e = _hex_to_rgb(end_color)
    except Exception:
        return

    def tick(i=0):
        t = i / max(1, steps)
        mixed = (
            int(s[0] + (e[0] - s[0]) * t),
            int(s[1] + (e[1] - s[1]) * t),
            int(s[2] + (e[2] - s[2]) * t),
        )
        try:
            widget.configure(highlightbackground=_rgb_to_hex(mixed))
        except Exception:
            return
        if i < steps:
            widget.after(delay, lambda: tick(i + 1))

    widget.after(16, tick)


def _enable_high_dpi_mode() -> None:
    """Improve visual sharpness on Windows high-resolution displays."""
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


# ──────────────────────────── Helpers ────────────────────────────

def _lbl(parent, text, font=FONT_BODY, fg=TEXT, bg=None, **kw):
    b = bg if bg is not None else parent.cget("bg")
    return tk.Label(parent, text=text, font=font, fg=fg, bg=b, **kw)


def _btn(parent, text, cmd, bg=BLUE, fg="#F8FAFC", w=16, **kw):
    btn = tk.Button(
        parent, text=text, command=cmd,
        bg=bg, fg=fg, font=FONT_BODY,
        relief="flat", bd=0, padx=11, pady=7,
        cursor="hand2", width=w,
        activebackground=_shade(bg, -0.16),
        activeforeground="#F8FAFC",
        highlightthickness=1,
        highlightbackground=_shade(bg, -0.2),
        highlightcolor=LINK,
        **kw
    )
    default_bg = bg
    hover_bg = _shade(bg, 0.10)

    def _on_enter(_):
        btn.configure(bg=hover_bg)

    def _on_leave(_):
        btn.configure(bg=default_bg)

    btn.bind("<Enter>", _on_enter)
    btn.bind("<Leave>", _on_leave)
    return btn


def _entry(parent, show="", width=28):
    return tk.Entry(
        parent,
        font=FONT_BODY,
        width=width,
        relief="solid",
        bd=1,
        show=show,
        bg="#0F172A",
        fg=TEXT,
        insertbackground=TEXT,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=LINK,
    )


def _sep(parent, bg=BORDER):
    return tk.Frame(parent, bg=bg, height=2)


def _card(parent, padx=12, pady=10, **kw):
    card = tk.Frame(
        parent,
        bg=WHITE,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        padx=padx,
        pady=pady,
        **kw,
    )
    _animate_panel_entry(card)
    return card


def _format_timestamp(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return value


def _login_prefs_path() -> str:
    prefs_root = os.getenv("APPDATA") or os.path.dirname(__file__)
    return os.path.join(prefs_root, "MentorPortal", "login_preferences.json")


def _profile_image_paths(user: dict):
    base_dir = os.path.dirname(__file__)
    raw_paths = []
    stored_path = user.get("profile_image")
    if stored_path:
        raw_paths.append(stored_path)

    for folder in ("images/profiles", "profiles", "images"):
        for stem in (user.get("roll_no"), user.get("user_id")):
            if not stem:
                continue
            for ext in PROFILE_EXTENSIONS:
                raw_paths.append(os.path.join(folder, f"{stem}{ext}"))

    resolved_paths = []
    seen = set()
    for raw_path in raw_paths:
        if not raw_path:
            continue
        path = raw_path if os.path.isabs(raw_path) else os.path.join(base_dir, raw_path)
        key = os.path.normcase(os.path.normpath(path))
        if key in seen:
            continue
        seen.add(key)
        resolved_paths.append(path)
    return resolved_paths


def _render_profile_photo(parent, user, width=140, height=170):
    frame = tk.Frame(parent, bg=LIGHT_BLUE, relief="solid", bd=1, width=width, height=height)
    frame.pack_propagate(False)

    inner = tk.Frame(frame, bg=WHITE)
    inner.pack(fill="both", expand=True, padx=6, pady=6)

    if PIL_AVAILABLE:
        resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
        for path in _profile_image_paths(user):
            if not os.path.exists(path):
                continue
            try:
                image = Image.open(path).convert("RGB")
                image = ImageOps.fit(
                    image,
                    (width - 12, height - 12),
                    method=resampling,
                    centering=(0.5, 0.5),
                )
                photo_image = ImageTk.PhotoImage(image)
                label = tk.Label(inner, image=photo_image, bg=WHITE, relief="flat")
                label.image = photo_image
                frame.photo_image = photo_image
                label.pack(fill="both", expand=True)
                return frame
            except Exception:
                continue

    initials = "".join(part[:1] for part in user.get("name", "User").split()[:2]).upper() or "U"
    _lbl(inner, initials, ("Segoe UI", 28, "bold"), NAVY, WHITE).pack(expand=True, pady=(22, 6))
    _lbl(inner, "Profile Photo", FONT_SMALL, MUTED, WHITE).pack(pady=(0, 12))
    return frame


# ──────────────────────── Chrome widgets ─────────────────────────

class HeaderBar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=HEADER_BG, pady=5)
        self.welcome_var = tk.StringVar(value="")
        tk.Label(self, textvariable=self.welcome_var,
                 font=FONT_SMALL, fg="#A8C4E8", bg=HEADER_BG).pack(side="left", padx=12)
        right = tk.Frame(self, bg=HEADER_BG)
        right.pack(side="right", padx=12)
        tk.Button(right, text="Log off", command=app.logout,
                  font=FONT_SMALL, fg="#A8C4E8", bg=HEADER_BG,
                  relief="flat", cursor="hand2").pack(side="right")
        tk.Label(right, text=" | Help", font=FONT_SMALL, fg="#A8C4E8", bg=HEADER_BG).pack(side="right")

    def set_user(self, name):
        self.welcome_var.set(f"  Welcome  {name.upper()}")


class BannerBar(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BLUE)
        for label, frame in [
            ("Home", "DashboardFrame"),
            ("Sessions", "BookingFrame"),
            ("Messages", "MessagingFrame"),
            ("Analytics", "AnalyticsFrame"),
        ]:
            tk.Button(
                self, text=label, font=FONT_SMALL,
                fg="#F8FAFC", bg=BLUE, relief="flat",
                padx=12, pady=5, cursor="hand2",
                activebackground=HEADER_BG, activeforeground="#F8FAFC",
                command=lambda f=frame: app.show(f),
            ).pack(side="left")


class NoticeBar(tk.Frame):
    def __init__(self, parent, text=""):
        super().__init__(parent, bg=WARN_BG, pady=5)
        if text:
            tk.Label(self, text=f"⚠  {text}",
                     font=FONT_SMALL, fg=WARN_FG, bg=WARN_BG).pack()


# ──────────────────────────── App Shell ──────────────────────────

class DetailNav(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=WHITE, relief="solid", bd=1, width=240)
        self.app = app
        self.pack_propagate(False)

        _lbl(self, " Detailed Navigation", FONT_LABEL, NAVY, WHITE).pack(
            fill="x", pady=(10, 4)
        )
        _sep(self).pack(fill="x")

        self.links = tk.Frame(self, bg=WHITE)
        self.links.pack(fill="both", expand=True, pady=(4, 8))

    def _items(self, user):
        session_label = "Manage Sessions" if user.get("role") == "mentor" else "Book a Session"
        items = [("Overview", "DashboardFrame")]
        if user.get("role") == "mentee":
            items.append(("Mentor Display", "MentorDisplayFrame"))
        items.extend([
            (session_label, "BookingFrame"),
            ("Messages", "MessagingFrame"),
            ("Feedback", "FeedbackFrame"),
        ])
        return items

    def refresh(self, user, active_frame=""):
        for widget in self.links.winfo_children():
            widget.destroy()

        for label, frame_name in self._items(user):
            is_active = frame_name == active_frame
            tk.Button(
                self.links,
                text=f"- {label}",
                font=FONT_SMALL,
                fg=NAVY if is_active else LINK,
                bg=LIGHT_BLUE if is_active else WHITE,
                relief="flat",
                anchor="w",
                padx=10,
                pady=3,
                cursor="hand2",
                activeforeground=NAVY,
                activebackground=LIGHT_BLUE,
                command=lambda f=frame_name: self.app.show(f),
            ).pack(fill="x")


class PrettyDetailNav(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=BG, width=280)
        self.app = app
        self.pack_propagate(False)

        self.card = tk.Frame(
            self,
            bg=WHITE,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.card.pack(fill="both", expand=True)

        tk.Frame(self.card, bg="#22D3EE", height=3).pack(fill="x")
        tk.Frame(self.card, bg=BLUE, height=2).pack(fill="x")

        header = tk.Frame(self.card, bg=WHITE, padx=14, pady=12)
        header.pack(fill="x")
        _lbl(header, "Detailed Navigation", FONT_HEADER, NAVY, WHITE).pack(anchor="w")
        _lbl(header, "Quick access to your workspace", FONT_SMALL, MUTED, WHITE).pack(anchor="w", pady=(2, 0))
        _sep(self.card).pack(fill="x")

        self.links = tk.Frame(self.card, bg=WHITE, padx=10, pady=10)
        self.links.pack(fill="both", expand=True)

    def _items(self, user):
        session_label = "Manage Sessions" if user.get("role") == "mentor" else "Book a Session"
        items = [("Overview", "DashboardFrame")]
        if user.get("role") == "mentee":
            items.append(("Mentor Display", "MentorDisplayFrame"))
        items.extend([
            (session_label, "BookingFrame"),
            ("Messages", "MessagingFrame"),
            ("Feedback", "FeedbackFrame"),
        ])
        return items

    def _nav_item(self, label, frame_name, is_active):
        row_bg = LIGHT_BLUE if is_active else WHITE
        accent_bg = "#22D3EE" if is_active else WHITE

        row = tk.Frame(self.links, bg=row_bg)
        row.pack(fill="x", pady=4)

        accent = tk.Frame(row, bg=accent_bg, width=5)
        accent.pack(side="left", fill="y")

        btn = tk.Button(
            row,
            text=label,
            font=FONT_LABEL if is_active else FONT_BODY,
            fg=NAVY if is_active else LINK,
            bg=row_bg,
            relief="flat",
            anchor="w",
            padx=12,
            pady=8,
            cursor="hand2",
            activeforeground=NAVY,
            activebackground=LIGHT_BLUE,
            command=lambda f=frame_name: self.app.show(f),
        )
        btn.pack(side="left", fill="x", expand=True)

        def on_enter(_):
            if not is_active:
                row.configure(bg="#172033")
                btn.configure(bg="#172033")
                accent.configure(bg="#334155")

        def on_leave(_):
            if not is_active:
                row.configure(bg=WHITE)
                btn.configure(bg=WHITE)
                accent.configure(bg=WHITE)

        row.bind("<Enter>", on_enter)
        row.bind("<Leave>", on_leave)
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    def refresh(self, user, active_frame=""):
        for widget in self.links.winfo_children():
            widget.destroy()

        for label, frame_name in self._items(user):
            self._nav_item(label, frame_name, frame_name == active_frame)


class MentorApp(tk.Tk):
    def __init__(self):
        _enable_high_dpi_mode()
        super().__init__()
        self.title("Menor Mentee Portal")
        self.geometry("1920x1080")
        self.minsize(1440, 900)
        self.tk.call("tk", "scaling", 1.35)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.current_user: Optional[dict] = None

        self.header = HeaderBar(self, self)
        self.main_shell = tk.Frame(self, bg=BG)
        self.main_shell.pack(fill="both", expand=True)
        self.main_shell.grid_rowconfigure(0, weight=1)
        self.main_shell.grid_columnconfigure(1, weight=1)

        self.sidebar = PrettyDetailNav(self.main_shell, self)

        self._container = tk.Frame(self.main_shell, bg=BG)
        self._container.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_columnconfigure(0, weight=1)

        self._frames = {}
        self._setup_ttk_theme()
        for F in (LoginFrame, DashboardFrame, MentorDisplayFrame,
                  BookingFrame, MessagingFrame,
                  FeedbackFrame):
            frame = F(self._container, self)
            self._frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show("LoginFrame")

    def show(self, name: str, **kwargs):
        # Hide all frames first
        for frame in self._frames.values():
            frame.grid_remove()
        
        # Show and raise the requested frame
        frame = self._frames[name]
        frame.grid()
        if hasattr(frame, "refresh"):
            frame.refresh(**kwargs)
        if self.current_user and name != "LoginFrame":
            self.sidebar.refresh(self.current_user, name)
            self.sidebar.grid(row=0, column=0, sticky="ns", padx=(10, 10), pady=10)
        else:
            self.sidebar.grid_remove()
        frame.tkraise()

    def _chrome_visible(self, visible: bool):
        if visible:
            self.header.pack(fill="x", before=self.main_shell)
            if self.current_user:
                self.sidebar.refresh(self.current_user)
                self.sidebar.grid(row=0, column=0, sticky="ns", padx=(10, 10), pady=10)
        else:
            self.header.pack_forget()
            self.sidebar.grid_remove()

    def logout(self):
        self.current_user = None
        self._chrome_visible(False)
        self.show("LoginFrame")

    def _setup_ttk_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TCombobox",
            fieldbackground="#0F172A",
            background=WHITE,
            foreground=TEXT,
            bordercolor=BORDER,
            arrowsize=14,
            padding=5,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#0F172A")],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", BLUE)],
            selectforeground=[("readonly", "#F8FAFC")],
        )

        style.configure(
            "Treeview",
            background=WHITE,
            fieldbackground=WHITE,
            foreground=TEXT,
            rowheight=30,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
        )
        style.configure(
            "Treeview.Heading",
            background="#0F172A",
            foreground="#BAE6FD",
            bordercolor=BORDER,
            relief="flat",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", BLUE)],
            foreground=[("selected", "#F8FAFC")],
        )


# ──────────────────────────── Login ──────────────────────────────

class LoginFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg="#0F172A")
        self.app = app
        self.photo_image = None  # Keep reference to prevent garbage collection
        self.save_password_var = tk.BooleanVar(value=False)
        self.show_password_var = tk.BooleanVar(value=False)
        self.input_shells = {}
        self.login_btn = None
        self._build()

    def _build(self):
        shell = tk.Frame(self, bg="#0B1220")
        shell.pack(fill="both", expand=True, padx=26, pady=26)

        accent_top = tk.Frame(shell, bg="#22D3EE", height=3)
        accent_top.pack(fill="x", side="top")

        card = tk.Frame(
            shell,
            bg="#111C33",
            highlightbackground="#334155",
            highlightthickness=1,
            bd=0,
        )
        card.pack(fill="both", expand=True)

        content = tk.Frame(card, bg="#111C33")
        content.pack(fill="both", expand=True, padx=24, pady=24)

        left_panel = tk.Frame(content, bg="#0E1A32", width=420)
        left_panel.pack(side="left", fill="both", expand=True)
        left_panel.pack_propagate(False)

        self._build_image_panel(left_panel)

        sep = tk.Frame(content, bg="#23314E", width=1)
        sep.pack(side="left", fill="y", padx=24)

        right_panel = tk.Frame(content, bg="#111C33")
        right_panel.pack(side="right", fill="both", expand=True, padx=12, pady=8)

        self._build_form_panel(right_panel)

        footer = tk.Frame(card, bg="#111C33", height=36)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        _lbl(
            footer,
            "Copyright (c) Menor Mentee Portal. All rights reserved.",
            FONT_SMALL,
            "#64748B",
            "#111C33",
        ).pack(anchor="center", pady=8)

    def _build_image_panel(self, panel):
        """Try to load and display an image, fallback to colored placeholder."""
        # Try to load image files in common locations
        image_paths = [
            "./kiit.png", "./kiit.jpg", "./kiit_building.png",
            "./images/kiit.png", "./images/kiit_building.jpg",
            os.path.join(os.path.dirname(__file__), "kiit.png"),
            os.path.join(os.path.dirname(__file__), "kiit.jpg"),
        ]

        image_loaded = False
        image_box = tk.Frame(panel, bg="#0B1220", highlightbackground="#334155", highlightthickness=1)
        image_box.pack(expand=True, padx=22, pady=22, fill="both")

        if PIL_AVAILABLE:
            for path in image_paths:
                if os.path.exists(path):
                    try:
                        img = Image.open(path)
                        img.thumbnail((520, 420), Image.Resampling.LANCZOS)
                        self.photo_image = ImageTk.PhotoImage(img)
                        img_label = tk.Label(image_box, image=self.photo_image, bg="#0B1220")
                        img_label.pack(expand=True, padx=16, pady=16)
                        image_loaded = True
                        break
                    except Exception:
                        pass

        if not image_loaded:
            placeholder = tk.Frame(image_box, bg="#1E3A8A", relief="flat", bd=0)
            placeholder.pack(expand=True, padx=16, pady=16, fill="both")
            _lbl(
                placeholder,
                "KALINGA INSTITUTE OF INDUSTRIAL\nTECHNOLOGY UNIVERSITY",
                ("Segoe UI", 16, "bold"),
                "#E2E8F0",
                "#1E3A8A",
                justify="center",
            ).pack(expand=True)
            _lbl(
                placeholder,
                "Mentor-Mentee Excellence Platform",
                ("Segoe UI", 11),
                "#BFDBFE",
                "#1E3A8A",
            ).pack(pady=(0, 18))

    def _styled_login_entry(self, parent, secret=False):
        shell = tk.Frame(parent, bg="#15213A", highlightbackground="#334155", highlightthickness=1)
        entry = tk.Entry(
            shell,
            font=("Segoe UI", 11),
            relief="flat",
            bd=0,
            show="*" if secret else "",
            bg="#15213A",
            fg="#E2E8F0",
            insertbackground="#E2E8F0",
        )
        entry.pack(fill="x", padx=10, pady=9)
        return shell, entry

    def _set_input_focus(self, key: str, focused: bool):
        shell = self.input_shells.get(key)
        if shell:
            shell.configure(highlightbackground="#22D3EE" if focused else "#334155")

    def _on_login_hover(self, entering: bool):
        if not self.login_btn:
            return
        self.login_btn.configure(bg="#38BDF8" if entering else "#0EA5E9")

    def _build_form_panel(self, panel):
        """Build the login form."""
        _lbl(panel, "Menor Mentee Portal", ("Segoe UI", 27, "bold"), "#F8FAFC", "#111C33").pack(
            anchor="w", pady=(14, 2)
        )
        _lbl(
            panel,
            "Welcome to KIIT University Portal.*",
            ("Segoe UI", 13, "bold"),
            "#22D3EE",
            "#111C33",
        ).pack(anchor="w", pady=(0, 10))
        _lbl(
            panel,
            "Sign in to book sessions, message mentors, and track growth analytics.",
            FONT_SMALL,
            "#94A3B8",
            "#111C33",
        ).pack(anchor="w", pady=(0, 22))

        for i, (lbl, attr, secret) in enumerate([
            ("Roll No.", "l_roll", False),
            ("Password", "l_pass", True),
        ]):
            _lbl(panel, lbl + " *", ("Segoe UI", 11, "bold"), "#CBD5E1", "#111C33").pack(anchor="w", pady=(8, 4))
            shell, e = self._styled_login_entry(panel, secret=secret)
            shell.pack(anchor="w", fill="x", pady=(0, 12))
            key = "roll" if not secret else "pass"
            self.input_shells[key] = shell
            e.bind("<FocusIn>", lambda _, k=key: self._set_input_focus(k, True))
            e.bind("<FocusOut>", lambda _, k=key: self._set_input_focus(k, False))
            setattr(self, attr, e)

        options_row = tk.Frame(panel, bg="#111C33")
        options_row.pack(anchor="w", pady=(0, 12))

        tk.Checkbutton(
            options_row,
            text="Save Password",
            variable=self.save_password_var,
            font=FONT_SMALL,
            fg="#94A3B8",
            bg="#111C33",
            activebackground="#111C33",
            activeforeground="#CBD5E1",
            selectcolor="#111C33",
            cursor="hand2",
        ).pack(side="left")

        tk.Checkbutton(
            options_row,
            text="Show Password",
            variable=self.show_password_var,
            command=self._toggle_password_visibility,
            font=FONT_SMALL,
            fg="#94A3B8",
            bg="#111C33",
            activebackground="#111C33",
            activeforeground="#CBD5E1",
            selectcolor="#111C33",
            cursor="hand2",
        ).pack(side="left", padx=(16, 0))

        self._load_saved_login()

        self.login_btn = tk.Button(
            panel,
            text="Log On",
            command=self._do_login,
            bg="#0EA5E9",
            fg="#F8FAFC",
            font=("Segoe UI", 12, "bold"),
            relief="flat",
            padx=18,
            pady=9,
            cursor="hand2",
            activebackground="#0369A1",
            activeforeground="#F8FAFC",
            width=18,
        )
        self.login_btn.pack(anchor="e", pady=(18, 6))
        self.login_btn.bind("<Enter>", lambda _: self._on_login_hover(True))
        self.login_btn.bind("<Leave>", lambda _: self._on_login_hover(False))

    def _do_login(self):
        roll_no = self.l_roll.get().strip()
        password = self.l_pass.get()
        ok, user = auth.login(roll_no, password)
        if ok:
            if self.save_password_var.get():
                self._save_login_preferences(roll_no, password)
            else:
                self._clear_login_preferences()
            self.app.current_user = user
            self.app.header.set_user(user["name"])
            self.app._chrome_visible(True)
            self.app.show("DashboardFrame")
        else:
            messagebox.showerror("Login Failed", "Incorrect roll number or password.")

    def _toggle_password_visibility(self):
        self.l_pass.configure(show="" if self.show_password_var.get() else "*")

    def _load_saved_login(self):
        path = _login_prefs_path()
        if not os.path.exists(path):
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                prefs = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        if not prefs.get("save_password"):
            return

        self.l_roll.delete(0, "end")
        self.l_roll.insert(0, prefs.get("roll_no", ""))
        self.l_pass.delete(0, "end")
        self.l_pass.insert(0, prefs.get("password", ""))
        self.save_password_var.set(True)

    def _save_login_preferences(self, roll_no: str, password: str):
        path = _login_prefs_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "save_password": True,
                        "roll_no": roll_no,
                        "password": password,
                    },
                    f,
                    indent=2,
                )
        except OSError:
            pass

    def _clear_login_preferences(self):
        path = _login_prefs_path()
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


# ──────────────────────────── Dashboard ──────────────────────────

class DashboardFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._hero_canvas = None

    def refresh(self, **_):
        for w in self.winfo_children():
            w.destroy()
        u = self.app.current_user
        if u:
            self._build_shared(u)

    def _build_shared(self, u):
        title_bar = tk.Frame(self, bg=TAB_BLUE)
        title_bar.pack(fill="x")
        _lbl(title_bar, "  Dashboard", FONT_HEADER, "#F8FAFC", TAB_BLUE).pack(side="left", pady=6)

        right = tk.Frame(self, bg=BG)
        right.pack(fill="both", expand=True, padx=10, pady=10)

        self._build_hero(right, u)

        det = _card(right)
        det.pack(fill="x", pady=(0, 8))
        det.grid_columnconfigure(0, weight=1)

        _lbl(det, "Student Details" if u["role"] == "mentee" else "Mentor Details",
             FONT_TITLE, NAVY, WHITE).grid(row=0, column=0, sticky="w", pady=(0, 8))
        _sep(det).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        content = tk.Frame(det, bg=WHITE)
        content.grid(row=2, column=0, sticky="ew")
        content.grid_columnconfigure(0, weight=1)

        info = tk.Frame(content, bg=WHITE)
        info.grid(row=0, column=0, sticky="nw")
        info.grid_columnconfigure(1, weight=1, minsize=170)
        info.grid_columnconfigure(3, weight=1, minsize=170)

        photo_panel = tk.Frame(content, bg=WHITE)
        photo_panel.grid(row=0, column=1, sticky="ne", padx=(24, 0))
        _render_profile_photo(photo_panel, u).pack(anchor="ne")
        _btn(
            photo_panel,
            "Change Photo",
            lambda user=u: self._change_profile_photo(user),
            bg=HEADER_BG,
            w=12,
        ).pack(anchor="ne", pady=(8, 0))

        def row(r, lbl, val, c=0):
            base_col = c * 2
            _lbl(info, lbl, FONT_LABEL, MUTED, WHITE).grid(
                row=r, column=base_col, sticky="w", padx=(0, 8), pady=4
            )
            _lbl(info, val, FONT_BODY, TEXT, WHITE).grid(
                row=r, column=base_col + 1, sticky="w", padx=(0, 24), pady=4
            )

        if u["role"] == "mentee":
            row(0, "School :",          u.get("school", "-"))
            row(1, "Student Name :",    u.get("name", "-"))
            row(2, "Program of Study:", u.get("program", "-"))
            row(3, "Semester :",        u.get("semester", "-"))
            row(0, "Roll No. :",        u.get("roll_no", "-"), c=1)
            row(1, "Reg. No. :",        u.get("reg_no", "-"), c=1)
        else:
            row(0, "Name :",        u.get("name", "-"))
            row(1, "Email :",       u.get("email", "-"))
            row(2, "Contact :",     u.get("contact_number", "-"))
            row(3, "Experience :",  f"{u.get('experience_years', 0)} years")
            row(0, "Rating :",      f"* {u.get('rating', 0.0):.1f}", c=1)
            row(1, "Sessions :",    str(u.get("sessions_completed", 0)), c=1)

        if u["role"] == "mentee":
            self._mentor_card(right, u)

    def _build_hero(self, parent, user):
        hero = tk.Canvas(
            parent,
            height=220,
            bg=WHITE,
            highlightthickness=1,
            highlightbackground=BORDER,
            bd=0,
            relief="flat",
        )
        hero.pack(fill="x", pady=(0, 12))
        _animate_panel_entry(hero, start_color="#67E8F9")
        self._hero_canvas = hero

        def draw_gradient(_=None):
            w = max(hero.winfo_width(), 2)
            h = max(hero.winfo_height(), 2)
            hero.delete("all")
            c1 = _hex_to_rgb("#0B3B66")
            c2 = _hex_to_rgb("#0E7490")
            for x in range(w):
                t = x / max(1, w - 1)
                r = int(c1[0] + (c2[0] - c1[0]) * t)
                g = int(c1[1] + (c2[1] - c1[1]) * t)
                b = int(c1[2] + (c2[2] - c1[2]) * t)
                hero.create_line(x, 0, x, h, fill=_rgb_to_hex((r, g, b)))

            hero.create_rectangle(0, h - 68, w, h, fill="#0B1220", outline="")
            hero.create_text(
                28,
                36,
                text=f"Welcome back, {user.get('name', 'User').split()[0]}",
                fill="#F8FAFC",
                font=("Segoe UI", 21, "bold"),
                anchor="w",
            )
            hero.create_text(
                28,
                74,
                text="High-impact mentorship workspace for fast, focused growth.",
                fill="#BFDBFE",
                font=("Segoe UI", 11),
                anchor="w",
            )

            chips = tk.Frame(hero, bg="#0B1220")
            chip_items = [
                ("Sessions", str(user.get("sessions_completed", 0))),
                ("Role", user.get("role", "-").title()),
                ("Rating", f"{user.get('rating', 0.0):.1f}"),
            ]
            for title, value in chip_items:
                chip = tk.Frame(chips, bg="#111827", highlightthickness=1, highlightbackground="#334155")
                chip.pack(side="left", padx=8)
                _lbl(chip, f" {title} ", FONT_SMALL, "#94A3B8", "#111827").pack(anchor="w", padx=8, pady=(6, 0))
                _lbl(chip, f" {value} ", ("Segoe UI", 12, "bold"), "#F8FAFC", "#111827").pack(anchor="w", padx=8, pady=(0, 7))
            hero.create_window(24, 132, window=chips, anchor="nw")

        hero.bind("<Configure>", draw_gradient)
        draw_gradient()

    def _change_profile_photo(self, user):
        selected_path = filedialog.askopenfilename(
            title="Choose Profile Photo",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not selected_path:
            return

        ext = os.path.splitext(selected_path)[1].lower() or ".png"
        if ext not in PROFILE_EXTENSIONS:
            messagebox.showerror("Invalid Photo", "Please choose a PNG, JPG, JPEG, WEBP, or BMP image.")
            return

        target_dir = os.path.join(os.path.dirname(__file__), "images", "profiles")
        os.makedirs(target_dir, exist_ok=True)
        file_stem = user.get("roll_no") or user.get("user_id") or "profile"
        target_path = os.path.join(target_dir, f"{file_stem}{ext}")

        try:
            shutil.copy2(selected_path, target_path)
        except OSError as exc:
            messagebox.showerror("Photo Update Failed", f"Could not copy the image.\n{exc}")
            return

        relative_path = os.path.relpath(target_path, os.path.dirname(__file__)).replace("\\", "/")
        ok, msg = auth.update_profile(user["user_id"], {"profile_image": relative_path})
        if not ok:
            messagebox.showerror("Photo Update Failed", msg)
            return

        self.app.current_user["profile_image"] = relative_path
        self.refresh()

    def _mentor_card(self, parent, u):
        import database as db
        mentor = db.get_assigned_mentor(u["user_id"])

        card = _card(parent)
        card.pack(fill="x", pady=4)

        hdr = tk.Frame(card, bg=LIGHT_BLUE)
        hdr.pack(fill="x", pady=(0, 8))
        _lbl(hdr, "  Mentor Information", FONT_HEADER, NAVY, LIGHT_BLUE).pack(side="left", pady=4, padx=10)

        for lbl, val in [
            ("Mentor Name :",    mentor.get("name", "—") if mentor else "Not yet assigned"),
            ("Contact Number :", mentor.get("contact_number", "—") if mentor else "—"),
            ("E-mail ID :",      mentor.get("email", "—") if mentor else "—"),
        ]:
            r = tk.Frame(card, bg=WHITE)
            r.pack(fill="x", pady=2, padx=8)
            _lbl(r, lbl, FONT_LABEL, TEXT, WHITE, width=18, anchor="w").pack(side="left")
            val_color = LINK if mentor and "@" in val else TEXT
            _lbl(r, val, FONT_BODY, val_color, WHITE).pack(side="left", anchor="w")


# ────────────────────── Mentor Display (KIIT tab) ─────────────────

class MentorDisplayFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg=BG)
        self.app = app

    def refresh(self, **_):
        for w in self.winfo_children():
            w.destroy()
        u = self.app.current_user
        if not u:
            return

        title_bar = tk.Frame(self, bg=TAB_BLUE)
        title_bar.pack(fill="x")
        _lbl(title_bar, "  Mentor Display", FONT_HEADER, WHITE, TAB_BLUE).pack(side="left", pady=5)
        _btn(title_bar, "← Back", lambda: self.app.show("DashboardFrame"),
               bg=HEADER_BG, w=10).pack(side="right", padx=8, pady=4)

        import database as db
        mentor = db.get_assigned_mentor(u["user_id"])

        card = _card(self, 20, 16)
        card.pack(fill="x", padx=20, pady=14)

        hdr = tk.Frame(card, bg=LIGHT_BLUE)
        hdr.pack(fill="x", pady=(0, 12))
        _lbl(hdr, "  Mentor Information", FONT_HEADER, NAVY, LIGHT_BLUE).pack(side="left", pady=5, padx=10)

        if mentor:
            pairs = [
                ("Mentor Name :",    mentor.get("name", "—")),
                ("Contact Number :", mentor.get("contact_number", "—")),
                ("E-mail ID :",      mentor.get("email", "—")),
                ("Skills :",         ", ".join(mentor.get("skills", [])) if mentor.get("skills") else "—"),
                ("Experience :",     f"{mentor.get('experience_years', 0)} years"),
                ("Rating :",         f"★ {mentor.get('rating', 0.0):.1f}"),
            ]
            for lbl, val in pairs:
                r = tk.Frame(card, bg=WHITE)
                r.pack(fill="x", pady=4, padx=8)
                _lbl(r, lbl, FONT_LABEL, TEXT, WHITE, width=18, anchor="w").pack(side="left", padx=(10, 20))
                val_color = LINK if "@" in val else TEXT
                _lbl(r, val, FONT_BODY, val_color, WHITE).pack(side="left", anchor="w")
        else:
            r = tk.Frame(card, bg=WHITE)
            r.pack(fill="x", pady=20)
            _lbl(r, "No mentor assigned yet", FONT_BODY, MUTED, WHITE).pack()


# ──────────────────────────── Match ──────────────────────────────

class MatchFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        title_bar = tk.Frame(self, bg=TAB_BLUE)
        title_bar.pack(fill="x")
        _lbl(title_bar, "  Find a Mentor", FONT_HEADER, WHITE, TAB_BLUE).pack(side="left", pady=5)
        _btn(title_bar, "← Back", lambda: self.app.show("DashboardFrame"),
               bg=HEADER_BG, w=10).pack(side="right", padx=8, pady=4)

        ctrl = tk.Frame(self, bg=BG, pady=8, padx=14)
        ctrl.pack(fill="x")
        _lbl(ctrl, "Top results:", bg=BG).pack(side="left")
        self.top_n = tk.Spinbox(ctrl, from_=1, to=20, width=4, font=FONT_BODY)
        self.top_n.delete(0, "end"); self.top_n.insert(0, "5")
        self.top_n.pack(side="left", padx=8)
        _btn(ctrl, "Search Mentors", self._search, w=16).pack(side="left")

        self.results = tk.Frame(self, bg=BG)
        self.results.pack(fill="both", expand=True, padx=12, pady=4)

    def refresh(self, **_): self._search()

    def _search(self):
        for w in self.results.winfo_children():
            w.destroy()
        u = self.app.current_user
        if not u or u["role"] != "mentee":
            _lbl(self.results, "Only mentees can search for mentors.", fg=DANGER).pack()
            return
        matches = matching.find_matches(u["user_id"], top_n=int(self.top_n.get() or 5))
        if not matches:
            _lbl(self.results, "No mentors found.", fg=MUTED).pack(pady=20)
            return

        canvas = tk.Canvas(self.results, bg=BG, highlightthickness=0)
        sb = ttk.Scrollbar(self.results, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for mentor, score in matches:
            card = _card(inner)
            card.pack(fill="x", pady=5, padx=4)

            top_row = tk.Frame(card, bg=WHITE)
            top_row.pack(fill="x")
            _lbl(top_row, mentor["name"], FONT_TITLE, NAVY, WHITE).pack(side="left")
            tk.Label(top_row, text=f"  Match: {score:.1f}/100  ",
                     font=FONT_SMALL, fg="#F8FAFC",
                     bg=SUCCESS if score >= 50 else MUTED, padx=6, pady=2).pack(side="right")
            _sep(card).pack(fill="x", pady=4)

            info = tk.Frame(card, bg=WHITE)
            info.pack(fill="x")
            for col_i, (lbl, val) in enumerate([
                ("Rating",     f"⭐ {mentor.get('rating', 0.0):.1f}"),
                ("Experience", f"{mentor.get('experience_years', 0)} yrs"),
                ("Contact",    mentor.get("contact_number", "—")),
                ("Skills",     ", ".join(mentor.get("skills", [])) or "—"),
            ]):
                f = tk.Frame(info, bg=WHITE)
                f.grid(row=0, column=col_i, sticky="w", padx=14)
                _lbl(f, lbl, FONT_LABEL, MUTED, WHITE).pack(anchor="w")
                _lbl(f, val, FONT_BODY,  TEXT,  WHITE).pack(anchor="w")

            _btn(card, "Book Session",
                 lambda mid=mentor["user_id"]: self.app.show("BookingFrame", mentor_id=mid),
                 bg=BLUE, w=14).pack(anchor="e", pady=6)


# ──────────────────────────── Booking ────────────────────────────

class BookingFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        title_bar = tk.Frame(self, bg=TAB_BLUE)
        title_bar.pack(fill="x")
        self.title_var = tk.StringVar(value="  Session Request")
        tk.Label(title_bar, textvariable=self.title_var, font=FONT_HEADER, fg=WHITE, bg=TAB_BLUE).pack(side="left", pady=5)
        _btn(title_bar, "← Back", lambda: self.app.show("DashboardFrame"),
               bg=HEADER_BG, w=10).pack(side="right", padx=8, pady=4)

        self.form = _card(self, 20, 14)
        self.form.pack(fill="x", padx=16, pady=10)
        hdr2 = tk.Frame(self.form, bg=LIGHT_BLUE)
        hdr2.pack(fill="x", pady=(0, 10))
        _lbl(hdr2, "  Raise a Concern", FONT_HEADER, NAVY, LIGHT_BLUE).pack(side="left", pady=4)

        grid = tk.Frame(self.form, bg=WHITE)
        grid.pack(fill="x", padx=10)

        _lbl(grid, "Assigned Mentor:", bg=WHITE).grid(row=0, column=0, sticky="nw", pady=4, padx=(0, 8))
        self.assigned_mentor_var = tk.StringVar(value="Not assigned")
        tk.Label(
            grid,
            textvariable=self.assigned_mentor_var,
            font=FONT_BODY,
            fg=TEXT,
            bg=WHITE,
            anchor="w",
            justify="left",
        ).grid(row=0, column=1, sticky="w", pady=4)

        _lbl(grid, "Concern:", bg=WHITE).grid(row=1, column=0, sticky="nw", pady=4, padx=(0, 8))
        self.concern_text = tk.Text(grid, font=FONT_BODY, width=42, height=4, relief="solid", bd=1)
        self.concern_text.grid(row=1, column=1, pady=4, sticky="w")

        self.request_btn = _btn(grid, "Request Session", self._do_book, w=18)
        self.request_btn.grid(row=2, column=0, columnspan=2, pady=12)

        self.sessions_frame = tk.Frame(self, bg=BG)
        self.sessions_frame.pack(fill="both", expand=True, padx=16)

    def refresh(self, **_):
        import database as db
        u = self.app.current_user
        if u and u.get("role") == "mentor":
            self.title_var.set("  Manage Sessions")
        else:
            self.title_var.set("  Session Request")

        if u and u.get("role") == "mentee":
            if not self.form.winfo_manager():
                self.form.pack(fill="x", padx=16, pady=10, before=self.sessions_frame)

            mentor = db.get_assigned_mentor(u["user_id"])
            if mentor:
                self.assigned_mentor_var.set(f"{mentor['name']}  |  {mentor['email']}")
                self.concern_text.configure(state="normal")
                self.request_btn.configure(state="normal")
            else:
                self.assigned_mentor_var.set("No assigned mentor")
                self.concern_text.delete("1.0", "end")
                self.concern_text.configure(state="disabled")
                self.request_btn.configure(state="disabled")
        elif self.form.winfo_manager():
            self.form.pack_forget()
        self._load_sessions()

    def _do_book(self):
        u = self.app.current_user
        concern = self.concern_text.get("1.0", "end").strip()
        ok, msg = booking.book_session(mentee_id=u["user_id"], concern=concern)
        if ok:
            self.concern_text.delete("1.0", "end")
            messagebox.showinfo("Request Submitted", msg)
            self._load_sessions()
        else:
            messagebox.showerror("Request Failed", msg)

    def _load_sessions(self):
        for w in self.sessions_frame.winfo_children():
            w.destroy()
        u = self.app.current_user
        if not u:
            return

        hdr_f = tk.Frame(self.sessions_frame, bg=LIGHT_BLUE)
        hdr_f.pack(fill="x", pady=(6, 4))
        _lbl(hdr_f, "  Requests & Upcoming Sessions", FONT_HEADER, NAVY, LIGHT_BLUE).pack(side="left", pady=4)

        upcoming = booking.get_upcoming_sessions(u["user_id"])
        if not upcoming:
            _lbl(self.sessions_frame, "  No active requests or sessions.", fg=MUTED).pack(anchor="w")
        else:
            for s in upcoming:
                det = booking.get_session_details(s["session_id"])
                card = _card(self.sessions_frame)
                card.pack(fill="x", pady=3)
                other = det.get("mentor_name") if u["role"] == "mentee" else det.get("mentee_name")

                top_row = tk.Frame(card, bg=WHITE)
                top_row.pack(fill="x")

                unresolved_request = s.get("status") in ("requested", "pending") and not s.get("date")
                if unresolved_request:
                    concern = det.get("concern", "-")
                    _lbl(
                        top_row,
                        f"Concern: {concern}",
                        FONT_BODY,
                        TEXT,
                        WHITE,
                        wraplength=720,
                        justify="left",
                    ).pack(side="left")
                else:
                    _lbl(
                        top_row,
                        f"{s['date']}  {s['time']}   -   {s['topic']}",
                        FONT_BODY,
                        TEXT,
                        WHITE,
                    ).pack(side="left")

                sc = (
                    BLUE if s.get("status") == "requested" else
                    "#FD7E14" if s.get("status") == "pending" and unresolved_request else
                    SUCCESS if s.get("status") == "confirmed" else
                    DANGER if s.get("status") == "cancelled" else
                    MUTED
                )
                tk.Label(
                    top_row,
                    text=f"  {s['status'].upper()}  ",
                    font=FONT_SMALL,
                    fg="#F8FAFC",
                    bg=sc,
                    padx=4,
                    pady=2,
                ).pack(side="right")

                detail = f"  Session ID: {s['session_id']}   |   With: {other}"
                if unresolved_request and s.get("requested_at"):
                    detail += f"   |   Requested: {_format_timestamp(s['requested_at'])}"
                _lbl(card, detail, FONT_SMALL, MUTED, WHITE).pack(anchor="w")

                btn_row = tk.Frame(card, bg=WHITE)
                btn_row.pack(anchor="e", pady=4)
                if u["role"] == "mentor" and unresolved_request:
                    _btn(
                        btn_row,
                        "Resolve",
                        lambda sid=s["session_id"]: self._resolve_and_message(sid),
                        bg=TAB_BLUE,
                        w=10,
                    ).pack(side="left", padx=4)
                    _btn(
                        btn_row,
                        "Resolved",
                        lambda sid=s["session_id"]: self._mark_resolved(sid),
                        bg=SUCCESS,
                        w=10,
                    ).pack(side="left", padx=4)
                elif u["role"] == "mentor" and s.get("status") == "pending":
                    _btn(
                        btn_row,
                        "Confirm",
                        lambda sid=s["session_id"]: self._confirm(sid),
                        bg=SUCCESS,
                        w=10,
                    ).pack(side="left", padx=4)
                    _btn(
                        btn_row,
                        "Resolved",
                        lambda sid=s["session_id"]: self._mark_resolved(sid),
                        bg=SUCCESS,
                        w=10,
                    ).pack(side="left")
                elif u["role"] == "mentor" and s.get("status") == "confirmed":
                    _btn(
                        btn_row,
                        "Resolved",
                        lambda sid=s["session_id"]: self._mark_resolved(sid),
                        bg=SUCCESS,
                        w=10,
                    ).pack(side="left")
                else:
                    _btn(
                        btn_row,
                        "Cancel",
                        lambda sid=s["session_id"]: self._cancel(sid),
                        bg=DANGER,
                        w=10,
                    ).pack(side="left")

        resolved_sessions = booking.get_resolved_sessions(u["user_id"])
        if resolved_sessions:
            resolved_hdr = tk.Frame(self.sessions_frame, bg=LIGHT_BLUE)
            resolved_hdr.pack(fill="x", pady=(14, 4))
            _lbl(resolved_hdr, "  Previously Resolved", FONT_HEADER, NAVY, LIGHT_BLUE).pack(side="left", pady=4)

            for s in resolved_sessions:
                det = booking.get_session_details(s["session_id"])
                card = _card(self.sessions_frame)
                card.pack(fill="x", pady=3)
                other = det.get("mentor_name") if u["role"] == "mentee" else det.get("mentee_name")

                top_row = tk.Frame(card, bg=WHITE)
                top_row.pack(fill="x")
                concern = det.get("concern") or s.get("topic") or "-"
                _lbl(
                    top_row,
                    f"Concern: {concern}",
                    FONT_BODY,
                    TEXT,
                    WHITE,
                    wraplength=720,
                    justify="left",
                ).pack(side="left")
                tk.Label(
                    top_row,
                    text="  RESOLVED  ",
                    font=FONT_SMALL,
                    fg="#F8FAFC",
                    bg=SUCCESS,
                    padx=4,
                    pady=2,
                ).pack(side="right")

                detail = f"  Session ID: {s['session_id']}   |   With: {other}"
                if s.get("resolved_at"):
                    detail += f"   |   Resolved: {_format_timestamp(s['resolved_at'])}"
                elif s.get("requested_at"):
                    detail += f"   |   Requested: {_format_timestamp(s['requested_at'])}"
                _lbl(card, detail, FONT_SMALL, MUTED, WHITE).pack(anchor="w")

    def _resolve_and_message(self, sid):
        session = booking.get_session_details(sid)
        if not session:
            messagebox.showerror("Session", "Session not found.")
            return

        ok, msg = booking.resolve_session_request(sid, self.app.current_user["user_id"])
        if not ok:
            messagebox.showerror("Session", msg)
            self._load_sessions()
            return

        current_user_id = self.app.current_user["user_id"]
        contact_id = session["mentee_id"] if current_user_id == session.get("mentor_id") else session.get("mentor_id")
        self.app.show("MessagingFrame", contact_id=contact_id, session_id=sid)

    def _mark_resolved(self, sid):
        ok, msg = booking.mark_session_resolved(sid, self.app.current_user["user_id"])
        if ok:
            messagebox.showinfo("Session", msg)
        else:
            messagebox.showerror("Session", msg)
        self._load_sessions()

    def _confirm(self, sid):
        ok, msg = booking.confirm_session(sid, self.app.current_user["user_id"])
        messagebox.showinfo("Session", msg); self._load_sessions()

    def _cancel(self, sid):
        ok, msg = booking.cancel_session(sid, self.app.current_user["user_id"])
        messagebox.showinfo("Session", msg); self._load_sessions()


# ──────────────────────────── Messaging ──────────────────────────

class MessagingFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._contact_id = None
        self._session_id = None
        self._inbox_data = []
        self._build()

    def _build(self):
        title_bar = tk.Frame(self, bg=TAB_BLUE)
        title_bar.pack(fill="x")
        _lbl(title_bar, "  Messages", FONT_HEADER, "#F8FAFC", TAB_BLUE).pack(side="left", pady=6)
        _btn(title_bar, "← Back", lambda: self.app.show("DashboardFrame"), bg=HEADER_BG, w=10).pack(
            side="right", padx=8, pady=4
        )

        pane = tk.PanedWindow(self, orient="horizontal", bg=BG, sashwidth=6, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=10, pady=10)

        left = _card(self, 0, 0)
        pane.add(left, minsize=320)
        tk.Label(left, text="  Conversations", font=FONT_HEADER, fg=NAVY, bg=LIGHT_BLUE, anchor="w").pack(
            fill="x", pady=(0, 4)
        )
        self.inbox_lb = tk.Listbox(
            left,
            font=FONT_BODY,
            width=34,
            bg="#0B1220",
            fg=TEXT,
            selectbackground=BLUE,
            selectforeground="#F8FAFC",
            exportselection=False,
            relief="flat",
            bd=0,
            highlightthickness=0,
            activestyle="none",
        )
        self.inbox_lb.pack(fill="both", expand=True, padx=6, pady=6)
        self.inbox_lb.bind("<<ListboxSelect>>", self._on_select)

        right = _card(self, 0, 0)
        pane.add(right, minsize=760)
        self.chat_title_var = tk.StringVar(value="  Chat")
        self.chat_meta_var = tk.StringVar(value="")
        chat_head = tk.Frame(right, bg=LIGHT_BLUE)
        chat_head.pack(fill="x")
        tk.Label(chat_head, textvariable=self.chat_title_var, font=FONT_HEADER, fg=NAVY, bg=LIGHT_BLUE, anchor="w").pack(fill="x")
        tk.Label(chat_head, textvariable=self.chat_meta_var, font=FONT_SMALL, fg=MUTED, bg=LIGHT_BLUE, anchor="w").pack(
            fill="x", padx=8, pady=(0, 6)
        )

        chat_wrap = tk.Frame(right, bg=WHITE)
        chat_wrap.pack(fill="both", expand=True, padx=6, pady=6)
        self.chat_canvas = tk.Canvas(chat_wrap, bg="#0B1220", highlightthickness=0)
        self.chat_scroll = ttk.Scrollbar(chat_wrap, orient="vertical", command=self.chat_canvas.yview)
        self.chat_canvas.configure(yscrollcommand=self.chat_scroll.set)
        self.chat_scroll.pack(side="right", fill="y")
        self.chat_canvas.pack(side="left", fill="both", expand=True)
        self.chat_body = tk.Frame(self.chat_canvas, bg="#0B1220")
        self.chat_canvas.create_window((0, 0), window=self.chat_body, anchor="nw")
        self.chat_body.bind("<Configure>", lambda e: self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all")))

        send_row = tk.Frame(right, bg=WHITE, pady=6)
        send_row.pack(fill="x", padx=6, pady=(0, 6))
        self.msg_entry = _entry(send_row, width=42)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.msg_entry.bind("<Return>", lambda _: self._send())
        _btn(send_row, "Send", self._send, w=8).pack(side="left")

    @staticmethod
    def _normalize_text(value: str, limit: int = 72) -> str:
        clean = " ".join((value or "").split())
        if len(clean) <= limit:
            return clean
        return clean[: limit - 3].rstrip() + "..."

    def refresh(self, contact_id=None, session_id=None, **_):
        u = self.app.current_user
        if not u:
            return

        self._contact_id = None
        self._session_id = None
        self.inbox_lb.delete(0, "end")
        self._inbox_data = messaging.get_inbox(u["user_id"])
        for idx, item in enumerate(self._inbox_data, start=1):
            label = self._normalize_text(item.get("thread_label", "Untitled thread"), limit=74)
            count = item.get("message_count", 0)
            self.inbox_lb.insert("end", f" {idx:02d}. {label} ({count})")

        if self._inbox_data:
            selected_index = 0
            if session_id:
                for idx, item in enumerate(self._inbox_data):
                    if item.get("session_id") == session_id:
                        selected_index = idx
                        break
            elif contact_id:
                for idx, item in enumerate(self._inbox_data):
                    if item["contact_id"] == contact_id:
                        selected_index = idx
                        break
            self._select_thread(selected_index)
        else:
            self.chat_title_var.set("  Chat")
            self.chat_meta_var.set("")
            self._render_empty("No conversation available yet.")

    def _on_select(self, _):
        sel = self.inbox_lb.curselection()
        if not sel:
            return
        self._select_thread(sel[0])

    def _select_thread(self, index):
        self.inbox_lb.selection_clear(0, "end")
        self.inbox_lb.selection_set(index)
        self.inbox_lb.activate(index)

        thread = self._inbox_data[index]
        self._contact_id = thread["contact_id"]
        self._session_id = thread.get("session_id")
        self.chat_title_var.set(f"  {thread.get('issue_title', 'Chat')}")

        meta_parts = [f"With: {thread['contact_name']}"]
        if thread.get("session_id"):
            meta_parts.append(f"Session ID: {thread['session_id']}")
        if thread.get("status"):
            meta_parts.append(thread["status"].upper())
        self.chat_meta_var.set("  " + "   |   ".join(meta_parts))
        self._load_chat()

    def _load_chat(self):
        u = self.app.current_user
        msgs = messaging.get_conversation(
            u["user_id"],
            self._contact_id,
            session_id=self._session_id,
        )
        contact_name = next(
            (
                item["contact_name"]
                for item in self._inbox_data
                if item["contact_id"] == self._contact_id and item.get("session_id") == self._session_id
            ),
            "Contact",
        )
        for w in self.chat_body.winfo_children():
            w.destroy()

        if not msgs:
            self._render_empty("No messages yet for this issue. Start the conversation here.")
        else:
            for idx, m in enumerate(msgs, start=1):
                is_current_user = m["sender_id"] == u["user_id"]
                sender_name = u.get("name", "User") if is_current_user else contact_name
                timestamp = _format_timestamp(m.get("timestamp", ""))
                self._add_bubble(idx, sender_name, timestamp, m["content"], mine=is_current_user)

        self.chat_canvas.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _render_empty(self, text):
        for w in self.chat_body.winfo_children():
            w.destroy()
        holder = tk.Frame(self.chat_body, bg="#0B1220")
        holder.pack(fill="both", expand=True, pady=22)
        _lbl(holder, text, FONT_BODY, MUTED, "#0B1220").pack(anchor="center")

    def _add_bubble(self, index, sender_name, timestamp, message, mine=False):
        row = tk.Frame(self.chat_body, bg="#0B1220")
        row.pack(fill="x", pady=6, padx=10)

        bubble_bg = "#0B7285" if mine else "#1F2937"
        bubble_border = "#22D3EE" if mine else "#334155"
        fg = "#F8FAFC" if mine else "#E5E7EB"

        bubble = tk.Frame(row, bg=bubble_bg, highlightthickness=1, highlightbackground=bubble_border)
        bubble.pack(side="right" if mine else "left", padx=4)

        _lbl(
            bubble,
            f" #{index:02d}  {sender_name}   {timestamp} ",
            ("Segoe UI", 9, "bold"),
            "#A5F3FC" if mine else "#94A3B8",
            bubble_bg,
        ).pack(anchor="w", padx=8, pady=(6, 2))
        _lbl(
            bubble,
            f" {self._normalize_text(message, limit=320)} ",
            FONT_BODY,
            fg,
            bubble_bg,
            wraplength=560,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(0, 8))

        _animate_panel_entry(bubble, start_color="#60A5FA", end_color=bubble_border, steps=7, delay=14)

    def _send(self):
        u = self.app.current_user
        if not self._contact_id:
            messagebox.showwarning("No Contact", "Select an issue thread first.")
            return
        ok, info, _ = messaging.send_message(
            u["user_id"],
            self._contact_id,
            self.msg_entry.get().strip(),
            session_id=self._session_id,
        )
        if ok:
            self.msg_entry.delete(0, "end")
            self.refresh(contact_id=self._contact_id, session_id=self._session_id)
        else:
            messagebox.showerror("Send Failed", info)


# ──────────────────────────── Feedback ───────────────────────────

class FeedbackFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self.fb_session_var = tk.StringVar()
        self._feedback_sessions = []
        self._build()

    def _build(self):
        title_bar = tk.Frame(self, bg=TAB_BLUE); title_bar.pack(fill="x")
        _lbl(title_bar, "  Feedback & Reviews", FONT_HEADER, WHITE, TAB_BLUE).pack(side="left", pady=5)
        _btn(title_bar, "← Back", lambda: self.app.show("DashboardFrame"),
               bg=HEADER_BG, w=10).pack(side="right", padx=8, pady=4)

        form = _card(self, 20, 14); form.pack(fill="x", padx=16, pady=10)
        hdr2 = tk.Frame(form, bg=LIGHT_BLUE); hdr2.pack(fill="x", pady=(0, 10))
        _lbl(hdr2, "  Submit Feedback", FONT_HEADER, NAVY, LIGHT_BLUE).pack(side="left", pady=4)

        grid = tk.Frame(form, bg=WHITE); grid.pack()
        _lbl(grid, "Session ID:", bg=WHITE).grid(row=0, column=0, sticky="w", pady=4, padx=(0, 8))
        self.fb_session = ttk.Combobox(
            grid,
            textvariable=self.fb_session_var,
            font=FONT_BODY,
            width=42,
            state="readonly",
        )
        self.fb_session.grid(row=0, column=1, pady=4, sticky="w")
        _lbl(grid, "Rating (1-5):", bg=WHITE).grid(row=1, column=0, sticky="w", pady=4, padx=(0, 8))
        self.fb_rating = tk.Spinbox(grid, from_=1, to=5, width=5, font=FONT_BODY)
        self.fb_rating.grid(row=1, column=1, sticky="w", pady=4)
        _lbl(grid, "Comment:", bg=WHITE).grid(row=2, column=0, sticky="nw", pady=4, padx=(0, 8))
        self.fb_comment = tk.Text(grid, font=FONT_BODY, width=30, height=3, relief="solid", bd=1)
        self.fb_comment.grid(row=2, column=1, pady=4)
        _btn(grid, "Submit Feedback", self._submit, w=18).grid(row=3, column=0, columnspan=2, pady=10)

        self.rev_frame = tk.Frame(self, bg=BG); self.rev_frame.pack(fill="both", expand=True, padx=16)

    def refresh(self, **_):
        self._load_feedback_sessions()
        self._load_reviews()

    def _submit(self):
        u = self.app.current_user
        session_id = self.fb_session_var.get().strip()
        if not session_id:
            messagebox.showwarning("No Session", "No session is available in the feedback dropdown.")
            return

        selected_session = next(
            (session for session in self._feedback_sessions if session.get("session_id") == session_id),
            None,
        )
        if selected_session:
            if selected_session.get("already_reviewed"):
                messagebox.showwarning("Already Reviewed", "You have already submitted feedback for this session.")
                return
            if selected_session.get("status") != "completed":
                messagebox.showwarning(
                    "Session Not Completed",
                    "This session ID was imported from your session list, but feedback can only be submitted after the session is completed.",
                )
                return

        ok, msg = fb.submit_feedback(
            session_id, u["user_id"],
            int(self.fb_rating.get()), self.fb_comment.get("1.0", "end").strip())
        if ok:
            self.fb_comment.delete("1.0", "end")
            self.fb_rating.delete(0, "end")
            self.fb_rating.insert(0, "1")
            messagebox.showinfo("Feedback", msg)
            self._load_feedback_sessions()
            self._load_reviews()
        else:  messagebox.showerror("Error", msg)

    def _load_feedback_sessions(self):
        u = self.app.current_user
        if not u:
            self.fb_session_var.set("")
            self.fb_session.configure(values=(), state="disabled")
            return

        self._feedback_sessions = fb.get_feedback_session_options(u["user_id"])
        options = [session["session_id"] for session in self._feedback_sessions]

        self.fb_session.configure(values=options)
        if options:
            self.fb_session.configure(state="readonly")
            if self.fb_session_var.get() not in options:
                self.fb_session_var.set(options[0])
        else:
            self.fb_session_var.set("")
            self.fb_session.configure(state="disabled")

    def _load_reviews(self):
        for w in self.rev_frame.winfo_children(): w.destroy()
        u = self.app.current_user
        if not u: return
        summary = fb.get_feedback_summary(u["user_id"])
        hdr_f = tk.Frame(self.rev_frame, bg=LIGHT_BLUE); hdr_f.pack(fill="x", pady=(4, 6))
        _lbl(hdr_f,
             f"  Your Average Rating: ⭐ {summary['average_rating']}  ({summary['total_reviews']} reviews)",
             FONT_HEADER, NAVY, LIGHT_BLUE).pack(side="left", pady=4)
        for review in fb.get_recent_reviews(u["user_id"]):
            card = _card(self.rev_frame); card.pack(fill="x", pady=3)
            _lbl(card, "⭐" * review["rating"] + f"  by {review['reviewer_name']}",
                 FONT_BODY, TEXT, WHITE).pack(anchor="w")
            if review.get("comment"):
                _lbl(card, review["comment"], FONT_SMALL, MUTED, WHITE,
                     wraplength=600).pack(anchor="w", pady=(2, 0))


# ──────────────────────────── Analytics ──────────────────────────

class AnalyticsFrame(tk.Frame):
    def __init__(self, parent, app: MentorApp):
        super().__init__(parent, bg=BG)
        self.app = app
        self._build()

    def _build(self):
        title_bar = tk.Frame(self, bg=TAB_BLUE); title_bar.pack(fill="x")
        _lbl(title_bar, "  Top Mentors — Leaderboard", FONT_HEADER, WHITE, TAB_BLUE).pack(side="left", pady=5)
        _btn(title_bar, "← Back", lambda: self.app.show("DashboardFrame"),
               bg=HEADER_BG, w=10).pack(side="right", padx=8, pady=4)

        ctrl = tk.Frame(self, bg=BG, pady=8, padx=14); ctrl.pack(fill="x")
        _lbl(ctrl, "Sort by:", bg=BG).pack(side="left")
        self.sort_var = ttk.Combobox(ctrl, values=["composite", "rating", "sessions"],
                                     state="readonly", width=14)
        self.sort_var.current(0); self.sort_var.pack(side="left", padx=8)
        _btn(ctrl, "Refresh", self.refresh, w=10).pack(side="left")

        self.body = tk.Frame(self, bg=BG); self.body.pack(fill="both", expand=True, padx=14)

    def refresh(self, **_):
        for w in self.body.winfo_children(): w.destroy()
        sort = self.sort_var.get() if hasattr(self, "sort_var") else "composite"
        summary = analytics.platform_summary()

        info = _card(self.body); info.pack(fill="x", pady=6)
        _lbl(info,
             f"Platform:   {summary['total_mentors']} Mentors   |   "
             f"{summary['total_mentees']} Mentees   |   "
             f"Avg Rating ⭐ {summary['avg_platform_rating']}   |   "
             f"Sessions: {summary['sessions']['total']}",
             FONT_BODY, NAVY, WHITE).pack(anchor="w")

        style = ttk.Style()
        style.configure("KIIT.Treeview.Heading",
                        background=BLUE, foreground="white", font=FONT_LABEL)
        style.configure("KIIT.Treeview", rowheight=26, font=FONT_BODY)
        style.map("KIIT.Treeview",
                  background=[("selected", LIGHT_BLUE)],
                  foreground=[("selected", NAVY)])

        cols = ("Rank", "Name", "Contact", "Rating", "Sessions", "Score")
        tree = ttk.Treeview(self.body, columns=cols, show="headings",
                            height=14, style="KIIT.Treeview")
        for col, w in zip(cols, [50, 200, 130, 80, 80, 80]):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")

        sb = ttk.Scrollbar(self.body, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True, pady=6)

        for m in analytics.top_mentors(n=15, sort_by=sort):
            tree.insert("", "end", values=(
                f"#{m['rank']}", m["name"],
                m.get("contact_number", "—"),
                f"⭐ {m['rating']:.1f}",
                m["sessions_completed"],
                f"{m['composite_score']:.2f}",
            ))
