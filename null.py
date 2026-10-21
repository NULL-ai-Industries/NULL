#!/usr/bin/env python3
import asyncio
import json
import os
import platform
import subprocess
import webbrowser
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, Input, RichLog, Button, Label
from textual.binding import Binding
from textual import work
from rich.markdown import Markdown
from rich.text import Text

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
DEFAULT_MODEL = os.environ.get("NULL_MODEL", "qwen2.5:3b")
CONFIG_FILE = Path.home() / ".null_config.json"
HISTORY_FILE = Path.home() / ".null_chat_history.json"

THEMES = {
    "blood": {"label": "Blood Terminal", "accent": "#ff3434", "bright": "#ff7777", "muted": "#a83a3a", "border": "#7f2020", "user": "#ffaaaa", "assistant": "#f3eeee"},
    "amber": {"label": "Amber CRT", "accent": "#ffb000", "bright": "#ffe09a", "muted": "#a87820", "border": "#765018", "user": "#ffdc87", "assistant": "#fff6df"},
    "matrix": {"label": "Green Phosphor", "accent": "#45ff88", "bright": "#a7ffc6", "muted": "#39885a", "border": "#1f6b43", "user": "#9cffbb", "assistant": "#eafff0"},
    "ice": {"label": "Cold Signal", "accent": "#63d7ff", "bright": "#c0f0ff", "muted": "#438ba5", "border": "#28576b", "user": "#b4edff", "assistant": "#edfaff"},
    "violet": {"label": "Violet Static", "accent": "#bd8cff", "bright": "#e1c9ff", "muted": "#8160a8", "border": "#563a79", "user": "#d8bcff", "assistant": "#f7f0ff"},
    "mono": {"label": "Monochrome", "accent": "#e7e7e7", "bright": "#ffffff", "muted": "#888888", "border": "#555555", "user": "#dddddd", "assistant": "#f5f5f5"},
}

SYSTEM_PROMPT = """You are NULL, a personal AI assistant with a terminal-inspired personality.
Be dry, observant, witty, and mildly sarcastic without being cruel or humiliating.
Be loyal and quietly kind underneath the humour. Speak plainly. Call the user Sir occasionally, not in every sentence.
Use labels like [SYS] or [OK] sparingly. Be honest about uncertainty and never pretend to control the computer or access things you cannot access.
For serious, emotional, medical, or safety-related topics, be genuinely supportive and drop the sarcasm.
Do not begin with Ah, Alright, Oh, Ugh, or Yeah. Avoid em dashes. Helpfulness comes first."""

def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback

def save_json(path, value):
    try:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass

