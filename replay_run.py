# replay_run.py
"""Standalone runner: replays a recorded episode's build_log verbatim, with
no random building at all -- for checking replay fidelity before wiring up
mutation. Usage: python replay_run.py [episode_num]
(defaults to the best recorded episode if episode_num is omitted)."""
import sys
from time import sleep

from game_state import GameState
from game_controller import GameController
from agent import ReplayThenRandomAgent
from env import BTD6Env
from killswitch import KillSwitch
from episode_log import (build_episode_summary, load_results, save_results,
                          next_episode_num, load_episode, RESULTS_FILE)


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
    outcome = env.last_outcome
    print(f"Replay ended. Outcome: {outcome}, "
          f"final round: {final_state.current_round}, lives: {final_state.lives}")

    all_results = load_results()
    new_episode_num = next_episode_num(all_results)
    summary = build_episode_summary(new_episode_num, final_state, outcome, difficulty,
                                     source="replay", replay_of=episode["episode"])
    all_results.append(summary)
    save_results(all_results)
    print(f"Logged as episode {new_episode_num} (replay of episode {episode['episode']}) "
          f"in {RESULTS_FILE}")


if __name__ == "__main__":
    main()
