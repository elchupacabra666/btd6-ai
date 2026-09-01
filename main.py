# main.py
from game_state import GameState
from game_controller import GameController
from agent import RandomAgent
from env import BTD6Env
from time import sleep
from killswitch import KillSwitch
from episode_log import build_episode_summary, save_results, RESULTS_FILE


def main():
    controller = GameController()

    DIFFICULTY = input("Enter difficulty (easy/medium/hard/impoppable): ").strip().lower()
    assert DIFFICULTY in ("easy", "medium", "hard", "impoppable")

    runs_input = input("Enter number of runs to play (leave blank for unlimited): ").strip()
    MAX_EPISODES = int(runs_input) if runs_input else None
    assert MAX_EPISODES is None or MAX_EPISODES > 0

    kill = KillSwitch(hotkey="ctrl+shift+q")
    episode_results = []
    episode_num = 0

    sleep(3)

    while not kill.is_triggered() and (MAX_EPISODES is None or episode_num < MAX_EPISODES):
        episode_num += 1
        print(f"\n=== Starting episode {episode_num} ===")

        starting_money = controller.read_money()
        starting_lives = controller.read_lives()
        starting_round = controller.read_round()

        state = GameState(starting_money, starting_lives, starting_round, DIFFICULTY)
        agent = RandomAgent(stop_probability=0.5, upgrade_probability=0.3)
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
