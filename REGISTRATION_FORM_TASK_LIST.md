# Dynamic Tournament Registration Form - Task List

**Project Start Date:** October 13, 2025  
**Estimated Completion:** November 10, 2025 (4 weeks)  
**Developer:** [Your Name]  
**Status:** Ready to Start

---

## 📋 MASTER TASK CHECKLIST

### ✅ = Completed | 🔄 = In Progress | ⏳ = Pending | ❌ = Blocked

---

## PHASE 1: DATABASE & GAME CONFIGURATION (Days 1-4) ✅ COMPLETED

### Database Models

- [x] **Task 1.1**: Create `GameConfiguration` model
  - [x] Define model fields (game_code, display_name, team_size, etc.)
  - [x] Add Meta class with ordering and indexes
  - [x] Create `__str__` method
  - [x] Add validation in `clean()` method
  - **Files**: `apps/tournaments/models/game_config.py`
  - **Status**: ✅ COMPLETED

- [x] **Task 1.2**: Create `GameFieldConfiguration` model
  - [x] Define model fields (field_name, field_type, validation_regex, etc.)
  - [x] Add ForeignKey to GameConfiguration
  - [x] Create FIELD_TYPES choices
  - [x] Add JSON field for select choices
  - [x] Add ordering by display_order
  - **Files**: `apps/tournaments/models/game_field_config.py`
  - **Status**: ✅ COMPLETED

- [x] **Task 1.3**: Create `PlayerRoleConfiguration` model
  - [x] Define model fields (role_code, role_name, is_unique, etc.)
  - [x] Add ForeignKey to GameConfiguration
  - [x] Add Meta class with unique_together constraint
  - [x] Create helper method `get_available_roles()`
  - **Files**: `apps/tournaments/models/player_role_config.py`
  - **Status**: ✅ COMPLETED

- [x] **Task 1.4**: Update models `__init__.py`
  - [x] Import new models
  - [x] Add to `__all__` list
  - [x] Test imports work correctly
  - **Files**: `apps/tournaments/models/__init__.py`
  - **Status**: ✅ COMPLETED

- [x] **Task 1.5**: Create and run migrations
  - [x] Run `python manage.py makemigrations`
  - [x] Review migration file (0045_gameconfiguration_playerroleconfiguration_and_more.py)
  - [x] Run `python manage.py migrate`
  - [x] Verify tables created in database
  - **Status**: ✅ COMPLETED

### Seed Data Script

- [x] **Task 1.6-1.15**: Create and populate game configurations
  - [x] Create management command structure
  - [x] Add Valorant configuration (5+2, 5 roles, 2 fields)
  - [x] Add Counter-Strike 2 configuration (5+2, 5 roles, 3 fields)
  - [x] Add Dota 2 configuration (5+2, 5 position-based roles, 3 fields)
  - [x] Add Mobile Legends configuration (5+2, 5 roles, 3 fields)
  - [x] Add PUBG configuration (4+2, 4 roles, 3 fields)
  - [x] Add Free Fire configuration (4+2, 4 roles, 3 fields)
  - [x] Add eFootball configuration (solo/2+1, no roles, 2 fields)
  - [x] Add FC 26 configuration (solo/1+1, no roles, 3 fields with platform select)
  - [x] Run seed command and verify
  - **Files**: `apps/tournaments/management/commands/seed_game_configs.py`
  - **Status**: ✅ COMPLETED
  - **Results**: 8 games, 22 fields, 28 roles seeded

### Admin Interface

- [x] **Task 1.16**: Create `GameConfigurationAdmin`
  - [x] Add to `apps/tournaments/admin/game_configs.py`
  - [x] Configure list_display with badges
  - [x] Add list_filter (is_solo, is_team, is_active)
  - [x] Add search_fields
  - [x] Add readonly_fields for timestamps
  - [x] Add custom badges (roster, types, active status)
  - **Status**: ✅ COMPLETED

- [x] **Task 1.17**: Create `GameFieldConfigurationAdmin`
  - [x] Add inline to GameConfigurationAdmin
  - [x] Configure field display
  - [x] Add ordering by display_order
  - [x] Add validation indicators
  - [x] Create standalone admin view
  - **Status**: ✅ COMPLETED

