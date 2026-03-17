#!/usr/bin/env python3
"""
StatsBomb Data Explorer — Flask Web Application
"""

import json
import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory, abort

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
COMPETITIONS_FILE = DATA_DIR / "competitions.json"
MATCHES_DIR = DATA_DIR / "matches"
EVENTS_DIR = DATA_DIR / "events"


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.route("/api/competitions")
def api_competitions():
    raw = _load_json(COMPETITIONS_FILE)

    grouped = {}
    for entry in raw:
        cid = entry["competition_id"]
        if cid not in grouped:
            grouped[cid] = {
                "competition_id": cid,
                "competition_name": entry["competition_name"],
                "country_name": entry["country_name"],
                "competition_gender": entry.get("competition_gender", "male"),
                "competition_international": entry.get("competition_international", False),
                "seasons": [],
            }
        grouped[cid]["seasons"].append({
            "season_id": entry["season_id"],
            "season_name": entry["season_name"],
            "match_available": entry.get("match_available"),
        })

    for comp in grouped.values():
        comp["seasons"].sort(key=lambda s: s["season_name"], reverse=True)

    competitions = sorted(grouped.values(), key=lambda c: c["competition_name"])
    return jsonify(competitions)


@app.route("/api/matches/<int:competition_id>/<int:season_id>")
def api_matches(competition_id, season_id):
    match_file = MATCHES_DIR / str(competition_id) / f"{season_id}.json"
    if not match_file.exists():
        return jsonify([])

    raw = _load_json(match_file)

    matches = []
    for m in raw:
        matches.append({
            "match_id": m["match_id"],
            "match_date": m.get("match_date"),
            "kick_off": m.get("kick_off"),
            "home_team": m["home_team"]["home_team_name"],
            "away_team": m["away_team"]["away_team_name"],
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
            "stadium": m.get("stadium", {}).get("name") if m.get("stadium") else None,
            "referee": m.get("referee", {}).get("name") if m.get("referee") else None,
            "home_managers": [mg.get("name") for mg in m["home_team"].get("managers", [])],
            "away_managers": [mg.get("name") for mg in m["away_team"].get("managers", [])],
        })

    matches.sort(key=lambda x: x["match_date"] or "", reverse=True)
    return jsonify(matches)


@app.route("/api/events/<int:match_id>")
def api_events(match_id):
    event_file = EVENTS_DIR / f"{match_id}.json"
    if not event_file.exists():
        abort(404)

    raw = _load_json(event_file)

    events = []
    for e in raw:
        event_type = e.get("type", {}).get("name", "Unknown")
        player = e.get("player", {})
        team = e.get("team", {})

        record = {
            "id": e.get("id"),
            "index": e.get("index"),
            "period": e.get("period"),
            "minute": e.get("minute"),
            "second": e.get("second"),
            "timestamp": e.get("timestamp"),
            "type": event_type,
            "team": team.get("name"),
            "player": player.get("name"),
            "play_pattern": e.get("play_pattern", {}).get("name"),
        }

        if event_type == "Shot" and "shot" in e:
            shot = e["shot"]
            record["shot_outcome"] = shot.get("outcome", {}).get("name")
            record["shot_xg"] = round(shot.get("statsbomb_xg", 0), 4)
            record["shot_technique"] = shot.get("technique", {}).get("name")
            record["shot_body_part"] = shot.get("body_part", {}).get("name")
            record["shot_type"] = shot.get("type", {}).get("name")

        if event_type == "Pass" and "pass" in e:
            p = e["pass"]
            record["pass_outcome"] = p.get("outcome", {}).get("name", "Complete")
            record["pass_length"] = round(p.get("length", 0), 1)
            record["pass_height"] = p.get("height", {}).get("name")
            record["pass_assist"] = p.get("goal_assist", False) or p.get("shot_assist", False)

        if event_type == "Carry" and "carry" in e:
            record["carry_end_location"] = e["carry"].get("end_location")

        if event_type == "Dribble" and "dribble" in e:
            record["dribble_outcome"] = e["dribble"].get("outcome", {}).get("name")

        events.append(record)

    return jsonify(events)


@app.route("/api/stats/<int:match_id>")
def api_stats(match_id):
    event_file = EVENTS_DIR / f"{match_id}.json"
    if not event_file.exists():
        abort(404)

    raw = _load_json(event_file)

    teams = list({e.get("team", {}).get("name") for e in raw if e.get("team")})
    stats = {t: {
        "shots": 0, "shots_on_target": 0, "goals": 0, "xg": 0.0,
        "passes": 0, "passes_complete": 0, "dribbles": 0, "dribbles_complete": 0,
        "fouls": 0, "corners": 0, "cards": 0,
    } for t in teams}

    for e in raw:
        team = e.get("team", {}).get("name")
        if not team or team not in stats:
            continue
        etype = e.get("type", {}).get("name")

        if etype == "Shot":
            stats[team]["shots"] += 1
            shot = e.get("shot", {})
            outcome = shot.get("outcome", {}).get("name", "")
            stats[team]["xg"] = round(stats[team]["xg"] + shot.get("statsbomb_xg", 0), 3)
            if outcome in ("Saved", "Goal", "Saved To Post", "Post"):
                stats[team]["shots_on_target"] += 1
            if outcome == "Goal":
                stats[team]["goals"] += 1

        elif etype == "Pass":
            stats[team]["passes"] += 1
            pass_data = e.get("pass", {})
            if "outcome" not in pass_data:   # no outcome key = complete
                stats[team]["passes_complete"] += 1

        elif etype == "Dribble":
            stats[team]["dribbles"] += 1
            if e.get("dribble", {}).get("outcome", {}).get("name") == "Complete":
                stats[team]["dribbles_complete"] += 1

        elif etype == "Foul Committed":
            stats[team]["fouls"] += 1

        elif etype in ("Bad Behaviour", "Foul Committed"):
            card = e.get("bad_behaviour", e.get("foul_committed", {})).get("card", {}).get("name", "")
            if "Yellow" in card or "Red" in card:
                stats[team]["cards"] += 1

    return jsonify(stats)


@app.route("/")
def index():
    # Serve directly to avoid Jinja2 parsing JSX {{ }} syntax
    return send_from_directory(os.path.join(app.root_path, "templates"), "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
