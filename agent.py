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
        print(f"PlaceMonkeyAction type: {tower_type}")
        return PlaceMonkeyAction(tower_type, self._random_position())


    def retry_placement(self, tower_type):
        position = self._random_position()
        print(f"Retry PlaceMonkeyAction type: {tower_type}")
        return PlaceMonkeyAction(tower_type, position)

    def _random_position(self):
        x1, y1, x2, y2 = regions.MAP_BOUNDS
        x = random.randint(x1, x2)
        y = random.randint(y1, y2)
        return (x, y)


def truncate_build_log(build_log, cutoff_round):
    """Keeps only events scheduled at or before cutoff_round."""
    return [event for event in build_log if event["round"] <= cutoff_round]


class ReplayThenRandomAgent:
    """Replays a recorded build_log up to (and including) cutoff_round, then
    permanently falls back to random play for the rest of the episode.

    Events are matched to live monkeys by position (not the old episode's
    monkey_id, which has no meaning in a fresh episode)."""

    def __init__(self, build_log, cutoff_round, fallback_agent=None):
        self.build_log = build_log
        self.cutoff_round = cutoff_round
        self.fallback_agent = fallback_agent or RandomAgent()
        self._index = 0
        self._exhausted = False  # True once we've passed cutoff_round -> random forever after

    def choose_action(self, state):
        if not self._exhausted and state.current_round > self.cutoff_round:
            self._exhausted = True

        if self._exhausted:
            return self.fallback_agent.choose_action(state)

        while (self._index < len(self.build_log)
               and self.build_log[self._index]["round"] == state.current_round):
            event = self.build_log[self._index]
            self._index += 1
            action = self._event_to_action(event, state)
            if action is not None:
                return action
            # else: target monkey missing (its placement earlier failed to verify) -> skip event

        return StartRoundAction()

    def _event_to_action(self, event, state):
        if event["type"] == "place":
            return PlaceMonkeyAction(event["tower_type"], tuple(event["position"]))

        if event["type"] == "upgrade":
            monkey = self._find_monkey_at(state, event["position"])
            if monkey is None:
                print(f"ReplayThenRandomAgent: SKIPPING upgrade (round {event['round']}, "
                      f"tower_type={event.get('tower_type')}, path {event['path_index']}) "
                      f"-- no monkey at position {event['position']}; its place event "
                      f"probably failed to verify earlier in this replay. "
                      f"Live positions right now: "
                      f"{[m.position for m in state.placed_monkeys]}")
                return None
            return UpgradeMonkeyAction(monkey.id, event["path_index"])

        if event["type"] == "start_round":
            return StartRoundAction()

        return None

    def _find_monkey_at(self, state, position):
        position = tuple(position)
        for m in state.placed_monkeys:
            if tuple(m.position) == position:
                return m
        return None

    def retry_placement(self, tower_type):
        if self._exhausted:
            return self.fallback_agent.retry_placement(tower_type)
        # Scripted phase: don't retry at a random spot -- it could occupy a
        # position a later scripted event depends on. Just give up on this one.
        return None