- [x] **Task 1.18**: Create `PlayerRoleConfigurationAdmin`
  - [x] Add inline to GameConfigurationAdmin
  - [x] Configure role display
  - [x] Add ordering by display_order
  - [x] Add is_unique indicator
  - [x] Create standalone admin view
  - **Status**: ✅ COMPLETED

- [x] **Task 1.19**: Test admin interface
  - [x] Register admin in `apps/tournaments/admin/__init__.py`
  - [x] Verify all 8 games appear correctly
  - [x] Verify field configurations display
  - [x] Verify role configurations display
  - [x] Test validation works
  - **Status**: ✅ COMPLETED

---

**Phase 1 Summary:**
- ✅ 3 new models created (GameConfiguration, GameFieldConfiguration, PlayerRoleConfiguration)
- ✅ Database migration applied (0045)
- ✅ 8 games seeded with 22 fields and 28 roles
- ✅ Comprehensive admin interface with inlines and badges
- ✅ Verified: Valorant (5+2, 5 roles), Dota 2 (position-based), eFootball (solo/team), FC 26 (platform select)
- ✅ All Phase 1 tasks completed successfully!

**Next:** Phase 2 - Backend API Enhancement

---

## PHASE 2: BACKEND API ENHANCEMENT (Days 5-7)

### API Endpoints

- [ ] **Task 2.1**: Create `GameConfigService`
  - [ ] Create `apps/tournaments/services/game_config_service.py`
  - [ ] Add `get_game_config(game_code)` method
  - [ ] Add `get_field_configs(game_code)` method
  - [ ] Add `get_role_configs(game_code)` method
  - [ ] Add caching decorator
  - **Estimated Time**: 2 hours

- [ ] **Task 2.2**: Create Game Config API endpoint
  - [ ] Create `apps/tournaments/views/api_game_config.py`
  - [ ] Add `game_config_api(request, game_code)` view
  - [ ] Return game, fields, and roles
  - [ ] Add error handling for invalid game codes
  - [ ] Add URL pattern
  - **Files**: `apps/tournaments/urls.py`
  - **Estimated Time**: 1.5 hours

- [ ] **Task 2.3**: Enhance Registration Context API
  - [ ] Modify `registration_context_api` in `registration_modern.py`
  - [ ] Add game configuration to response
  - [ ] Include field definitions
  - [ ] Include role options
  - [ ] Test with different games
  - **Estimated Time**: 2 hours

- [ ] **Task 2.4**: Enhance Auto-fill Profile Data
  - [ ] Extend `auto_fill_profile_data()` in RegistrationService
  - [ ] Add game_ids dictionary structure
  - [ ] Support multiple game IDs per user
  - [ ] Create UserGameProfile model (if needed)
  - [ ] Test data retrieval
  - **Estimated Time**: 3 hours

- [ ] **Task 2.5**: Enhance Auto-fill Team Data
  - [ ] Extend `auto_fill_team_data()` in RegistrationService
  - [ ] Include player game IDs
  - [ ] Include player roles
  - [ ] Support roster with starters + subs
  - [ ] Test with sample team data
  - **Estimated Time**: 3 hours

### Validation Enhancement

- [ ] **Task 2.6**: Create game validators module
  - [ ] Create `apps/tournaments/validators/game_validators.py`
  - [ ] Add `validate_riot_id()` function
  - [ ] Add `validate_steam_id()` function
  - [ ] Add `validate_mlbb_id()` function
  - [ ] Add validators for all game IDs
  - **Estimated Time**: 2 hours

- [ ] **Task 2.7**: Extend validation API
  - [ ] Modify `validate_registration_api` in `registration_modern.py`
  - [ ] Add game-specific validation
  - [ ] Validate field formats using regex
  - [ ] Validate team size requirements
  - [ ] Validate role assignments
  - [ ] Test with invalid data
  - **Estimated Time**: 2 hours

- [ ] **Task 2.8**: Create player data validator
  - [ ] Add `validate_player_data()` in RegistrationService
  - [ ] Check required fields per game
  - [ ] Validate role uniqueness (e.g., one IGL)
  - [ ] Validate roster size (starters + subs)
  - [ ] Return detailed error messages
  - **Estimated Time**: 2 hours

### Registration Submission

- [ ] **Task 2.9**: Update Registration model (if needed)
  - [ ] Add JSONField for player_data
  - [ ] Add migration for new field
  - [ ] Update Registration serializer
  - **Estimated Time**: 1 hour

