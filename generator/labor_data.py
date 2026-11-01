
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
import random

from generator.config import (
    START_DATE,
    DAYS_TO_GENERATE,
    OUTPUT_DIR,
    SEED,
)

SKILLS = [
    "CUTTING",
    "MACHINING",
    "ASSEMBLY",
    "PACKAGING",
]


def generate_labor_calendar():
    random.seed(SEED)

    records = []
    start = date.fromisoformat(START_DATE)

    for day in range(DAYS_TO_GENERATE):
        current_date = start + timedelta(days=day)

        for skill in SKILLS:
            for shift, start_time, end_time in [
                ("SHIFT-1", "06:00", "14:00"),
                ("SHIFT-2", "14:00", "22:00"),
            ]:
                workers = random.randint(3, 8)
                working = current_date.weekday() != 6

                records.append({
                    "labor_calendar_id": (
                        f"LAB-{current_date.strftime('%Y%m%d')}-"
                        f"{skill}-{shift}"
                    ),
                    "work_date": current_date.isoformat(),
                    "skill": skill,
                    "shift": shift,
                    "start_time": start_time,
                    "end_time": end_time,
                    "available_workers": workers if working else 0,
                    "is_working": working,
                })

                # This block must be outside all three loops.
                df = pd.DataFrame(records)

                output = Path(OUTPUT_DIR)
                output.mkdir(parents=True, exist_ok=True)

                output_path = output / "labor_calendars.csv"
                df.to_csv(output_path, index=False)

                print("Labor calendar generated!")
                print("Random seed:", SEED)
                print("Total records:", len(df))
                print("Output:", output_path)


if __name__ == "__main__":
    generate_labor_calendar()
