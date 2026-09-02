# BTD6 AI Agent & Evolutionary Optimizer

An automated gameplay framework for **Bloons TD 6 (BTD6)** that utilizes computer vision, simulated inputs, and evolutionary algorithms to train, log, and optimize automated play strategies. 

## Overview

This project orchestrates automated builds, tower placements, and upgrades across rounds. It reads the game state directly from the screen using OCR and pixel matching, logs every episode's build order, and uses an evolutionary mutation pipeline to breed successful gameplay strategies over multiple generations.

## Features

* **Computer Vision Controller:** Reads live cash, lives, and rounds from the screen using `mss`, OpenCV, and Tesseract OCR.
* **State Validation:** Uses fast pixel-color matching for detecting round completion, victory screens, defeat states, and automatic restarts.
* **Evolutionary Strategy Generator:** Explores random gameplay loops, mutates successful build logs across generations, and preserves historical lineage in JSON databases.
* **Replay & Mutation Engines:** Replays recorded episode histories verbatim or introduces random cutoff mutations to discover optimal paths.
* **Win32 Input Automation:** Sends direct mouse clicks and keyboard shortcuts to interact with the game window.
* **Global Killswitch:** Instantly aborts execution at a safe checkpoint using a system-wide hotkey (`Ctrl + Shift + Q`).

## Project Structure

* `main.py` — Entry point for running live random-agent training loops.
* `evolve.py` — Evolutionary training pipeline that mutates successful runs across generations and saves to `champion.json`.
* `env.py` — Core episode orchestrator managing build phases, round transitions, and termination checks.
* `game_controller.py` — Coordinates mouse input, screen actions, and OCR status validation.
* `ocr.py` & `capture.py` — Handles screen grabbing, image preprocessing, and Tesseract text extraction.
* `agent.py` — AI behavior definitions, including random builders and mutation replay agents.
* `game_state.py` — Tracks placed monkeys, upgrade trees, money, and round history.
* `episode_log.py` — Manages reading and writing run histories to `learning_memory.json`.
* `costs.py` & `progress.py` — Static definitions for tower pricing, difficulty scales, and account unlock caps.
* `mutate_run.py` & `replay_run.py` — Standalone scripts for replaying or branching off specific recorded gameplay sessions.
* `regions.py` & `controls.py` — Hardcoded screen coordinates, UI colors, and low-level Windows API input wrappers.

## Setup & Installation

### Requirements
* Python 3.x
* **Tesseract OCR:** Must be installed on your system for text recognition.
* A primary 1080p monitor (or adjust the hardcoded bounds in `regions.py` for your resolution).

### Python Dependencies
Install the required packages using pip:
```bash
pip install mss pytesseract opencv-python keyboard numpy
```

## Usage

1. **Launch the Game:** Open Bloons TD 6. The scripts will automatically attempt to find the window, maximize it, and bring it to the foreground.
2. **Run Training / Evolution:**
   * Run standard random episodes:
     ```bash
     python main.py
     ```
   * Run the evolutionary optimizer to breed better strategies:
     ```bash
     python evolve.py
     ```
   * Replay a specific recorded run:
     ```bash
     python replay_run.py [episode_number]
     ```
   * Mutate a specific recorded run:
     ```bash
     python mutate_run.py [episode_number]
     ```
3. **Emergency Stop:** Press `Ctrl + Shift + Q` at any time to safely halt execution via the global killswitch.
