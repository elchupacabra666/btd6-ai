from __future__ import annotations

import ctypes
from ctypes import wintypes
from time import sleep

import keyboard


user32 = ctypes.windll.user32
SW_RESTORE = 9
SW_MAXIMIZE = 3
WINDOW_TITLE = "BloonsTD6"
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)


def get_window_text(hwnd: int) -> str:
	length = user32.GetWindowTextLengthW(hwnd)
	buffer = ctypes.create_unicode_buffer(length + 1)
	user32.GetWindowTextW(hwnd, buffer, length + 1)
	return buffer.value


def maximize_bloons_td6() -> bool:
	hwnd_result = None

	@EnumWindowsProc
	def enum_windows_proc(hwnd, lparam):
		nonlocal hwnd_result
		if not user32.IsWindowVisible(hwnd):
			return True

		title = get_window_text(hwnd)
		if title == WINDOW_TITLE:
			hwnd_result = hwnd
			return False
		return True

	user32.EnumWindows(enum_windows_proc, 0)

	if hwnd_result is None:
		print(f"No visible window found with title {WINDOW_TITLE!r}")
		return False

	user32.ShowWindow(hwnd_result, SW_RESTORE)
	user32.ShowWindow(hwnd_result, SW_MAXIMIZE)
	user32.SetForegroundWindow(hwnd_result)
	return True


def send_key(key: str, timeout=0.1, amount=1) -> bool:
	"""Bring the game to foreground, then send a raw key string (e.g. 'q')."""
	if not key:
		return False

	if not maximize_bloons_td6():
		return False

	keyboard.send(key)
	return True


def click(x: int, y: int) -> bool:
    if not user32.SetCursorPos(x, y):
        return False
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return True


if __name__ == "__main__":
	maximize_bloons_td6()
	sleep(2)
	send_key("q")
