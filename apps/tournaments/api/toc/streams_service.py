"""
TOC Streams & Media Service — Sprint 28.

Broadcast stations, stream scheduling, multi-stream dashboard,
VOD library, overlay data API, and viewer stats.
"""

import logging
from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.match import Match

logger = logging.getLogger("toc.streams")


class TOCStreamsService:
    """All read/write operations for the Streams & Media tab."""

    @staticmethod
    def get_streams_dashboard(tournament: Tournament) -> dict:
        """Full streams dashboard data."""
        config = tournament.config or {}
        streams_config = config.get("streams", {})
        stations = streams_config.get("stations", [])
        overlay_key = streams_config.get("overlay_api_key", "")

        # Get all matches with stream URLs
        streamed_matches = Match.objects.filter(
            tournament=tournament,
        ).exclude(stream_url__isnull=True).exclude(stream_url="").values(
            "id", "match_number", "round_number", "state",
            "participant1_name", "participant2_name",
            "participant1_score", "participant2_score",
            "stream_url", "scheduled_time", "started_at",
        )

        live_streams = []
        upcoming_streams = []
        completed_streams = []
        for m in streamed_matches:
            entry = {
                "match_id": m["id"],
                "match_number": m["match_number"],
                "round": m["round_number"],
                "round_number": m["round_number"],
                "p1": m["participant1_name"] or "TBD",
                "p2": m["participant2_name"] or "TBD",
                "participant1_name": m["participant1_name"] or "TBD",
                "participant2_name": m["participant2_name"] or "TBD",
                "p1_score": m["participant1_score"],
                "p2_score": m["participant2_score"],
                "stream_url": m["stream_url"],
                "scheduled_time": m["scheduled_time"].isoformat() if m["scheduled_time"] else None,
                "started_at": m["started_at"].isoformat() if m["started_at"] else None,
                "state": "in_progress" if m["state"] == "live" else m["state"],
            }
            if m["state"] == "live":
                live_streams.append(entry)
            elif m["state"] == "completed":
                completed_streams.append(entry)
            else:
                upcoming_streams.append(entry)

        # VOD library
        vods = streams_config.get("vods", [])

        return {
            "stations": stations,
            "live": live_streams,
            "upcoming": upcoming_streams,
            "completed": completed_streams,
            "vods": vods,
            "overlay_api_key": overlay_key,
            "summary": {
                "total_stations": len(stations),
                "live": len(live_streams),
                "live_count": len(live_streams),
                "upcoming": len(upcoming_streams),
                "upcoming_count": len(upcoming_streams),
                "total_vods": len(vods),
                "vod_count": len(vods),
                "total_streamed": len(list(streamed_matches)),
            },
        }

    @staticmethod
    def add_station(tournament: Tournament, data: dict) -> dict:
        """Add a broadcast station."""
        config = tournament.config or {}
        streams = config.get("streams", {})
        stations = streams.get("stations", [])

        station = {
            "id": f"station-{len(stations) + 1}",
            "name": data.get("name", f"Station {len(stations) + 1}"),
            "platform": data.get("platform", "twitch"),
            "url": data.get("url", ""),
            "caster": data.get("caster", ""),
            "observer": data.get("observer", ""),
            "language": data.get("language", "en"),
            "is_primary": data.get("is_primary", len(stations) == 0),
            "status": "idle",
            "created_at": timezone.now().isoformat(),
        }
        stations.append(station)
        streams["stations"] = stations
        config["streams"] = streams
        tournament.config = config
        tournament.save(update_fields=["config"])
        return station

    @staticmethod
    def update_station(tournament: Tournament, station_id: str, data: dict) -> dict:
        """Update a broadcast station."""
        config = tournament.config or {}
        streams = config.get("streams", {})
        stations = streams.get("stations", [])

        for s in stations:
            if s["id"] == station_id:
                for key in ["name", "platform", "url", "caster", "observer", "language", "is_primary", "status"]:
                    if key in data:
                        s[key] = data[key]
                streams["stations"] = stations
                config["streams"] = streams
                tournament.config = config
                tournament.save(update_fields=["config"])
                return s

        return {"error": "Station not found"}

    @staticmethod
    def delete_station(tournament: Tournament, station_id: str) -> dict:
        """Delete a broadcast station."""
        config = tournament.config or {}
        streams = config.get("streams", {})
        stations = streams.get("stations", [])
        before = len(stations)
        stations = [s for s in stations if s["id"] != station_id]
        streams["stations"] = stations
        config["streams"] = streams
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"deleted": before - len(stations) > 0}

    @staticmethod
    def assign_stream(tournament: Tournament, match_id: int, stream_url: str) -> dict:
        """Assign a stream URL to a match."""
        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            return {"error": "Match not found"}
        match.stream_url = stream_url
        match.save(update_fields=["stream_url"])
        return {"match_id": match_id, "stream_url": stream_url}

    @staticmethod
    def add_vod(tournament: Tournament, data: dict) -> dict:
        """Add a VOD to the library."""
        config = tournament.config or {}
        streams = config.get("streams", {})
        vods = streams.get("vods", [])

        vod = {
            "id": f"vod-{len(vods) + 1}",
            "title": data.get("title", ""),
            "url": data.get("url", ""),
            "platform": data.get("platform", "youtube"),
            "match_id": data.get("match_id"),
            "duration": data.get("duration", ""),
            "thumbnail": data.get("thumbnail", ""),
            "created_at": timezone.now().isoformat(),
        }
        vods.append(vod)
        streams["vods"] = vods
        config["streams"] = streams
        tournament.config = config
        tournament.save(update_fields=["config"])
        return vod

    @staticmethod
    def delete_vod(tournament: Tournament, vod_id: str) -> dict:
        """Delete a VOD from the library."""
        config = tournament.config or {}
        streams = config.get("streams", {})
        vods = streams.get("vods", [])
        vods = [v for v in vods if v["id"] != vod_id]
        streams["vods"] = vods
        config["streams"] = streams
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"deleted": True}

    @staticmethod
    def get_overlay_data(tournament: Tournament, match_id: int = 0) -> dict:
        """Get real-time data for OBS/stream overlays."""
        data = {
            "tournament": {
                "name": tournament.name,
                "game": tournament.game.name if tournament.game else "",
                "format": tournament.format,
                "status": tournament.status,
            },
        }

        if match_id:
            try:
                m = Match.objects.get(id=match_id, tournament=tournament)
                data["match"] = {
                    "id": m.id,
                    "match_number": m.match_number,
                    "round": m.round_number,
                    "state": m.state,
                    "p1_name": m.participant1_name or "TBD",
                    "p2_name": m.participant2_name or "TBD",
                    "p1_score": m.participant1_score,
                    "p2_score": m.participant2_score,
                    "scheduled_time": m.scheduled_time.isoformat() if m.scheduled_time else None,
                    "started_at": m.started_at.isoformat() if m.started_at else None,
                }
            except Match.DoesNotExist:
                data["match"] = None
        else:
            # Get current live match (if any)
            live = Match.objects.filter(tournament=tournament, state="live").first()
            if live:
                data["match"] = {
                    "id": live.id,
                    "match_number": live.match_number,
                    "round": live.round_number,
                    "state": "live",
                    "p1_name": live.participant1_name or "TBD",
                    "p2_name": live.participant2_name or "TBD",
                    "p1_score": live.participant1_score,
                    "p2_score": live.participant2_score,
                }
            else:
                data["match"] = None

        return data

    @staticmethod
    def generate_overlay_key(tournament: Tournament) -> dict:
        """Generate a new overlay API key."""
        import secrets
        key = secrets.token_urlsafe(32)
        config = tournament.config or {}
        streams = config.get("streams", {})
        streams["overlay_api_key"] = key
        config["streams"] = streams
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"overlay_api_key": key}
