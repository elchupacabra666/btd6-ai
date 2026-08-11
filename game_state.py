import json
import itertools

class Monkey:
    _id_counter = itertools.count(1)

    def __init__(self, tower_type, position, upgrades=None, cost=0):
        self.id = next(Monkey._id_counter)
        self.tower_type = tower_type
        self.position = position  # Tuple (X, Y)
        self.upgrades = upgrades if upgrades is not None else [0, 0, 0]
        self.total_spent = cost           # useful later for reward shaping

    def to_dict(self):
        # Helps with saving to JSON later
        return {
            "id": self.id,
            "tower_type": self.tower_type,
            "position": self.position,
            "upgrades": self.upgrades,
            "total_spent": self.total_spent,
        }
    
    @classmethod
    def from_dict(cls, data):
        m = cls(data["tower_type"], tuple(data["position"]),
                 data["upgrades"], data.get("total_spent", 0))
        m.id = data["id"]
        return m
    

    def can_upgrade(self, path_index):
        future_upgrades = list(self.upgrades)
        future_upgrades[path_index] += 1

        # rule 1: only 2 paths
        sum = 0
        for i in range(len(future_upgrades)):
            if future_upgrades[i] > 0:
                sum += 1
        if sum >= 3:
            return False
        
        # rule 2: no path more than 5
        for i in range(len(future_upgrades)):
            if future_upgrades[i] > 5:
                return False
        # rule 3: no 2 paths more than 3 
        sum = 0
        for i in range(len(future_upgrades)):
            if future_upgrades[i] >= 3:
                sum += 1

        if sum >= 2:
            return False


        return True


    def apply_upgrade(self, path_index, cost=0):
        if self.can_upgrade(path_index):
            self.upgrades[path_index] += 1
            self.total_spent += cost
            return True
        return False
    


class GameState:
    def __init__(self, starting_money, starting_lives, starting_round, difficulty):
        Monkey._id_counter = itertools.count(1)  # monkey ids restart at 1 each episode
        self.money = starting_money
        self.lives = starting_lives
        self.current_round = starting_round
        self.difficulty = difficulty
        self.placed_monkeys = []
        self.build_log = []  # chronological log of place/upgrade events, tagged with round

    # --- placement / upgrades ---

    def add_monkey(self, tower_type, position, cost=0, upgrades=None):
        new_monkey = Monkey(tower_type, position, upgrades, cost)
        self.placed_monkeys.append(new_monkey)
        return new_monkey  # caller (the Action) wants this id for commit()

    def get_monkey(self, monkey_id):
        for m in self.placed_monkeys:
            if m.id == monkey_id:
                return m
        return None

    def remove_monkey(self, monkey_id):
        m = self.get_monkey(monkey_id)
        if m:
            self.placed_monkeys.remove(m)
        return m

    def upgrade_monkey(self, monkey_id, path_index, cost=0):
        m = self.get_monkey(monkey_id)
        if m is None:
            return False
        return m.apply_upgrade(path_index, cost)

    # --- build/upgrade history ---

    def log_event(self, event_type, **details):
        """Records a successful place/upgrade, tagged with the round it happened in
        (i.e. the round about to start when the build-phase action was committed)."""
        self.build_log.append({"round": self.current_round, "type": event_type, **details})

    # --- meta state ---

    def update_round(self, new_round):
        self.current_round = new_round

    def advance_round(self):
        """Call once a round has finished playing, moving state into the
        next build phase. Round is tracked locally like this instead of
        being re-read via OCR every sync, since the round counter is the
        value OCR misreads most."""
        self.current_round += 1

    def sync(self, controller):
        """Refresh money/lives from the live game via OCR."""
        self.money = controller.read_money()
        self.lives = controller.read_lives()

    # --- persistence ---

    def to_dict(self):
        return {
            "money": self.money,
            "lives": self.lives,
            "round": self.current_round,
            "placed_monkeys": [m.to_dict() for m in self.placed_monkeys],
            "build_log": self.build_log,
        }

    def save_to_json(self, filename="learning_memory.json"):
        with open(filename, "w") as file:
            json.dump(self.to_dict(), file, indent=4)

    @classmethod
    def load_from_json(cls, filename="learning_memory.json"):
        with open(filename, "r") as file:
            data = json.load(file)
        state = cls(data["money"], data["lives"], data["round"])
        state.placed_monkeys = [Monkey.from_dict(m) for m in data["placed_monkeys"]]
        return state

