
### **Part 1 (Revised): Foundational Principles & Registration Flow**

This revised blueprint is tailored to your specific development constraints, focusing on flexibility for organizers and a straightforward data entry process for users, without relying on external game APIs.

#### **1. Core Philosophy: The Organizer-Driven Form**

We are shifting from a "profile-first" model to a **"form-first, organizer-driven"** model. This means the registration form is the primary point of data collection, and its rules are defined by the tournament organizer, not by a rigid system.

* **Principle 1: Direct Data Entry is Key.**
    Users will enter their game information directly into the registration form. To make this faster for repeat users, the form will *attempt* to auto-fill fields with data from their user profile, but **every field will remain fully editable.** This eliminates the need to redirect users to their profile page during registration. We will add a simple checkbox to let users save the information they enter back to their profile for future use.

* **Principle 2: Configurable Fields (Required vs. Optional).**
    Your point is spot on—flexibility is essential. The system will not have hard-coded "required" fields. Instead, when an organizer creates a tournament, they will have a settings panel where they can toggle which fields are **Required** and which are **Optional**. For example, one organizer might make `Discord ID` required for a *CS2* tournament, while another makes it optional.

* **Principle 3: Format Validation, Not API Validation.**
    Given no access to game APIs, we cannot verify if a Game ID is real, active, or belongs to the user. This is a critical point for the developer. Our "validation" will be limited to checking the **pattern/format** of the input.
    * **Example:** We can check that a `Riot ID` contains a "#" (e.g., `PlayerName#TAG`), but we can't check if `PlayerName#TAG` actually exists in VALORANT.
    * This approach prevents obvious typos and guides the user, but the responsibility for accurate data ultimately lies with the player and the tournament admin.

* **Principle 4: Captain as the Data Manager.**
    For team tournaments, the captain remains the central figure. However, their role is now simplified. They are responsible for gathering and **manually entering** the required information for their entire roster. The system will assist them but will not force a complex player-invite-and-accept workflow.

---

#### **2. Proposed Form Structure: SOLO Tournaments**

This structure is for 1v1 games like **eFootball** and **EA Sports FC 26**.

**Pre-requisite:** The user is logged into their account on your platform.

---

**Step 1: Game & Contact Information**

This is a single-step form designed for speed and clarity.

* **Tournament Details (Read-only):**
    * **Tournament Name:** `eFootball Mobile Weekly Cup #23`
    * **Game:** `eFootball`

* **Player Game Identity:**
    * **In-Game Name (IGN):** `[Text Field]`
        * *Functionality:* Auto-fills from the user's profile if available, but remains editable.
        * *Configuration:* Organizer can set this to `Required` or `Optional`.
    * **Game User ID:** `[Text Field]`
        * *Label:* This label is dynamic based on the game (e.g., **eFootball User ID**, **EA ID**, **PSN ID**).
        * *Functionality:* Auto-fills from profile if available, remains editable.
        * *Configuration:* Organizer can set this to `Required` or `Optional`.
    * **Platform (If applicable for the game):** `[Dropdown]`
        * *Options:* `PC`, `PlayStation 5`, `Xbox Series X/S`.
        * *Functionality:* Only shown if the tournament organizer enables it for that game.
    * `[Checkbox]` **Save my Game IDs to my profile for future tournaments.**
        * *Functionality:* If checked, the entered `IGN` and `Game User ID` will be saved to the user's main profile after successful registration.

* **Contact Information:**
    * **Discord ID:** `[Text Field]`
        * *Functionality:* Auto-fills from profile, remains editable.
        * *Configuration:* Organizer can set this to `Required` or `Optional`.
        * *Helper Text:* "Example: `username` or `username#1234`"
    * **Phone Number:** `[Text Field]`
        * *Functionality:* Auto-fills from profile, remains editable.
        * *Configuration:* Organizer can set this to `Required` or `Optional`.

---

**Step 2: Review & Confirm**

* **Registration Summary:**
    * A clean, read-only display of all the information entered in Step 1.

* **Agreements & Rules:**
    * `[Checkbox]` **I have read and agree to the Tournament Rules.** (The "Tournament Rules" is a link).
        * This checkbox is always required to submit the form.

* **Action Button:**
    * **Button:** `[Confirm Registration]`

---

#### **3. Proposed Form Structure: TEAM Tournaments**

This flow is for the **Team Captain**. It is designed to be a simple roster-building tool.

---

**Step 1: Team & Captain Information**

* **Tournament Details (Read-only):**
    * **Tournament Name:** `VALORANT Champions Tour: Bangladesh Qualifiers`
    * **Game:** `VALORANT`

* **Team Information:**
    * **Select Your Team:** `[Dropdown menu listing teams where the user is Captain]`
        * *Functionality:* Selecting a team auto-fills the `Team Name` field.
    * **Team Name:** `[Text Field]`
        * *Functionality:* Can be edited by the captain for this specific tournament if needed.

