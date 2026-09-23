# Domain rules

- `User`: account, BCrypt password, nationality, global `is_admin`.
- `Player`: human or bot, five stats, ELO, match history, photo, and relations.
  Bots have no user and do not vote or score in leagues.
- `PlayerRelation`: canonical pair of players, with together/apart counters.
- `Match`, `MatchPlayer`, and `Team`: call-up, assigned sides, votes, winner, and
  pre-set groups. A match can reference a league.

The match flow is create → select players → preserve groups → balance humans →
fill capacity with bots → choose winner. Core logic is in
`services/match_service.py`; the balancing algorithm is `utils/balance_teams.py`.
When a winner is assigned, history/ELO, relations, evaluation permissions, and
eligible league rankings are updated. Closure happens after all votes, an
irreversible result, or 24-hour timeout.

League model:

- `League`: public/private, special, system-managed national league, owner,
  country, divisions, optional group-size cap.
- `LeagueMember`: `member` or `admin` inside a league.
- `LeagueRanking`: `general`, `solo_duo`, and `grupo` for every membership.

Global admins manage any league; owners and league admins manage theirs. Normal
users can create at most three leagues. Uruguay national membership is automatic
for applicable human players and cannot be left. League-match guests may play,
but only members receive points. Ranking APIs and rules live in
`league_service.py`; point updates run in `update_league_ranking_after_match()`.

