# MAA Task Bar Hero
# Concept and direction by Marcus Xu.
# Built with Codex as a coding assistant.
# Shared for learning, experimentation, and automation research.

import json
import os
import ctypes
from ctypes import wintypes
from pathlib import Path
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog
from tkinter import scrolledtext
from tkinter import messagebox
from tkinter import ttk

from config import CONFIG_FILE_NAME, get_base_dir, get_config
from debug_files import (
    clear_generated_debug_files,
    export_debug_zip,
    get_export_default_path,
    has_significant_error,
    refresh_stale_debug_zip_selection,
)
from route_config import AVAILABLE_LEVELS, build_display_name


BASE_DIR = get_base_dir()
OUTPUT_FILE = BASE_DIR / "farm_plan.json"
MAIN_FILE = BASE_DIR / "main.py"
BOT_CONSOLE_LOG = BASE_DIR / "bot_console.log"
APP_VERSION = "v1.2, 2026-06-12"

INVISIBLE_UNICODE_TRANSLATION = {
    ord("\u200b"): None,
    ord("\u200c"): None,
    ord("\u200d"): None,
    ord("\ufeff"): None,
}


def configure_console_encoding():
    for stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue

        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def sanitize_text_for_output(value):
    return str(value).translate(INVISIBLE_UNICODE_TRANSLATION)


configure_console_encoding()

RECOMMENDED_GUIDE_LEVELS = [
    "Level 80 | Torment | Chapter 1 | Level 1-3",
    "Level 65 | Hell | Chapter 2 | Level 2-5",
    "Level 50 | Nightmare | Chapter 3 | Level 3-5",
    "Level 40 | Nightmare | Chapter 1 | Level 1-9",
    "Level 30 | Normal | Chapter 3 | Level 3-8",
    "Level 20 | Normal | Chapter 2 | Level 2-8",
    "Level 15 | Normal | Chapter 2 | Level 2-3",
    "Level 10 | Normal | Chapter 1 | Level 1-8",
    "Level 5 | Normal | Chapter 1 | Level 1-4",
    "Normal | Chapter 1 | Level 1-1",
]

RECOMMENDED_GUIDE_ROUTES = [
    ("torment", "chapter_1", "1-3"),
    ("hell", "chapter_2", "2-5"),
    ("nightmare", "chapter_3", "3-5"),
    ("nightmare", "chapter_1", "1-9"),
    ("normal", "chapter_3", "3-8"),
    ("normal", "chapter_2", "2-8"),
    ("normal", "chapter_2", "2-3"),
    ("normal", "chapter_1", "1-8"),
    ("normal", "chapter_1", "1-4"),
    ("normal", "chapter_1", "1-1"),
]

DIFFICULTY_OPTIONS = [
    ("normal", "Normal"),
    ("nightmare", "Nightmare"),
    ("hell", "Hell"),
    ("torment", "Torment"),
]

# The GUI no longer offers a recognition mode choice; it always saves balanced.
GUI_RECOGNITION_MODE = "balanced"

# GUI display labels are localized; config/internal values remain English.
DIFFICULTY_LABELS = {
    key: label for key, label in DIFFICULTY_OPTIONS
}
DIFFICULTY_KEYS_BY_LABEL = {
    label: key for key, label in DIFFICULTY_OPTIONS
}

WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
EMERGENCY_HOTKEY_ID = 0x4DAA
MODIFIER_FLAGS = {
    "alt": 0x0001,
    "ctrl": 0x0002,
    "control": 0x0002,
    "shift": 0x0004,
    "win": 0x0008,
}
FUNCTION_KEY_VK = {
    f"F{index}": 0x70 + index - 1
    for index in range(1, 25)
}

try:
    USER32 = ctypes.WinDLL("user32", use_last_error=True) if os.name == "nt" else None
    KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True) if os.name == "nt" else None
except Exception:
    USER32 = None
    KERNEL32 = None


class POINT(ctypes.Structure):
    _fields_ = [
        ("x", wintypes.LONG),
        ("y", wintypes.LONG),
    ]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


if USER32 is not None:
    USER32.RegisterHotKey.argtypes = [
        wintypes.HWND,
        ctypes.c_int,
        wintypes.UINT,
        wintypes.UINT,
    ]
    USER32.RegisterHotKey.restype = wintypes.BOOL
    USER32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    USER32.UnregisterHotKey.restype = wintypes.BOOL
    USER32.GetMessageW.argtypes = [
        ctypes.POINTER(MSG),
        wintypes.HWND,
        wintypes.UINT,
        wintypes.UINT,
    ]
    USER32.GetMessageW.restype = ctypes.c_int
    USER32.PostThreadMessageW.argtypes = [
        wintypes.DWORD,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    ]
    USER32.PostThreadMessageW.restype = wintypes.BOOL

if KERNEL32 is not None:
    # GetCurrentThreadId is exported by kernel32.dll, not user32.dll.
    KERNEL32.GetCurrentThreadId.argtypes = []
    KERNEL32.GetCurrentThreadId.restype = wintypes.DWORD


def config_bool_value(name, default):
    value = get_config().get(name, default)

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}

    return bool(value)


def parse_emergency_hotkey_config():
    modifiers_text = str(
        get_config().get("emergency_hotkey_modifiers", "ctrl+shift")
    ).strip()
    key_text = str(get_config().get("emergency_hotkey_key", "F12")).strip().upper()

    modifiers = 0
    display_parts = []

    for part in re.split(r"[+\s]+", modifiers_text.lower()):
        if not part:
            continue

        flag = MODIFIER_FLAGS.get(part)

        if flag is None:
            continue

        modifiers |= flag
        display_parts.append("Ctrl" if part in {"ctrl", "control"} else part.title())

    if key_text in FUNCTION_KEY_VK:
        vk = FUNCTION_KEY_VK[key_text]
    elif len(key_text) == 1 and key_text.isalnum():
        vk = ord(key_text)
    else:
        vk = None

    display = " + ".join(display_parts + ([key_text] if key_text else []))
    return modifiers, vk, display or "Ctrl + Shift + F12"

