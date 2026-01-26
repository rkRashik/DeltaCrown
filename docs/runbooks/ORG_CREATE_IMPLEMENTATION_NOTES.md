# Organization Create Implementation Notes (P3-T7)

**Status**: ✅ Phase B Complete - Full backend integration with pixel-perfect UI

## Routes

### UI View
- **URL**: `/orgs/create/`
- **Name**: `organizations:org_create`
- **Auth**: Required (`@login_required`)
- **Template**: `templates/organizations/org/org_create.html`
- **JavaScript**: `static/organizations/org/org_create.js`

### API Endpoints

#### Validation Endpoints (GET)
- `/api/vnext/organizations/validate-name/?name=<name>`
- `/api/vnext/organizations/validate-badge/?badge=<badge>` (ticker/tag)
- `/api/vnext/organizations/validate-slug/?slug=<slug>`

**Response Pattern** (Hub-style):
```json
{
  "ok": true,
  "available": true
}
```

**Error Response**:
```json
{
  "ok": false,
  "available": false,
  "field_errors": {
    "name": "Error message here"
  }
}
```

#### Creation Endpoint (POST)
- `/api/vnext/organizations/create/`
- **Content-Type**: `multipart/form-data` (for logo/banner uploads)
- **Auth**: Required

**Success Response**:
```json
{
  "ok": true,
  "data": {
    "organization_id": 123,
    "organization_slug": "my-org",
    "organization_url": "/orgs/my-org/"
  }
}
```

## Field Mapping

### Organization Model Fields
- `name` → Organization.name (required, unique, case-insensitive)
- `slug` → Organization.slug (auto-generated from name if not provided)
- `badge` → Organization.badge (ticker/tag text for now)
- `description` → Organization.description (manifesto/mission)
- `website` → Organization.website
- `twitter` → Organization.twitter
- `logo` → Organization.logo (ImageField)
- `banner` → Organization.banner (ImageField)
- `ceo` → Set to request.user automatically

### OrganizationProfile Model Fields (New)
**Step 2: Operations**
- `founded_year` → OrganizationProfile.founded_year
- `organization_type` → OrganizationProfile.organization_type (club/pro/guild)
- `hq_city` → OrganizationProfile.hq_city
- `hq_address` → OrganizationProfile.hq_address (for Pro orgs)
- `business_email` → OrganizationProfile.business_email (for Pro orgs)
- `trade_license` → OrganizationProfile.trade_license
- `discord_link` → OrganizationProfile.discord_link
- `instagram` → OrganizationProfile.instagram
- `facebook` → OrganizationProfile.facebook
- `youtube` → OrganizationProfile.youtube
- `region_code` → OrganizationProfile.region_code (ISO country code)

**Step 3: Treasury**
- `currency` → OrganizationProfile.currency (BDT/USD)
- `payout_method` → OrganizationProfile.payout_method (mobile/bank)

**Step 4: Branding**
- `brand_color` → OrganizationProfile.brand_color (hex code)

## Wizard Steps

1. **Identity**: Name, ticker, slug, manifesto
2. **Operations**: Type, location, socials
3. **Treasury**: Payout method, currency
4. **Branding**: Logo, banner, colors
5. **Ratification**: Terms acceptance

## Database Tables

### Created in Migration `0004_create_organization_profile`
- `organizations_organizationprofile`
  - OneToOne to Organization
  - Stores extended metadata

### Auto-created Records
1. **Organization** (core model)
2. **OrganizationProfile** (extended metadata)
3. **OrganizationMembership** (user as CEO)

## Testing

### Run All Tests
```bash
pytest apps/organizations/tests/test_org_create_endpoints.py -v
```

### Test Coverage
- 20 tests across 4 test classes
- Validation endpoints (name, badge, slug)
- Creation endpoint (success + failure cases)
- Field validation
- Authentication requirements
- Auto-slug generation
- Duplicate prevention

## Frontend Features

### Live Preview
- Certificate dossier updates in real-time as user types
- Logo preview on file upload
- Banner preview on file upload
- Brand color preview

### Validation
- Debounced validation (300ms delay)
- Name uniqueness check (case-insensitive)
- Slug uniqueness check
- Visual feedback (green border = available, red border = taken)

### Error Handling
- Field errors navigate to correct step
- Inline error messages below fields
- Form prevents submission without terms acceptance

## Production Checklist

- ✅ Pixel-perfect UI parity with design
- ✅ All 5 wizard steps functional
- ✅ Live dossier preview
- ✅ CSRF protection
- ✅ Form validation (frontend + backend)
- ✅ Debounced API calls
- ✅ Image upload support
- ✅ CEO membership auto-created
- ✅ Comprehensive tests (20 tests)
- ✅ Hub-style API responses
- ✅ Zero legacy dependencies
- ✅ Modular architecture

## Files Modified/Created

### Created
- `templates/organizations/org/org_create.html` (726 lines)
- `static/organizations/org/org_create.js` (357 lines)
- `apps/organizations/models/organization_profile.py` (128 lines)
- `apps/organizations/constants/regions.py` (53 lines)
- `apps/organizations/tests/test_org_create_endpoints.py` (388 lines)
- `apps/organizations/migrations/0004_create_organization_profile.py`

### Modified
- `apps/organizations/views/org.py` (added `org_create` view)
- `apps/organizations/api/views.py` (added 4 new endpoints, +368 lines)
- `apps/organizations/api/urls.py` (added 4 new routes)
- `apps/organizations/views/__init__.py` (exported `org_create`)
- `apps/organizations/models/__init__.py` (exported `OrganizationProfile`)

## Next Steps (Optional Enhancements)

1. **Email Verification**: Send verification email for business_email
2. **Document Upload**: Allow trade license document upload
3. **Brand Kit**: Additional brand assets (fonts, colors, guidelines)
4. **Preview Mode**: Preview organization page before submission
5. **Multi-step Progress Save**: Save draft between steps
6. **Org Type-specific Validation**: Different rules for club vs pro vs guild

---

**Implementation Date**: 2026-01-26  
**Phase**: P3-T7 Organization Create  
**Status**: ✅ Ready for testing at `/orgs/create/`
