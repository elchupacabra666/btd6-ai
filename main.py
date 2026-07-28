# main.py
from game_state import GameState
from game_controller import GameController
from agent import RandomAgent
from env import BTD6Env
from time import sleep

def main():
    controller = GameController()

    DIFFICULTY = input("Enter difficulty (easy/medium/hard/impoppable): ").strip().lower()
    assert DIFFICULTY in ("easy", "medium", "hard", "impoppable")

    sleep(3)

    starting_money = controller.read_money()
    starting_lives = controller.read_lives()
    starting_round = controller.read_round()



    state = GameState(starting_money, starting_lives, starting_round, DIFFICULTY)
    agent = RandomAgent(stop_probability=0.2, upgrade_probability=0.6)
    env = BTD6Env(state, controller, agent, round_poll_interval=5.0)

    final_state = env.run_episode()
    final_state.save_to_json("learning_memory.json")
    print(f"Episode ended. Final round: {final_state.current_round}, lives: {final_state.lives}")

if __name__ == "__main__":
    main()