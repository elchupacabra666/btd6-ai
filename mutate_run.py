# mutate_run.py
"""Loops episodes seeded from one recorded build_log:

  Run 1:   replays the build_log verbatim (falls back to random play only
           once the scripted rounds run out, instead of stalling on
           StartRoundAction like replay_run.py does on purpose).
  Run 2+:  randomly cuts off the last N scripted rounds (N random each run)
           and plays the remainder randomly, to explore variations around
           a known-decent run.

Usage: python mutate_run.py [episode_num]
(defaults to the best recorded episode if episode_num is omitted). Asks for
a run cap at startup -- leave blank to run until the killswitch."""
import random
import sys
from time import sleep

from game_state import GameState
from game_controller import GameController
from agent import ReplayThenRandomAgent, RandomAgent
from env import BTD6Env
from killswitch import KillSwitch
from episode_log import (build_episode_summary, load_results, save_results,
                          next_episode_num, load_episode, RESULTS_FILE)


def build_log_top_round(build_log, fallback=0):
    rounds = [event["round"] for event in build_log]
    return max(rounds) if rounds else fallback


def main():
    source_episode_num = int(sys.argv[1]) if len(sys.argv) > 1 else None
    source = load_episode(episode_num=source_episode_num)

    build_log = source.get("build_log", [])
    difficulty = source["difficulty"]
    top_round = build_log_top_round(build_log, fallback=source.get("final_round", 0))

    print(f"Mutating from episode {source['episode']} "
          f"(outcome={source['outcome']}, difficulty={difficulty}, "
          f"scripted through round {top_round})")

    cap_input = input("How many runs? (blank = until killswitch): ").strip()
    run_cap = int(cap_input) if cap_input else None

    controller = GameController()
    kill = KillSwitch(hotkey="ctrl+shift+q")
    fallback_agent = RandomAgent(stop_probability=0.5, upgrade_probability=0.4)

    sleep(3)

    run_num = 0
    while not kill.is_triggered() and (run_cap is None or run_num < run_cap):
        run_num += 1

        if run_num == 1:
            cutoff_round = top_round
            rounds_cut = 0
        else:
            rounds_cut = random.randint(1, top_round) if top_round > 0 else 0
            cutoff_round = top_round - rounds_cut

        print(f"\n=== Mutation run {run_num}"
              f"{f'/{run_cap}' if run_cap else ''}: "
              f"cutoff_round={cutoff_round} (cutting last {rounds_cut} scripted rounds) ===")

        starting_money = controller.read_money()
        starting_lives = controller.read_lives()
        starting_round = controller.read_round()

        state = GameState(starting_money, starting_lives, starting_round, difficulty)
        agent = ReplayThenRandomAgent(build_log, cutoff_round=cutoff_round,
                                       fallback_agent=fallback_agent)
        env = BTD6Env(state, controller, agent, round_poll_interval=0.5, killswitch=kill)

        final_state = env.run_episode()
        outcome = env.last_outcome
        print(f"Run {run_num} ended. Outcome: {outcome}, "
              f"final round: {final_state.current_round}, lives: {final_state.lives}")

        all_results = load_results()
        new_episode_num = next_episode_num(all_results)
        summary = build_episode_summary(new_episode_num, final_state, outcome, difficulty,
                                         source="mutation", replay_of=source["episode"],
                                         cutoff_round=cutoff_round, rounds_cut=rounds_cut)
        all_results.append(summary)
        save_results(all_results)
        print(f"Logged as episode {new_episode_num} in {RESULTS_FILE}")

        if kill.is_triggered():
            print("Killswitch triggered -- stopping.")
            break

        if run_cap is not None and run_num >= run_cap:
            print(f"Run cap ({run_cap}) reached -- stopping.")
            break

        if outcome == "victory":
            input("Victory! Set up the next map, then press Enter to continue...")
        elif outcome == "ocr_error":
            input("OCR read failed repeatedly -- game state unknown, skipped auto-restart. "
                  "Fix the game/screen manually, then press Enter to continue...")
        else:
            print("Defeat -- clicking restart...")
            controller.click_restart()
            sleep(3)  # let the map reload before reading fresh state


if __name__ == "__main__":
    main()
