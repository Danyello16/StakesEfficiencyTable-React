# Promotion Stakes Dashboard

A small Python and React app for Key Account Managers to compare casino game stakes before and during promotions. The supplied data is fictional.

The dashboard lets you search promotions, filter by casino or measurement status, sort by uplift, view before/during amounts, and export the results as CSV. Promotions that cannot be compared fairly are marked as unavailable, with an explanation.

## Run locally

You need **Python 3.10+**, **Node.js 20+**, and npm. Open a terminal in the project root.

**Backend — Windows (Command Prompt or PowerShell):**

```bat
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --reload
```

On macOS/Linux, use `python3 -m venv .venv`, then `.venv/bin/python` in place of `.\.venv\Scripts\python.exe` in the other two commands.

**Frontend — second terminal:**

```bat
cd frontend
npm ci
npm run dev
```

Open **http://localhost:5173**. Leave both terminals running. If PowerShell blocks `npm`, use `npm.cmd ci` and `npm.cmd run dev` instead.

## Results and tests

`results.csv` is included. To regenerate it, run this from the project root (Windows):

```bat
.\.venv\Scripts\python.exe -m backend.analysis
```

To run the Python tests:

```bat
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The CSV has one row per promotion: `promo_id,before,during,uplift`. Amounts are in EUR; uplift is a percentage with one decimal (for example, `12.3`). Blank uplift means the comparison is not reliable. P05 has invalid dates; P07 has an incomplete baseline, so its `before` amount is only the observed partial total.

Uplift describes a change in stakes; it does not prove the promotion caused it.