- [ ] **Task 2.10**: Enhance registration submission
  - [ ] Modify `submit_registration_api` in `registration_modern.py`
  - [ ] Handle dynamic player data
  - [ ] Store game-specific IDs
  - [ ] Store role assignments
  - [ ] Test with Valorant data
  - [ ] Test with eFootball data
  - **Estimated Time**: 3 hours

- [ ] **Task 2.11**: Test all APIs with Postman/curl
  - [ ] Test game config API for all 8 games
  - [ ] Test enhanced context API
  - [ ] Test validation API with various inputs
  - [ ] Test submission API with complete data
  - [ ] Document API responses
  - **Estimated Time**: 2 hours

---

## PHASE 3: FRONTEND - FORM GENERATOR (Days 8-12)

### Core JavaScript Classes

- [ ] **Task 3.1**: Create `TournamentRegistrationForm` class
  - [ ] Create `static/tournaments/js/registration-wizard.js`
  - [ ] Add constructor with tournament slug
  - [ ] Add properties: currentStep, totalSteps, formData
  - [ ] Add `initialize()` method
  - [ ] Add step navigation methods
  - **Estimated Time**: 2 hours

- [ ] **Task 3.2**: Create `FieldRenderer` class
  - [ ] Create `static/tournaments/js/field-renderer.js`
  - [ ] Add `renderField(config, value)` static method
  - [ ] Support text, number, email, select, textarea types
  - [ ] Add validation attributes
  - [ ] Add help text and placeholders
  - **Estimated Time**: 3 hours

- [ ] **Task 3.3**: Create `GameValidator` class
  - [ ] Create `static/tournaments/js/game-validators.js`
  - [ ] Add regex patterns for all game IDs
  - [ ] Add `validateField(name, value, game)` method
  - [ ] Add `validateRiotId()` specific method
  - [ ] Add validators for all 8 games
  - **Estimated Time**: 2 hours

- [ ] **Task 3.4**: Create `AutoFillHandler` class
  - [ ] Create `static/tournaments/js/auto-fill-handler.js`
  - [ ] Add `fillUserProfile()` method
  - [ ] Add `fillTeamRoster()` method
  - [ ] Add `fillGameCredentials()` method
  - [ ] Handle missing data gracefully
  - **Estimated Time**: 2 hours

- [ ] **Task 3.5**: Create `PlayerRosterManager` class
  - [ ] Create `static/tournaments/js/player-roster-manager.js`
  - [ ] Add `renderPlayerCard(player, index)` method
  - [ ] Add `addSubPlayer()` method
  - [ ] Add `removeSubPlayer()` method
  - [ ] Add role validation logic
  - **Estimated Time**: 3 hours

### Step Components

- [ ] **Task 3.6**: Build Step 1 - Profile & Team Selection
  - [ ] Create profile summary card
  - [ ] Add team selector dropdown (if multiple teams)
  - [ ] Display team roster preview
  - [ ] Add edit profile button
  - [ ] Add "Next" button with validation
  - **Estimated Time**: 3 hours

- [ ] **Task 3.7**: Build Step 2 - Player Roster (Team)
  - [ ] Create starting lineup table (dynamic based on game)
  - [ ] Create substitutes table
  - [ ] Add role dropdowns per player
  - [ ] Add "Add Sub" button (up to limit)
  - [ ] Add validation for roster completeness
  - [ ] Add "Back" and "Next" buttons
  - **Estimated Time**: 4 hours

- [ ] **Task 3.8**: Build Step 2 - Solo Player Form
  - [ ] Create single player card
  - [ ] Add game-specific fields dynamically
  - [ ] Add validation
  - [ ] Show/hide based on tournament type
  - **Estimated Time**: 2 hours

- [ ] **Task 3.9**: Build Step 3 - Game Credentials
  - [ ] Loop through all players (or solo player)
  - [ ] Render game-specific fields per player
  - [ ] Add validation indicators (✓ or ✗)
  - [ ] Add format helpers and examples
  - [ ] Add "Back" and "Next" buttons
  - **Estimated Time**: 4 hours

