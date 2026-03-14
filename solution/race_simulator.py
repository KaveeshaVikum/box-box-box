import json
import sys

BASE_TIRE_OFFSET = {
    "SOFT": -1.6,
    "MEDIUM": 0.0,
    "HARD": 0.85,
}

LINEAR_WEAR = {
    "SOFT": 0.10,
    "MEDIUM": 0.065,
    "HARD": 0.03,
}

QUADRATIC_WEAR = {
    "SOFT": 0.0030,
    "MEDIUM": 0.0012,
    "HARD": 0.0010,
}

FINAL_TIRE_BONUS = {
    "SOFT": -0.6,
    "MEDIUM": -0.3,
    "HARD": 0.0,
}


def temp_adjustment(tire, track_temp):
    if tire == "SOFT":
        return max(0.0, track_temp - 30) * 0.03
    if tire == "MEDIUM":
        return max(0.0, track_temp - 32) * 0.012
    if tire == "HARD":
        return max(0.0, 26 - track_temp) * 0.008
    return 0.0

def lap_time(base_lap_time, tire, tire_age, track_temp):
    return (
        base_lap_time
        + BASE_TIRE_OFFSET.get(tire, 0.0)
        + LINEAR_WEAR.get(tire, 0.08) * tire_age
        + QUADRATIC_WEAR.get(tire, 0.001) * (tire_age ** 2)
        + temp_adjustment(tire, track_temp)
    )


def get_final_tire(strategy):
    pit_stops = strategy.get("pit_stops", [])
    if pit_stops:
        return pit_stops[-1].get("to_tire", strategy.get("starting_tire", "MEDIUM"))
    return strategy.get("starting_tire", "MEDIUM")


def race_length_adjustment(strategy, race_config):
    total_laps = race_config["total_laps"]
    starting_tire = strategy.get("starting_tire", "MEDIUM")
    pit_stops = strategy.get("pit_stops", [])

    if not pit_stops:
        return 0.0

    first_stop_lap = pit_stops[0]["lap"]
    final_tire = get_final_tire(strategy)

    adj = 0.0

    if starting_tire == "SOFT":
        adj -= first_stop_lap * 0.10
    elif starting_tire == "MEDIUM":
        adj -= first_stop_lap * 0.14
    elif starting_tire == "HARD":
        adj -= first_stop_lap * 0.04

    if total_laps >= 48 and final_tire == "HARD":
        adj -= 0.8
    if total_laps >= 48 and final_tire == "MEDIUM":
        adj -= 0.4
    if total_laps <= 42 and final_tire == "SOFT":
        adj -= 0.5

    adj += FINAL_TIRE_BONUS.get(final_tire, 0.0)

    return adj


def simulate_driver(strategy, race_config):
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
        total_time += lap_time(base_lap_time, current_tire, tire_age, track_temp)
        tire_age += 1

        if stop_index < len(pit_stops) and pit_stops[stop_index]["lap"] == lap:
            stop = pit_stops[stop_index]
            total_time += pit_lane_time
            current_tire = stop.get("to_tire", current_tire)
            tire_age = 0
            stop_index += 1

    total_time += race_length_adjustment(strategy, race_config)
    return total_time


def main():
    data = json.load(sys.stdin)

    race_id = data.get("race_id")
    race_config = data.get("race_config", {})
    strategies = data.get("strategies", {})

    results = []

    for _, strategy in strategies.items():
        driver_id = strategy.get("driver_id")
        if not driver_id:
            continue

        total_time = simulate_driver(strategy, race_config)
        results.append((driver_id, total_time))

    results.sort(key=lambda x: x[1])

    output = {
        "race_id": race_id,
        "finishing_positions": [driver_id for driver_id, _ in results]
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()