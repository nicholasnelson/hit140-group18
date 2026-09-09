# FIFA World Cup 2026 venue-scoring task

This folder contains one of the four analytic tasks required for Objective 1.

## Research question

Did group-stage matches played in Mexico have a different mean number of total goals than group-stage matches played in Canada or the United States?

This task looks at match location. It does not analyse goal timing, host-team points, knockout competitiveness, or scorer concentration.

## What the workflow does

1. Validates the 104-match source snapshot.
2. Keeps the 72 group-stage matches so tournament stage is held constant.
3. Maps Guadalajara, Mexico City, and Monterrey to Mexico and all other host cities to Canada/United States.
4. Calculates total full-time goals for each match.
5. Produces descriptive statistics and a 95% Welch confidence interval.
6. Runs a two-sided Welch two-sample t-test.
7. Checks distribution shape and variance imbalance.
8. Runs a fixed-seed randomisation test as a sensitivity analysis.
9. Writes the cleaned CSV, JSON results, and an SVG figure.

## Run locally

```bash
python3 run_all.py
python3 -m unittest discover -s tests -v
```

The analysis uses only the Python standard library. The output files are included for review.

## Files to adapt before submission

- The member should run the workflow, verify the interpretation, and explain the work in their own presentation.
- Record only genuine collaboration activity and commits. Do not backdate or fabricate evidence.
