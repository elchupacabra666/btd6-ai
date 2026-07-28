from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from time import sleep

from game_state import GameState 
from game_controller import GameController, OCRReadError
from costs import tower_cost, upgrade_cost

@dataclass
class ActionResult:
    success: bool
    money_before: int
    money_after: int
    error: Optional[str] = None

class Action(ABC):
    @abstractmethod
    def validate(self, state: GameState) -> bool: ...
    @abstractmethod
    def execute(self, controller: GameController, state: GameState) -> None: ...
    @abstractmethod
    def verify(self, controller: GameController, state: GameState) -> ActionResult: ...
    @abstractmethod
    def commit(self, state: GameState, result: ActionResult) -> None: ...

class PlaceMonkeyAction(Action):
    def __init__(self, monkey_type, position):
        self.monkey_type = monkey_type
        self.position = position

    def validate(self, state):
        return state.money >= tower_cost(self.monkey_type, state.difficulty)

    def execute(self, controller, state):
        controller.select_monkey_shortcut(self.monkey_type)
        controller.click_map(self.position)

    
    def verify(self, controller, state):
        money_before = state.money
        sleep(0.5)
        try:
            money_after = controller.read_money()
        except OCRReadError:
            controller.cancel_placement()
            return ActionResult(success=False, money_before=money_before,
                                 money_after=money_before, error="stuck_placement_cancelled")

        cost = tower_cost(self.monkey_type, state.difficulty)
        print(f"success calculation: {money_after} == {money_before} - {cost}")
        success = money_after == money_before - cost
        return ActionResult(success=success, money_before=money_before, money_after=money_after)

    def commit(self, state, result):
        if result.success:
            cost = tower_cost(self.monkey_type, state.difficulty)
            state.add_monkey(self.monkey_type, self.position, cost=cost)
            state.money = result.money_after

class UpgradeMonkeyAction(Action):
    def __init__(self, monkey_id, path_index):
        self.monkey_id = monkey_id
        self.path_index = path_index
        self.cost = None  # computed in validate()

    def validate(self, state):
        monkey = state.get_monkey(self.monkey_id)
        if monkey is None or not monkey.can_upgrade(self.path_index):
            return False
        self.cost = upgrade_cost(
            monkey.tower_type, self.path_index, monkey.upgrades[self.path_index], state.difficulty
        )
        return state.money >= self.cost

    def execute(self, controller, state):
        monkey = state.get_monkey(self.monkey_id)
        controller.click_upgrade_path(monkey.position, self.path_index)
        controller.cancel_placement()

    def verify(self, controller, state):
        money_before = state.money
        sleep(0.5)
        try:
            money_after = controller.read_money()
        except OCRReadError:
            return ActionResult(
                success=False,
                money_before=money_before,
                money_after=money_before,
                error="ocr_read_failed",
            )
        print(f"success calculation: {money_after} == {money_before} - {self.cost}")
        success = money_after == money_before - self.cost
        return ActionResult(success=success, money_before=money_before, money_after=money_after)

    def commit(self, state, result):
        if result.success:
            state.upgrade_monkey(self.monkey_id, self.path_index, cost=self.cost)
            state.money = result.money_after



class StartRoundAction(Action):
    """Signals the agent is done building and wants to start the round."""

    def validate(self, state):
        return True  # always legal to start whenever agent chooses to

    def execute(self, controller, state):
        controller.click_start_round()

    def verify(self, controller, state):
        # no money-delta check makes sense here; success = the click happened.
        # Env's _wait_for_round_end() is what actually confirms the round began.
        return ActionResult(success=True, money_before=state.money, money_after=state.money)

    def commit(self, state, result):
        pass  # nothing to update on GameState directly; Env handles round transition