* **Captain's Information (Auto-filled but editable):**
    * **Captain's In-Game Name:** `[Text Field]`
    * **Captain's Riot ID:** `[Text Field]`
    * **Captain's Discord ID:** `[Text Field]`
    * `[Checkbox]` **Update my profile with the info I entered above.**

---

**Step 2: Team Roster & Roles**

This is a straightforward data entry table managed entirely by the captain.

* **Roster Requirements (Informational Text):**
    * "This tournament requires a minimum of **5** players and allows a maximum of **2** substitutes. Please fill in the details for each player."

* **Roster Entry UI:**
    * A list of player "slots." The captain can click "Add Player" to create a new slot. Each slot contains a set of fields to be filled in manually.
    

    **Player 1 (Captain):**
    * Fields are pre-filled and locked from Step 1.
    * **Role:** `[Dropdown]` (Options are dynamic per game, e.g., `Duelist`, `Controller`, etc.)

    **Player 2:**
    * **In-Game Name:** `[Text Field]`
    * **Riot ID (or Steam ID, etc.):** `[Text Field]`
    * **Role:** `[Dropdown]`
    * `(Optional) Discord ID:` `[Text Field]` (Label shows "Optional" if set by organizer).

    **Player 3:**
    * ... (same fields as Player 2) ...

    ... and so on, up to the maximum roster size. The captain can add or remove player slots as needed.

* **Key Functionality:** There is **no invite system**. The captain is fully responsible for gathering and accurately typing in their team's information. This removes significant development complexity.

---

**Step 3: Review & Submit**

* **Final Roster Summary:**
    * A clean, read-only table displaying the entire roster as entered by the captain: Player Name, Game ID, and Role. This is the final check for typos.

* **Agreements & Rules:**
    * `[Checkbox]` **As team captain, I confirm that all player information is accurate and that the entire roster agrees to the Tournament Rules.**

* **Action Button:**
    * **Button:** `[Submit Registration]`
    * *Validation:* The button is disabled unless the minimum number of player slots (as set by the organizer) have been filled out.

---



### **Part 2 (Revised): Game-Specific Field & Roster Specifications**

This document serves as the technical blueprint for the dynamic fields within the tournament registration form. It is built upon the "form-first, organizer-driven" philosophy from Part 1 and incorporates the specific requirements from your developer instruction guide.

#### **General Roster & Player Field Information**

For **Team-Based Games**, the fields detailed below are to be presented for **each player** the captain adds to the roster in Step 2. The system should enforce the minimum number of starters and allow up to the maximum number of substitutes as specified for each game.

For **Solo Games**, these fields will appear in the single-step registration form.

---

### **A. Team-Based Games**

#### **1. VALORANT**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `riotId` | Riot ID | Text Input | `Example: PlayerName#TAG` | Must contain a single `#` character. Min length: 5 (e.g., `a#a`). |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer can set as Required/Optional). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Duelist
* Controller
* Initiator
* Sentinel
* IGL (In-Game Leader)

---

#### **2. CS2 (Counter-Strike 2)**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `steamId` | Steam ID | Text Input | `e.g., STEAM_0:1:123456 or 7656119...` | Must contain numbers and start with `STEAM_` or `765`. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Note on `steamId`:** It's helpful to add a small link below this field: "How to find your Steam ID?" which links to a simple guide.

**Player Role Dropdown Options (`playerRole`):**
* IGL (In-Game Leader)
* Entry Fragger
* AWPer
* Lurker
* Support

---

#### **3. Dota 2**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `steamId` | Steam ID | Text Input | `e.g., STEAM_0:1:123456 or 7656119...` | Must contain numbers and start with `STEAM_` or `765`. |
| `dotaFriendId` | Dota 2 Friend ID | Text Input | `Find this in your Dota 2 profile` | Must be numbers only. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Position | Dropdown | `Select a position` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Hard Carry (Pos 1)
* Midlaner (Pos 2)
* Offlaner (Pos 3)
* Soft Support (Pos 4)
* Hard Support (Pos 5)

---

#### **4. Mobile Legends: Bang Bang (MLBB)**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `inGameName` | In-Game Name | Text Input | `The exact name shown in MLBB` | Must not be empty. |
| `mlbbUserId` | MLBB User ID | Text Input | `Example: 12345678 (1234)` | Must be numbers only. Can accept format `ID(Zone)`. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Gold Laner
* EXP Laner
* Mid Laner
* Jungler
* Roamer

---

