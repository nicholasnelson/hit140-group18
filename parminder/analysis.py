import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

DATA = "Dataset_Line_Breaks.csv"
MIN_ATTEMPTS = 5

CONFEDERATIONS = {
    "Austria": "UEFA",
    "England": "UEFA",
    "Germany": "UEFA",
    "Netherlands": "UEFA",
    "Portugal": "UEFA",
    "Scotland": "UEFA",
    "Spain": "UEFA",
    "Sweden": "UEFA",
    "Türkiye": "UEFA",
    "Argentina": "CONMEBOL",
    "Brazil": "CONMEBOL",
    "Colombia": "CONMEBOL",
    "Ecuador": "CONMEBOL",
    "Uruguay": "CONMEBOL",
    "Algeria": "CAF",
    "Cabo Verde": "CAF",
    "Congo DR": "CAF",
    "Côte d'Ivoire": "CAF",
    "Morocco": "CAF",
    "Tunisia": "CAF",
    "Haiti": "CONCACAF",
    "Panama": "CONCACAF",
    "USA": "CONCACAF",
    "Curaçao": "CONCACAF",
    "Uzbekistan": "AFC",
}

EXTRA_GOALKEEPERS = set()

UNIT_COLS = [
    "u4_att_line", "u4_att_mid_line", "u4_mid_line", "u4_def_line",
    "u3_att_line", "u3_mid_line", "u3_def_line",
    "u2_mid_line", "u2_def_line",
]


def load():
    try:
        df = pd.read_csv(DATA)
    except FileNotFoundError:
        sys.exit(f"{DATA} not found. Run 'python main.py' first.")

    if "Raw_Distributions" in df.columns:
        sys.exit(f"{DATA} is in the old unlabelled format. "
                 f"Re-run 'python main.py' to regenerate it.")

    unmapped = sorted(set(df["Team"]) - set(CONFEDERATIONS))
    if unmapped:
        sys.exit(f"Teams missing from CONFEDERATIONS: {unmapped}\n"
                 f"Add them before running the analysis.")

    df["Confederation"] = df["Team"].map(CONFEDERATIONS)
    return df


def drop_goalkeepers(df):
    is_gk = (df["Player_Num"] == 1) | df.apply(
        lambda r: (r["Match"], r["Player_Num"]) in EXTRA_GOALKEEPERS, axis=1
    )

    appearances = df.groupby(["Match", "Team"])
    missing = [k for k, g in appearances if not is_gk[g.index].any()]
    if missing:
        print(f"  Note: {len(missing)} of {appearances.ngroups} team-match "
              f"records have no identified goalkeeper row.")

    print(f"  Removed {is_gk.sum()} goalkeeper rows.")
    return df[~is_gk].copy()


def add_difficulty_features(df):
    """
    Three proportions describing how hard a player's line-break attempts
    were. Each is a share of that player's total attempts.
    """
    df["prop_deep"] = df[UNIT_COLS[:7]].sum(axis=1) / df["Att"]  # 3 or 4 units broken
    df["prop_over"] = df["dir_over"] / df["Att"]
    df["prop_cross"] = df["type_cross"] / df["Att"]
    return df


