# killswitch.py
import threading
import keyboard


class KillSwitch:
    """
    Global emergency stop. Works even while BTD6 has focus, since
    keyboard.add_hotkey() registers a system-wide hook, not a
    window-specific one.
    """

    def __init__(self, hotkey="ctrl+shift+q"):
        self.hotkey = hotkey
        self.stop_event = threading.Event()
        keyboard.add_hotkey(hotkey, self._trigger)
        print(f"[KillSwitch] armed — press {hotkey} to stop")

    def _trigger(self):
        print(f"\n[KillSwitch] {self.hotkey} pressed — stopping at next safe checkpoint")
        self.stop_event.set()

    def is_triggered(self) -> bool:
        return self.stop_event.is_set()

    def reset(self):
        self.stop_event.clear()