
### **Technical Specification: Team App Role & Permission System Overhaul**

#### **1. Objective**

To significantly enhance and professionalize our Team App by overhauling the current role and permission system. The goal is to move from our simplistic, "Captain-led" model to a more flexible and detailed hierarchical system that accurately reflects how modern esports organizations are structured.

This update will provide greater clarity, flexibility, and a more premium feel for our users.

#### **2. Current System Limitations**

Currently, our system uses roles like `Player`, `Substitute`, `Coach`, and `Manager`, with the team creator being automatically designated as the `Captain`. This model has several key limitations:

  * **Overloaded "Captain" Role:** The "Captain" role merges the administrative/logistical duties of a manager with the in-game tactical duties of a leader. In reality, these are often different people.
  * **Inflexibility:** A team's best in-game leader (the true captain) may not be the best person to handle administrative tasks like registering for tournaments. Our current system forces this responsibility onto them.
  * **Outdated Terminology:** The "Captain" as the sole administrative head feels dated compared to the "Manager" and "Owner" structure seen on professional platforms.

#### **3. The Proposed Professional Role Hierarchy**

We will replace the current system with a new, permission-based hierarchy. This structure distinguishes between administrative authority and in-game leadership.

| Role/Title | Assignment Logic | Key Permissions & Responsibilities | Purpose |
| :--- | :--- | :--- | :--- |
| **Team Owner** | **(New)** The user who creates the team. One per team. | **Root Admin:** <br> - Full control over team profile (name, logo, etc.).<br> - Can assign/unassign **all** other roles.<br> - Can transfer ownership to another member.<br> - **Can delete the team.** | The ultimate authority and founder of the team. |
| **Manager** | **(New)** Appointed by the Team Owner. Multiple possible. | **Administrator:** <br> - Manages roster (invites/kicks members).<br> - Registers the team for tournaments.<br> - Edits team profile.<br> - Main point of contact for tournament staff. <br> *Cannot delete the team or transfer ownership.* | The logistical and administrative head of the team. |
| **Coach** | **(Existing)** Appointed by Owner or Manager. | **Non-Administrative:**<br> - Can view roster and team info.<br> - Access to strategic planning tools (if any).<br> *Cannot edit the roster or team profile.* | The strategic and performance guide for the team. |
| **Captain** | **(Revised Title)** A special title/badge assigned to a `Player` or `Substitute` by an Owner or Manager. | **In-Game Leadership (Minimal Admin Power):**<br> - Publicly identifies the In-Game Leader (IGL).<br> - May have minor permissions like "Ready Up" in a match lobby. | Signifies the on-field, tactical leader. |
| **Player** | **(Existing)** A core member of the active roster. | **Member:**<br> - Can view team info and upcoming matches.<br> - Can leave the team. | A starting member of the team. |
| **Substitute** | **(Existing)** A backup member of the roster. | **Member:**<br> - Same permissions as a Player. | A backup player for the team. |

#### **4. Actionable Steps for Implementation**

**Phase 1: Backend & Data Migration**

1.  **Schema Update:** Modify the database schema to support the new roles. This includes adding an `Owner` and `Manager` role and changing `Captain` to a boolean flag or separate title field (e.g., `is_captain`).
2.  **Data Migration Script:** This is critical. A script must be written to migrate all existing teams. For every current team, the user designated as "Captain" should be migrated to the new **"Team Owner"** role.
3.  **Implement Permission Logic:** Update the backend APIs to enforce the new permission rules. For every action (e.g., `invitePlayer`, `editTeamProfile`, `deleteTeam`), add a check to ensure the user's role has the required permission level.

**Phase 2: Frontend UI/UX Update**