def main():
    print("Loading data...")
    df = load()
    print(f"  {len(df)} player-match rows, {df['Match'].nunique()} matches.")

    df = drop_goalkeepers(df)

    df = df[df["Att"] >= MIN_ATTEMPTS].copy()
    print(f"  {len(df)} rows remain after requiring Att >= {MIN_ATTEMPTS}.")

    df = add_difficulty_features(df)

    print("\n1. DESCRIPTIVE STATISTICS (raw, unadjusted)")
    target = df[df["Confederation"].isin(["UEFA", "CONMEBOL"])]
    desc = target.groupby("Confederation").agg(
        Players=("Completion_Pct", "size"),
        Attempts=("Att", "sum"),
        Mean_Completion=("Completion_Pct", "mean"),
        SD=("Completion_Pct", "std"),
        Mean_Prop_Over=("prop_over", "mean"),
        Mean_Prop_Cross=("prop_cross", "mean"),
    ).round(2)
    print(desc.to_string())

    print("\n2. EXPECTED COMPLETION MODEL")
    model = smf.wls("Completion_Pct ~ prop_over + prop_cross",
                    data=df, weights=df["Att"]).fit()
    print(model.summary().tables[1])
    print(f"  R-squared: {model.rsquared:.3f}   n = {int(model.nobs)}")

    df["Expected_Pct"] = model.predict(df)
    df["PCOE"] = df["Completion_Pct"] - df["Expected_Pct"]

    print("\n3. TEAM-LEVEL PASS COMPLETION OVER EXPECTED (PCOE)")
    target = df[df["Confederation"].isin(["UEFA", "CONMEBOL"])]
    teams = target.groupby(["Team", "Confederation"]).agg(
        Attempts=("Att", "sum"),
        Actual=("Completion_Pct", "mean"),
        Expected=("Expected_Pct", "mean"),
        PCOE=("PCOE", "mean"),
    ).round(2).reset_index().sort_values("PCOE", ascending=False)
    print(teams.to_string(index=False))

    print("\n4. COMPARING THE TWO CONFEDERATIONS")
    uefa = teams.loc[teams["Confederation"] == "UEFA", "PCOE"]
    conmebol = teams.loc[teams["Confederation"] == "CONMEBOL", "PCOE"]

    for name, s in [("UEFA", uefa), ("CONMEBOL", conmebol)]:
        print(f"  {name:9s} n = {len(s)}  mean = {s.mean():+.2f}  "
              f"SD = {s.std():.2f}")

    t_stat, p_val = stats.ttest_ind(uefa, conmebol, equal_var=False)
    diff = uefa.mean() - conmebol.mean()
    print(f"\n  Welch's t-test:  t = {t_stat:.3f},  p = {p_val:.4f}")
    print(f"  Difference in means (UEFA - CONMEBOL): {diff:+.2f} percentage points")

    if p_val < 0.05:
        print("  Reject the null: the confederations differ in adjusted "
              "line-break completion.")
    else:
        print("  Fail to reject the null: no evidence of a difference in "
              "adjusted line-break completion.")

    plot(teams)


def plot(teams):
    """
    Dot plot rather than a violin plot: with 9 and 5 teams there are far too
    few points for a density curve to mean anything, and the earlier violin
    implied a smooth distribution that the data does not support.
    """
    sns.set_theme(style="whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))

    colours = {"UEFA": "#0033a0", "CONMEBOL": "#009c3b"}
    span = teams["PCOE"].max() - teams["PCOE"].min()
    min_gap = span * 0.045 

    for i, conf in enumerate(["UEFA", "CONMEBOL"]):
        group = teams[teams["Confederation"] == conf].sort_values("PCOE")
        ax.scatter([i] * len(group), group["PCOE"], s=110,
                   color=colours[conf], zorder=3)

        label_y = []
        for y in group["PCOE"]:
            if label_y and y - label_y[-1] < min_gap:
                y = label_y[-1] + min_gap
            label_y.append(y)

        for (_, r), ly in zip(group.iterrows(), label_y):
            ax.annotate(r["Team"], xy=(i, r["PCOE"]), xytext=(i - 0.07, ly),
                        ha="right", va="center", fontsize=8, color="#444",
                        arrowprops=dict(arrowstyle="-", color="#bbb",
                                        linewidth=0.7, shrinkA=0, shrinkB=4))

        m = group["PCOE"].mean()
        ax.hlines(m, i - 0.02, i + 0.18, color="black", linewidth=2, zorder=4)
        ax.text(i + 0.2, m, f"mean {m:+.2f}", va="center", fontsize=9)

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["UEFA", "CONMEBOL"])
    ax.axhline(0, color="red", linestyle="--", linewidth=1)
    ax.set_title("Pass completion over expected on line-breaking passes\n"
                 "Team means, 2026 World Cup match sample", fontweight="bold")
    ax.set_ylabel("PCOE (actual % - expected %)")
    ax.set_xlabel("")
    ax.set_xlim(-0.6, 1.6)

    plt.tight_layout()
    plt.savefig("UEFA_vs_CONMEBOL_PCOE.png", dpi=200)
    print("\nSaved UEFA_vs_CONMEBOL_PCOE.png")


if __name__ == "__main__":
    main()
