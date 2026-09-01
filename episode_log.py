# episode_log.py
"""Shared helpers for recording episode results to learning_memory.json.
Used by both main.py (live/random play) and replay_run.py (scripted replay)."""
import json

RESULTS_FILE = "learning_memory.json"


def build_episode_summary(episode_num, state, outcome, difficulty, **extra):
    """Builds one learning_memory.json entry. Extra keyword args (e.g.
    source="replay", replay_of=<episode_num>) are merged in as-is, so callers
    can tag entries without changing the base schema."""
    summary = {
        "episode": episode_num,
        "outcome": outcome,
        "final_round": state.current_round,
        "final_lives": state.lives,
        "difficulty": difficulty,
        "monkeys_placed": len(state.placed_monkeys),
    }
    summary.update(extra)
    summary["build_log"] = state.build_log
    summary["final_monkeys"] = [m.to_dict() for m in state.placed_monkeys]
    return summary


def load_results(filename=RESULTS_FILE):
    """Loads recorded episodes, or [] if the file doesn't exist yet."""
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def save_results(results, filename=RESULTS_FILE):
    with open(filename, "w") as file:
        json.dump(results, file, indent=4)


def next_episode_num(results):
    """Next free episode number, so appended runs don't collide with
    existing ones."""
    return max((e["episode"] for e in results), default=0) + 1


def load_episode(filename=RESULTS_FILE, episode_num=None):
    """Loads one recorded episode by number, or the best one (by victory,
    then final_round, then final_lives) if episode_num is omitted."""
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
