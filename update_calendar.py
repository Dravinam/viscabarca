import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

API_TOKEN = os.environ["FOOTBALL_DATA_TOKEN"]
TEAM_ID = 81
OUTPUT_FILE = "matches.ics"


def escape_ics(text):
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def fetch_matches():
    now = datetime.now(timezone.utc)

    params = urllib.parse.urlencode({
        "dateFrom": now.date().isoformat(),
        "dateTo": (now + timedelta(days=365)).date().isoformat(),
        "limit": 500,
    })

    url = (
        f"https://api.football-data.org/v4/teams/"
        f"{TEAM_ID}/matches?{params}"
    )

    request = urllib.request.Request(
        url,
        headers={"X-Auth-Token": API_TOKEN}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("matches", [])


def format_utc(date_string):
    match_time = datetime.fromisoformat(
        date_string.replace("Z", "+00:00")
    )
    return match_time.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def create_event(match):
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]

    summary = f"{home} vs {away}"
    start = datetime.fromisoformat(
        match["utcDate"].replace("Z", "+00:00")
    ).astimezone(timezone.utc)

    end = start + timedelta(hours=2)

    competition = match.get("competition", {}).get("name", "Football")
    venue = match.get("venue") or "Venue to be confirmed"
    match_id = match["id"]

    description = (
        f"Competition: {competition}\\n"
        f"Venue: {venue}\\n"
        "Fixture information provided by football-data.org.\\n"
        "Match duration is estimated at 2 hours."
    )

    lines = [
        "BEGIN:VEVENT",
        f"UID:barcelona-match-{match_id}@barcelona-match-calendar",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}",
        f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}",
        f"SUMMARY:{escape_ics(summary)}",
        f"DESCRIPTION:{escape_ics(description)}",
        f"LOCATION:{escape_ics(venue)}",
        "BEGIN:VALARM",
        "TRIGGER:-PT30M",
        "ACTION:DISPLAY",
        "DESCRIPTION:FC Barcelona match starts in 30 minutes",
        "END:VALARM",
        "END:VEVENT",
    ]

    return lines


def main():
    matches = fetch_matches()
    now = datetime.now(timezone.utc)

    events = []

    for match in matches:
        if match.get("status") not in ("SCHEDULED", "TIMED"):
            continue

        start = datetime.fromisoformat(
            match["utcDate"].replace("Z", "+00:00")
        )

        if start <= now:
            continue

        home_id = match.get("homeTeam", {}).get("id")
        away_id = match.get("awayTeam", {}).get("id")

        if TEAM_ID not in (home_id, away_id):
            continue

        events.extend(create_event(match))

    calendar = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Barcelona Match Calendar//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:FC Barcelona Matches",
        *events,
        "END:VCALENDAR",
        "",
    ]

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="\r\n") as file:
        file.write("\r\n".join(calendar))

    print(f"Calendar generated: {OUTPUT_FILE}")
    print(f"Upcoming matches included: {len(events) // 16}")


if __name__ == "__main__":
    main()
