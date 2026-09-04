import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

CONFEDERATION_MAP = {
    "Scotland": "UEFA", "Germany": "UEFA", "Sweden": "UEFA", "Spain": "UEFA",
    "Portugal": "UEFA", "Austria": "UEFA", "Netherlands": "UEFA", "Turkey": "UEFA", "England": "UEFA",
    "Brazil": "CONMEBOL", "Ecuador": "CONMEBOL", "Argentina": "CONMEBOL", 
    "Colombia": "CONMEBOL", "Uruguay": "CONMEBOL",
    "Haiti": "CONCACAF", "Morocco": "CAF", "Ivory Coast": "CAF", "Curaçao": "CONCACAF",
    "Tunisia": "CAF", "Cape Verde": "CAF", "Algeria": "CAF", "DR Congo": "CAF",
    "Uzbekistan": "AFC", "USA": "CONCACAF", "Panama": "CONCACAF"
}

def load_and_engineer_features(filepath):
    """Loads the Line Breaks dataset and engineers tactical difficulty features."""
    df = pd.read_csv(filepath)
    
    df = df[df['Att'] >= 5].copy()
    
    col_names = [
        'u4_al', 'u4_aml', 'u4_ml', 'u4_dl', 
        'u3_al', 'u3_ml', 'u3_dl',          
        'u2_ml', 'u2_dl',                   
        'dir_through', 'dir_around', 'dir_over',
        'type_pass', 'type_cross', 'type_prog'  
    ]
    
    df[col_names] = df['Raw_Distributions'].str.split(expand=True).astype(float)
    
    df['prop_deep_bypasses'] = (df[['u4_al', 'u4_aml', 'u4_ml', 'u4_dl', 'u3_al', 'u3_ml', 'u3_dl']].sum(axis=1)) / df['Att']
    
    df['prop_over'] = df['dir_over'] / df['Att']
    
    df['prop_cross'] = df['type_cross'] / df['Att']
    
    df['Confederation'] = df['Team'].map(CONFEDERATION_MAP).fillna("OTHER")
    
    return df

def main():
    print("Loading data and engineering tactical features...")
    df = load_and_engineer_features("Dataset_Line_Breaks.csv")
    
    print("\n--- 1. BUILDING EXPECTED LINE BREAK (xLB) MODEL ---")
    formula = "Completion_Pct ~ prop_deep_bypasses + prop_over + prop_cross"
    model = smf.wls(formula, data=df, weights=df['Att']).fit()
    print(model.summary().tables[1])
    
    df['xLB'] = model.predict(df)
    df['PCOE'] = df['Completion_Pct'] - df['xLB']
    
    print("\n--- 2. AGGREGATING UEFA VS CONMEBOL ---")
    target_df = df[df['Confederation'].isin(['UEFA', 'CONMEBOL'])]
    
    team_agg = target_df.groupby(['Team', 'Confederation']).agg(
        Total_Attempts=('Att', 'sum'),
        Avg_Raw_Completion=('Completion_Pct', 'mean'),
        Avg_Expected_Completion=('xLB', 'mean'),
        Team_PCOE=('PCOE', 'mean')
    ).reset_index().sort_values(by='Team_PCOE', ascending=False)
    
    confed_agg = team_agg.groupby('Confederation').agg(
        Teams=('Team', 'count'),
        Mean_PCOE=('Team_PCOE', 'mean')
    ).reset_index()
    
    print(confed_agg.to_string(index=False))
    
    print("\n--- 3. STATISTICAL SIGNIFICANCE TESTING ---")
    uefa_pcoe = team_agg[team_agg['Confederation'] == 'UEFA']['Team_PCOE']
    conmebol_pcoe = team_agg[team_agg['Confederation'] == 'CONMEBOL']['Team_PCOE']
    
    t_stat, p_val = stats.ttest_ind(uefa_pcoe, conmebol_pcoe, equal_var=False)
    print(f"Welch's t-test statistic: {t_stat:.3f}")
    print(f"P-value: {p_val:.4f}")
    
    if p_val < 0.05:
        print("Conclusion: There IS a statistically significant difference between UEFA and CONMEBOL passing precision after adjusting for pass difficulty.")
    else:
        print("Conclusion: There is NO statistically significant difference between UEFA and CONMEBOL. Any variations are likely due to variance/sample size.")

    sns.set_theme(style="whitegrid")
    plt.figure(figsize=(10, 6))
    
    sns.violinplot(x="Confederation", y="Team_PCOE", data=team_agg, inner=None, color=".8")
    sns.swarmplot(x="Confederation", y="Team_PCOE", data=team_agg, size=8, 
                  palette={"UEFA": "#0033a0", "CONMEBOL": "#009c3b"}, hue="Confederation", legend=False)
    
    plt.title("Pass Completion Over Expected (PCOE)\nUEFA vs CONMEBOL (Line-Breaking Passes)", fontsize=14, fontweight='bold')
    plt.ylabel("PCOE (Actual % - Expected %)", fontsize=12)
    plt.xlabel("")
    plt.axhline(0, color='red', linestyle='--', label='Average World Cup Baseline')
    plt.legend()
    plt.tight_layout()
    plt.savefig("UEFA_vs_CONMEBOL_PCOE.png", dpi=300)
    print("\n✅ Visualization saved as 'UEFA_vs_CONMEBOL_PCOE.png'")

if __name__ == "__main__":
    main()