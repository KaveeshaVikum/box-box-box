import json
from pathlib import Path

HIST_DIR = Path("data/historical_races")


def load_races(limit_files=2):
    races = []
    files = sorted(HIST_DIR.glob("*.json"))[:limit_files]
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                races.extend(data)
    return races


def summarize_driver(strategy):
    start = strategy.get("starting_tire")
    pits = strategy.get("pit_stops", [])
    first_pit = pits[0]["lap"] if pits else None
    last_tire = pits[-1]["to_tire"] if pits else start
    return start, first_pit, len(pits), last_tire


def main():
    races = load_races(limit_files=2)
    print(f"Loaded races: {len(races)}")

    for race in races[:5]:
        race_id = race.get("race_id")
        config = race.get("race_config", {})
        finishing = race.get("finishing_positions", [])
        strategies = race.get("strategies", {})

        print("\n" + "=" * 60)
        print("Race:", race_id)
        print("Track:", config.get("track"))
        print("Laps:", config.get("total_laps"))
        print("Base lap:", config.get("base_lap_time"))
        print("Pit lane:", config.get("pit_lane_time"))
        print("Temp:", config.get("track_temp"))
        print("Top 10:")

        for pos, driver_id in enumerate(finishing[:10], start=1):
            matched = None
            for _, s in strategies.items():
                if s.get("driver_id") == driver_id:
                    matched = s
                    break

            if matched:
                start, first_pit, pit_count, last_tire = summarize_driver(matched)
                print(
                    f"{pos:2d}. {driver_id} | start={start} | first_pit={first_pit} | pits={pit_count} | last_tire={last_tire}"
                )
            else:
                print(f"{pos:2d}. {driver_id} | strategy not found")


if __name__ == "__main__":
    main()