- [ ] **Task 3.10**: Build Step 4 - Payment & Confirmation
  - [ ] Add payment method selector
  - [ ] Show payment instructions per method
  - [ ] Add payer mobile number field
  - [ ] Add transaction ID field
  - [ ] Add terms checkbox
  - [ ] Add registration summary card
  - [ ] Add "Back" and "Submit" buttons
  - **Estimated Time**: 3 hours

### Progress Wizard

- [ ] **Task 3.11**: Create progress indicator component
  - [ ] Create `templates/tournaments/components/progress_wizard.html`
  - [ ] Add step bubbles (1, 2, 3, 4)
  - [ ] Add step labels
  - [ ] Add active/completed states
  - [ ] Add CSS animations
  - **Estimated Time**: 2 hours

- [ ] **Task 3.12**: Implement step navigation
  - [ ] Add `nextStep()` method
  - [ ] Add `prevStep()` method
  - [ ] Add `goToStep(n)` method
  - [ ] Validate before allowing next
  - [ ] Update progress indicator
  - [ ] Scroll to top on step change
  - **Estimated Time**: 2 hours

### Form Assembly

- [ ] **Task 3.13**: Create main registration template
  - [ ] Create `templates/tournaments/registration_dynamic.html`
  - [ ] Add tournament header
  - [ ] Add progress wizard placeholder
  - [ ] Add step containers (4 divs)
  - [ ] Add navigation buttons
  - [ ] Include all JavaScript files
  - **Estimated Time**: 2 hours

- [ ] **Task 3.14**: Implement form initialization
  - [ ] Fetch tournament data
  - [ ] Fetch game configuration
  - [ ] Fetch user context (profile + team)
  - [ ] Determine if solo or team
  - [ ] Determine if captain or member
  - [ ] Build appropriate form
  - **Estimated Time**: 2 hours

- [ ] **Task 3.15**: Connect to backend APIs
  - [ ] Add CSRF token handling
  - [ ] Implement API call wrapper
  - [ ] Add error handling
  - [ ] Add loading states
  - [ ] Test API integration
  - **Estimated Time**: 2 hours

---

## PHASE 4: VALIDATION & ERROR HANDLING (Days 13-14)

### Client-Side Validation

- [ ] **Task 4.1**: Implement field-level validation
  - [ ] Add `blur` event listeners
  - [ ] Validate on input change
  - [ ] Show inline error messages
  - [ ] Add error styling (red border)
  - [ ] Add success indicators (green checkmark)
  - **Estimated Time**: 2 hours

- [ ] **Task 4.2**: Implement step validation
  - [ ] Validate Step 1 (profile completeness)
  - [ ] Validate Step 2 (roster completeness + roles)
  - [ ] Validate Step 3 (all game IDs)
  - [ ] Validate Step 4 (payment + terms)
  - [ ] Block "Next" button if invalid
  - **Estimated Time**: 3 hours

- [ ] **Task 4.3**: Add role validation
  - [ ] Check for duplicate unique roles (e.g., IGL)
  - [ ] Ensure all roles assigned
  - [ ] Validate role options from config
  - [ ] Show role conflict errors
  - **Estimated Time**: 2 hours

- [ ] **Task 4.4**: Add roster size validation
  - [ ] Check minimum starters met
  - [ ] Check maximum starters not exceeded
  - [ ] Check subs within limit
  - [ ] Show clear error messages
  - **Estimated Time**: 1 hour

### Server-Side Validation

- [ ] **Task 4.5**: Extend validation API endpoint
  - [ ] Add comprehensive field checks
  - [ ] Return field-specific errors
  - [ ] Return non-field errors (roster, roles)
  - [ ] Test with invalid data
  - **Estimated Time**: 2 hours

- [ ] **Task 4.6**: Add game-specific validators
  - [ ] Use validators from Task 2.6
  - [ ] Integrate with Django form validation
  - [ ] Return detailed error messages
  - [ ] Test all game ID formats
  - **Estimated Time**: 2 hours

### Error Display

- [ ] **Task 4.7**: Create error display components
  - [ ] Add inline field errors (below input)
  - [ ] Add summary error panel (top of form)
  - [ ] Add step error indicators (progress wizard)
  - [ ] Add toast notifications
  - **Estimated Time**: 2 hours

- [ ] **Task 4.8**: Implement error handling UX
  - [ ] Scroll to first error on validation fail
  - [ ] Highlight error fields
  - [ ] Show which step has errors
  - [ ] Allow clicking step to view errors
  - **Estimated Time**: 2 hours

