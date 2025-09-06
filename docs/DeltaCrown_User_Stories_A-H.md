# DeltaCrown — Narrative User Stories (Parts A–H)
_Date: September 06, 2025_

These stories narrate **what the user expects to do** on the platform and **why** each feature exists. Hand this to developers/designers so everyone shares the same mental model before building.

---

## Cast & Glossary
- **Player**: any signed-in user.
- **Captain**: the Player who manages a team (roster edits, registrations).
- **Organizer/Admin**: staff verifying payments, managing brackets/schedules.
- **Games**: _eFootball_ (Solo or Duo), _Valorant_ (Team only).
- **Payment methods**: **bKash**, **Nagad**, **Rocket**.
- **Active Team**: a user can have **one active team per game** (enforced).
- **Preset**: a saved snapshot used to prefill registration forms quickly.

---

## Global Rules woven through every story (Hard Rules)
1) **Unique**: email (CI), username, team name per game (CI), team tag per game (CI).  
2) **Eligibility**: roster members must be real site users with profiles.  
3) **One active team per game per user**; captain-only registration for Valorant.  
4) **Profile** includes IGN + socials; privacy toggles respected on public pages.  
5) **Autofill priority**: Active Team → Preset → Profile → Empty.  
6) **Payments**: if fee > 0, user selects method and submits number + transaction ID. Organizer manually verifies and can contact the payer.  

---

## Story A — Discover & Register: eFootball (Solo)

**As a Player**, I:
1. Sign in.  
2. Open an **eFootball Solo** tournament detail page to read rules & fees.  
3. Click **Register** → the registration page opens.  
4. The form **prefills** my name, email, phone, and **IGN** from my profile.  
5. If the tournament has a fee, I **select a payment method** (bKash/Nagad/Rocket), **pay externally**, then **enter my mobile number** and **transaction ID**.  
6. I tick required agreements and click **Submit**.  
7. I instantly see a **success page** and receive a **confirmation email** stating “registration received, pending payment verification” (if paid).  
8. Later, the Organizer manually **verifies** my payment. If something doesn’t match, they may **email me** for clarification.  
9. In my **Profile → Registrations**, I **see** that tournament listed.  
10. After registrations close, I visit the tournament page to see **participants, groups, schedules**.

**Acceptance**: clean prefill, payment fields only when fee>0, email sent, profile lists registration, public schedule visible post-close.

---

## Story B — Team Up & Register: eFootball (Duo)

**As a Player (Captain) registering a Duo event**, I:
1. Ensure I have an **eFootball Team** with my partner.  
   - If I **don’t** have one yet, I create it once (team name/tag/logo); we both become members.  
   - The platform enforces that I have **only one active eFootball team**.
2. Open the **Duo tournament** page → **Register**.  
3. The form **auto-uses my active eFootball team**; it **prefills** both the **captain** and **mate** details (names, emails, phones, IGNs).  
   - If partner details aren’t in the team/profile, I can **type them**; I can also **Save as my eFootball Team** to create/update a preset for future speed.  
4. If fee>0, I complete the **payment step** (method, number, transaction ID).  
5. Submit → success + email. Organizer verifies payment and may contact us if mismatch.  
6. Partner can see the team on the **team page**, and I see the registration in **my profile**.  
7. After reg closes: our **team name appears** in participants; **groups** and **match schedule** render publicly.

**Acceptance**: active-team auto-binding, duo roster size enforced (=2), preset option, payment verification flow, public visibility after close.

---

## Story C — Assemble & Register: Valorant (Team 5–7)

**As a Captain**, I:
1. Build a **Valorant team** first. The roster must have **min 5 / max 7** (2 subs).  
   - Each member is a site user; their **Riot ID** (`username#tagline`) and **Discord** are recorded, plus roles (Starter/Sub).  
   - I must be **Captain** to proceed.
2. Open a **Valorant tournament** → **Register**.  
3. The form **auto-selects my active Valorant team** and **prefills** players’ details.  
   - Only **I (Captain)** can register.  
   - I can **Save as my Valorant Team** (preset) so we skip typing next time.
4. If fee>0: choose method, pay, fill number + transaction ID; submit.  
5. I get an email; Organizer manually verifies payment.  
6. After reg closes, the **team appears** on participants; **groups** (if any) and **schedule** render.  
7. In **My Matches**, my teammates see every match card with opponent/time/BoX/score and quick actions (Report/Confirm/Dispute).

**Acceptance**: captain-only, roster size 5–7, auto-use active team, preset option, payment verified, My Matches reflects upcoming & recent matches.

---

## Story D — Profile & Teams: One Team Per Game, Clear Overview

**As a Player**, I see a **My Teams by Game** block in my profile:
- For **eFootball** and **Valorant**, it shows my **active team** (logo/name/tag) or a **Create Team** CTA.
- I cannot have **two active teams** for the same game.
- Clicking into team **Manage**, I can adjust metadata (Part C) and handle roster invitations.

