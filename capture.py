import mss
import numpy as np

_sct = mss.mss()

def grab_screen():
    """Returns a full-screen BGR numpy array."""
    monitor = _sct.monitors[1]  # primary monitor; adjust if multi-monitor
    raw = np.array(_sct.grab(monitor))
    return raw[:, :, :3]  # drop alpha channel