---

## PHASE 5: AUTO-FILL SYSTEM (Days 15-17)

### User Profile Auto-fill

- [ ] **Task 5.1**: Create UserGameProfile model (optional)
  - [ ] Store user's game IDs
  - [ ] Structure: user, game_code, game_data (JSON)
  - [ ] Create migration
  - **Estimated Time**: 1.5 hours

- [ ] **Task 5.2**: Implement profile data collection
  - [ ] Fetch from UserProfile model
  - [ ] Fetch from UserGameProfile (if exists)
  - [ ] Fetch from previous registrations
  - [ ] Merge data sources
  - **Estimated Time**: 2 hours

- [ ] **Task 5.3**: Implement auto-fill on form load
  - [ ] Call auto-fill API
  - [ ] Populate form fields
  - [ ] Handle missing fields gracefully
  - [ ] Show "Auto-filled" indicator
  - **Estimated Time**: 2 hours

- [ ] **Task 5.4**: Add manual edit capability
  - [ ] Add "Edit" button next to auto-filled fields
  - [ ] Enable field on edit click
  - [ ] Track manual changes
  - [ ] Save changes to profile (optional)
  - **Estimated Time**: 2 hours

### Team Roster Auto-fill

- [ ] **Task 5.5**: Extend Team model (if needed)
  - [ ] Add game_data JSONField for game-specific info
  - [ ] Store player game IDs
  - [ ] Store player roles
  - [ ] Create migration
  - **Estimated Time**: 1.5 hours

- [ ] **Task 5.6**: Implement team roster data collection
  - [ ] Fetch team members
  - [ ] Fetch player game IDs
  - [ ] Fetch player roles
  - [ ] Order by captain first
  - **Estimated Time**: 2 hours

- [ ] **Task 5.7**: Implement roster auto-fill
  - [ ] Call team auto-fill API
  - [ ] Populate player cards
  - [ ] Assign roles automatically
  - [ ] Fill game IDs for each player
  - [ ] Handle incomplete rosters
  - **Estimated Time**: 3 hours

- [ ] **Task 5.8**: Add smart role assignment
  - [ ] Use roles from previous tournaments
  - [ ] Use roles from team profile
  - [ ] Allow captain to reassign
  - [ ] Save role preferences
  - **Estimated Time**: 2 hours

### Data Persistence

- [ ] **Task 5.9**: Implement draft save (optional)
  - [ ] Add "Save Draft" button
  - [ ] Store form data in session
  - [ ] Restore draft on return
  - [ ] Clear draft on submission
  - **Estimated Time**: 2 hours

- [ ] **Task 5.10**: Update profile on submission
  - [ ] Save game IDs to UserGameProfile
  - [ ] Update team game_data
  - [ ] Save role preferences
  - [ ] Use for future auto-fill
  - **Estimated Time**: 2 hours

---

## PHASE 6: UI/UX DESIGN (Days 18-20)

### Design System

- [ ] **Task 6.1**: Create CSS variables for theme
  - [ ] Define color palette
  - [ ] Define typography scale
  - [ ] Define spacing scale
  - [ ] Define shadows and borders
  - **File**: `static/tournaments/css/registration-form.css`
  - **Estimated Time**: 1.5 hours

- [ ] **Task 6.2**: Design player card component
  - [ ] Card layout with avatar
  - [ ] Field grouping
  - [ ] Role selector styling
  - [ ] Hover effects
  - [ ] Mobile responsive
  - **Estimated Time**: 2 hours

- [ ] **Task 6.3**: Design progress wizard
  - [ ] Step bubbles design
  - [ ] Connection lines
  - [ ] Active/completed states
  - [ ] Step labels
  - [ ] Responsive layout
  - **Estimated Time**: 2 hours

- [ ] **Task 6.4**: Design form controls
  - [ ] Input field styling
  - [ ] Select dropdown styling
  - [ ] Checkbox/radio styling
  - [ ] Button designs (primary, secondary)
  - [ ] Error state styling
  - **Estimated Time**: 2 hours

### Animations & Interactions

- [ ] **Task 6.5**: Add step transitions
  - [ ] Fade in/out between steps
  - [ ] Slide animations
  - [ ] Progress bar animation
  - [ ] Smooth scrolling
  - **Estimated Time**: 2 hours

