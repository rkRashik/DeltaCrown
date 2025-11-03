# **Game Requirements Blueprint for New Tournament Engine**

This document outlines the specific technical and logical requirements for each game in the DeltaCrown system. This data will be used to define the interface for our new "Pluggable Game Module" architecture.

### **Game Requirements Table**

| Game | Primary Type | Platform(s) | Standard Player ID (for Registration) | Standard Team | Key Tournament Settings & Result Logic |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **Valorant** | Team vs. Team | PC | **Riot ID** (e.g., `PlayerName#TAG`) | **5v5** (Rosters 5-7) | **Result:** Map Score (e.g., 13-9). **Settings:** Map Veto (Ban/Pick) system. |
| **Counter-Strike** | Team vs. Team | PC | **Steam ID** (e.g., `steamID64`) | **5v5** (Rosters 5-7) | **Result:** Map Score (e.g., 13-9). **Settings:** Map Veto (Ban/Pick) system. |
| **Dota 2** | Team vs. Team | PC | **Steam ID** (e.g., `steamID64`) | **5v5** (Rosters 5-7) | **Result:** Best of X (e.g., 2-1). **Settings:** Character "Draft/Ban" phase. |
| **eFootball** | 1v1 (Solo) | Cross-Platform (PC, Console, Mobile) | **Konami ID** (Username) | **1v1** (Can also be 2v2) | **Result:** Game Score (e.g., 2-1). **Settings:** Platform selection, cross-play toggle. |
| **EA Sports FC 26** | 1v1 (Solo) | PC, Console, Mobile | **EA ID** (Username, PSN, or Xbox) | **1v1** | **Result:** Game Score (e.g., 3-0). **Settings:** Platform selection. |
| **Mobile Legends: Bang Bang** | Team vs. Team | Mobile | **User ID \+ Zone ID** (e.g., `123456 (7890)`) | **5v5** (Rosters 5-6) | **Result:** Best of X (e.g., 2-1). **Settings:** Character "Draft/Ban" phase. |
| **Call of Duty: Mobile** | Team vs. Team | Mobile | **In-Game Name (IGN) / UID** | **5v5** (Rosters 5-6) | **Result:** Best of 5 (across *different modes* like Hardpoint, S\&D). **Settings:** Item/Scorestreak/Perk bans. |
| **Free Fire** | Battle Royale | Mobile | **In-Game Name (IGN) / UID** | **4-Player Squads** | **Result:** **Point-based.** Teams get points for Kills \+ Final Placement (e.g., 1st=12pts, 2nd=9pts...). |
| **PUBG** (Mobile) | Battle Royale | Mobile | **In-Game Name (IGN) / UID** | **4-Player Squads** | **Result:** **Point-based.** Teams get points for Kills \+ Final Placement (similar to Free Fire). |

