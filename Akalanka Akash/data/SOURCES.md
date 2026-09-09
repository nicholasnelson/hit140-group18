# Data provenance

## Match results

- Dataset: OpenFootball World Cup 2026 JSON
- Repository: https://github.com/openfootball/worldcup.json
- Raw file: https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json
- Local snapshot retrieval date: 7 September 2026
- Expected records: 104 matches
- Local SHA-256: `0ae2c18109b5aa86bc11928b43586ca430c234804d5bbf808d2c3bf2051ecfca`

OpenFootball describes the dataset as public-domain, community-maintained data. It is a reproducible secondary source rather than an official FIFA record.

## Host-city classification

FIFA lists Mexico's three host cities as Guadalajara, Mexico City, and Monterrey:

- https://www.fifa.com/en/articles/world-cup-2026-host-country-mexico-guide
- https://gpcustomersupportfwc2026.tickets.fifa.com/hc/en-gb/articles/28783291386653-1-When-and-where-is-the-FIFA-World-Cup-2026-being-held

The analysis maps the source labels `Guadalajara (Zapopan)`, `Mexico City`, and `Monterrey (Guadalupe)` to Mexico. The remaining source venues are in Canada or the United States.

## Availability on the assignment's listed websites

The variables used in this task are also available from the websites listed in the project brief:

- FIFA publishes the complete tournament schedule and results with group, teams, score, and host venue: https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums
- FBref's Scores & Fixtures table provides round, date, teams, score, and stadium for the tournament: https://fbref.com/en/comps/1/2026/schedule/2026-World-Cup-Scores-and-Fixtures
- The Stats Don't Lie World Cup page provides group-stage fixtures, results, and match statistics: https://www.thestatsdontlie.com/football/world-cup-2026/

Representative checks against FBref confirmed the same teams, scores, and host locations for Mexico versus South Africa, Korea Republic versus Czechia, Canada versus Qatar, Ghana versus Panama, and Uzbekistan versus Colombia. FIFA's results page also shows the opening Mexico versus South Africa and Korea Republic versus Czechia records with the same scores and Mexican host cities. The sources use different venue names. The local snapshot uses host-city labels, while FBref uses stadium names. This does not change the country classification.

## Audit note

The local snapshot is community-maintained, so the supplied websites should remain the verification sources for reported scores and venues:

- https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums
