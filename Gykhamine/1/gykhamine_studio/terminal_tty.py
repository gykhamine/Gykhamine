"""Module généré automatiquement depuis gy.py"""
import os, pty, tty, termios, fcntl, struct, threading, select
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk
from .config import global_log

#  NATIVE TTY TERMINAL (POPUP)
# ═══════════════════════════════════════════════════════════════════════
class NativeTtyTerminal(Gtk.Window):
    def __init__(self, parent, title, command, cwd=None):
        super().__init__(title=title, transient_for=parent, default_width=900, default_height=600)
        self.add_css_class("rounded-dialog")
        self.command = command
        self.cwd = cwd
        self.pid = None
        self.master_fd = None
        self.is_running = False
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(box)
        
        header = Gtk.HeaderBar()
        btn_close = Gtk.Button(label="✕ Close Terminal")
        btn_close.connect("clicked", lambda *_: self._close_terminal())
        header.pack_end(btn_close)
        box.append(header)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_hexpand(True)
        self.scrolled.set_vexpand(True)
        box.append(self.scrolled)
        
        self.text_view = Gtk.TextView()
        self.text_view.set_editable(False)
        self.text_view.set_cursor_visible(True)
        self.text_view.set_monospace(True)
        self.text_view.set_wrap_mode(Gtk.WrapMode.NONE)
        self.text_view.add_css_class("terminal-tty-view")
        
        provider = Gtk.CssProvider()
        provider.load_from_data(b""".terminal-tty-view { background-color: #000000 !important; color: #cccccc; font-family: 'Fira Code', 'Consolas', 'Monaco', monospace; font-size: 14px; padding: 10px; }""")
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        self.scrolled.set_child(self.text_view)
        self.buf = self.text_view.get_buffer()
        
        self.key_controller = Gtk.EventControllerKey()
        self.key_controller.connect("key-pressed", self._on_key_pressed)
        self.text_view.add_controller(self.key_controller)
        
        self.resize_controller = Gtk.EventControllerMotion()
        self.connect("notify::default-width", self._on_resize)
        self.connect("notify::default-height", self._on_resize)
        
        self.show()
        self._spawn_shell()

    def _spawn_shell(self):
        self.pid, self.master_fd = pty.fork()
        if self.pid == 0:
            try:
                if self.cwd: os.chdir(self.cwd)
                if self.command: os.execvp("bash", ["bash", "-c", self.command])
                else: os.execvp("bash", ["bash"])
            except Exception as e:
                print(f"Exec error: {e}")
                os._exit(1)
        else:
            self.is_running = True
            attrs = termios.tcgetattr(self.master_fd)
            attrs[3] = attrs[3] & ~termios.ECHO
            termios.tcsetattr(self.master_fd, termios.TCSANOW, attrs)
            threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        while self.is_running:
            try:
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if r:
                    data = os.read(self.master_fd, 1024)
                    if not data:
                        self.is_running = False
                        GLib.idle_add(self._close_terminal)
                        break
                    text = data.decode('utf-8', errors='replace')
                    GLib.idle_add(self._append_text, text)
            except OSError:
                self.is_running = False
                break

    def _append_text(self, text):
        end_iter = self.buf.get_end_iter()
        self.buf.insert(end_iter, text)
        mark = self.buf.create_mark(None, end_iter, False)
        self.text_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if not self.is_running: return False
        char = chr(keyval) if keyval < 128 else None
        data = b""
        if char and not (state & Gdk.ModifierType.CONTROL_MASK): data = char.encode('utf-8')
        elif keyval == Gdk.KEY_Return: data = b"\n"
        elif keyval == Gdk.KEY_BackSpace: data = b"\x7f"
        elif keyval == Gdk.KEY_Tab: data = b"\t"
        elif keyval == Gdk.KEY_Escape: data = b"\x1b"
        elif keyval == Gdk.KEY_Up: data = b"\x1b[A"
        elif keyval == Gdk.KEY_Down: data = b"\x1b[B"
        elif keyval == Gdk.KEY_Right: data = b"\x1b[C"
        elif keyval == Gdk.KEY_Left: data = b"\x1b[D"
        elif state & Gdk.ModifierType.CONTROL_MASK:
            if keyval == Gdk.KEY_c: data = b"\x03"
            elif keyval == Gdk.KEY_d: data = b"\x04"
            elif keyval == Gdk.KEY_l: data = b"\x0c"
            elif keyval == Gdk.KEY_u: data = b"\x15"
            elif keyval == Gdk.KEY_w: data = b"\x17"
        
        if data:
            try: os.write(self.master_fd, data)
            except OSError: self.is_running = False
            return True
        return False

    def _on_resize(self, *args):
        if not self.is_running: return
        h, w = self.text_view.get_allocated_height(), self.text_view.get_allocated_width()
        cols = max(w // 9, 80)
        rows = max(h // 18, 24)
        try: fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
        except Exception as e:
            global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
    def _close_terminal(self, *args):
        self.is_running = False
        if self.pid:
            try: os.kill(self.pid, 9); os.waitpid(self.pid, 0)
            except Exception as e:
                global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
        if self.master_fd:
            try: os.close(self.master_fd)
            except Exception as e:
                global_log(f"⚠️ Erreur dans gy.py: {type(e).__name__} - {e}")
        self.destroy()

# ═══════════════════════════════════════════════════════════════════════
