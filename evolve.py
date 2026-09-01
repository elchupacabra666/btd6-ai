# evolve.py
"""One-button evolutionary run.

Generation 0 is pure random exploration (X episodes). Every generation after
that mutates the previous generation's best result (X episodes, same
cutoff-and-replay scheme as mutate_run.py). The best result of each
generation is appended to champion.json -- so it ends up holding the full
lineage, one entry per generation.

The moment any episode ends in victory, that run is appended to
champion.json and the whole program stops immediately -- no more episodes,
no more generations.

Usage: python evolve.py
Asks for difficulty, episodes per generation, and number of generations
(evolution layers) at startup, then runs unattended -- besides restarting
the game after a defeat, and pausing on a repeated OCR read error so you can
fix the screen by hand."""
import json
import random
from time import sleep

from game_state import GameState
from game_controller import GameController
from agent import RandomAgent, ReplayThenRandomAgent
from env import BTD6Env
from killswitch import KillSwitch
from episode_log import build_episode_summary, load_results, save_results, next_episode_num, RESULTS_FILE
from mutate_run import build_log_top_round

CHAMPION_FILE = "champion.json"

RANKING_KEY = lambda e: (e["outcome"] == "victory", e["final_round"], e["final_lives"])


def load_champions(filename=CHAMPION_FILE):
    """Loads the recorded per-generation champions, or [] if none yet."""
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def append_champion(entry, filename=CHAMPION_FILE):
    """Appends one champion entry (tagged with its generation) to
    champion.json, preserving every earlier generation's champion."""
    champions = load_champions(filename)
    champions.append(entry)
    with open(filename, "w") as file:
        json.dump(champions, file, indent=4)


def run_one_episode(controller, kill, state, agent, difficulty, generation, source):
    env = BTD6Env(state, controller, agent, round_poll_interval=0.5, killswitch=kill)
    final_state = env.run_episode()
    outcome = env.last_outcome

    all_results = load_results()
    episode_num = next_episode_num(all_results)
    summary = build_episode_summary(episode_num, final_state, outcome, difficulty,
                                     source=source, generation=generation)
    all_results.append(summary)
    save_results(all_results)
    print(f"  -> outcome={outcome}, final round={final_state.current_round}, "
          f"lives={final_state.lives} (logged as episode {episode_num} in {RESULTS_FILE})")
    return summary


def reset_for_next_episode(controller, outcome):
    """Mirrors main.py / mutate_run.py's between-episode handling. Never
    called after a victory -- the caller stops the program first."""
    if outcome == "ocr_error":
        input("OCR read failed repeatedly -- game state unknown, skipped auto-restart. "
              "Fix the game/screen manually, then press Enter to continue...")
    else:
        print("Defeat -- clicking restart...")
        controller.click_restart()
        sleep(3)


def main():
    controller = GameController()

    difficulty = input("Enter difficulty (easy/medium/hard/impoppable): ").strip().lower()
    assert difficulty in ("easy", "medium", "hard", "impoppable")

    episodes_per_gen = int(input("How many episodes per generation? ").strip())
    num_generations = int(input("How many generations (evolution layers)? ").strip())
    assert episodes_per_gen > 0 and num_generations > 0

    print(f"\nPlan: {num_generations} generation(s) x {episodes_per_gen} episode(s) "
          f"= up to {num_generations * episodes_per_gen} episodes total "
          f"(fewer if a victory ends it early), difficulty={difficulty}.")

    kill = KillSwitch(hotkey="ctrl+shift+q")
    champion = None
    sleep(3)

    for gen in range(num_generations):
        is_random_gen = (gen == 0) or (champion is None)
        label = "random exploration" if is_random_gen else "mutation"
        print(f"\n=== Generation {gen} ({label}, {episodes_per_gen} episodes) ===")

        top_round = None
        if not is_random_gen:
            top_round = build_log_top_round(champion["build_log"], fallback=champion["final_round"])

        gen_results = []
        for i in range(episodes_per_gen):
            if kill.is_triggered():
                print("Killswitch triggered -- stopping.")
                if gen_results:
                    append_champion(max(gen_results, key=RANKING_KEY))
                return

            print(f"\n-- Generation {gen}, episode {i + 1}/{episodes_per_gen} --")
            starting_money = controller.read_money()
            starting_lives = controller.read_lives()
            starting_round = controller.read_round()
            state = GameState(starting_money, starting_lives, starting_round, difficulty)

            if is_random_gen:
                agent = RandomAgent(stop_probability=0.2, upgrade_probability=0.4)
                source = "random"
            else:
                fallback_agent = RandomAgent(stop_probability=0.2, upgrade_probability=0.4)
                if i == 0:
                    cutoff_round = top_round
                else:
                    cutoff_round = top_round - random.randint(1, top_round) if top_round > 0 else 0
                agent = ReplayThenRandomAgent(champion["build_log"], cutoff_round=cutoff_round,
                                               fallback_agent=fallback_agent)
                source = "mutation"

            summary = run_one_episode(controller, kill, state, agent, difficulty, gen, source)

            if summary["outcome"] == "victory":
                append_champion(summary)
                print(f"\n*** VICTORY on generation {gen}, episode {i + 1}! "
                      f"Winning strategy appended to {CHAMPION_FILE}. Stopping. ***")
                return

            gen_results.append(summary)

            if kill.is_triggered():
                print("Killswitch triggered -- stopping.")
                append_champion(max(gen_results, key=RANKING_KEY))
                return

            reset_for_next_episode(controller, summary["outcome"])

        gen_best = max(gen_results, key=RANKING_KEY)
        append_champion(gen_best)
        print(f"\nGeneration {gen} complete. Best of this generation: episode {gen_best['episode']} "
              f"(final round {gen_best['final_round']}, lives {gen_best['final_lives']}, "
              f"outcome {gen_best['outcome']}) -- appended to {CHAMPION_FILE}")

        # Next generation always mutates from this generation's best, full stop --
        # no comparison against earlier generations.
        champion = gen_best

    print(f"\nAll {num_generations} generation(s) complete. "
          f"Last generation's champion: episode {champion['episode']} "
          f"(final round {champion['final_round']}). "
          f"See {CHAMPION_FILE} for the full per-generation lineage, "
          f"and {RESULTS_FILE} for every attempt made.")


if __name__ == "__main__":
    main()
