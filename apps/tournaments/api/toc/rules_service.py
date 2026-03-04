"""
TOC Rules & Info Service — Sprint 28.

Rich rulebook management, versioned rules, FAQ sections,
player acknowledgement tracking, prize info, and tournament info page.
"""

import logging
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament

logger = logging.getLogger("toc.rules")


class TOCRulesService:
    """All read/write operations for the Rules & Info tab."""

    @staticmethod
    def get_rules_dashboard(tournament: Tournament) -> dict:
        """Full rules & info dashboard."""
        config = tournament.config or {}
        rules_config = config.get("rules_info", {})

        sections = rules_config.get("sections", TOCRulesService._default_sections())
        faq = rules_config.get("faq", [])
        acknowledgements = rules_config.get("acknowledgements", {})
        prize_info = rules_config.get("prize_info", {})
        quick_ref = rules_config.get("quick_reference", {})
        versions = rules_config.get("versions", [])

        # Tournament info
        info = {
            "name": tournament.name,
            "game": tournament.game.name if tournament.game else "",
            "format": tournament.format,
            "mode": getattr(tournament, "mode", "online"),
            "platform": getattr(tournament, "platform", "pc"),
            "max_participants": tournament.max_participants,
            "registration_start": tournament.registration_start.isoformat() if tournament.registration_start else None,
            "registration_end": tournament.registration_end.isoformat() if tournament.registration_end else None,
            "tournament_start": tournament.tournament_start.isoformat() if tournament.tournament_start else None,
            "tournament_end": tournament.tournament_end.isoformat() if tournament.tournament_end else None,
            "prize_pool": float(tournament.prize_pool or 0),
            "prize_currency": tournament.prize_currency or "USD",
            "entry_fee": float(tournament.entry_fee_amount or 0),
            "entry_fee_currency": tournament.entry_fee_currency or "USD",
        }

        ack_total = len(acknowledgements)
        from apps.tournaments.models.registration import Registration
        total_participants = Registration.objects.filter(
            tournament=tournament,
            status__in=["confirmed", "auto_approved"],
        ).count()

        return {
            "sections": sections,
            "faq": faq,
            "prize_info": prize_info,
            "quick_reference": quick_ref,
            "versions": versions,
            "tournament_info": info,
            "summary": {
                "total_sections": len(sections),
                "total_faq": len(faq),
                "acknowledged": ack_total,
                "total_participants": total_participants,
                "ack_pct": round(ack_total / total_participants * 100) if total_participants > 0 else 0,
                "current_version": versions[-1]["version"] if versions else "1.0",
            },
        }

    @staticmethod
    def _default_sections():
        """Default rulebook sections."""
        return [
            {"id": "general", "title": "General Rules", "content": "", "order": 1},
            {"id": "game", "title": "Game-Specific Rules", "content": "", "order": 2},
            {"id": "match", "title": "Match Rules", "content": "", "order": 3},
            {"id": "conduct", "title": "Code of Conduct", "content": "", "order": 4},
            {"id": "prizes", "title": "Prize Rules", "content": "", "order": 5},
        ]

    @staticmethod
    def update_section(tournament: Tournament, section_id: str, data: dict) -> dict:
        """Update a rulebook section."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        sections = rules.get("sections", TOCRulesService._default_sections())

        found = False
        for s in sections:
            if s["id"] == section_id:
                if "title" in data:
                    s["title"] = data["title"]
                if "content" in data:
                    s["content"] = data["content"]
                s["updated_at"] = timezone.now().isoformat()
                found = True
                break

        if not found:
            # Add new section
            sections.append({
                "id": section_id,
                "title": data.get("title", section_id.replace("_", " ").title()),
                "content": data.get("content", ""),
                "order": len(sections) + 1,
                "updated_at": timezone.now().isoformat(),
            })

        rules["sections"] = sections
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"section_id": section_id, "updated": True}

    @staticmethod
    def delete_section(tournament: Tournament, section_id: str) -> dict:
        """Delete a rulebook section."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        sections = rules.get("sections", [])
        sections = [s for s in sections if s["id"] != section_id]
        rules["sections"] = sections
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"deleted": True}

    @staticmethod
    def add_faq(tournament: Tournament, data: dict) -> dict:
        """Add a FAQ entry."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        faq = rules.get("faq", [])

        entry = {
            "id": f"faq-{len(faq) + 1}",
            "question": data.get("question", ""),
            "answer": data.get("answer", ""),
            "order": len(faq) + 1,
            "created_at": timezone.now().isoformat(),
        }
        faq.append(entry)
        rules["faq"] = faq
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return entry

    @staticmethod
    def update_faq(tournament: Tournament, faq_id: str, data: dict) -> dict:
        """Update a FAQ entry."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        faq = rules.get("faq", [])

        for f in faq:
            if f["id"] == faq_id:
                if "question" in data:
                    f["question"] = data["question"]
                if "answer" in data:
                    f["answer"] = data["answer"]
                f["updated_at"] = timezone.now().isoformat()
                rules["faq"] = faq
                config["rules_info"] = rules
                tournament.config = config
                tournament.save(update_fields=["config"])
                return f
        return {"error": "FAQ not found"}

    @staticmethod
    def delete_faq(tournament: Tournament, faq_id: str) -> dict:
        """Delete a FAQ entry."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        faq = rules.get("faq", [])
        faq = [f for f in faq if f["id"] != faq_id]
        rules["faq"] = faq
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"deleted": True}

    @staticmethod
    def publish_version(tournament: Tournament, data: dict) -> dict:
        """Publish a new version of the rules."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        versions = rules.get("versions", [])

        version_num = data.get("version", f"{len(versions) + 1}.0")
        changelog = data.get("changelog", "")

        versions.append({
            "version": version_num,
            "changelog": changelog,
            "published_at": timezone.now().isoformat(),
            "published_by": data.get("published_by", ""),
        })

        rules["versions"] = versions
        # Reset acknowledgements on new version
        rules["acknowledgements"] = {}
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"version": version_num, "published_at": timezone.now().isoformat()}

    @staticmethod
    def update_prize_info(tournament: Tournament, data: dict) -> dict:
        """Update prize distribution info."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        rules["prize_info"] = {
            "distribution": data.get("distribution", []),
            "payment_method": data.get("payment_method", ""),
            "payment_schedule": data.get("payment_schedule", ""),
            "notes": data.get("notes", ""),
            "updated_at": timezone.now().isoformat(),
        }
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return rules["prize_info"]

    @staticmethod
    def update_quick_reference(tournament: Tournament, data: dict) -> dict:
        """Update the quick reference card."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        rules["quick_reference"] = {
            "format": data.get("format", ""),
            "checkin_time": data.get("checkin_time", ""),
            "match_format": data.get("match_format", ""),
            "map_pool": data.get("map_pool", ""),
            "special_rules": data.get("special_rules", ""),
            "contact": data.get("contact", ""),
            "updated_at": timezone.now().isoformat(),
        }
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return rules["quick_reference"]

    @staticmethod
    def acknowledge_rules(tournament: Tournament, user_id: int) -> dict:
        """Record that a user has acknowledged the rules."""
        config = tournament.config or {}
        rules = config.get("rules_info", {})
        acks = rules.get("acknowledgements", {})
        acks[str(user_id)] = timezone.now().isoformat()
        rules["acknowledgements"] = acks
        config["rules_info"] = rules
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"acknowledged": True, "user_id": user_id}
