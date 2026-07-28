# game_controller.py
import time
import mss
import controls
import capture
import regions
from ocr import getTextFromImage
import winsound


class OCRReadError(Exception):
    """OCR failed to parse an expected numeric value."""


class GameController:
    def __init__(self, ocr_retries=3, ocr_retry_delay=0.15):
        self.ocr_retries = ocr_retries
        self.ocr_retry_delay = ocr_retry_delay

    # ---------- low-level screen reads ----------

    def _read_number(self, region_name, region):
        """Grabs screen, crops to region, OCRs, parses int. Retries on failure."""
        last_err = None
        for attempt in range(self.ocr_retries):
            controls.maximize_bloons_td6()
            frame = capture.grab_screen()
            x1, y1, x2, y2 = region
            crop = frame[y1:y2, x1:x2]
            print(f"Reading: {region_name!r}")
            text, _ = getTextFromImage(crop, debug=False)
            print(f"Money read: {text}")
            try:
                return int(text.strip())
            except ValueError:
                last_err = text
                time.sleep(self.ocr_retry_delay)
        raise OCRReadError(f"Could not parse {region_name} from OCR output: {last_err!r}")

    def read_money(self):
        return self._read_number("money", regions.MONEY_REGION)

    def read_lives(self):
        return self._read_number("lives", regions.LIVES_REGION)

    def read_round(self):
        return self._read_number("round", regions.ROUND_REGION)
    

    def _check_pixel_color(self, position):
        """Check the color at a pixel position. position is a tuple (x, y)."""
        x, y = position
        controls.maximize_bloons_td6()
        with mss.mss() as sct:
            region = {"left": x, "top": y, "width": 1, "height": 1}
            pixel = sct.grab(region)
            b, g, r = pixel.pixel(0, 0)  # or np.array(pixel)[0,0][:3]
            return (r, g, b)

    # return true if round ended
    def check_round_end(self):
        return self._check_pixel_color(regions.ROUND_END_PIXEL) == regions.PRESS_TO_START_BUTTON_COLOR
    
    def is_double_speed(self):
        check = self._check_pixel_color(regions.SPEED_TOGGLE_PIXEL)
        return check == regions.SPEED_TOGGLE_ON_COLOR

    def ensure_double_speed(self):
        """Click the speed toggle only if the game isn't already at 2x."""
        if not self.is_double_speed():
            controls.click(*regions.START_ROUND_BUTTON)
            time.sleep(0.1)

    # ---------- mechanical actions ----------

    def select_monkey_shortcut(self, tower_type):
        controls.send_key(regions.MONKEY_BUY_SHORTCUT[tower_type])
        time.sleep(0.01)

    def cancel_placement(self):
        """Press Escape to back out of any held-tower placement mode."""
        controls.send_key("esc")
        time.sleep(0.01)

    def deselect_monkey(self):
        """Click empty grass to deselect the currently-selected tower."""
        x, y = regions.MAP_BOUNDS[0], regions.MAP_BOUNDS[1]  # any known-safe empty point
        controls.click(x, y)
        time.sleep(0.01)

    def click_map(self, position):
        x, y = position
        controls.click(x, y)
        time.sleep(0.01)

    def click_start_round(self):
        x, y = regions.START_ROUND_BUTTON
        controls.click(x, y)
        time.sleep(0.01)

    def click_monkey(self, position):
        x, y = position
        controls.click(x, y)
        time.sleep(0.05)  # selection animation

    def click_upgrade_path(self, monkey_position, path_index):
        """Selects the monkey, then sends the shortcut key for the given
        upgrade path (0=top, 1=middle, 2=bottom)."""
        self.click_monkey(monkey_position)
        controls.send_key(regions.UPGRADE_PATH_SHORTCUT[path_index])
        time.sleep(0.01)