- [ ] **Task 6.6**: Add loading states
  - [ ] Skeleton screens for data fetch
  - [ ] Spinner for API calls
  - [ ] Button loading states
  - [ ] Progress indicators
  - **Estimated Time**: 2 hours

- [ ] **Task 6.7**: Add micro-interactions
  - [ ] Input focus effects
  - [ ] Button hover effects
  - [ ] Validation success animations
  - [ ] Error shake animations
  - **Estimated Time**: 2 hours

### Responsive Design

- [ ] **Task 6.8**: Optimize for mobile (< 768px)
  - [ ] Stack form fields vertically
  - [ ] Adjust player card layout
  - [ ] Optimize touch targets
  - [ ] Test on iOS and Android
  - **Estimated Time**: 3 hours

- [ ] **Task 6.9**: Optimize for tablet (768px - 1024px)
  - [ ] 2-column layouts where appropriate
  - [ ] Optimize spacing
  - [ ] Test on iPad
  - **Estimated Time**: 2 hours

- [ ] **Task 6.10**: Optimize for desktop (> 1024px)
  - [ ] Use available space efficiently
  - [ ] Multi-column layouts
  - [ ] Side-by-side step content
  - [ ] Test on various screen sizes
  - **Estimated Time**: 2 hours

### Accessibility

- [ ] **Task 6.11**: Add keyboard navigation
  - [ ] Tab order optimization
  - [ ] Enter key submission
  - [ ] Arrow key navigation
  - [ ] Escape key to cancel
  - **Estimated Time**: 2 hours

- [ ] **Task 6.12**: Add ARIA labels
  - [ ] Form field labels
  - [ ] Button labels
  - [ ] Error announcements
  - [ ] Progress indicator labels
  - **Estimated Time**: 1.5 hours

- [ ] **Task 6.13**: Add screen reader support
  - [ ] Test with NVDA/JAWS
  - [ ] Add live regions for errors
  - [ ] Add descriptions
  - [ ] Fix any issues
  - **Estimated Time**: 2 hours

---

## PHASE 7: TESTING & QA (Days 21-23)

### Unit Tests

- [ ] **Task 7.1**: Write model tests
  - [ ] Test GameConfiguration model
  - [ ] Test GameFieldConfiguration model
  - [ ] Test PlayerRoleConfiguration model
  - [ ] Test validation methods
  - **File**: `tests/tournaments/test_game_config.py`
  - **Estimated Time**: 3 hours

- [ ] **Task 7.2**: Write service tests
  - [ ] Test GameConfigService methods
  - [ ] Test enhanced auto-fill methods
  - [ ] Test validation functions
  - [ ] Test registration submission
  - **File**: `tests/tournaments/test_registration_service.py`
  - **Estimated Time**: 3 hours

- [ ] **Task 7.3**: Write API tests
  - [ ] Test game config API
  - [ ] Test enhanced context API
  - [ ] Test validation API
  - [ ] Test submission API
  - **File**: `tests/tournaments/test_registration_api.py`
  - **Estimated Time**: 3 hours

### Integration Tests

- [ ] **Task 7.4**: Test Valorant registration flow
  - [ ] Solo player registration
  - [ ] Team captain registration (full roster)
  - [ ] Non-captain approval request
  - [ ] Payment submission
  - [ ] Verify database records
  - **Estimated Time**: 2 hours

- [ ] **Task 7.5**: Test eFootball registration flow
  - [ ] Solo player registration
  - [ ] Team registration (2+1)
  - [ ] Validate game-specific fields
  - [ ] Test payment flow
  - **Estimated Time**: 1.5 hours

- [ ] **Task 7.6**: Test MLBB registration flow
  - [ ] Team registration (5+2)
  - [ ] Role assignment validation
  - [ ] Game ID format validation
  - [ ] Complete submission
  - **Estimated Time**: 1.5 hours

- [ ] **Task 7.7**: Test error scenarios
  - [ ] Invalid game IDs
  - [ ] Incomplete roster
  - [ ] Duplicate roles
  - [ ] Payment validation
  - [ ] Capacity full
  - **Estimated Time**: 2 hours

### Browser Testing

