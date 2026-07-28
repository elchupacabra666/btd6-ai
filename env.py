# env.py
import time
import logging

from game_state import GameState
from game_controller import GameController
from actions import Action, ActionResult, PlaceMonkeyAction, UpgradeMonkeyAction, StartRoundAction


def _setup_logger():
    logger = logging.getLogger("btd6_env")
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # avoid duplicate handlers if instantiated twice
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                                       datefmt="%H:%M:%S")

        file_handler = logging.FileHandler("btd6_episode.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


class BTD6Env:
    """
    Orchestrates one BTD6 episode: alternates between an agent-driven
    build/upgrade phase (between rounds) and a round phase (no actions
    allowed, game runs on its own).

    Env owns the ONLY authority to:
      - decide when GameState re-syncs from the live screen
      - decide when actions are allowed (round_active gate)
      - compute reward
      - detect game over
    """

    def __init__(self, state: GameState, controller: GameController, agent,
                 round_poll_interval: float = 5.0):
        self.state = state
        self.controller = controller
        self.agent = agent

        self.round_active = False
        self.round_poll_interval = round_poll_interval

        self._lives_before_round = None
        self.log = _setup_logger()

    # ---------------------------------------------------------------
    # Episode loop
    # ---------------------------------------------------------------

    def run_episode(self):
        """Runs one full game from current state until game over."""
        self.log.info("=== Episode start ===")
        self.state.sync(self.controller)
        self.log.info(f"Initial state: money={self.state.money} "
                       f"lives={self.state.lives} round={self.state.current_round}")

        while not self.is_game_over():
            self._build_phase()
            self.state.sync(self.controller)
            self.log.info(f"Sync after build phase: money={self.state.money} "
                           f"lives={self.state.lives} round={self.state.current_round}")
            self._round_phase()

        self.log.info(f"=== Episode end === final round={self.state.current_round} "
                       f"lives={self.state.lives}")
        return self.state

    def _build_phase(self):
        self.log.info("-- Build phase start --")
        self.log.info(f"Money {self.state.money}")
        while True:
            action = self.agent.choose_action(self.state)

            if isinstance(action, StartRoundAction):
                self.log.info("Agent chose: start round")
                self.step(action)
                break

            elif isinstance(action, PlaceMonkeyAction):
                self.log.info(f"Agent chose: place {action.monkey_type} at {action.position}")
                self._attempt_placement(action)

            elif isinstance(action, UpgradeMonkeyAction):
                self.log.info(f"Agent chose: upgrade monkey {action.monkey_id} "
                               f"path {action.path_index}")
                self._attempt_upgrade(action)

            else:
                self.log.warning(f"Unknown action type from agent: {action!r} — skipping")

    def _attempt_placement(self, action, max_attempts=20):
        tower_type = action.monkey_type
        for attempt in range(max_attempts):
            self.log.info(f"Placement attempt {attempt + 1}/{max_attempts} "
                           f"for {tower_type} at {action.position}")

            obs, reward, done, info = self.step(action)
            result = info.get("result")

            if result is not None and result.success:
                self.log.info(f"Placement SUCCEEDED: {tower_type} at {action.position} "
                               f"(money {result.money_before} -> {result.money_after})")
                return True

            if info.get("invalid"):
                self.log.info(f"Placement INVALID (validate() rejected): {tower_type} "
                               f"— giving up on this intent")
                return False

            if result is not None:
                self.log.info(f"Placement FAILED (verify(): {result.error or 'money mismatch'}) "
                               f"— retrying with new position")

            action = self.agent.retry_placement(tower_type)

        self.log.warning(f"Placement GAVE UP after {max_attempts} attempts: {tower_type}")
        return False

    def _attempt_upgrade(self, action, max_attempts=3):
        monkey_id, path_index = action.monkey_id, action.path_index
        for attempt in range(max_attempts):
            self.log.info(f"Upgrade attempt {attempt + 1}/{max_attempts} "
                           f"for monkey {monkey_id} path {path_index}")

            obs, reward, done, info = self.step(action)
            result = info.get("result")

            if result is not None and result.success:
                self.log.info(f"Upgrade SUCCEEDED: monkey {monkey_id} path {path_index} "
                               f"(money {result.money_before} -> {result.money_after})")
                return True

            if info.get("invalid"):
                self.log.info(f"Upgrade INVALID (validate() rejected): monkey {monkey_id} "
                               f"path {path_index} — giving up")
                return False

            if result is not None:
                self.log.warning(f"Upgrade FAILED (verify(): {result.error or 'money mismatch'}) "
                                  f"— retrying identical action "
                                  f"({attempt + 1}/{max_attempts})")

        self.log.warning(f"Upgrade GAVE UP after {max_attempts} attempts: "
                          f"monkey {monkey_id} path {path_index}")
        self.controller.deselect_monkey()
        return False

    def _round_phase(self):
        """Starts the round, waits for it to end, then re-syncs state."""
        self._lives_before_round = self.state.lives
        self.log.info(f"-- Round phase start -- (round={self.state.current_round}, "
                       f"lives={self.state.lives})")

        self.round_active = True
        self._wait_for_round_end()
        self.round_active = False

        self.state.sync(self.controller)
        lives_lost = self._lives_before_round - self.state.lives
        self.log.info(f"-- Round phase end -- round={self.state.current_round}, "
                       f"lives={self.state.lives} (lost {lives_lost})")

    # ---------------------------------------------------------------
    # Single action step (build phase only)
    # ---------------------------------------------------------------

    def step(self, action: Action):
        if self.round_active:
            raise RuntimeError("Cannot act while a round is active")

        if not action.validate(self.state):
            self.log.info(f"Action invalid at validate(): {action.__class__.__name__}")
            return self._obs(), self._invalid_action_penalty(), False, {"invalid": True}

        action.execute(self.controller, self.state)
        result = action.verify(self.controller, self.state)
        action.commit(self.state, result)

        reward = self._compute_action_reward(result)
        done = self.is_game_over()
        return self._obs(), reward, done, {"result": result}

    # ---------------------------------------------------------------
    # Round-end detection
    # ---------------------------------------------------------------

    def _wait_for_round_end(self):
        """Polls the round-end pixel until the round finishes, ensuring 2x speed each poll."""
        poll_count = 0
        while True:
            time.sleep(self.round_poll_interval)
            poll_count += 1

            if self.controller.check_round_end():
                self.log.info(f"Round end detected after {poll_count} polls "
                               f"({poll_count * self.round_poll_interval:.1f}s)")
                return True

            self.controller.ensure_double_speed()
            self.log.debug(f"Poll {poll_count}: round still active")

    # ---------------------------------------------------------------
    # Reward + termination
    # ---------------------------------------------------------------

    def _compute_action_reward(self, result: ActionResult) -> float:
        return 0

    def _invalid_action_penalty(self) -> float:
        return -1.0

    def is_game_over(self) -> bool:
        return self.state.lives <= 0

    def _obs(self):
        return self.state.to_dict()