1.  **"Manage Team" UI:** The team management page needs to be updated. The Team Owner should have an interface to assign `Manager`, `Coach`, and `Captain` roles to team members (e.g., via a dropdown next to each member's name).
2.  **Display the Captain Title:** In the roster view, the player designated as `Captain` should be clearly marked, for instance, with a star icon (⭐) next to their name.
3.  **Conditional Rendering:** The UI must dynamically show/hide administrative buttons based on the logged-in user's role. A standard `Player` should not see the "Invite Member" or "Edit Team" buttons.
4.  **Onboarding & Tooltips:** Add tooltips or info icons in the "Manage Team" section to briefly explain the purpose and permissions of each role. This will help users understand the new system.

#### **5. Summary of Benefits**

This overhaul will align our platform with professional esports standards, providing the flexibility and clarity that serious teams require. It solves the ambiguity of the "Captain" role and empowers teams to structure themselves in a logical and effective way.




### **Technical Specification: Roster Card UI & Content Display**

#### **1. Objective**

This document provides the technical and design specifications for displaying the new dual-role system on the team roster page. The implementation must be professional, intuitive, and context-aware, ensuring that the right information is shown to the right audience.

#### **2. Core Principle: Contextual Rendering**

The content displayed on a player card will be determined by the viewer's status. The frontend will need to render two distinct views based on whether the viewer is a member of the team or a member of the public.

  * **Public View:** For any user not logged in or not part of the team. Focuses on the competitive lineup.
  * **Team Member View:** For logged-in users who are part of the team (`Owner`, `Manager`, `Coach`, `Player`, `Substitute`). Focuses on administrative clarity.

#### **3. Specification 1: The Public Roster Card**

The public-facing card is designed to showcase the team's active players and their in-game functions. Administrative roles are intentionally hidden to maintain a clean, professional look.

**Key Requirements:**

  * Administrative roles (`Team Owner`, `Manager`, `Coach`) **MUST NOT** be displayed on the public card.
  * The primary focus is on the player's identity and tactical role.

**Card Content Fields (Public View):**

| Element | Data Field | Description / Implementation Notes |
| :--- | :--- | :--- |
| **Avatar** | `player.avatarUrl` | The user's profile picture. |
| **Name** | `player.inGameName` | The player's primary in-game name or display name. |
| **Captain Badge** | `player.isCaptain` (boolean) | If `true`, display a prominent star icon (⭐) next to the player's name to signify their role as the in-game Captain. |
| **In-Game Role** | `player.inGameRole` | The player's tactical role for the specific game (e.g., "Duelist", "AWPer"). This is a critical piece of information. |
| **Status Tag** | `player.teamRole` | A subtle tag that displays "Player" or "Substitute". The backend should filter out non-playing roles for this view. |

**Component Structure (Public View):**

```
+--------------------------------------+
|          [ Player Avatar ]           |
|                                      |
|    ⭐ PlayerInGameName               |
|    --------------------------        |
|    In-Game Role: INITIATOR           |
|                                      |
|    [ PLAYER ]                        |
+--------------------------------------+
```

-----

#### **4. Specification 2: The Team Member Roster Card**

This view is for internal team management. It must clearly display the full administrative and tactical hierarchy of the team.

**Key Requirements:**

  * All team-specific roles (`Team Owner`, `Manager`, `Coach`) **MUST** be clearly visible.
  * The card should provide a complete picture of the member's status within the team.

**Card Content Fields (Team Member View):**

| Element | Data Field | Description / Implementation Notes |
| :--- | :--- | :--- |
| **Avatar** | `player.avatarUrl` | The user's profile picture. |
| **Name** | `player.displayName` | The user's main platform display name. |
| **Captain Badge** | `player.isCaptain` (boolean) | Same implementation as the public view. |
| **Team Role** | `player.teamRole` | **Primary identifier.** Display the full role name prominently (e.g., "Team Owner", "Manager", "Player"). |
| **In-Game Role** | `player.inGameRole` | Display the tactical role if the member is a `Player` or `Substitute`. This field should be hidden for `Owner`, `Manager`, or `Coach` unless they also have a playing role. |

**Component Structure (Team Member View - for a Player who is also Captain):**

```
+--------------------------------------+
|          [ Player Avatar ]           |
|                                      |
|    ⭐ PlayerDisplayName              |
|    --------------------------        |
|    Team Role: PLAYER                 |
|    In-Game Role: CONTROLLER          |
+--------------------------------------+
```

-----

#### **5. Specification 3: The Player Details Modal (Pop-up)**

Clicking a roster card in **either view** should trigger a pop-up modal with more detailed information. This modal's content is consistent for all viewers.

**Trigger:** `onClick` event on the entire player card component.

**Modal Content Fields:**

| Section | Element | Data Field | Description / Implementation Notes |
| :--- | :--- | :--- | :--- |
| **Header** | Avatar & Name | `player.avatarUrl`, `player.displayName` | A larger version of the avatar next to their primary display name. |
| **Game ID** | Game ID Label & Value | `player.gameId` | Display the relevant game ID. Since each team is game-specific, the label must be dynamic (e.g., "Riot ID:", "Steam ID:"). |
| **Team Details**| Team Role | `player.teamRole` | Display the member's full team role (e.g., "Player", "Manager"). |
| | In-Game Role | `player.inGameRole` | Display their tactical role. |
| | Captain Status | `player.isCaptain` | Display as "Yes" or "No". |
| **Action Button**| "View Full Profile" Button | `player.profileUrl` | A prominent button that navigates the user to that player's main profile page on our platform. |

#### **6. API Endpoint Suggestions**

The API endpoint that serves the team roster data should include a field in its response to facilitate the conditional rendering, such as `viewer_is_member: true/false`. This allows the frontend to easily determine which card view to display.

The payload for each player in the roster array should contain all the necessary fields for both views and the modal.