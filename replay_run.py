# replay_run.py
"""Standalone runner: replays a recorded episode's build_log verbatim, with
no random building at all -- for checking replay fidelity before wiring up
mutation. Usage: python replay_run.py [episode_num]
(defaults to the best recorded episode if episode_num is omitted)."""
import json
import sys
from time import sleep

from game_state import GameState
from game_controller import GameController
from agent import ReplayThenRandomAgent
from env import BTD6Env
from killswitch import KillSwitch

RESULTS_FILE = "learning_memory.json"


def load_episode(filename=RESULTS_FILE, episode_num=None):
    with open(filename, "r") as file:
        episodes = json.load(file)

    if not episodes:
        raise ValueError(f"{filename} has no recorded episodes")

    if episode_num is not None:
        matches = [e for e in episodes if e["episode"] == episode_num]
        if not matches:
            raise ValueError(f"No episode #{episode_num} found in {filename}")
        return matches[0]

    return max(episodes, key=lambda e: (e["outcome"] == "victory", e["final_round"], e["final_lives"]))


def main():
    episode_num = int(sys.argv[1]) if len(sys.argv) > 1 else None
    episode = load_episode(episode_num=episode_num)
    print(f"Replaying episode {episode['episode']} "
          f"(outcome={episode['outcome']}, final_round={episode['final_round']}, "
          f"difficulty={episode['difficulty']})")

    build_log = episode.get("build_log", [])
    difficulty = episode["difficulty"]

    controller = GameController()
    kill = KillSwitch(hotkey="ctrl+shift+q")

    sleep(3)

    starting_money = controller.read_money()
    starting_lives = controller.read_lives()
    starting_round = controller.read_round()

    state = GameState(starting_money, starting_lives, starting_round, difficulty)
    agent = ReplayThenRandomAgent(build_log, cutoff_round=float("inf"))
    env = BTD6Env(state, controller, agent, round_poll_interval=0.5, killswitch=kill)

    final_state = env.run_episode()
    print(f"Replay ended. Outcome: {env.last_outcome}, "
          f"final round: {final_state.current_round}, lives: {final_state.lives}")


if __name__ == "__main__":
    main()