**Acceptance**: block accurately reflects active teams; creation flows set the correct `game` field; guardrails prevent multiple actives per game.

---

## Story E — Team Pages Like Pros (Public + Manage)

**As a Visitor**, I open `/teams/<game>/<slug>/` to see a **pro-looking team page**:
- **Hero** with banner GIF, logo, team name/tag/region, socials.  
- **Current Roster** with roles, each member linking to their **public profile**.  
- **Team Stats** (played, W/L, win rate, streak).  
- **Achievements** (e.g., “Top 4 at X 2025”), **Upcoming matches**, **Recent results**.

**As a Captain**, I open `/profile/teams/<game>/manage/`:
- Upload **banner GIF** and **roster poster**, set **slug** (fixed or admin-renamable).  
- Edit socials, region.  
- Manage **roster** (invite/remove/transfer captain; enforce size rules).  
- Add **achievements**; trigger **rebuild stats** on demand.

**Acceptance**: public page renders all sections; manage respects permissions; roster size rules enforced; social links and media show correctly.

---

## Story F — Payments: Nudge & Verify (Admin)

**As an Organizer/Admin**, in the admin panel I can:
- Select **PENDING** payers and **email** them a reminder (with preview & dry-run).  
- **Bulk verify** payments for a batch after cross-checking transaction IDs.  
- The system records **who verified**, **when**, and an optional **note**.  
- If an entry is inconsistent, I can **contact the player** via email directly.

**Acceptance**: emails sent in batches; verified rows updated w/ audit trail; error cases allow contacting users.

---

## Story G — After Registration: Participants, Groups & Schedule

**As a Player**, once registration **closes**:
- I go to the tournament page and see: **my team listed** in **Participants**, **Groups** (if group stage exists), and the **match schedule**.  
- If groups are used, they may be stored in **Bracket.data JSON** first; later we can move to real **Group** models.  
- In **My Matches**, I can filter by game, state, date range, tournament.

**Acceptance**: post-close renders correctly; groups parse from JSON; My Matches filters work and are scoped to the user’s teams.

---

## Story H — Profiles: Identity, Socials & Privacy

**As a Player**, my profile is a first-class public page:
- **Unique email & username**; my **IGN** is shown (unless private).  
- I can **decorate** with **YouTube**, **Facebook**, **Twitch**, and game IDs (Riot/Discord/eFootball).  
- I can toggle **privacy**: hide email/phone/socials or make my profile private.  
- **Team pages** and **rosters** link to my profile, respecting privacy toggles.

**Acceptance**: privacy respected everywhere; unique constraints enforced; links validated; public view clean and discoverable.

---

## Story I — Autofill & Presets: Frictionless Repeat Registrations

**As a Player/Captain**, I hate typing the same data twice:
- When I register, the system **prefills** using **Active Team → Preset → Profile → Empty**.  
- If I correct something, I can tick **“Save as my [Game] Team”** to update my preset so next time it’s spot-on.  
- Snapshots of submitted data are stored with the registration for history; **eligibility** still derives from current **TeamMemberships**.

**Acceptance**: prefill priority followed; preset saving updates future forms; historical snapshots retained.

---

## Edge Cases Narratives (What happens when things go wrong)

- **No active team** for the game → registration **blocked** with a clear CTA to **Create Team**.  
- **Roster size invalid** (Valorant <5 or >7; eFootball Duo ≠ 2) → form **error** and hints to fix in Manage Team.  
- **Member on two teams (same game)** → add attempt fails due to **one-active-per-game** rule.  
- **Payment mismatch** → Organizer can email the payer; status remains **PENDING** until resolved.  
- **Duplicate team name/tag (case)** → creation/update fails with friendly error (CI unique constraints).  
- **Profile private** → public pages respect hidden fields; team roster still lists the member with minimal info.

---

## Why these stories matter
- They translate directly into UI, models, and constraints the devs will implement.  
- They make it clear what **“done”** looks like for each part (A–H).  
- They align operations (Admins), gameplay needs (rosters, schedules), and player experience (prefill, presets, privacy).

---

## Acceptance Criteria Summary (Checklist)
- [ ] Registration flows: Solo, Duo, Valorant — prefill works; payment captured when fee>0; confirmations sent.  
- [ ] One active team per game per user; captain-only for Valorant.  
- [ ] Public team pages + captain manage console; roster/achievements/stats.  
- [ ] Payments admin: email pending; bulk verify; audit trail.  
- [ ] Groups render from JSON; schedules visible post-close.  
- [ ] My Matches filters by game/state/date/tournament.  
- [ ] CI uniqueness (email, username, team name/tag per game).  
- [ ] Profiles with IGN/socials + privacy respected.  
- [ ] Autofill priority + presets; snapshots stored.
