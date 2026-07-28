# agent.py
import random

from actions import PlaceMonkeyAction, UpgradeMonkeyAction, StartRoundAction
from costs import TOWER_COSTS, tower_cost, upgrade_cost
import regions
from progress import MAX_UPGRADE_TIER


class RandomAgent:
    def __init__(self, stop_probability=0, upgrade_probability=0.2):
        self.stop_probability = stop_probability
        self.upgrade_probability = upgrade_probability

    def choose_action(self, state):
        roll = random.random()
        print(f"choose_action: round={state.current_round!r} roll={roll:.3f}")

        if roll < self.stop_probability:
            print("decision: start round")
            return StartRoundAction()

        if roll < self.stop_probability + self.upgrade_probability:
            candidates = self._upgrade_candidates(state)

            print(f"upgrade candidates ({len(candidates)}): {candidates}")
            for m in state.placed_monkeys:
                print(f"Monkey: {m.id}, type: {m.tower_type}, upgrades: {m.upgrades}")
            
            if candidates:
                
                return self._choose_upgrade(state, candidates)
            print("decision: upgrade rolled, but none available -> build instead")
            return self._choose_build(state)

        print("decision: build new")
        return self._choose_build(state)

    # ---------------------------------------------------------------
    # Upgrade path
    # ---------------------------------------------------------------

    def _upgrade_candidates(self, state):
        return [
            (monkey.id, path_index)
            for monkey in state.placed_monkeys
            for path_index in range(len(monkey.upgrades))
            if monkey.can_upgrade(path_index)
            and monkey.upgrades[path_index] < MAX_UPGRADE_TIER.get(monkey.tower_type, 5)
            and state.money >= upgrade_cost(
                monkey.tower_type, path_index, monkey.upgrades[path_index], state.difficulty
            )
        ]
    
    def _choose_upgrade(self, state, candidates):
        monkey_id, path_index = random.choice(candidates)
        return UpgradeMonkeyAction(monkey_id, path_index)

    # ---------------------------------------------------------------
    # Build path
    # ---------------------------------------------------------------

    def _choose_build(self, state):
        affordable_types = [
            t for t in TOWER_COSTS
            if state.money >= tower_cost(t, state.difficulty)
        ]
        if not affordable_types:
            return StartRoundAction()
        tower_type = random.choice(affordable_types)
        return PlaceMonkeyAction(tower_type, self._random_position())


    def retry_placement(self, tower_type):
        position = self._random_position()
        return PlaceMonkeyAction(tower_type, position)

    def _random_position(self):
        x1, y1, x2, y2 = regions.MAP_BOUNDS
        x = random.randint(x1, x2)
        y = random.randint(y1, y2)
        return (x, y)