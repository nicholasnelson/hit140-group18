import pandas as pd, numpy as np

# ---- 1. load ----
tmk = pd.read_csv('./data/qualified_teams_transfermarkt.csv')
elo = pd.read_csv('./data/pre_world_cup_rating.csv')
mt  = pd.read_csv('./data/external_template.csv')

# ---- 2. unify team names ----
ALIAS = {
    'bosnia-herzegovina': 'bosnia and herzegovina',
    'bosnia & herzegovina': 'bosnia and herzegovina',
    'democratic republic of the congo': 'dr congo',
    'congo dr': 'dr congo',
    'turkiye': 'turkey',
    'türkiye': 'turkey',
    'usa': 'united states',
    'korea republic': 'south korea',
    'cabo verde': 'cape verde',
    'ir iran': 'iran',
    'czech republic': 'czechia',
    "côte d'ivoire": 'ivory coast',
}

def norm(s):
    s = str(s).strip().lower()
    return ALIAS.get(s, s)

for d, col in [(tmk, 'Team'), (elo, 'Team'), (mt, 'team_name')]:
    d['key'] = d[col].map(norm)

# ---- 3. clean Transfermarkt columns ----
def parse_value(v):                       # '€1.56bn' -> 1560.0, '€946.00m' -> 946.0 (in € million)
    v = str(v).replace('€', '').replace(',', '').strip().lower()
    if v.endswith('bn'): return float(v[:-2]) * 1000
    if v.endswith('m'):  return float(v[:-1])
    if v.endswith('k'):  return float(v[:-1]) / 1000
    return np.nan

tmk['squad_value_meur']   = tmk['Market_Value'].map(parse_value)
tmk['avg_player_value_meur'] = tmk['Avg_Market_Value'].map(parse_value)
tmk['foreigners_pct']     = tmk['Foreigners_Pct'].str.replace('%', '').str.strip().astype(float)
tmk = tmk.rename(columns={'Avg_Age': 'squad_avg_age',
                          'WC_Participations': 'wc_participations',
                          'Squad': 'squad_size'})
tmk = tmk[['key', 'squad_size', 'squad_avg_age', 'wc_participations',
           'foreigners_pct', 'squad_value_meur', 'avg_player_value_meur']]

# ---- 4. clean rating columns (only pre-tournament rating + rank) ----
elo = elo.rename(columns={'Rating': 'elo', 'Rank_Global': 'elo_rank'})
elo = elo[['key', 'elo', 'elo_rank']]

teams = mt[['team_id', 'team_name', 'key']].drop_duplicates()
ext = (teams.merge(elo, on='key', how='left')
            .merge(tmk, on='key', how='left')
            .drop(columns='key'))

print('rows:', len(ext), '(expected 48)')
print('missing values per column:\n', ext.isna().sum())
print('teams with any missing data:\n', ext[ext.isna().any(axis=1)][['team_id', 'team_name']])
print(ext.describe().T[['min', 'max']])

ext.to_csv('./data/external.csv', index=False)
ext.head()