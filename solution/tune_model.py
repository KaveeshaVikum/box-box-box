import json
import itertools
from pathlib import Path

HIST_DIR = Path("data/historical_races")


def load_races(limit_files=3):
    races = []
    files = sorted(HIST_DIR.glob("*.json"))[:limit_files]
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                races.extend(data)
    return races


def get_final_tire(strategy):
    pits = strategy.get("pit_stops", [])
    if pits:
        return pits[-1]["to_tire"]
    return strategy.get("starting_tire", "MEDIUM")


def top10_score(pred, actual):
    score = 0
    for i, driver in enumerate(pred[:10]):
        if i < len(actual) and driver == actual[i]:
            score += 1
    return score


def simulate_driver(strategy, race_config, params):
    total_laps = race_config["total_laps"]
    base_lap_time = race_config["base_lap_time"]
    pit_lane_time = race_config["pit_lane_time"]
    track_temp = race_config["track_temp"]

    current_tire = strategy.get("starting_tire", "MEDIUM")
    pit_stops = sorted(strategy.get("pit_stops", []), key=lambda x: x["lap"])

    total_time = 0.0
    tire_age = 0
    stop_index = 0

    for lap in range(1, total_laps + 1):
        lap_time = (
            base_lap_time
            + params["BASE_TIRE_OFFSET"][current_tire]
            + params["LINEAR_WEAR"][current_tire] * tire_age
            + params["QUADRATIC_WEAR"][current_tire] * (tire_age ** 2)
        )

        if current_tire == "SOFT":
            lap_time += max(0.0, track_temp - 30) * params["SOFT_TEMP"]
        elif current_tire == "MEDIUM":
            lap_time += max(0.0, track_temp - 32) * params["MEDIUM_TEMP"]
        elif current_tire == "HARD":
            lap_time += max(0.0, 26 - track_temp) * params["HARD_TEMP"]

        total_time += lap_time
        tire_age += 1

        if stop_index < len(pit_stops) and pit_stops[stop_index]["lap"] == lap:
            stop = pit_stops[stop_index]
            total_time += pit_lane_time
            current_tire = stop.get("to_tire", current_tire)
            tire_age = 0
            stop_index += 1

    final_tire = get_final_tire(strategy)
    total_time += params["FINAL_TIRE_BONUS"][final_tire]
    return total_time


def predict_race(race, params):
    race_config = race["race_config"]
    strategies = race["strategies"]

    results = []
    for _, strategy in strategies.items():
        driver_id = strategy["driver_id"]
        total_time = simulate_driver(strategy, race_config, params)
        results.append((driver_id, total_time))

    results.sort(key=lambda x: x[1])
    return [driver_id for driver_id, _ in results]


def evaluate_params(races, params):
    total = 0
    for race in races:
        actual = race.get("finishing_positions", [])
        pred = predict_race(race, params)
        total += top10_score(pred, actual)
    return total


def build_candidates():
    soft_offsets = [-1.5, -1.4, -1.3]
    hard_offsets = [0.9, 1.0, 1.1]

    soft_linear = [0.11, 0.12, 0.13]
    medium_linear = [0.07, 0.08, 0.09]
    hard_linear = [0.035, 0.04, 0.045]

    soft_quad = [0.0035, 0.0045, 0.0055]
    medium_quad = [0.0015, 0.0020, 0.0025]
    hard_quad = [0.0007, 0.0008, 0.0010]

    soft_bonus = [-0.8, -0.7, -0.6]
    medium_bonus = [-0.5, -0.4, -0.3]

    soft_temp = [0.025, 0.030, 0.035]
    medium_temp = [0.012, 0.015, 0.018]
    hard_temp = [0.010, 0.012, 0.015]

    for (
        so, ho,
        sl, ml, hl,
        sq, mq, hq,
        sb, mb,
        st, mt, ht
    ) in itertools.product(
        soft_offsets, hard_offsets,
        soft_linear, medium_linear, hard_linear,
        soft_quad, medium_quad, hard_quad,
        soft_bonus, medium_bonus,
        soft_temp, medium_temp, hard_temp
    ):
        yield {
            "BASE_TIRE_OFFSET": {
                "SOFT": so,
                "MEDIUM": 0.0,
                "HARD": ho,
            },
            "LINEAR_WEAR": {
                "SOFT": sl,
                "MEDIUM": ml,
                "HARD": hl,
            },
            "QUADRATIC_WEAR": {
                "SOFT": sq,
                "MEDIUM": mq,
                "HARD": hq,
            },
            "FINAL_TIRE_BONUS": {
                "SOFT": sb,
                "MEDIUM": mb,
                "HARD": 0.0,
            },
            "SOFT_TEMP": st,
            "MEDIUM_TEMP": mt,
            "HARD_TEMP": ht,
        }


def main():
    races = load_races(limit_files=3)
    print(f"Loaded {len(races)} races")

    best_score = -1
    best_params = None
    checked = 0

    for params in build_candidates():
        checked += 1
        score = evaluate_params(races, params)

        if score > best_score:
            best_score = score
            best_params = params
            print("\nNEW BEST")
            print("checked:", checked)
            print("score:", best_score)
            print(json.dumps(best_params, indent=2))

        if checked % 200 == 0:
            print("checked so far:", checked, "best:", best_score)

        if checked >= 1500:
            break

    print("\nFINAL BEST SCORE:", best_score)
    print(json.dumps(best_params, indent=2))


if __name__ == "__main__":
    main()