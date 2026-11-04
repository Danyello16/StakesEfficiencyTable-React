# Notes

## Data problems

- Some site names contained unquoted commas in `stakes_delivery.csv` (2,562 rows). I repaired those rows during import and matched promotions using `site_id`.
- I treated 39 identical records as duplicates to avoid double-counting. I kept 12 negative entries, which appear to be corrections to daily stakes.
- P05 has invalid dates. P07 has only one of seven required baseline days, so calculating its uplift would be misleading. Both remain in the output with blank uplift; P07's `before` number is a partial total.
- The analysis also checks for missing daily records and overlapping promotions.

## With more time

I'd add daily trend charts, better weekday-matched comparisons, and more tests for missing data or overlapping promotions. That would help KAMs distinguish normal changes in stakes from a possible promotion effect.

## AI tools used

ChatGPT generated much of the initial Python/React code and tests. I used OpenAI Codex to audit the calculations, fix the game search, add a CSV-output test, and run technical checks. AI did a substantial part of the implementation.