- [ ] **Task 7.8**: Test on Chrome
  - [ ] Latest version
  - [ ] Test all features
  - [ ] Check console for errors
  - **Estimated Time**: 1.5 hours

- [ ] **Task 7.9**: Test on Firefox
  - [ ] Latest version
  - [ ] Test all features
  - [ ] Check console for errors
  - **Estimated Time**: 1.5 hours

- [ ] **Task 7.10**: Test on Safari
  - [ ] macOS Safari
  - [ ] iOS Safari
  - [ ] Test all features
  - **Estimated Time**: 1.5 hours

- [ ] **Task 7.11**: Test on Edge
  - [ ] Latest version
  - [ ] Test all features
  - **Estimated Time**: 1 hour

- [ ] **Task 7.12**: Test on mobile browsers
  - [ ] Chrome Mobile (Android)
  - [ ] Safari Mobile (iOS)
  - [ ] Test touch interactions
  - [ ] Test responsive layout
  - **Estimated Time**: 2 hours

### Performance Testing

- [ ] **Task 7.13**: Test form load time
  - [ ] Measure initial page load
  - [ ] Measure API response times
  - [ ] Optimize slow areas
  - [ ] Target < 2 seconds
  - **Estimated Time**: 2 hours

- [ ] **Task 7.14**: Test with large rosters
  - [ ] Test with 7+ player teams
  - [ ] Check rendering performance
  - [ ] Check validation speed
  - [ ] Optimize if needed
  - **Estimated Time**: 1.5 hours

### User Acceptance Testing

- [ ] **Task 7.15**: UAT with stakeholders
  - [ ] Demonstrate all game types
  - [ ] Get feedback on UI/UX
  - [ ] Note requested changes
  - [ ] Prioritize fixes
  - **Estimated Time**: 3 hours

- [ ] **Task 7.16**: Fix UAT issues
  - [ ] Implement high-priority fixes
  - [ ] Re-test
  - [ ] Get approval
  - **Estimated Time**: 4 hours (variable)

---

## PHASE 8: DEPLOYMENT & DOCUMENTATION (Days 24-25)

### Pre-Deployment

- [ ] **Task 8.1**: Run all migrations on staging
  - [ ] Apply game config migrations
  - [ ] Run seed command
  - [ ] Verify data integrity
  - **Estimated Time**: 1 hour

- [ ] **Task 8.2**: Deploy to staging environment
  - [ ] Push code to staging branch
  - [ ] Run collectstatic
  - [ ] Restart services
  - [ ] Smoke test
  - **Estimated Time**: 1 hour

- [ ] **Task 8.3**: Full regression test on staging
  - [ ] Test all 8 game types
  - [ ] Test payment flow
  - [ ] Test admin interface
  - [ ] Test existing features (ensure no breaks)
  - **Estimated Time**: 3 hours

### Feature Flag Setup

- [ ] **Task 8.4**: Implement feature flag
  - [ ] Add `ENABLE_DYNAMIC_REGISTRATION` setting
  - [ ] Update URL routing to check flag
  - [ ] Test flag on/off states
  - **Estimated Time**: 1 hour

- [ ] **Task 8.5**: Implement A/B testing (optional)
  - [ ] Route 10% of users to new form
  - [ ] Track conversion rates
  - [ ] Compare old vs new
  - **Estimated Time**: 2 hours

### Documentation

- [ ] **Task 8.6**: Write admin guide
  - [ ] How to configure games
  - [ ] How to add new games
  - [ ] How to modify field configs
  - [ ] How to add new roles
  - **File**: `docs/admin/game-configuration-guide.md`
  - **Estimated Time**: 2 hours

- [ ] **Task 8.7**: Write organizer guide
  - [ ] How to select game for tournament
  - [ ] What fields are required
  - [ ] How to review registrations
  - **File**: `docs/organizers/registration-guide.md`
  - **Estimated Time**: 1.5 hours

- [ ] **Task 8.8**: Update API documentation
  - [ ] Document new endpoints
  - [ ] Document request/response formats
  - [ ] Add code examples
  - **File**: Update `TOURNAMENT_REGISTRATION_DOCUMENTATION.md`
  - **Estimated Time**: 2 hours

- [ ] **Task 8.9**: Write user guide
  - [ ] How to register (with screenshots)
  - [ ] How to fill game IDs
  - [ ] Common issues and solutions
  - **File**: `docs/users/registration-user-guide.md`
  - **Estimated Time**: 2 hours