#### **5. PUBG (PC/Mobile)**
* **Team Size:** 4 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `characterName` | PUBG Character Name | Text Input | `The exact name shown in PUBG` | Must not be empty. |
| `pubgId` | PUBG ID | Text Input | `Example: 5123456789` | Must be numbers only (for Mobile) or alphanumeric. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* IGL / Shot Caller
* Assaulter / Fragger
* Support
* Sniper / Scout

---

#### **6. Free Fire**
* **Team Size:** 4 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `inGameName` | In-Game Name | Text Input | `The exact name shown in Free Fire` | Must not be empty. |
| `freeFireUid` | Free Fire UID | Text Input | `Example: 1234567890` | Must be numbers only. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Rusher
* Flanker
* Support
* Shot Caller (IGL)

---

### **B. Solo / Individual Entry Games**

#### **7. eFootball**
* **Format:** Can be Solo (1v1) or Team (2v2 with 1 sub). The form should adapt.

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `efootballUsername` | eFootball Username | Text Input | `Your username in the game` | Must not be empty. |
| `efootballUserId`| eFootball User ID | Text Input | `Example: 123456789` | Must be numbers only. |

---

#### **8. FC 26 (EA Sports FC)**
* **Format:** Can be Solo (1v1) or Team (1v1 with 1 sub for co-op formats).

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `platform` | Platform | Dropdown | `Select your gaming platform` | Must select one option. |
| `platformId` | EA ID / PSN ID / Gamertag | Text Input | `Enter your ID for the selected platform` | No special format validation. |
| `fc26Username` | FC 26 Username | Text Input | `Your username in FC 26` | Must not be empty. |

**Platform Dropdown Options (`platform`):**
* PC (EA App)
* PlayStation
* Xbox

**Note on `platformId`:** The label for this field should dynamically change based on the `platform` selection (e.g., if "PlayStation" is chosen, the label becomes "PSN ID").

---
### **Part 3 (Revised): UI/UX, Design Philosophy & The Dynamic Wizard Flow**

This document outlines the visual design, user experience (UX) principles, and interaction model for the tournament registration process. The goal is to create an interface that is not just functional but also immersive, visually appealing with an "esports vibe," and flawlessly responsive across all devices.

#### **1. Visual Design Philosophy: The "Esports Vibe"**

The interface should feel like an extension of the gaming experience itself—sleek, energetic, and intuitive.

* **Color Palette:**
    * **Primary Background:** A dark theme is non-negotiable. Use a deep charcoal (`#121212`) or dark navy blue, not pure black, to avoid eye strain.
    * **Component Backgrounds:** Use slightly lighter shades of the primary background for form fields and cards (`#1E1E1E`) to create a sense of depth.
    * **Primary Accent Color:** A vibrant, high-energy color for buttons, active states, and highlights. This could be a neon blue, electric purple, or a fiery orange. This color should be used sparingly to draw the user's attention to key actions.
    * **Feedback Colors:**
        * **Success:** A bright, clear green (`#00FF7F`).
        * **Error:** A sharp, visible red (`#FF4136`).
        * **Warning/Info:** A noticeable amber or yellow (`#FFD700`).

* **Typography:**
    * **Headings:** Use a modern, bold sans-serif font like **Montserrat**, **Poppins**, or **Teko**. Headings should be sharp, well-spaced, and in all-caps or title case for impact.
    * **Body & Labels:** A highly legible sans-serif font like **Roboto** or **Inter**. Ensure sufficient font weight so labels don't get lost against the dark background.
    * **Hierarchy:** Create a clear visual hierarchy. Main step titles should be large, section titles slightly smaller, and field labels smaller still but perfectly readable.

