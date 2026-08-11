# main.py
import json

from game_state import GameState
from game_controller import GameController
from agent import RandomAgent
from env import BTD6Env
from time import sleep
from killswitch import KillSwitch

RESULTS_FILE = "learning_memory.json"


def build_episode_summary(episode_num, state, outcome, difficulty):
    return {
        "episode": episode_num,
        "outcome": outcome,
        "final_round": state.current_round,
        "final_lives": state.lives,
        "difficulty": difficulty,
        "monkeys_placed": len(state.placed_monkeys),
        "build_log": state.build_log,
        "final_monkeys": [m.to_dict() for m in state.placed_monkeys],
    }


def save_results(results, filename=RESULTS_FILE):
    with open(filename, "w") as file:
        json.dump(results, file, indent=4)


def main():
    controller = GameController()

    DIFFICULTY = input("Enter difficulty (easy/medium/hard/impoppable): ").strip().lower()
    assert DIFFICULTY in ("easy", "medium", "hard", "impoppable")

    kill = KillSwitch(hotkey="ctrl+shift+q")
    episode_results = []
    episode_num = 0

    sleep(3)

    while not kill.is_triggered():
        episode_num += 1
        print(f"\n=== Starting episode {episode_num} ===")

        starting_money = controller.read_money()
        starting_lives = controller.read_lives()
        starting_round = controller.read_round()

        state = GameState(starting_money, starting_lives, starting_round, DIFFICULTY)
        agent = RandomAgent(stop_probability=0.5, upgrade_probability=0.4)
        env = BTD6Env(state, controller, agent, round_poll_interval=0.5, killswitch=kill)

        final_state = env.run_episode()
        outcome = env.last_outcome
        print(f"Episode {episode_num} ended. Outcome: {outcome}, "
              f"final round: {final_state.current_round}, lives: {final_state.lives}")

        episode_results.append(build_episode_summary(episode_num, final_state, outcome, DIFFICULTY))
        save_results(episode_results)

        if kill.is_triggered():
            print("Killswitch triggered -- stopping.")
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
