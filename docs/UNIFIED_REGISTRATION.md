# Unified Tournament Registration System

## Overview

The new unified tournament registration system implements a streamlined registration process for both individual (1v1) and team-based tournaments, exactly as specified in your requirements.

## Key Features

### 1. Authentication Check ✅
- All registration attempts require user authentication
- Unauthenticated users are redirected to the login page
- Cannot proceed without being signed in

### 2. Tournament Type Determination & Team Check ✅

#### A) 1v1 (Solo) Tournament Flow
- User is directed to a dynamic registration form
- Form includes:
  - Pre-filled data from user profile (name, email)
  - Organizer-defined custom fields (in-game ID, agreement to rules)
  - Payment information if tournament has entry fee

#### B) Team Tournament Flow
- **Team Membership Check**: System checks if user is already in a team
- **IF user IS in a team**:
  - Checks if team is already registered
  - **Already registered**: Shows "Already Registered" status page
  - **Not registered**: Captain can register the team (non-captains get error message)
- **IF user is NOT in a team**:
  - Shows team creation form
  - Option to "Save as permanent team" or register with temporary details
  - Upon submission, creates team profile and assigns user as captain

### 3. Payment Integration ✅
- Payment details dynamically pulled from tournament settings
- Supports multiple payment methods (bKash, Nagad, Rocket, Bank Transfer)
- Shows payment instructions and gateway information from admin configuration
- Validates payment information before submission

## Implementation Details

### Files Created/Modified

1. **apps/tournaments/views/registration_unified.py** - Main unified registration view
2. **templates/tournaments/unified_register.html** - Registration form template
3. **templates/tournaments/registration_status.html** - Status page template
4. **apps/tournaments/urls.py** - Added unified registration URL
5. **tests/test_unified_registration.py** - Comprehensive test suite

### URL Structure

- New URL: `/tournaments/register-new/<slug>/` 
- Original URL still works: `/tournaments/register/<slug>/`

### Key Functions

- `_get_user_team()` - Checks user's team membership and captain status
- `_is_team_tournament()` - Determines if tournament requires teams
- `_check_team_registration_status()` - Validates team registration status
- `_get_organizer_fields()` - Extracts custom fields from tournament settings
- `_create_team_for_user()` - Creates new team during registration
- `_process_registration()` - Handles actual registration creation

### Dynamic Form Generation

The form adapts based on:
- Tournament type (solo vs team)
- User's team status
- Organizer requirements (custom fields)
- Payment configuration
- Entry fee amount

### Team Creation Logic

When a user has no team:
- Shows team creation fields
- Option to create permanent team or just register
- If "Save as permanent team" is checked:
  - Creates Team record
  - Creates TeamMembership record with CAPTAIN role
  - Links team to tournament registration
- If not checked, registers with temporary team name only

### Payment Handling

- Validates payment fields for paid tournaments
- Creates PaymentVerification records for admin review
- Supports all configured payment methods
- Shows appropriate payment instructions

### Status Management

The system handles various registration states:
- **Not registered**: Shows registration form
- **Already registered**: Shows status page with link back to tournament
- **Team not registered**: Captain can register team
- **Non-captain trying to register**: Error message

## Benefits

1. **Streamlined UX**: Single flow handles all registration scenarios
2. **Team-Aware**: Intelligent team detection and creation
3. **Organizer Control**: Dynamic fields based on admin configuration
4. **Payment Integration**: Seamless payment collection and verification
5. **Status Transparency**: Clear feedback on registration status
6. **Security**: Proper authentication and authorization checks

## Testing

Comprehensive test suite covers:
- Authentication requirements
- Solo vs team tournament flows
- Team creation during registration
- Payment validation
- Already registered status
- Free tournament handling

## Migration Path

The new system is deployed alongside the existing registration system:
- Original URLs continue to work
- New URLs provide enhanced functionality
- Gradual migration possible by updating links to use new URLs

## Usage

To use the new system, update tournament links to point to:
```
{% url 'tournaments:unified_register' slug=tournament.slug %}
```

Instead of:
```
{% url 'tournaments:register' slug=tournament.slug %}
```

The new system provides a much better user experience and handles all the edge cases you specified in your requirements.