KEY_INFO_LINES = [
    "Before using, make sure the following are ready:",
    "",
    "1. Keep every extracted file in a fixed location. Do not move or delete files. Non-ASCII paths are not recommended.",
    "2. Open the map so the level list is visible. If storage transfer is enabled, open the storage screen too.",
    "3. Keep chest drop UI opaque, UI size at 1x, and the battle log in a fixed-window state.",
    "4. Recommended setup is 1080p with 100% Windows scaling. 2K, 3K, and 4K are supported where possible, but not guaranteed on every device.",
    "5. Keep game zoom at 1x / 100%. 1.25x, 1.5x, and 2x game/browser zoom are not supported.",
    "6. MAA may take over the mouse while switching levels. Do not use the mouse until switching is complete; recovery usually settles in 10-20 seconds.",
    "7. Emergency Stop: Ctrl + Shift + F12. This hotkey can safely stop MAA at any time.",
]

class RoutePlannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"MAA Task Bar Hero - {APP_VERSION}")
        self.root.geometry("1180x840")
        self.root.minsize(1040, 760)

        self.selected_routes = []
        self.available_level_items = []
        self.bot_process = None
        self.bot_log_handle = None
        self.log_read_position = 0
        self.is_closing = False
        self.hotkey_registered = False
        self.hotkey_polling = False
        self.hotkey_thread = None
        self.hotkey_thread_id = None
        self.hotkey_thread_started = threading.Event()
        self.emergency_stop_pending = False
        self.emergency_hotkey_enabled = config_bool_value("emergency_hotkey_enabled", True)
        self.emergency_hotkey_modifiers, self.emergency_hotkey_vk, self.emergency_hotkey_display = (
            parse_emergency_hotkey_config()
        )
        self.last_navigation_failure_warning = ""
        self.notified_warning_keys = set()
        self.status_var = tk.StringVar(value="Ready: choose routes, then save and start the bot.")
        self.background_input_var = tk.BooleanVar(value=False)
        self.move_to_storage_var = tk.BooleanVar(
            value=bool(get_config().get("move_backpack_to_storage_after_blue_chest", False))
        )
        self.move_to_storage_after_non_blue_var = tk.BooleanVar(
            value=config_bool_value("move_backpack_to_storage_after_non_blue_box", True)
        )
        self.stack_stash_var = tk.BooleanVar(
            value=config_bool_value("stack_stash_after_transfer", True)
        )
        self.rune_of_opening_var = tk.BooleanVar(
            value=config_bool_value("has_rune_of_opening", False)
        )
        self.repeat_same_level_var = tk.BooleanVar(
            value=config_bool_value("repeat_same_level_after_blue_chest", False)
        )
        self.same_tier_substitution_var = tk.BooleanVar(
            value=config_bool_value("same_tier_substitution_enabled", True)
        )
        self.no_chest_retries_var = tk.StringVar(value=str(self.get_default_no_chest_retries()))
        self.difficulty_var = tk.StringVar(value="normal")
        self.difficulty_display_var = tk.StringVar(value=DIFFICULTY_LABELS.get("normal", "Normal"))

        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TLabelframe.Label", font=("Segoe UI", 11, "bold"))

        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=0)
        root.rowconfigure(1, weight=3)
        root.rowconfigure(2, weight=0)
        root.rowconfigure(3, weight=2)

        # Top: usage info on the left, recommendation guide on the right.
        top_frame = tk.Frame(root)
        top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)

        key_info_frame = tk.LabelFrame(top_frame, text="Key Info")
        key_info_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        key_info_frame.columnconfigure(0, weight=1)

        key_info_text = "\n".join(KEY_INFO_LINES)
        key_info_label = tk.Label(
            key_info_frame,
            text=key_info_text,
            anchor="nw",
            justify="left",
            wraplength=520,
            fg="#333333",
        )
        key_info_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=6)
        # Wrap at the frame's real width so the long English lines use fewer rows.
        key_info_label.bind(
            "<Configure>",
            lambda event: event.widget.configure(wraplength=max(200, event.width - 4)),
        )

        guide_frame = tk.LabelFrame(top_frame, text="Recommended Farming Guide")
        guide_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        guide_frame.columnconfigure(0, weight=1)

        guide_text = "\n".join(RECOMMENDED_GUIDE_LEVELS)
        tk.Label(
            guide_frame,
            text=guide_text,
            anchor="w",
            justify="left",
            wraplength=440,
            fg="#333333",
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=6)

        guide_button_frame = tk.Frame(guide_frame)
        guide_button_frame.grid(row=0, column=1, sticky="e", padx=8, pady=6)

        tk.Button(
            guide_button_frame,
            text="Use Recommended",
            width=16,
            command=self.load_recommended_plan,
        ).grid(row=0, column=0, pady=(0, 4))

        tk.Button(
            guide_button_frame,
            text="Save and Start",
            width=16,
            command=self.start_recommended_plan,
        ).grid(row=1, column=0)

        # Middle: route planner.
        planner_frame = tk.LabelFrame(root, text="Route Selection")
        planner_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)
        planner_frame.columnconfigure(0, weight=1)
        planner_frame.columnconfigure(2, weight=1)
        planner_frame.rowconfigure(2, weight=1)

        # Left: difficulty dropdown + filtered levels.
        filter_frame = tk.Frame(planner_frame)
        filter_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(8, 4))
        filter_frame.columnconfigure(1, weight=1)

        tk.Label(filter_frame, text="Difficulty:").grid(row=0, column=0, sticky="w")

        difficulty_menu = tk.OptionMenu(
            filter_frame,
            self.difficulty_display_var,
            *[label for _key, label in DIFFICULTY_OPTIONS],
            command=self.on_difficulty_changed,
        )
        difficulty_menu.grid(row=0, column=1, sticky="w", padx=(8, 0))

        tk.Label(planner_frame, text="Available Levels").grid(
            row=1, column=0, sticky="n", padx=(0, 10), pady=(0, 0)
        )

        self.available_listbox = tk.Listbox(planner_frame, width=52, height=16, exportselection=False)
        self.available_listbox.grid(row=2, column=0, sticky="nsew", padx=(8, 10), pady=(24, 8))

        # Middle buttons.
        button_frame = tk.Frame(planner_frame)
        button_frame.grid(row=2, column=1, sticky="n", padx=8, pady=(24, 8))

        # Two columns so all six buttons stay visible when the window is short.
        tk.Button(button_frame, text="Add →", width=11, command=self.add_selected).grid(row=0, column=0, padx=2, pady=4)
        tk.Button(button_frame, text="← Remove", width=11, command=self.remove_selected).grid(row=0, column=1, padx=2, pady=4)
        tk.Button(button_frame, text="Move Up", width=11, command=self.move_up).grid(row=1, column=0, padx=2, pady=4)
        tk.Button(button_frame, text="Move Down", width=11, command=self.move_down).grid(row=1, column=1, padx=2, pady=4)
        tk.Button(button_frame, text="Clear All", width=11, command=self.clear_plan).grid(row=2, column=0, padx=2, pady=4)
        tk.Button(button_frame, text="Load Routes", width=11, command=self.load_existing_plan).grid(row=2, column=1, padx=2, pady=4)

        # Right: selected plan.
        tk.Label(planner_frame, text="Current Farming Cycle").grid(
            row=1, column=2, sticky="n", padx=(10, 0), pady=(0, 0)
        )

        self.plan_listbox = tk.Listbox(planner_frame, width=52, height=16, exportselection=False)
        self.plan_listbox.grid(row=2, column=2, sticky="nsew", padx=(10, 8), pady=(24, 8))

        # Help text.
        help_text = (
            "Instructions: choose a difficulty on the left, then choose levels and add them to the cycle list.\n"
            "The right-side list runs in a loop automatically; no duplicate entries are needed.\n"
            "Retry count is saved to each route. More features are in development; bug reports are welcome.\n"
            "For questions or bug reports, contact Marcus-Xu-04 on GitHub or refer to the project release notes."
        )

        tk.Label(planner_frame, text=help_text, justify="left", anchor="w").grid(
            row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8)
        )

        # Controls.
        control_frame = tk.LabelFrame(root, text="Bot Control")
        control_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        control_frame.columnconfigure(4, weight=1)

        tk.Button(
            control_frame,
            text="Save and Start",
            width=18,
            command=self.start_bot,
        ).grid(row=0, column=0, padx=(10, 8), pady=(10, 4))

        tk.Button(
            control_frame,
            text="Stop",
            width=14,
            command=self.stop_bot,
        ).grid(row=0, column=1, padx=(0, 12), pady=(10, 4))

        tk.Button(
            control_frame,
            text="Export Debug ZIP",
            width=18,
            command=self.export_debug_zip,
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=(10, 8), pady=(0, 8))

        tk.Label(
            control_frame,
            text="Retries when no chest drops:",
            anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=(0, 4), pady=(10, 4))

        tk.Checkbutton(
            control_frame,
            text="Move backpack items to storage after blue chest",
            variable=self.move_to_storage_var,
        ).grid(row=1, column=2, columnspan=3, sticky="w", padx=(0, 10), pady=(4, 10))

        tk.Checkbutton(
            control_frame,
            text="Repeat the same level after a blue chest",
            variable=self.repeat_same_level_var,
        ).grid(row=1, column=4, sticky="w", padx=(14, 10), pady=(4, 10))

        tk.Checkbutton(
            control_frame,
            text="Try same-tier substitute when route navigation fails",
            variable=self.same_tier_substitution_var,
        ).grid(row=2, column=4, sticky="w", padx=(14, 10), pady=(0, 8))

        tk.Checkbutton(
            control_frame,
            text="Move backpack items to storage after brown/other chest",
            variable=self.move_to_storage_after_non_blue_var,
        ).grid(row=3, column=2, columnspan=2, sticky="w", padx=(0, 10), pady=(0, 8))

        tk.Checkbutton(
            control_frame,
            text="Stash All on stash tabs 1, 2, 3 in order (stacks items)",
            variable=self.stack_stash_var,
        ).grid(row=3, column=4, sticky="w", padx=(14, 10), pady=(0, 8))

        tk.Checkbutton(
            control_frame,
            text="I own the Rune of Opening (Space opens all chests)",
            variable=self.rune_of_opening_var,
        ).grid(row=2, column=2, columnspan=2, sticky="w", padx=(0, 10), pady=(0, 8))

        tk.Entry(
            control_frame,
            textvariable=self.no_chest_retries_var,
            width=6,
        ).grid(row=0, column=3, sticky="w", pady=(10, 4))

        tk.Label(
            control_frame,
            textvariable=self.status_var,
            anchor="w",
        ).grid(row=0, column=4, sticky="ew", padx=(14, 10), pady=(10, 4))

        tk.Checkbutton(
            control_frame,
            text="Background input mode (in development)",
            variable=self.background_input_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=(10, 8), pady=(4, 10))

        tk.Label(
            control_frame,
            text=f"Concept & Direction: Marcus Xu · Build {APP_VERSION}",
            anchor="e",
            fg="#666666",
        ).grid(row=4, column=2, columnspan=3, sticky="e", padx=(8, 10), pady=(0, 8))

        tk.Label(
            control_frame,
            text=f"Emergency stop hotkey: {self.emergency_hotkey_display}",
            anchor="w",
            fg="#444444",
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=(10, 8), pady=(0, 8))

        # Log panel.
        log_frame = tk.LabelFrame(root, text="Bot Log")
        log_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=9,
            state="disabled",
            wrap="word",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self.populate_available_levels()
        self.load_existing_plan(silent=True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.register_emergency_hotkey()
        self.root.after(1000, self.refresh_bot_status)

    def register_emergency_hotkey(self):
        if not self.emergency_hotkey_enabled:
            self.append_log_text("\n[GUI] Emergency stop hotkey disabled by config.\n")
            return

        if USER32 is None:
            self.append_log_text(
                "\n[GUI] Emergency stop hotkey unavailable: Windows user32 API not available.\n"
            )
            return

        if not self.emergency_hotkey_modifiers or self.emergency_hotkey_vk is None:
            self.append_log_text(
                "\n[GUI] Emergency stop hotkey registration failed: invalid hotkey config.\n"
            )
            return

        if self.hotkey_thread is not None and self.hotkey_thread.is_alive():
            self.append_log_text(
                "\n[GUI] Emergency hotkey registration skipped; thread already running.\n"
            )
            return

        self.hotkey_polling = True
        self.hotkey_thread_started.clear()
        self.hotkey_thread = threading.Thread(
            target=self.emergency_hotkey_message_loop,
            name="MAA-TBH-emergency-hotkey",
            daemon=True,
        )
        self.hotkey_thread.start()

    def unregister_emergency_hotkey(self):
        self.hotkey_polling = False

        if USER32 is None:
            return

        thread_id = self.hotkey_thread_id

        if thread_id:
            ok = USER32.PostThreadMessageW(thread_id, WM_QUIT, 0, 0)

            if not ok:
                error_code = ctypes.get_last_error()
                self.append_log_text(
                    "\n[GUI] Emergency hotkey WM_QUIT post failed | "
                    f"thread_id={thread_id} | error_code={error_code}\n"
                )

        if self.hotkey_thread is not None and self.hotkey_thread.is_alive():
            self.hotkey_thread.join(timeout=0.5)

            if self.hotkey_thread.is_alive():
                self.append_log_text(
                    "\n[GUI] Emergency hotkey thread did not exit before GUI close timeout.\n"
                )

    def notify_from_hotkey_thread(self, callback, *args):
        if self.is_closing:
            return

        try:
            self.root.after(0, callback, *args)
        except Exception:
            pass

    def notify_hotkey_log(self, text):
        self.notify_from_hotkey_thread(self.append_log_text, text)

    def notify_hotkey_status(self, text):
        self.notify_from_hotkey_thread(self.status_var.set, text)

    def emergency_hotkey_message_loop(self):
        thread_id = KERNEL32.GetCurrentThreadId()
        self.hotkey_thread_id = thread_id
        self.hotkey_thread_started.set()

        ok = USER32.RegisterHotKey(
            None,
            EMERGENCY_HOTKEY_ID,
            self.emergency_hotkey_modifiers,
            self.emergency_hotkey_vk,
        )

        if not ok:
            error_code = ctypes.get_last_error()
            self.hotkey_registered = False
            self.hotkey_polling = False
            self.hotkey_thread_id = None
            self.notify_hotkey_log(
                "\n[GUI] Emergency hotkey registration failed | "
                f"hotkey={self.emergency_hotkey_display} | "
                f"thread_id={thread_id} | hotkey_id={EMERGENCY_HOTKEY_ID} | "
                f"error_code={error_code}\n"
            )
            self.notify_hotkey_status(
                f"Emergency stop hotkey registration failed; GUI remains usable: {self.emergency_hotkey_display}"
            )
            return

        self.hotkey_registered = True
        self.notify_hotkey_log(
            "\n[GUI] Emergency hotkey registered | "
            f"hotkey={self.emergency_hotkey_display} | "
            f"modifiers={self.emergency_hotkey_modifiers} | "
            f"vk={self.emergency_hotkey_vk} | "
            f"thread_id={thread_id} | hotkey_id={EMERGENCY_HOTKEY_ID}\n"
        )

        msg = MSG()

        try:
            while True:
                result = USER32.GetMessageW(ctypes.byref(msg), None, 0, 0)

                if result == 0:
                    break

                if result == -1:
                    error_code = ctypes.get_last_error()
                    self.notify_hotkey_log(
                        "\n[GUI] Emergency hotkey message loop error | "
                        f"thread_id={thread_id} | error_code={error_code}\n"
                    )
                    break

                if msg.message == WM_HOTKEY and msg.wParam == EMERGENCY_HOTKEY_ID:
                    self.notify_hotkey_log(
                        "\n[GUI] Emergency hotkey WM_HOTKEY received | "
                        f"thread_id={thread_id} | hotkey_id={EMERGENCY_HOTKEY_ID}\n"
                    )
                    self.notify_from_hotkey_thread(self.handle_emergency_hotkey)
        finally:
            if self.hotkey_registered:
                USER32.UnregisterHotKey(None, EMERGENCY_HOTKEY_ID)
                self.hotkey_registered = False

            if self.hotkey_polling and not self.is_closing:
                self.notify_hotkey_log(
                    "\n[GUI] Emergency hotkey thread exited unexpectedly.\n"
                )

            self.hotkey_thread_id = None
            self.notify_hotkey_log(
                "\n[GUI] Emergency hotkey message loop exited.\n"
            )

    def handle_emergency_hotkey(self):
        self.append_log_text("\n[GUI] EMERGENCY STOP triggered by global hotkey\n")

        if self.bot_log_handle is not None:
            try:
                self.write_bot_console_log("EMERGENCY STOP triggered by global hotkey\n")
                self.bot_log_handle.flush()
            except Exception:
                pass

        self.emergency_stop_bot_process()

    def emergency_stop_bot_process(self):
        if self.emergency_stop_pending:
            return

        if self.bot_process is None or self.bot_process.poll() is not None:
            self.status_var.set("Emergency stop hotkey triggered: bot is not running.")
            self.append_log_text("[GUI] Emergency stop hotkey pressed; no bot process was running.\n")

            if self.bot_process is not None:
                self.bot_process = None
                self.close_bot_log_handle()

            return

        self.emergency_stop_pending = True
        self.status_var.set("Emergency stop hotkey triggered: stopping bot...")

        try:
            self.bot_process.terminate()
        except Exception as e:
            self.append_log_text(f"[GUI] Emergency terminate failed: {e}\n")

        self.root.after(750, self.finish_emergency_stop_bot_process)

    def finish_emergency_stop_bot_process(self):
        process = self.bot_process

        if process is None:
            self.emergency_stop_pending = False
            self.close_bot_log_handle()
            return

        try:
            if process.poll() is None:
                self.append_log_text("[GUI] Emergency stop escalating to process kill.\n")

                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        timeout=2,
                    )
                else:
                    process.kill()

            try:
                process.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
        except Exception as e:
            self.append_log_text(f"[GUI] Emergency kill/check failed: {e}\n")
        finally:
            self.bot_process = None
            self.emergency_stop_pending = False
            self.close_bot_log_handle()
            self.cleanup_after_clean_stop(process_exit_code=None, closing=False)
            self.status_var.set("Emergency stop executed: bot stopped.")

    def find_available_level(self, difficulty, chapter, level_name):
        for level in AVAILABLE_LEVELS:
            if (
                level.get("difficulty") == difficulty
                and level.get("chapter") == chapter
                and level.get("level") == level_name
            ):
                return level

        return None

    def build_recommended_plan(self):
        plan = []
        missing = []

        for difficulty, chapter, level_name in RECOMMENDED_GUIDE_ROUTES:
            level = self.find_available_level(difficulty, chapter, level_name)

            if level is None or not level.get("enabled", True):
                missing.append(f"{difficulty} {level_name}")
                continue

            plan.append(level.copy())

        return plan, missing

    def load_recommended_plan(self, show_message=True):
        plan, missing = self.build_recommended_plan()

        if not plan:
            messagebox.showwarning("Recommended routes unavailable", "No available recommended routes were found.")
            return False

        self.selected_routes = plan
        self.refresh_plan_listbox()
        self.status_var.set(f"Loaded {len(plan)} recommended route(s).")

        if show_message:
            if missing:
                messagebox.showwarning(
                    "Some recommended routes are missing",
                    "Loaded available recommended routes. These targets are unavailable:\n" + "\n".join(missing),
                )
            else:
                messagebox.showinfo("Recommended routes loaded", f"Loaded {len(plan)} recommended route(s).")

        return True

    def start_recommended_plan(self):
        if not self.load_recommended_plan(show_message=False):
            return

        self.start_bot()

    def get_default_no_chest_retries(self):
        config = get_config()

        if "default_no_chest_retries" in config:
            value = config.get("default_no_chest_retries")
        else:
            value = int(config.get("default_max_trials_if_no_chest", 1)) - 1

        try:
            value = int(value)
        except (TypeError, ValueError):
            return 0

        return max(0, value)

    def get_no_chest_retries_from_input(self):
        raw_value = self.no_chest_retries_var.get().strip()

        try:
            retries = int(raw_value)
        except ValueError:
            messagebox.showwarning(
                "Invalid retry count",
                "Retry count must be an integer greater than or equal to 0."
            )
            return None

        if retries < 0:
            messagebox.showwarning(
                "Invalid retry count",
                "Retry count must be an integer greater than or equal to 0."
            )
            return None

        return retries

    def save_gui_options_config(self):
        config_path = BASE_DIR / CONFIG_FILE_NAME

        try:
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as f:
                    config = json.load(f)
            else:
                config = get_config().copy()
        except (OSError, json.JSONDecodeError):
            config = get_config().copy()

        if not isinstance(config, dict):
            config = get_config().copy()

        config["recognition_mode"] = GUI_RECOGNITION_MODE
        config["same_tier_substitution_enabled"] = bool(self.same_tier_substitution_var.get())
        config["repeat_same_level_after_blue_chest"] = bool(self.repeat_same_level_var.get())
        config["move_backpack_to_storage_after_non_blue_box"] = bool(
            self.move_to_storage_after_non_blue_var.get()
        )
        config["stack_stash_after_transfer"] = bool(self.stack_stash_var.get())
        config["has_rune_of_opening"] = bool(self.rune_of_opening_var.get())

        with config_path.open("w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            f.write("\n")

    def format_level_label(self, level):
        # Built from the route fields, not the saved display_name, so plans saved
        # by older Chinese builds still show English labels.
        try:
            return build_display_name(level["difficulty"], level["level"])
        except (KeyError, ValueError):
            return str(level.get("display_name") or level.get("name", "Unknown route"))

    def on_difficulty_changed(self, display_label):
        self.difficulty_var.set(DIFFICULTY_KEYS_BY_LABEL.get(display_label, display_label))
        self.populate_available_levels()

    def populate_available_levels(self):
        self.available_listbox.delete(0, tk.END)
        self.available_level_items = []

        selected_difficulty = self.difficulty_var.get()

        for level in AVAILABLE_LEVELS:
            if level.get("difficulty") != selected_difficulty:
                continue

            self.available_level_items.append(level)
            label = self.format_level_label(level)

            if not level.get("enabled", True):
                note = level.get("note", "")
                label = f"[Unavailable] {label}"

                if note:
                    label += f" - {note}"

            self.available_listbox.insert(tk.END, label)

    def refresh_plan_listbox(self):
        self.plan_listbox.delete(0, tk.END)

        for i, level in enumerate(self.selected_routes, start=1):
            label = self.format_level_label(level)
            self.plan_listbox.insert(tk.END, f"{i}. {label}")

    def add_selected(self):
        selection = self.available_listbox.curselection()

        if not selection:
            return

        index = selection[0]
        level = self.available_level_items[index]

        if not level.get("enabled", True):
            messagebox.showwarning(
                "Level unavailable",
                f"{self.format_level_label(level)} cannot be added yet.\n\n"
                f"{level.get('note', '')}"
            )
            return

        self.selected_routes.append(level.copy())
        self.refresh_plan_listbox()

    def remove_selected(self):
        selection = self.plan_listbox.curselection()

        if not selection:
            return

        index = selection[0]
        self.selected_routes.pop(index)
        self.refresh_plan_listbox()

    def move_up(self):
        selection = self.plan_listbox.curselection()

        if not selection:
            return

        index = selection[0]

        if index == 0:
            return

        self.selected_routes[index - 1], self.selected_routes[index] = (
            self.selected_routes[index],
            self.selected_routes[index - 1],
        )

        self.refresh_plan_listbox()
        self.plan_listbox.selection_set(index - 1)

    def move_down(self):
        selection = self.plan_listbox.curselection()

        if not selection:
            return

        index = selection[0]

        if index >= len(self.selected_routes) - 1:
            return

        self.selected_routes[index + 1], self.selected_routes[index] = (
            self.selected_routes[index],
            self.selected_routes[index + 1],
        )

        self.refresh_plan_listbox()
        self.plan_listbox.selection_set(index + 1)

    def clear_plan(self):
        self.selected_routes = []
        self.refresh_plan_listbox()

    def save_plan(self, show_message=True):
        if not self.selected_routes:
            messagebox.showwarning(
                "No routes selected",
                "Please add at least one farming target to the route list."
            )
            return False

        no_chest_retries = self.get_no_chest_retries_from_input()

        if no_chest_retries is None:
            return False

        try:
            self.save_gui_options_config()
        except OSError as e:
            messagebox.showerror("Config save failed", f"Could not save settings to config.json:\n\n{e}")
            return False

        plan = []

        for i, level in enumerate(self.selected_routes, start=1):
            route = level.copy()
            route["name"] = f"Route {i}"
            route["no_chest_retries"] = no_chest_retries
            route.pop("max_trials_if_no_chest", None)
            plan.append(route)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=4, ensure_ascii=False)

        self.status_var.set(f"Saved {len(plan)} route(s) to {OUTPUT_FILE.name}.")

        if show_message:
            messagebox.showinfo(
                "Saved",
                f"Farming route saved to {OUTPUT_FILE.name}"
            )

        return True

    def start_bot(self):
        if self.bot_process is not None and self.bot_process.poll() is None:
            messagebox.showinfo("Bot already running", "Easy there, the bot is already running.")
            return

        if not self.save_plan(show_message=False):
            return

        frozen_app = getattr(sys, "frozen", False)

        if not frozen_app and not MAIN_FILE.exists():
            messagebox.showerror("Start failed", f"Could not find {MAIN_FILE}")
            return

        try:
            self.close_bot_log_handle()
            self.clear_log_text()
            self.log_read_position = 0
            self.bot_log_handle = open(BOT_CONSOLE_LOG, "w", encoding="utf-8", buffering=1)
            self.log_read_position = 0
            self.write_bot_console_log(
                f"=== Bot process started | timestamp={self.current_timestamp()} ===\n"
            )

            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            env = os.environ.copy()
            input_mode = "background" if self.background_input_var.get() else "foreground"
            env["MAATBH_INPUT_MODE"] = input_mode
            env["MAATBH_SHOW_PREVIEW"] = "0"
            env["MAATBH_ENABLE_BEEP"] = "0"
            env["MAATBH_AUTO_OPEN_BLUE"] = "1"
            env["MAATBH_NAVIGATE_ON_START"] = "1"
            env["MAATBH_MOVE_TO_STORAGE"] = "1" if self.move_to_storage_var.get() else "0"
            env["MAATBH_MOVE_TO_STORAGE_AFTER_NON_BLUE_BOX"] = (
                "1" if self.move_to_storage_after_non_blue_var.get() else "0"
            )
            env["MAATBH_REPEAT_SAME_LEVEL_AFTER_BLUE_CHEST"] = (
                "1" if self.repeat_same_level_var.get() else "0"
            )
            env["MAATBH_STACK_STASH_AFTER_TRANSFER"] = "1" if self.stack_stash_var.get() else "0"
            env["MAATBH_HAS_RUNE_OF_OPENING"] = "1" if self.rune_of_opening_var.get() else "0"
            env["PYTHONUNBUFFERED"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            self.write_bot_console_log(f"=== Input mode: {input_mode} ===\n")
            self.write_bot_console_log(f"=== Recognition mode: {GUI_RECOGNITION_MODE} ===\n")
            self.write_bot_console_log(
                f"=== Move backpack to storage: {'on' if self.move_to_storage_var.get() else 'off'} ===\n"
            )
            self.write_bot_console_log(
                "=== Move backpack to storage after non-blue box: "
                f"{'on' if self.move_to_storage_after_non_blue_var.get() else 'off'} ===\n"
            )
            self.write_bot_console_log(
                f"=== Repeat same level after blue chest: {'on' if self.repeat_same_level_var.get() else 'off'} ===\n"
            )
            self.write_bot_console_log(
                f"=== Stack stash pages after transfer: {'on' if self.stack_stash_var.get() else 'off'} ===\n"
            )
            self.write_bot_console_log(
                f"=== Rune of Opening (Space opens all chests): {'on' if self.rune_of_opening_var.get() else 'off'} ===\n"
            )
            bot_command = (
                [sys.executable, "--bot"]
                if frozen_app
                else [sys.executable, "-u", str(MAIN_FILE)]
            )

            self.bot_process = subprocess.Popen(
                bot_command,
                cwd=str(BASE_DIR),
                stdin=subprocess.PIPE,
                stdout=self.bot_log_handle,
                stderr=subprocess.STDOUT,
                creationflags=creationflags,
                env=env,
            )
            if self.bot_process.stdin is not None:
                self.bot_process.stdin.close()
            if input_mode == "background":
                self.status_var.set("Bot started: experimental background input mode. Disable this if the game does not respond.")
            else:
                self.status_var.set("Bot started: foreground mouse mode.")
        except Exception as e:
            self.close_bot_log_handle()
            self.bot_process = None
            messagebox.showerror("Start failed", f"Could not start main.py:\n\n{e}")

    def stop_bot(self):
        if not self.stop_bot_process():
            self.status_var.set("Bot is not currently running.")

    def export_debug_zip(self):
        self.prepare_debug_export_logs()

        default_path = get_export_default_path(BASE_DIR)
        zip_path = filedialog.asksaveasfilename(
            title="Export Debug ZIP",
            initialdir=str(default_path.parent),
            initialfile=default_path.name,
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )

        if not zip_path:
            self.status_var.set("Debug ZIP export cancelled; logs were preserved.")
            return

        zip_path = refresh_stale_debug_zip_selection(zip_path, default_path)

        self.prepare_debug_export_logs()

        try:
            result = export_debug_zip(
                BASE_DIR,
                zip_path,
                gui_console_text=self.get_gui_console_text(),
            )
        except Exception as e:
            messagebox.showerror("Export Debug ZIP failed", f"Could not export Debug ZIP:\n\n{e}")
            self.status_var.set("Debug ZIP export failed; logs were preserved.")
            return

        cleanup_allowed = (
            result.get("has_runtime_evidence")
            and not result.get("is_stale_export")
        )

        if cleanup_allowed:
            cleanup = self.clear_generated_debug_files_after_safe_event("debug_zip_exported")
            cleanup_message = f"Cleaned generated files: {len(cleanup['removed'])}"
        else:
            cleanup = {"removed": [], "failed": []}
            cleanup_message = "Generated debug files were not cleaned."

        message = (
            f"Debug ZIP exported:\n{Path(result['zip_path']).name}\n\n"
            f"ZIP path: {result['zip_path']}\n"
            f"Included files: {len(result['included'])}\n"
            f"Missing optional files: {len(result['missing'])}\n"
            f"Runtime evidence included: {result.get('has_runtime_evidence')}\n"
            f"Warnings detected: {result.get('has_warnings')}\n"
            f"{cleanup_message}"
        )

        if cleanup["failed"]:
            message += f"\nCleanup skipped/failed for: {len(cleanup['failed'])} file(s)"

        if not result.get("has_runtime_evidence"):
            message += (
                "\n\nDebug ZIP has no runtime evidence and may be stale "
                "or exported from the wrong folder."
            )
            messagebox.showwarning("Export Debug ZIP", message)
            self.status_var.set("Debug ZIP exported with no runtime evidence; logs were preserved.")
        elif result.get("is_stale_export"):
            message += (
                "\n\nDebug ZIP exported with stale/missing-evidence warnings. "
                "Generated debug files were not cleaned."
            )
            messagebox.showwarning("Export Debug ZIP", message)
            self.status_var.set("Debug ZIP exported with warnings; logs were preserved.")
        elif result.get("has_warnings"):
            message += "\n\nDebug ZIP exported with warnings. See debug_manifest.txt."
            messagebox.showwarning("Export Debug ZIP", message)
            self.status_var.set(f"Debug ZIP exported with warnings: {Path(result['zip_path']).name}")
        else:
            messagebox.showinfo("Export Debug ZIP", message)
            self.status_var.set(f"Debug ZIP exported: {Path(result['zip_path']).name}")

    def prepare_debug_export_logs(self):
        if self.bot_log_handle is not None:
            try:
                self.bot_log_handle.flush()
            except Exception:
                pass

        try:
            self.refresh_process_log()
        except Exception:
            pass

    def current_timestamp(self):
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def write_bot_console_log(self, text):
        if self.bot_log_handle is None:
            return

        try:
            self.bot_log_handle.write(sanitize_text_for_output(text))
        except UnicodeEncodeError:
            fallback = sanitize_text_for_output(text).encode(
                "utf-8",
                errors="replace",
            ).decode("utf-8", errors="replace")
            self.bot_log_handle.write(fallback)

    def clear_generated_debug_files_after_safe_event(self, reason):
        cleanup = clear_generated_debug_files(BASE_DIR)

        if cleanup["failed"]:
            self.append_log_text(
                "\n[GUI] Debug cleanup had skipped/failed files after "
                f"{reason}:\n"
                + "\n".join(f"- {path}: {error}" for path, error in cleanup["failed"])
                + "\n"
            )

        return cleanup

    def cleanup_after_clean_stop(self, process_exit_code=None, closing=False):
        if has_significant_error(BASE_DIR, process_exit_code=process_exit_code):
            if not closing:
                self.status_var.set("Bot stopped; debug files preserved because an error was detected.")
            return

        cleanup = self.clear_generated_debug_files_after_safe_event("clean_bot_stop")

        if not closing:
            self.status_var.set(f"Bot stopped cleanly; cleared {len(cleanup['removed'])} generated debug file(s).")

    def stop_bot_process(self, closing=False):
        if self.bot_process is None:
            return False

        process = self.bot_process

        existing_code = process.poll()

        if existing_code is not None:
            self.bot_process = None
            self.close_bot_log_handle()
            self.cleanup_after_clean_stop(process_exit_code=existing_code, closing=closing)
            return False

        stop_failed = False

        try:
            if self.bot_log_handle is not None:
                self.write_bot_console_log("=== GUI requested bot shutdown ===\n")
                self.bot_log_handle.flush()

            process.terminate()

            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                    )
                else:
                    process.kill()

                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)

            if not closing:
                self.status_var.set("Bot stopped.")
        except Exception as e:
            stop_failed = True
            if not closing:
                messagebox.showerror("Stop Bot failed", f"Could not stop bot:\n\n{e}")
        finally:
            self.bot_process = None
            self.close_bot_log_handle()

            if not stop_failed:
                self.cleanup_after_clean_stop(process_exit_code=None, closing=closing)

        return True

    def refresh_bot_status(self):
        if self.is_closing:
            return

        self.refresh_process_log()

        if self.bot_process is not None:
            code = self.bot_process.poll()

            if code is not None:
                self.status_var.set(f"Bot exited with code: {code}")
                self.bot_process = None
                self.close_bot_log_handle()
                self.cleanup_after_clean_stop(process_exit_code=code)

        if not self.is_closing:
            self.root.after(1000, self.refresh_bot_status)

    def close_bot_log_handle(self):
        if self.bot_log_handle is not None:
            try:
                self.bot_log_handle.close()
            except Exception:
                pass

            self.bot_log_handle = None

    def clear_log_text(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def append_log_text(self, text):
        if not text:
            return

        text = sanitize_text_for_output(text).replace("\x00", "")

        if not text:
            return

        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def get_gui_console_text(self):
        try:
            return self.log_text.get("1.0", tk.END).strip()
        except Exception:
            return ""

    def refresh_process_log(self):
        if not BOT_CONSOLE_LOG.exists():
            return

        try:
            file_size = BOT_CONSOLE_LOG.stat().st_size

            if self.log_read_position > file_size:
                self.log_read_position = 0

            with open(BOT_CONSOLE_LOG, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self.log_read_position)
                text = f.read()
                self.log_read_position = f.tell()

            self.append_log_text(text)
            self.handle_navigation_failure_warning(text)
        except Exception as e:
            self.append_log_text(f"\n[GUI] Could not read bot log: {e}\n")

    def handle_navigation_failure_warning(self, text):
        if "USER WARNING: Navigation failed" not in text:
            return

        warning_lines = [
            line.strip()
            for line in text.splitlines()
            if "USER WARNING: Navigation failed" in line
        ]

        if not warning_lines:
            return

        for warning in warning_lines:
            key = self.make_navigation_failure_warning_key(warning)

            if key in self.notified_warning_keys:
                self.append_log_text(
                    f"\n[GUI] GUI warning suppressed after first notification | key={key}\n"
                )
                continue

            self.notified_warning_keys.add(key)
            self.last_navigation_failure_warning = warning
            self.status_var.set("Navigation failed for a route; skipped and continued. Export Debug ZIP.")
            messagebox.showwarning(
                "Navigation route skipped",
                warning.replace("USER WARNING: ", "")
            )

    def make_navigation_failure_warning_key(self, warning):
        route_match = re.search(r"Route\s+(\d+)", warning)
        route = route_match.group(1) if route_match else "unknown_route"

        target = "unknown_target"
        target_match = re.search(
            r"Route\s+\d+:\s*(.*?)\.\s*The route was skipped",
            warning,
        )

        if target_match:
            target = target_match.group(1).strip()

        reason = "navigation_failed"
        reason_match = re.search(r"reason=([^|\]]+)", warning)

        if reason_match:
            reason = reason_match.group(1).strip()

        return f"navigation_failure|route={route}|target={target}|reason={reason}"

    def on_close(self):
        self.is_closing = True
        self.unregister_emergency_hotkey()
        self.stop_bot_process(closing=True)
        self.close_bot_log_handle()
        self.root.destroy()

    def load_existing_plan(self, silent=False):
        if not os.path.exists(OUTPUT_FILE):
            if not silent:
                messagebox.showinfo("Route file not found", f"{OUTPUT_FILE.name} does not exist.")
            return

        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                plan = json.load(f)

            if not isinstance(plan, list):
                raise ValueError("farm_plan.json must be a list.")

            self.selected_routes = plan
            if plan:
                first_route = plan[0]

                if "no_chest_retries" in first_route:
                    retries = first_route.get("no_chest_retries")
                elif "max_trials_if_no_chest" in first_route:
                    retries = first_route.get("max_trials_if_no_chest", 1)
                else:
                    retries = self.get_default_no_chest_retries()

                try:
                    if "no_chest_retries" not in first_route and "max_trials_if_no_chest" in first_route:
                        retries = int(retries) - 1

                    retries = max(0, int(retries))
                    self.no_chest_retries_var.set(str(retries))
                except (TypeError, ValueError):
                    self.no_chest_retries_var.set(str(self.get_default_no_chest_retries()))

            self.refresh_plan_listbox()

            if not silent:
                messagebox.showinfo("Loaded", f"Loaded {len(plan)} route(s) from {OUTPUT_FILE.name}.")

            self.status_var.set(f"Loaded {len(plan)} route(s).")

        except Exception as e:
            messagebox.showerror("Load failed", f"Could not load {OUTPUT_FILE.name}:\n\n{e}")


if __name__ == "__main__":
    if "--bot" in sys.argv:
        import main

        main.run_main_with_fatal_logging()
    else:
        root = tk.Tk()
        app = RoutePlannerApp(root)
        root.mainloop()