* **Layout & Components:**
    * **Card-Based Design:** Avoid plain, boring form layouts. Enclose related groups of information (like a single player's roster details) in "cards." These cards should have a subtle border, a slightly different background color, and a soft glow effect in the accent color when hovered over.
    * **Spacing:** Be generous with whitespace (or "darkspace" in this theme). Give elements room to breathe. This prevents the UI from feeling cluttered and overwhelming, which is crucial for a form with many fields.
    * **Iconography:** Use sharp, custom icons for actions (e.g., a stylized trash can for "Remove Player," a plus icon for "Add Player"). Game logos should be prominently displayed to reinforce context.

---

#### **2. The Dynamic Wizard Flow: The Core User Journey**

The registration process is a multi-step "wizard." Its length is dynamic, based on whether the tournament has an entry fee.

* **The Stepper Component:** At the top of the screen, a visual stepper must always be visible.
    * It should clearly label each step (e.g., `1. TEAM INFO`, `2. ROSTER`, `3. REVIEW`, `4. PAYMENT`).
    * **States:**
        * **Completed:** The number/icon has a solid fill of the accent color and a checkmark. The line connecting to the next step is also filled.
        * **Active:** The number/icon is highlighted, perhaps with a pulsing glow effect. The text is bold and bright.
        * **Upcoming:** The number/icon and text are semi-transparent or grayed out.

**Scenario A: FREE Tournament (3 Steps)**
`[ 1. Team ]` -> `[ 2. Roster ]` -> `[ 3. Review & Submit ]`

**Scenario B: PAID Tournament (4 Steps)**
`[ 1. Team ]` -> `[ 2. Roster ]` -> `[ 3. Review ]` -> `[ 4. Finalize & Pay ]`

---

#### **3. Step-by-Step UI/UX Breakdown (Team Tournament Example)**

This details what the user sees and interacts with at each stage.

**Step 1: Team & Captain Information**
* **UI:** A single, clean card centered on the screen. The tournament banner/logo is displayed prominently above.
* **UX:**
    * The "Select Your Team" dropdown should be large and easy to use. Upon selection, the captain's details (`In-Game Name`, `Game ID`) should fade in smoothly, pre-filled.
    * If any of the captain's required game IDs are missing from their profile, the field will appear empty with a red border, and a helpful message will appear: "Your Riot ID is missing. Please enter it to continue."
    * The "Next: Build Roster" button remains disabled until all required fields in this step are valid.

**Step 2: Team Roster & Roles**
* **UI:** This is the most complex screen. Instead of a table, use the **Player Card** system.
    * The captain's card is at the top, locked and pre-filled.
    * Below it are empty slots represented by cards with a dashed border and a large `[ + ADD PLAYER ]` button inside.
    * When a player is added, their card appears with all the required fields from Part 2 (`Display Name`, `Game ID`, `Role Dropdown`, etc.).
    * Each card has a clear "Remove Player" icon in the top-right corner.
    * A running counter is visible: `ROSTER: 3/5 Players Filled`.
* **UX:**
    * **Smooth Transitions:** Clicking `[ + ADD PLAYER ]` should animate a new card smoothly into the list, not just make it pop in.
    * **Inline Validation:** As the captain fills out a teammate's info and moves to the next field, the previous one is validated instantly. A small green check appears for valid data, and a red error message appears for invalid data. This provides immediate feedback.
    * **Role Dropdowns:** These should be styled to match the theme, not be the default browser dropdowns.

**Step 3: Review / Review & Submit**
* **UI:** A clean, read-only summary. Display the team name and logo prominently. The roster is shown as a list of simplified player cards, showing only the name, game ID, and role. This is for final verification.
* **UX:**
    * An "Edit" button next to each section (e.g., "Team Info," "Roster") allows the captain to quickly jump back to that specific step to make changes without losing their progress.
    * A single, mandatory checkbox is at the bottom: `[ ] I confirm all information is correct and my team agrees to the tournament rules.`
    * **The Final Button (Dynamic):**
        * **For FREE tournaments:** The button reads `[ COMPLETE REGISTRATION ]`.
        * **For PAID tournaments:** The button reads `[ PROCEED TO PAYMENT ]`.

**Step 4: Finalize & Pay (For Paid Tournaments Only)**
* This is the final hand-off step. The UI is simple:
    * A confirmation message: "Your roster has been saved. You will now be redirected to complete your payment and secure your spot."
    * A summary of the fee (`Registration Fee: ৳500`).
    * An auto-redirect will occur after 5 seconds, with a visible countdown. A `[ Pay Now ]` button is also available if they don't want to wait.
    * This takes them to your existing, separate payment page.

---

#### **4. Mobile-First Responsive Design**

The experience must be seamless on mobile.

* **Layout:** All multi-column layouts on desktop will collapse into a single, scrollable column on mobile. The stepper at the top may shrink to show only icons, with the current step's text visible.
* **Player Cards:** On mobile, Player Cards will stack vertically, each taking up the full width of the screen.
* **Tap Targets:** Buttons, form fields, and dropdowns must have large enough tap targets to be easily used with a thumb. Follow platform accessibility guidelines (e.g., minimum 44x44px tap area).
* **Font Sizes:** Font sizes must be legible on small screens. Use responsive font sizing (e.g., using `vw` units or media queries) to ensure readability without forcing the user to zoom.

---

#### **5. Micro-interactions & Polishing**

These small details elevate the UX from "good" to "great."

* **Loading States:** When a user clicks a submission button (`Next`, `Complete Registration`), the button should transition to a loading state (e.g., a spinner appears inside it) to provide feedback that the system is working.
* **Auto-Saving:** Implement auto-saving in the browser's local storage for the Roster step. A small, non-intrusive message can appear at the bottom: "Your roster draft has been saved."
* **Hover Effects:** Buttons should subtly glow or change brightness on hover. Player cards should lift or have their border highlighted. These effects make the UI feel alive and responsive.

By implementing this detailed UI/UX plan, your registration form will become a powerful, engaging, and professional part of your platform that builds player confidence and excitement from the very first interaction.