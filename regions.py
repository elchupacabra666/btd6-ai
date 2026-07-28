# regions.py

# OCR crop regions (x1, y1, x2, y2) — match what you already tuned in ocr.py
MONEY_REGION = (343, 14, 528, 61)
LIVES_REGION = (140, 14, 274, 61)   # fill in from your existing crops
ROUND_REGION = (1379, 27, 1660, 69)

ROUND_END_PIXEL = (1830, 1000)

START_ROUND_BUTTON = (1840, 1030) 
PRESS_TO_START_BUTTON_COLOR = (255, 255, 255)

SPEED_TOGGLE_PIXEL = (1842, 992)
SPEED_TOGGLE_ON_COLOR = (3, 242, 163)

MAP_BOUNDS = (37, 15, 1620, 1060)

# Shop icons: fixed screen position regardless of game state
MONKEY_BUY_SHORTCUT = {
    "dart_monkey": "q",
    "boomerang_monkey": "w",
    "bomb_shooter": "e",
    "tack_shooter": "r",
    "ice_monkey": "t",
    "glue_gunner": "y",
    "sniper_monkey": "z",
    "monkey_sub": "x",
    "monkey_buccaneer": "c",
    "monkey_ace": "v",
    "heli_pilot": "b",
    "mortar_monkey": "n",
    "dartling_gunner": "m",
    "wizard_monkey": "a",
    "super_monkey": "s",
    "ninja_monkey": "d",
    "alchemist": "f",
    "druid": "g",
    "banana_farm": "h",
    "spike_factory": "j",
    "monkey_village": "k",
    "engineer_monkey": "l",
    "beast_handler": "i",
    "heroes": "u"
}

# When a monkey is selected, BTD6 shows 2 upgrade paths as buttons.
# Their position is a FIXED OFFSET from the monkey, but the panel
# flips horizontally if the monkey is on the right half of the screen.
UPGRADE_PATH_SHORTCUT = {
    0: ",",  # top path
    1: ".",  # middle path
    2: "/",  # bottom path
}

SCREEN_MIDPOINT_X = 1920 // 2  # adjust to your resolution