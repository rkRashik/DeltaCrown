# **📘 DeltaCrown Team Creation – Technical Implementation Guide**

**UI/UX Vibe:** Liquid Cyberpunk / Gen Z Professional

**Developer Persona:** Backend Engineer / Fullstack Architect

---

## **1\. Core Logic & Strategy**

The team creation process has been upgraded from a simple form to a **Multi-Step Strategic Wizard**. It enforces the new **"Managers Manage, Players Play"** policy by allowing creation without a Game Passport unless the user is assigned to a player slot.

### **The "Command Structure" Fork**

The most critical addition in this version is the **Independent vs. Organization** choice.

* **Independent:** User owns the "Slot" directly.  
* **Organization:** The "Slot" is owned by a business entity. The user is a Division Manager.  
  ---

  ## **2\. Component Implementation Details**

  ### **A. Navigation & Progress Control**

* **The Wizard (goToStep):** Uses CSS classes active and hidden.  
* **State Preservation:** As the user moves through steps, the JavaScript updatePreview() function keeps the right-side "Holographic Preview" in sync.  
* **Backend Hook:** Before moving from Step 2 to Step 3, the developer should implement an AJAX check to ensure the **Team Name** and **Tag** are unique in the database for the selected game.

  ### **B. Step 2: Identity & Command Structure**

| Element | Field Name | Requirement |
| :---- | :---- | :---- |
| **Command Structure** | org\_status | Radio: independent OR organization. |
| **Parent Org** | organization\_id | Only visible if org\_status \== 'organization'. |
| **Squad Name** | name | String. Min 3, Max 20\. |
| **Tag** | tag | String. Max 5\. Enforced Uppercase. |
| **Description** | description | Textarea. Optional. |

**Developer Note:** If inheritBranding is checked, the backend should ignore any uploaded files and link the team directly to the parent Org's logo and banner fields.

### **C. Step 3: Operations & Recruitment**

* **Smart Detect Region:** Currently uses a mockup for Bangladesh. **Implementation:** Use a Geo-IP service or a Django middleware to pass the user's current country name and flag to the template.  
* **Command Authority:** \* If invite is selected, the field managerEmail becomes mandatory.  
  * **Backend Logic:** On form submission, if an email is provided, create a TeamInvite object with the role MANAGER.  
* **Squad Recruitment:** This allows bulk invitation. The backend should process these as a list of TeamInvite objects with the role PLAYER.

  ### **D. Step 4: Visual Assets (Visual UI Fix)**

* **Redesign:** The upload boxes now use a higher contrast background (\#12121A) and a dashed border system.  
* **Logic:** previewImage() handles local file reading to show the user their upload instantly without a server round-trip.  
* **Recommendation:** Use a library like Pillow on the backend to enforce the recommended dimensions (500x500 for logos) and compress them to .webp for faster Hub loading.  
  ---

  ## **3\. Real-Time Validation System**

The template features a high-visibility validation system:

1. **Border Toggling:** Inputs use .error (Red) or .success (Neon Green/Cyan) classes.  
2. **Status Icons:** The status-icon div toggles between an asterisk (Required), a checkmark (Valid), or an exclamation (Invalid).  
3. **Real-Time Count:** The \#nameCount span updates on every keystroke (oninput).

**Validation Requirements:**

* **Name:** Must not contain profanity (Check against a blacklist on backend).  
* **Tag:** Must be alphanumeric only.  
* **Email:** Standard email regex validation.  
  ---

  ## **4\. The "Holographic Preview" (UX Engine)**

The sticky sidebar on the right is the **Conversion Engine**. It makes the user feel like they are already part of the platform.

* **Dynamic Badge:** Shows the Organization name at the top if selected.  
* **Identity Sync:** The TAG text is replaced by the actual Logo image once uploaded.  
* **Gamification:** Shows 0 CP and Unranked to trigger the user's desire to start competing immediately.  
  ---

  ## **5\. Missing Implementation Logic (For Developers)**

The following logic exists in the UI but requires Backend scripts:

1. **Draft System:** The "Back" button preserves input data in the DOM, but for a "Premium" experience, the developer should implement localStorage or a DraftTeam model to save progress if the user accidentally closes the tab.  
2. **Code of Conduct Signature:** The \#termsCheck checkbox must be saved as a timestamp in the database (tos\_accepted\_at) for legal compliance.  
3. **Country List:** The \#manualRegion select should be populated using django-countries or a similar package to ensure ISO standard country codes are used.  
   ---

   ## **6\. Migration Checklist**

* \[ \] **Tailwind Sync:** Ensure delta-gold, delta-violet, and delta-electric are added to the main tailwind.config.js.  
* \[ \] **CSRF Protection:** Since this template uses a \<form\>, ensure {% csrf\_token %} is added inside the tag when converting to a Django template.  
* \[ \] **Media Handling:** The multipart/form-data encoding must be set on the form tag to allow the Logo and Banner uploads to reach the server.  
* \[ \] **Mobile Touch:** The Game Grid items have been given larger hit targets for iOS/Android users.  
  ---

**Final Goal:** When the user clicks "Establish Team", they should be redirected to the **Team Dashboard** with a success toast notification: *"Unit Online. Welcome to the DeltaCrown Ecosystem."*

* 

