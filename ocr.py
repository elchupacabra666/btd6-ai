# width, height, top, left

from pathlib import Path
import time
import shutil

import pytesseract
import numpy as np
import cv2


DEBUG_DIR = Path("./DEBUG")


def clear_debug_dir():
    if DEBUG_DIR.exists():
        shutil.rmtree(DEBUG_DIR)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)


def save_debug_image(step_name, image):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    safe_step_name = step_name.replace(" ", "_").lower()
    filename = DEBUG_DIR / f"ocr_{safe_step_name}_{int(time.time() * 1000)}.png"
    cv2.imwrite(str(filename), image, [cv2.IMWRITE_PNG_COMPRESSION, 0])


def formatImageOCR(originalScreenshot, debug=False):
    screenshot = np.array(originalScreenshot, dtype=np.uint8)
    if debug:
        save_debug_image("01_original_screenshot", screenshot)

    # Crop region: top-left corner (0, 0) to (500, 75)
    screenshot = screenshot[0:75, 0:500]
    if debug:
        save_debug_image("02_cropped_region", screenshot)

    # Get local maximum:
    kernelSize = 5
    maxKernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernelSize, kernelSize))
    localMax = cv2.morphologyEx(screenshot, cv2.MORPH_CLOSE, maxKernel, None, None, 1, cv2.BORDER_REFLECT101)
    if debug:
        save_debug_image("03_local_maximum", localMax)

    # Perform gain division
    gainDivision = np.divide(
        screenshot,
        localMax,
        out=np.zeros_like(screenshot, dtype=np.float32),
        where=localMax != 0,
    )
    if debug:
        save_debug_image("04_gain_division", np.clip(255 * gainDivision, 0, 255).astype("uint8"))

    # Clip the values to [0,255]
    gainDivision = np.clip((255 * gainDivision), 0, 255)
    # Convert the mat type from float to uint8:
    gainDivision = gainDivision.astype("uint8")
    if debug:
        save_debug_image("05_gain_division_uint8", gainDivision)

    # Convert RGB to grayscale:
    grayscaleImage = cv2.cvtColor(gainDivision, cv2.COLOR_BGR2GRAY)
    if debug:
        save_debug_image("06_grayscale", grayscaleImage)

    # Resize image to improve the quality
    grayscaleImage = cv2.resize(grayscaleImage, (0, 0), fx=3.0, fy=3.0)
    if debug:
        save_debug_image("07_resized", grayscaleImage)

    # Get binary image via Otsu:
    _, final_image = cv2.threshold(grayscaleImage, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if debug:
        save_debug_image("08_threshold_otsu", final_image)

    # Set kernel (structuring element) size:
    kernelSize = 3
    # Set morph operation iterations:
    opIterations = 1
    # Get the structuring element:
    morphKernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernelSize, kernelSize))
    # Perform closing:
    final_image = cv2.morphologyEx(
        final_image,
        cv2.MORPH_CLOSE,
        morphKernel,
        None,
        None,
        opIterations,
        cv2.BORDER_REFLECT101,
    )
    if debug:
        save_debug_image("09_morphology_close", final_image)

    # Flood fill (white + black):
    cv2.floodFill(final_image, mask=None, seedPoint=(int(0), int(0)), newVal=(255))
    if debug:
        save_debug_image("10_floodfill_from_corner", final_image)

    # Invert image so target blobs are colored in white:
    final_image = 255 - final_image
    if debug:
        save_debug_image("11_inverted", final_image)

    # Find the blobs on the binary image:
    contours, hierarchy = cv2.findContours(final_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # Process the contours:
    for i, c in enumerate(contours):
        # Get contour hierarchy:
        currentHierarchy = hierarchy[0][i][3]
        # Look only for children contours (the holes):
        if currentHierarchy != -1:
            # Get the contour bounding rectangle:
            boundRect = cv2.boundingRect(c)
            # Get the dimensions of the bounding rect:
            rectX = boundRect[0]
            rectY = boundRect[1]
            rectWidth = boundRect[2]
            rectHeight = boundRect[3]
            # Get the center of the contour the will act as
            # seed point to the Flood-Filling:
            fx = rectX + 0.5 * rectWidth
            fy = rectY + 0.5 * rectHeight
            # Fill the hole:
            cv2.floodFill(final_image, mask=None, seedPoint=(int(fx), int(fy)), newVal=(0))


    if debug:
        save_debug_image("13_final_output", final_image)

    return final_image


# Change to https://stackoverflow.com/questions/66334737/pytesseract-is-very-slow-for-real-time-ocr-any-way-to-optimise-my-code 
# or https://www.reddit.com/r/learnpython/comments/kt5zzw/how_to_speed_up_pytesseract_ocr_processing/

def getTextFromImage(image, debug=False):
    """ returns text from image """
    if debug:
        clear_debug_dir()
    imageCandidate = formatImageOCR(image, debug=debug)
    # Tesseract expects dark text on a light background; formatImageOCR
    # produces the opposite (white text on black), so invert before OCR.
    ocrReadyImage = 255 - imageCandidate

    # DEBUG log round to disk
    if debug:
        save_debug_image("14_tesseract_input", ocrReadyImage)

    raw_text = pytesseract.image_to_string(ocrReadyImage, config='--psm 7 -c tessedit_char_whitelist=0123456789$/')
    if debug:
        print(f"Raw text: {raw_text!r}")
    text = raw_text.split("/")[0].replace("\n", "").replace("+", "").replace("$", "")
    return text, imageCandidate

if __name__ == "__main__":
    screenshots_dir = Path("./screenshots")

    if not screenshots_dir.exists():
        print(f"Error: {screenshots_dir} folder not found.")
        print("Please run screenCapture.py first to generate screenshots.")
        exit(1)

    # Get all PNG files sorted by name (timestamp order)
    screenshot_files = sorted(screenshots_dir.glob("screenshot_*.png"))

    if not screenshot_files:
        print(f"No screenshots found in {screenshots_dir}")
        exit(1)

    print(f"Processing {len(screenshot_files)} screenshots...\n")

    for idx, screenshot_path in enumerate(screenshot_files, 1):
        start_time = time.perf_counter()

        image = cv2.imread(str(screenshot_path))
        if image is None:
            print(f"[{idx}] ERROR: Could not load {screenshot_path.name}")
            continue

        text, _ = getTextFromImage(image, debug=False)
        elapsed = time.perf_counter() - start_time

        print(f"[{idx}] {screenshot_path.name}: {text} ({elapsed:.3f}s)")

    print("\nProcessing complete!")
