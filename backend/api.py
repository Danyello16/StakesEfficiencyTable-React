"""Read-only API for the React KAM dashboard."""
import csv
import io

from fastapi import FastAPI
from fastapi.responses import Response

from backend.analysis import build_report

app = FastAPI(title="Greentube Promo Analysis", version="1.0")
report = build_report()


@app.get("/api/report")
def get_report():
    return report


@app.get("/api/results.csv")
def download_results():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["promo_id", "before", "during", "uplift"])
    for row in report["promos"]:
        writer.writerow([
            row["promo_id"],
            f"{row['before']:.2f}" if row["before"] is not None else "",
            f"{row['during']:.2f}" if row["during"] is not None else "",
            f"{row['uplift']:.1f}" if row["uplift"] is not None else "",
        ])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="results.csv"'},
    )