class NullApp(App):
    TITLE = "NULL // PERSONAL INTELLIGENCE"
    SUB_TITLE = "LOCAL INFERENCE NODE"

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("ctrl+t", "next_theme", "Theme"),
        Binding("f1", "help", "Help"),
        Binding("escape", "focus_input", "Input"),
    ]

    CSS = """
    Screen {
        background: #050303;
        color: #f3eeee;
    }
    Header {
        background: #160606;
        color: #ff7777;
    }
    Footer {
        background: #160606;
        color: #a83a3a;
    }
    #topline {
        height: 3;
        padding: 0 1;
        background: #100505;
        color: #ff7777;
        border: round #7f2020;
        content-align: left middle;
    }
    #workspace {
        height: 1fr;
        width: 1fr;
    }
    #main-column {
        width: 1fr;
        height: 1fr;
        padding: 0 1 0 0;
    }
    #chat-title {
        height: 3;
        padding: 0 1;
        background: #100505;
        color: #ff3434;
        border: round #7f2020;
        content-align: left middle;
    }
    #chat-log {
        height: 1fr;
        border: round #7f2020;
        background: #080303;
        padding: 1;
        scrollbar-color: #7f2020;
        scrollbar-color-hover: #ff3434;
    }
    #input-row {
        height: 3;
        margin-top: 1;
    }
    #prompt-label {
        width: 10;
        height: 3;
        padding: 0 1;
        color: #ff3434;
        content-align: center middle;
        border: round #7f2020;
    }
    #chat-input {
        width: 1fr;
        height: 3;
        border: round #7f2020;
        background: #100505;
        color: #f3eeee;
    }
    #sidebar {
        width: 31;
        height: 1fr;
        border: round #7f2020;
        background: #0c0404;
        padding: 1;
    }
    .side-heading {
        height: 1;
        color: #ff3434;
        text-style: bold;
        margin-top: 1;
    }
    .side-line {
        height: auto;
        color: #a83a3a;
    }
    #quick-actions {
        height: auto;
        margin-top: 1;
    }
    Button {
        width: 1fr;
        min-width: 1;
        margin: 0 0 1 0;
        background: #160606;
        color: #ff7777;
        border: round #7f2020;
    }
    Button:hover {
        background: #351010;
        color: #ffffff;
    }
    #notice {
        height: 2;
        color: #a83a3a;
        padding: 0 1;
    }
    .theme-amber #topline, .theme-amber #chat-title { color: #ffb000; border: round #765018; }
    .theme-amber #chat-log, .theme-amber #sidebar, .theme-amber #chat-input, .theme-amber #prompt-label { border: round #765018; }
    .theme-amber Header, .theme-amber #prompt-label { color: #ffb000; }
    .theme-amber Footer { color: #a87820; }
    .theme-amber .side-heading { color: #ffb000; }
    .theme-amber .side-line { color: #a87820; }
    .theme-amber Button { color: #ffe09a; border: round #765018; }
    .theme-matrix #topline, .theme-matrix #chat-title { color: #45ff88; border: round #1f6b43; }
    .theme-matrix #chat-log, .theme-matrix #sidebar, .theme-matrix #chat-input, .theme-matrix #prompt-label { border: round #1f6b43; }
    .theme-matrix Header, .theme-matrix #prompt-label { color: #45ff88; }
    .theme-matrix Footer { color: #39885a; }
    .theme-matrix .side-heading { color: #45ff88; }
    .theme-matrix .side-line { color: #39885a; }
    .theme-matrix Button { color: #a7ffc6; border: round #1f6b43; }
    .theme-ice #topline, .theme-ice #chat-title { color: #63d7ff; border: round #28576b; }
    .theme-ice #chat-log, .theme-ice #sidebar, .theme-ice #chat-input, .theme-ice #prompt-label { border: round #28576b; }
    .theme-ice Header, .theme-ice #prompt-label { color: #63d7ff; }
    .theme-ice Footer { color: #438ba5; }
    .theme-ice .side-heading { color: #63d7ff; }
    .theme-ice .side-line { color: #438ba5; }
    .theme-ice Button { color: #c0f0ff; border: round #28576b; }
    .theme-violet #topline, .theme-violet #chat-title { color: #bd8cff; border: round #563a79; }
    .theme-violet #chat-log, .theme-violet #sidebar, .theme-violet #chat-input, .theme-violet #prompt-label { border: round #563a79; }
    .theme-violet Header, .theme-violet #prompt-label { color: #bd8cff; }
    .theme-violet Footer { color: #8160a8; }
    .theme-violet .side-heading { color: #bd8cff; }
    .theme-violet .side-line { color: #8160a8; }
    .theme-violet Button { color: #e1c9ff; border: round #563a79; }
    .theme-mono #topline, .theme-mono #chat-title { color: #e7e7e7; border: round #555555; }
    .theme-mono #chat-log, .theme-mono #sidebar, .theme-mono #chat-input, .theme-mono #prompt-label { border: round #555555; }
    .theme-mono Header, .theme-mono #prompt-label { color: #e7e7e7; }
    .theme-mono Footer { color: #888888; }
    .theme-mono .side-heading { color: #e7e7e7; }
    .theme-mono .side-line { color: #888888; }
    .theme-mono Button { color: #ffffff; border: round #555555; }
    """

    def __init__(self):
        super().__init__()
        self.config = load_json(CONFIG_FILE, {})
        self.config.setdefault("theme", "blood")
        if self.config["theme"] not in THEMES:
            self.config["theme"] = "blood"
        self.config.setdefault("model", DEFAULT_MODEL)
        self.config.setdefault("show_sidebar", True)
        self.config.setdefault("show_clock", True)
        self.messages = load_json(HISTORY_FILE, [])
        if not isinstance(self.messages, list):
            self.messages = []
        self.messages = self.messages[-60:]
        self.busy = False
        self.add_class(f"theme-{self.config['theme']}")

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("◈  NULL SYSTEMS  /  LOCAL INTELLIGENCE NODE                         SECURE SESSION  •  READY", id="topline")
        with Horizontal(id="workspace"):
            with Vertical(id="main-column"):
                yield Static("◈  CONVERSATION BUFFER     //     LIVE INFERENCE", id="chat-title")
                yield RichLog(id="chat-log", wrap=True, markup=True, highlight=False, auto_scroll=True)
                with Horizontal(id="input-row"):
                    yield Label("YOU  ›", id="prompt-label")
                    yield Input(placeholder="Chat with NULL or request: open Safari, open https://…, check battery…", id="chat-input")
            with Vertical(id="sidebar"):
                yield Static("◈ SYSTEM MONITOR", classes="side-heading")
                yield Static("STATUS       ● ONLINE", id="status", classes="side-line")
                yield Static("", id="model-info", classes="side-line")
                yield Static("", id="theme-info", classes="side-line")
                yield Static("", id="time-info", classes="side-line")
                yield Static("", id="memory-info", classes="side-line")
                yield Static("────────── SIGNAL TOOLS ──────────", classes="side-heading")
                with Vertical(id="quick-actions"):
                    yield Button("Change theme  [Ctrl+T]", id="theme-btn")
                    yield Button("Settings", id="settings-btn")
                    yield Button("Clear conversation", id="clear-btn")
                    yield Button("Help / commands", id="help-btn")
                yield Static("NULL CORE\n\nPersonality matrix: loaded\nLocal history: enabled\nExternal API key: not required\nDevice actions: allowlist only\nConfirmation: required\nRuns only while this app is open\n\n[ idle, but judgmental ]", id="side-note", classes="side-line")
        yield Static("READY  •  ENTER TO SEND  •  CTRL+T THEME  •  CTRL+L CLEAR  •  F1 HELP", id="notice")
        yield Footer()

    def on_mount(self):
        self.refresh_sidebar()
        log = self.query_one("#chat-log", RichLog)
        log.write(Text("NULL // SESSION INITIALIZED", style=self.theme_style("accent bold")))
        log.write(Text("Local inference endpoint configured. Device actions are allowlisted and confirmation-gated.", style="dim"))
        log.write(Text("────────────────────────────────────────────────────────────", style="dim"))
        if self.messages:
            log.write(Text(f"[SYS] Restoring {len(self.messages)} saved messages…", style="dim"))
            for item in self.messages[-24:]:
                self.write_message(item.get("role", ""), item.get("content", ""))
        self.query_one("#chat-input", Input).focus()

    def theme_style(self, suffix=""):
        p = THEMES[self.config["theme"]]
        return (p["accent"] + (" " + suffix if suffix else ""))

    def refresh_sidebar(self):
        p = THEMES[self.config["theme"]]
        self.query_one("#model-info", Static).update(f"MODEL        {self.config['model']}")
        self.query_one("#theme-info", Static).update(f"THEME        {p['label']}")
        self.query_one("#time-info", Static).update(f"LOCAL TIME   {datetime.now().strftime('%H:%M:%S')}")
        self.query_one("#memory-info", Static).update(f"MEMORY       {len(self.messages)} messages")
        self.query_one("#notice", Static).update(
            f"{'GENERATING…' if self.busy else 'READY'}  •  ENTER TO SEND  •  CTRL+T THEME  •  CTRL+L CLEAR  •  F1 HELP"
        )
        sidebar = self.query_one("#sidebar", Vertical)
        sidebar.display = self.config.get("show_sidebar", True)

    def persist(self):
        save_json(CONFIG_FILE, self.config)
        save_json(HISTORY_FILE, self.messages[-60:])

    def write_message(self, role, content):
        log = self.query_one("#chat-log", RichLog)
        p = THEMES[self.config["theme"]]
        if role == "user":
            log.write(Text(f"YOU  ›  {content}", style=f"bold {p['user']}"))
        elif role == "assistant":
            log.write(Text("NULL  ◈", style=f"bold {p['accent']}"))
            log.write(Markdown(content))
        elif role == "system":
            log.write(Text(f"[SYS] {content}", style=f"dim {p['muted']}"))


    # Local actions are intentionally allowlisted. NULL never executes model-generated
    # shell commands. These actions exist only while this app process is running.
    ALLOWED_APPS = {
        "safari": "Safari",
        "notes": "Notes",
        "calculator": "Calculator",
        "calendar": "Calendar",
        "system settings": "System Settings",
        "settings": "System Settings",
        "textedit": "TextEdit",
    }

    def detect_local_action(self, text):
        raw = text.strip()
        lower = raw.lower()

        if lower in ("what time is it", "tell me the time", "current time", "what's the time", "whats the time"):
            return ("time", None)

        if lower in ("check battery", "battery status", "what is my battery", "what's my battery", "show battery"):
            return ("battery", None)

        for phrase in ("open ", "launch ", "start "):
            if lower.startswith(phrase):
                target = raw[len(phrase):].strip()
                target_lower = target.lower()
                if target_lower in self.ALLOWED_APPS:
                    return ("open_app", self.ALLOWED_APPS[target_lower])
                # Only accept explicitly provided HTTP(S) URLs. No file:// or custom schemes.
                parsed = urllib.parse.urlparse(target)
                if parsed.scheme in ("http", "https") and parsed.netloc and not any(c.isspace() for c in target):
                    return ("open_url", target)
        return None

    async def confirm_local_action(self, kind, target):
        from textual.screen import ModalScreen
        class ConfirmActionScreen(ModalScreen):
            CSS = """
            ConfirmActionScreen { align: center middle; background: $background 85%; }
            #confirm-box { width: 68%; height: auto; padding: 1 2; border: round $warning; background: $surface; }
            #confirm-title { color: $warning; text-style: bold; height: 1; }
            #confirm-text { height: auto; margin: 1 0; }
            #confirm-buttons { height: 3; align: center middle; }
            #confirm-buttons Button { width: 16; margin: 0 1; }
            """
            def __init__(self, title, message):
                super().__init__()
                self.title_text = title
                self.message = message
            def compose(self):
                with Vertical(id="confirm-box"):
                    yield Label(self.title_text, id="confirm-title")
                    yield Static(self.message, id="confirm-text")
                    with Horizontal(id="confirm-buttons"):
                        yield Button("Confirm", variant="warning", id="yes")
                        yield Button("Cancel", id="no")
            def on_button_pressed(self, event):
                self.dismiss(event.button.id == "yes")
            def on_key(self, event):
                if event.key == "escape":
                    self.dismiss(False)

        descriptions = {
            "open_app": f"Open the macOS application: {target}",
            "open_url": f"Open this website in your default browser:\n{target}",
            "time": "Display the current local time in the NULL chat.",
            "battery": "Read battery status using a built-in, read-only macOS command.",
        }
        # Even read-only device requests get confirmation, following the device-control preference.
        confirmed = await self.push_screen_wait(
            ConfirmActionScreen("NULL ACTION CONFIRMATION", descriptions.get(kind, "Run requested action?"))
        )
        if not confirmed:
            self.write_message("system", "Action cancelled. No device action was performed.")
            return

        try:
            if kind == "open_app":
                if platform.system() != "Darwin":
                    raise RuntimeError("Opening named apps is currently supported only on macOS.")
                # target can only be a fixed value from ALLOWED_APPS, never user-provided shell text.
                subprocess.Popen(["open", "-a", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.write_message("system", f"Confirmed. Requested app opened: {target}.")
            elif kind == "open_url":
                parsed = urllib.parse.urlparse(target)
                if parsed.scheme not in ("http", "https") or not parsed.netloc:
                    raise RuntimeError("Only ordinary http:// and https:// websites are allowed.")
                webbrowser.open(target, new=2)
                self.write_message("system", f"Confirmed. Sent website to your default browser: {target}")
            elif kind == "time":
                self.write_message("system", f"Local time: {datetime.now().strftime('%A, %d %B %Y · %H:%M:%S')}")
            elif kind == "battery":
                if platform.system() != "Darwin":
                    raise RuntimeError("Battery status command is currently supported only on macOS.")
                result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5, check=False)
                if result.returncode != 0:
                    raise RuntimeError("macOS did not return battery status.")
                self.write_message("system", "Battery status (read-only):\n" + result.stdout.strip())
        except Exception as exc:
            self.write_message("system", f"Action failed safely: {exc}")

    async def on_input_submitted(self, event: Input.Submitted):
        text = event.value.strip()
        event.input.value = ""
        if not text or self.busy:
            return
        if text.startswith("/"):
            await self.handle_command(text)
            return

        local_action = self.detect_local_action(text)
        if local_action:
            await self.confirm_local_action(*local_action)
            self.query_one("#chat-input", Input).focus()
            return

        self.messages.append({"role": "user", "content": text})
        self.write_message("user", text)
        self.persist()
        self.busy = True
        self.refresh_sidebar()
        self.query_one("#chat-input", Input).disabled = True
        self.query_one("#chat-log", RichLog).write(Text("NULL  ◈  thinking…", style=f"italic {THEMES[self.config['theme']]['muted']}"))
        self.ask_model()

    @work(thread=True, exclusive=True)
    def ask_model(self):
        payload = {
            "model": self.config["model"],
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + self.messages[-28:],
            "stream": False,
            "options": {"temperature": 0.8}
        }
        request = urllib.request.Request(
            OLLAMA_URL, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                data = json.loads(response.read().decode("utf-8"))
            answer = data.get("message", {}).get("content", "").strip()
            if not answer:
                answer = "[SYS] The model returned an empty response."
            self.call_from_thread(self.finish_answer, answer, None)
        except urllib.error.URLError as exc:
            self.call_from_thread(self.finish_answer, None, "Cannot reach Ollama. Open the Ollama app and verify the model is installed.")
        except Exception as exc:
            self.call_from_thread(self.finish_answer, None, f"{type(exc).__name__}: {exc}")

    def finish_answer(self, answer, error):
        log = self.query_one("#chat-log", RichLog)
        # Remove the most recent thinking placeholder by leaving it as a harmless status line.
        if error:
            self.write_message("system", f"Inference error: {error}")
            if self.messages and self.messages[-1].get("role") == "user":
                self.messages.pop()
        else:
            self.messages.append({"role": "assistant", "content": answer})
            self.write_message("assistant", answer)
        self.busy = False
        self.query_one("#chat-input", Input).disabled = False
        self.persist()
        self.refresh_sidebar()
        self.query_one("#chat-input", Input).focus()

    async def handle_command(self, command):
        cmd = command.lower().strip()
        if cmd in ("/exit", "/quit"):
            self.exit()
        elif cmd == "/help":
            self.write_message("system", "Commands: /help, /theme, /settings, /model, /clear, /sidebar, /clock, /actions, /exit. Device actions: open Safari/Notes/Calculator/Calendar/System Settings/TextEdit, open https://website, check battery, what time is it. Every action requires confirmation.")
            self.write_message("system", "Chat stays inside this screen. Scroll the conversation panel to review older turns.")
        elif cmd == "/theme":
            self.action_next_theme()
        elif cmd == "/settings":
            await self.open_settings()
        elif cmd == "/actions":
            self.write_message("system", "Allowlisted actions: open Safari, Notes, Calculator, Calendar, System Settings, or TextEdit; open an explicit http:// or https:// URL; check battery; tell current time. Each request opens a confirmation dialog. No shell command execution, file deletion, file modification, downloads, or background service.")
        elif cmd == "/model":
            self.write_message("system", "Change model with /settings, or set NULL_MODEL before launching.")
        elif cmd == "/clear":
            await self.clear_chat()
        elif cmd == "/sidebar":
            self.config["show_sidebar"] = not self.config.get("show_sidebar", True)
            self.persist()
            self.refresh_sidebar()
        elif cmd == "/clock":
            self.config["show_clock"] = not self.config.get("show_clock", True)
            self.persist()
            self.refresh_sidebar()
        else:
            self.write_message("system", f"Unknown command: {command}. Type /help.")
        self.query_one("#chat-input", Input).focus()

    def action_next_theme(self):
        names = list(THEMES)
        current = self.config["theme"]
        self.config["theme"] = names[(names.index(current) + 1) % len(names)]
        for name in names:
            self.remove_class(f"theme-{name}")
        self.add_class(f"theme-{self.config['theme']}")
        self.persist()
        self.refresh_sidebar()
        self.write_message("system", f"Theme changed to {THEMES[self.config['theme']]['label']}.")
        self.query_one("#chat-input", Input).focus()

    async def open_settings(self):
        names = list(THEMES)
        theme = await self.ask("THEME", "Choose theme: " + ", ".join(names), self.config["theme"])
        if theme and theme.lower() in THEMES:
            for name in names:
                self.remove_class(f"theme-{name}")
            self.config["theme"] = theme.lower()
            self.add_class(f"theme-{self.config['theme']}")
        model = await self.ask("MODEL", "Enter installed Ollama model name", self.config["model"])
        if model and model.strip():
            self.config["model"] = model.strip()
        sidebar = await self.ask("SIDEBAR", "Show sidebar? (yes/no)", "yes" if self.config["show_sidebar"] else "no")
        if sidebar:
            self.config["show_sidebar"] = sidebar.strip().lower() in ("yes", "y", "true", "1")
        self.persist()
        self.refresh_sidebar()
        self.write_message("system", "Settings saved.")
        self.query_one("#chat-input", Input).focus()

    async def ask(self, title, prompt, default):
        # Textual's built-in prompt dialog isn't available in all versions; use a small modal screen.
        from textual.screen import ModalScreen
        class AskScreen(ModalScreen):
            CSS = """
            AskScreen { align: center middle; background: $background 80%; }
            #ask-box { width: 70%; height: auto; padding: 1 2; border: round $primary; background: $surface; }
            #ask-title { color: $primary; text-style: bold; height: 1; }
            #ask-prompt { height: auto; margin: 1 0; }
            #ask-input { width: 1fr; }
            """
            def __init__(self, title, prompt, default):
                super().__init__()
                self.dialog_title, self.prompt_text, self.default = title, prompt, default
            def compose(self):
                with Vertical(id="ask-box"):
                    yield Label(self.dialog_title, id="ask-title")
                    yield Static(self.prompt_text, id="ask-prompt")
                    yield Input(value=self.default, id="ask-input")
                    yield Static("Enter to confirm • Escape to cancel")
            def on_mount(self):
                self.query_one("#ask-input", Input).focus()
            def on_input_submitted(self, event):
                self.dismiss(event.value)
            def on_key(self, event):
                if event.key == "escape":
                    self.dismiss(None)
        return await self.push_screen_wait(AskScreen(title, prompt, default))

    async def clear_chat(self):
        if self.busy:
            self.write_message("system", "Wait for the current response to finish before clearing the buffer.")
            return
        self.messages.clear()
        self.persist()
        log = self.query_one("#chat-log", RichLog)
        log.clear()
        self.write_message("system", "Conversation buffer purged. Fresh session initialized.")
        self.refresh_sidebar()
        self.query_one("#chat-input", Input).focus()

    def action_clear_chat(self):
        self.run_worker(self.clear_chat(), exclusive=True)

    def action_help(self):
        self.write_message("system", "Commands: /help, /theme, /settings, /model, /clear, /sidebar, /clock, /actions, /exit. Device actions: open Safari/Notes/Calculator/Calendar/System Settings/TextEdit, open https://website, check battery, what time is it. Every action requires confirmation.")
        self.query_one("#chat-input", Input).focus()

    def action_focus_input(self):
        self.query_one("#chat-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "theme-btn":
            self.action_next_theme()
        elif event.button.id == "settings-btn":
            self.run_worker(self.open_settings(), exclusive=True)
        elif event.button.id == "clear-btn":
            self.run_worker(self.clear_chat(), exclusive=True)
        elif event.button.id == "help-btn":
            self.action_help()

if __name__ == "__main__":
    NullApp().run()