### Production Deployment

- [ ] **Task 8.10**: Create deployment checklist
  - [ ] Database backup
  - [ ] Migration plan
  - [ ] Rollback plan
  - [ ] Monitoring setup
  - **Estimated Time**: 1 hour

- [ ] **Task 8.11**: Deploy to production
  - [ ] Schedule maintenance window
  - [ ] Run migrations
  - [ ] Deploy code
  - [ ] Run collectstatic
  - [ ] Restart services
  - [ ] Verify health checks
  - **Estimated Time**: 2 hours

- [ ] **Task 8.12**: Post-deployment verification
  - [ ] Test registration for each game
  - [ ] Monitor error logs
  - [ ] Check performance metrics
  - [ ] Verify payment flow
  - **Estimated Time**: 2 hours

### Monitoring & Support

- [ ] **Task 8.13**: Set up monitoring
  - [ ] Add logging for registration events
  - [ ] Set up error alerts
  - [ ] Monitor API response times
  - [ ] Track registration conversion rates
  - **Estimated Time**: 2 hours

- [ ] **Task 8.14**: Create support runbook
  - [ ] Common issues and fixes
  - [ ] How to debug registration errors
  - [ ] How to manually fix registrations
  - [ ] Emergency contacts
  - **Estimated Time**: 1.5 hours

---

## 🎯 PRIORITY CHECKPOINTS

### Checkpoint 1: After Phase 1 (Day 4)
- ✅ All 8 games configured in database
- ✅ Admin interface functional
- ✅ Can view and edit game configs

### Checkpoint 2: After Phase 2 (Day 7)
- ✅ All APIs returning correct data
- ✅ Auto-fill working for sample data
- ✅ Validation logic tested

### Checkpoint 3: After Phase 3 (Day 12)
- ✅ Form renders dynamically for all games
- ✅ Can navigate through all steps
- ✅ Can submit registration

### Checkpoint 4: After Phase 5 (Day 17)
- ✅ Auto-fill working from real data
- ✅ Team roster populates correctly
- ✅ Form saves and restores state

### Checkpoint 5: After Phase 7 (Day 23)
- ✅ All tests passing
- ✅ Browser compatibility confirmed
- ✅ Performance targets met
- ✅ UAT approved

### Checkpoint 6: After Phase 8 (Day 25)
- ✅ Deployed to production
- ✅ Monitoring active
- ✅ Documentation complete
- ✅ Support team trained

---

## 📈 PROGRESS TRACKING

### Week 1 (Days 1-5)
**Target:** Complete Phase 1 + Start Phase 2  
**Deliverables:** Database models, seed data, admin interface, API enhancements started

### Week 2 (Days 6-12)
**Target:** Complete Phase 2-3  
**Deliverables:** All APIs functional, dynamic form working

### Week 3 (Days 13-19)
**Target:** Complete Phase 4-6  
**Deliverables:** Validation complete, auto-fill working, UI polished

### Week 4 (Days 20-25)
**Target:** Complete Phase 7-8  
**Deliverables:** Testing done, deployed to production, documented

---

## 🚨 RISK MITIGATION

| Task | Risk Level | Mitigation |
|------|-----------|-----------|
| Seed data quality | Medium | Manual review + test registrations |
| Auto-fill conflicts | Medium | Fallback to manual entry |
| Browser compatibility | Low | Use standard JS + test early |
| Performance with large rosters | Low | Test with max team size |
| Production deployment | Medium | Thorough staging test + feature flag |

---

## ✅ COMPLETION CRITERIA

**Project is complete when:**
- ✅ All 135 tasks checked off
- ✅ All 8 game types fully functional
- ✅ All tests passing (100% critical paths)
- ✅ Browser compatibility confirmed
- ✅ UAT approved by stakeholders
- ✅ Deployed to production successfully
- ✅ Documentation complete and reviewed
- ✅ Monitoring active and alerts configured
- ✅ Zero critical bugs in first week post-launch

---

**Total Tasks:** 135  
**Estimated Total Hours:** 160-200 hours  
**Estimated Duration:** 20-25 working days (4-5 weeks)

**Ready to start? Mark Task 1.1 as complete and let's build this! 🚀**

