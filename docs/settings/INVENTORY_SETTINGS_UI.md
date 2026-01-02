# Inventory Settings UI Documentation

**Date**: January 2, 2026
**Status**: ✅ **OPERATIONAL (BETA)** - Phase 3A Complete
**Location**: Settings Control Deck → Inventory Tab
**Test Status**: 19/19 passing

---

## Overview

The Inventory & Trade feature allows users to:
1. View their owned items
2. Gift items to other users
3. Propose trades with other users

**Implementation Status**: Backend fully operational (Phase 3A complete), UI enabled with Beta badge indicating production-ready with potential rough edges.

---

## Backend Endpoints

### 1. My Inventory (GET)
**URL**: `/me/inventory/`  
**URL Name**: `economy:my_inventory`  
**View Function**: `apps.economy.inventory_api.my_inventory_view`  
**Authentication**: Required (`@login_required`, `@csrf_protect`)  
**Permissions**: User must be authenticated  

**Response Format**:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "item_slug": "awp-dragon-lore",
        "item_name": "AWP | Dragon Lore",
        "quantity": 1,
        "rarity": "LEGENDARY",
        "acquired_from": "Bounty Reward",
        "acquired_at": "2025-12-15T10:30:00Z",
        "is_locked": false,
        "can_gift": true,
        "can_trade": true
      }
    ]
  }
}
```

**Error Responses**:
- 401: Not authenticated
- 500: Server error

---

### 2. User Inventory (GET)
**URL**: `/profiles/<username>/inventory/`  
**URL Name**: `economy:user_inventory`  
**View Function**: `apps.economy.inventory_api.user_inventory_view`  
**Authentication**: Required  
**Permissions**: Enforced by `inventory_visibility` field (PUBLIC/FRIENDS/PRIVATE)

**Privacy Logic**:
```python
# From apps/economy/inventory_services.py
def can_view_inventory(viewer, profile_owner):
    if viewer == profile_owner:
        return True  # Always see your own
    
    visibility = profile_owner.privacy_settings.inventory_visibility
    
    if visibility == 'PUBLIC':
        return True
    elif visibility == 'FRIENDS':
        return profile_owner.followers.filter(id=viewer.id).exists()
    else:  # PRIVATE
        return False
```

**Response Format**: Same as My Inventory endpoint

**Error Responses**:
- 401: Not authenticated
- 403: Privacy settings block access
- 404: User not found

---

### 3. Gift Item (POST)
**URL**: `/me/inventory/gift/`  
**URL Name**: `economy:gift_item`  
**View Function**: `apps.economy.inventory_api.gift_item_view`  
**Authentication**: Required  
**Content-Type**: `application/json`

**Request Payload**:
```json
{
  "recipient_username": "target_user",
  "item_slug": "awp-dragon-lore",
  "quantity": 1,
  "message": "Congrats on the win!" // Optional
}
```

**Validation Rules**:
- Sender must own sufficient quantity
- Item must be giftable (`can_gift=true`)
- Item must not be locked (`is_locked=false`)
- Recipient user must exist
- Cannot gift to yourself

**Response Format**:
```json
{
  "success": true,
  "message": "Gift request created successfully",
  "data": {
    "gift_id": 123,
    "status": "PENDING",
    "recipient": "target_user",
    "item": "awp-dragon-lore",
    "quantity": 1
  }
}
```

**Error Responses**:
- 400: Invalid payload, insufficient quantity, locked item, self-gift
- 401: Not authenticated
- 404: Recipient not found, item not found

---

### 4. Trade Request (POST)
**URL**: `/me/inventory/trade/request/`  
**URL Name**: `economy:trade_request`  
**View Function**: `apps.economy.inventory_api.trade_request_view`  
**Authentication**: Required  
**Content-Type**: `application/json`

**Request Payload**:
```json
{
  "target_username": "other_user",
  "offered_item_slug": "m4a4-howl",
  "offered_quantity": 1,
  "requested_item_slug": "awp-dragon-lore",  // Optional (null = item-for-nothing)
  "requested_quantity": 1,                    // Optional (ignored if requested_item_slug is null)
  "message": "Fair trade?"                    // Optional
}
```

**Validation Rules**:
- Sender must own offered item in sufficient quantity
- Offered item must be tradable (`can_trade=true`)
- Offered item must not be locked
- If `requested_item_slug` provided: target must own it in sufficient quantity
- Cannot trade with yourself

**Trade Types**:
1. **Item-for-Item**: Both `offered_item_slug` and `requested_item_slug` provided
2. **Item-for-Nothing**: Only `offered_item_slug` provided (gift-like but requires acceptance)

**Response Format**:
```json
{
  "success": true,
  "message": "Trade request created successfully",
  "data": {
    "trade_id": 456,
    "status": "PENDING",
    "target": "other_user",
    "offered_item": "m4a4-howl",
    "requested_item": "awp-dragon-lore",
    "expires_at": "2026-01-09T12:00:00Z"  // 7 days
  }
}
```

**Error Responses**:
- 400: Invalid payload, insufficient quantity, locked item, non-tradable item, self-trade
- 401: Not authenticated
- 404: Target user not found, item not found

---

### 5. Trade Respond (POST)
**URL**: `/me/inventory/trade/respond/`  
**URL Name**: `economy:trade_respond`  
**View Function**: `apps.economy.inventory_api.trade_respond_view`  
**Authentication**: Required  
**Content-Type**: `application/json`

**Request Payload**:
```json
{
  "trade_id": 456,
  "action": "accept"  // or "decline"
}
```

**Validation Rules**:
- Trade must exist and be in PENDING status
- User must be the target of the trade (not the creator)
- Both parties must still own their respective items (if accepting)

**On Accept**:
- Items are swapped between users
- Trade status → ACCEPTED
- Transaction recorded in `apps.economy.models.Transaction`

**On Decline**:
- Trade status → DECLINED
- No items moved

**Response Format**:
```json
{
  "success": true,
  "message": "Trade accepted successfully",
  "data": {
    "trade_id": 456,
    "status": "ACCEPTED"
  }
}
```

**Error Responses**:
- 400: Invalid action, trade already resolved, insufficient items
- 401: Not authenticated
- 403: Not the trade target
- 404: Trade not found

---

## UI Components

### Location
**Template**: `templates/user_profile/profile/settings_control_deck.html`  
**Lines**: 614-663  
**Tab ID**: `#tab-inventory`

### Components

#### 1. My Inventory Viewer
**HTML Lines**: 619-625  
**Container ID**: `#inventory-list`  
**JavaScript**: `loadInventory()` (line 1810)  
**Auto-load**: Called in DOMContentLoaded (line 1951)

**Behavior**:
- Fetches from `{% url "economy:my_inventory" %}` on page load
- Renders items with name, quantity, rarity, acquired source
- Shows "No items in inventory" if empty
- Shows error message if fetch fails

**Item Display Format**:
```html
<div class="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10">
    <div>
        <div class="font-bold text-white">[Item Name]</div>
        <div class="text-xs text-gray-400">Qty: [X] | Rarity: [RARITY]</div>
    </div>
    <div class="text-xs text-gray-500">[Acquired From]</div>
</div>
```

---

#### 2. Gift Item Form
**HTML Lines**: 627-640  
**Form ID**: `#gift-form`  
**Submit Handler**: `sendGift(event)` (line 1839)  
**onsubmit**: `sendGift(event)` (line 629)

**Fields**:
- `recipient_username` (text, required) - Target user
- `item_slug` (text, required) - Item identifier (e.g., "awp-dragon-lore")
- `quantity` (number, required) - Amount to gift (min: 1)
- `message` (textarea, optional) - Gift message

**Submit Behavior**:
1. Prevent default form submission
2. Show loading state on button (`<i class="fa-solid fa-spinner fa-spin"></i> Sending...`)
3. Collect form data into JSON object
4. POST to `{% url "economy:gift_item" %}` with CSRF token
5. On success:
   - Show success toast
   - Reset form
   - Reload inventory (`loadInventory()`)
6. On error:
   - Show error toast
   - Keep form data

**Error Handling**:
- Network errors caught with try/catch
- Backend validation errors displayed via toast
- Button restored to original state in finally block

---

#### 3. Trade Request Form
**HTML Lines**: 642-660  
**Form ID**: `#trade-form`  
**Submit Handler**: `proposeTrade(event)` (line 1882)  
**onsubmit**: `proposeTrade(event)` (line 644)

**Fields**:
- `target_username` (text, required) - Trade partner
- `offered_item_slug` (text, required) - Your item slug
- `offered_quantity` (number, required) - Your item quantity (min: 1)
- `requested_item_slug` (text, optional) - Their item slug (can be null for item-for-nothing)
- `requested_quantity` (number, optional) - Their item quantity (ignored if requested item null)
- `message` (textarea, optional) - Trade message

**Submit Behavior**:
1. Prevent default form submission
2. Show loading state on button
3. Collect form data (includes null handling for requested item)
4. POST to `{% url "economy:trade_request" %}` with CSRF token
5. On success:
   - Show success toast
   - Reset form
   - Reload inventory
6. On error:
   - Show error toast
   - Keep form data

**Special Handling**:
- Allows `requested_item_slug` to be null (item-for-nothing trade)
- Validates non-empty strings before including in payload

---

## JavaScript Functions

### loadInventory()
**Location**: Line 1810  
**Purpose**: Fetch and display user's inventory  
**Triggered**: DOMContentLoaded (page init)

```javascript
async function loadInventory() {
    const container = document.getElementById('inventory-list');
    if (!container) return;
    
    try {
        const response = await fetch('{% url "economy:my_inventory" %}', {
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        });
        const result = await response.json();
        
        if (result.success && result.data.items.length > 0) {
            container.innerHTML = result.data.items.map(item => `...`).join('');
        } else {
            container.innerHTML = '<p class="text-sm text-gray-500">No items in inventory.</p>';
        }
    } catch (error) {
        container.innerHTML = '<p class="text-sm text-red-400">Failed to load inventory.</p>';
        console.error('Inventory load error:', error);
    }
}
```

---

### sendGift(event)
**Location**: Line 1839  
**Purpose**: Submit gift request  
**Triggered**: Gift form submit

```javascript
async function sendGift(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const originalHTML = button.innerHTML;
    
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    
    const data = {
        recipient_username: form.recipient_username.value,
        item_slug: form.item_slug.value,
        quantity: parseInt(form.quantity.value),
        message: form.message.value
    };
    
    try {
        const response = await fetch('{% url "economy:gift_item" %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (result.success) {
            showToast('Gift sent successfully', 'success');
            form.reset();
            loadInventory();
        } else {
            showToast(result.error || 'Failed to send gift', 'error');
        }
    } catch (error) {
        showToast('Network error', 'error');
        console.error('Gift error:', error);
    } finally {
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}
```

---

### proposeTrade(event)
**Location**: Line 1882  
**Purpose**: Submit trade request  
**Triggered**: Trade form submit

```javascript
async function proposeTrade(event) {
    event.preventDefault();
    const form = event.target;
    const button = form.querySelector('button[type="submit"]');
    const originalHTML = button.innerHTML;
    
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Proposing...';
    
    const data = {
        target_username: form.target_username.value,
        offered_item_slug: form.offered_item_slug.value,
        offered_quantity: parseInt(form.offered_quantity.value),
        requested_item_slug: form.requested_item_slug.value || null,
        requested_quantity: form.requested_item_slug.value ? parseInt(form.requested_quantity.value) : null,
        message: form.message.value
    };
    
    try {
        const response = await fetch('{% url "economy:trade_request" %}', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        
        if (result.success) {
            showToast('Trade request sent', 'success');
            form.reset();
            loadInventory();
        } else {
            showToast(result.error || 'Failed to propose trade', 'error');
        }
    } catch (error) {
        showToast('Network error', 'error');
        console.error('Trade error:', error);
    } finally {
        button.disabled = false;
        button.innerHTML = originalHTML;
    }
}
```

---

## Database Models

### InventoryItem
**File**: `apps/economy/models.py:672`  
**Purpose**: Master catalog of all available items

**Key Fields**:
- `slug` (CharField, unique) - Item identifier
- `name` (CharField) - Display name
- `rarity` (CharField) - COMMON/UNCOMMON/RARE/EPIC/LEGENDARY
- `can_gift` (BooleanField, default=True)
- `can_trade` (BooleanField, default=True)
- `description` (TextField)

---

### UserInventoryItem
**File**: `apps/economy/models.py:776`  
**Purpose**: Tracks user ownership

**Key Fields**:
- `user` (ForeignKey → User)
- `item` (ForeignKey → InventoryItem)
- `quantity` (IntegerField, default=1)
- `acquired_from` (CharField) - "Bounty Reward", "Purchase", "Gift", "Trade"
- `acquired_at` (DateTimeField)
- `is_locked` (BooleanField, default=False) - Prevents gift/trade

---

### GiftRequest
**File**: `apps/economy/models.py:862`  
**Purpose**: One-way item transfers

**Key Fields**:
- `sender` (ForeignKey → User)
- `recipient` (ForeignKey → User)
- `item` (ForeignKey → InventoryItem)
- `quantity` (IntegerField)
- `status` (CharField) - PENDING/ACCEPTED/DECLINED/EXPIRED
- `message` (TextField, optional)
- `created_at` (DateTimeField)
- `expires_at` (DateTimeField) - 7 days default

**Lifecycle**:
1. PENDING → ACCEPTED (recipient accepts, item transferred)
2. PENDING → DECLINED (recipient rejects, no transfer)
3. PENDING → EXPIRED (7 days pass, auto-expire)

---

### TradeRequest
**File**: `apps/economy/models.py:979`  
**Purpose**: Two-way item swaps

**Key Fields**:
- `creator` (ForeignKey → User)
- `target` (ForeignKey → User)
- `offered_item` (ForeignKey → InventoryItem)
- `offered_quantity` (IntegerField)
- `requested_item` (ForeignKey → InventoryItem, null=True) - Null = item-for-nothing
- `requested_quantity` (IntegerField, null=True)
- `status` (CharField) - PENDING/ACCEPTED/DECLINED/EXPIRED
- `message` (TextField, optional)
- `created_at` (DateTimeField)
- `expires_at` (DateTimeField) - 7 days default

**Lifecycle**:
1. PENDING → ACCEPTED (target accepts, items swapped)
2. PENDING → DECLINED (target rejects, no swap)
3. PENDING → EXPIRED (7 days pass, auto-expire)

---

## Privacy Settings

### Field: inventory_visibility
**Model**: `apps.accounts.models.PrivacySettings`  
**Choices**: PUBLIC, FRIENDS, PRIVATE  
**Default**: PUBLIC

**Enforcement**:
```python
# From apps/economy/inventory_services.py
def can_view_inventory(viewer, profile_owner):
    if viewer == profile_owner:
        return True  # Owner always sees own inventory
    
    visibility = profile_owner.privacy_settings.inventory_visibility
    
    if visibility == 'PUBLIC':
        return True  # Anyone can see
    elif visibility == 'FRIENDS':
        # Check if viewer follows profile_owner
        return profile_owner.followers.filter(id=viewer.id).exists()
    else:  # PRIVATE
        return False  # Only owner
```

**UI Control**:
- Location: Privacy Tab → Inventory Visibility form (line 583)
- Auto-saves via `savePrivacy()` function
- Select dropdown with 3 options

---

## Testing

### Test Suite
**File**: `apps/economy/tests/test_phase3a_inventory.py`  
**Status**: ✅ **19/19 PASSING**

**Test Classes**:
1. **InventoryModelTest** (3 tests)
   - Item creation
   - Locked items prevent gift/trade
   - Ownership tracking

2. **InventoryAPITest** (3 tests)
   - Auth required for my_inventory
   - My inventory returns items
   - Privacy enforcement for user_inventory

3. **InventoryVisibilityTest** (3 tests)
   - PUBLIC visible to anyone
   - FRIENDS respects follow status
   - PRIVATE only visible to owner

4. **GiftingTest** (6 tests)
   - Gift creation succeeds
   - Gift accept transfers items
   - Insufficient quantity fails
   - Locked item fails
   - Non-giftable item fails
   - Self-gift fails

5. **TradingTest** (4 tests)
   - Trade creation succeeds
   - Trade accept swaps items
   - Non-tradable item fails
   - Self-trade fails

**Run Command**:
```bash
python manage.py test apps.economy.tests.test_phase3a_inventory --keepdb -v 2
```

---

## Known Limitations

1. **No Accept/Decline UI in Settings**: Users can send gifts/trades but cannot respond to incoming requests via Settings page. Requires dedicated Inventory page (`/me/inventory/`) with full UI (future enhancement).

2. **No Trade History**: Past transactions not visible in Settings Control Deck.

3. **No Search/Filter**: Cannot search or filter inventory items. Shows all items linearly.

4. **No Item Details Modal**: Clicking items doesn't show detailed information (description, acquisition date, etc.).

5. **Manual Refresh Required**: After sending gift/trade, inventory reloads, but user must manually check if they received items (no real-time notifications).

---

## Future Enhancements

### Phase 3C Enhancements (Proposed)
1. **Dedicated Inventory Page** (`/me/inventory/`)
   - Full CRUD for gifts/trades
   - Accept/Decline UI
   - Trade history
   - Search/filter/sort
   - Item detail modals

2. **Real-Time Updates**
   - WebSocket notifications for incoming gifts/trades
   - Live inventory updates

3. **Inventory Analytics**
   - Total value tracking
   - Rarity distribution charts
   - Acquisition source breakdown

4. **Batch Operations**
   - Multi-item gifts
   - Bulk item management

---

## Conclusion

The Inventory & Trade feature is **production-ready** with a minimal MVP implementation in Settings Control Deck. Backend is complete (19/19 tests passing), all endpoints operational, and privacy enforcement functional. The Beta badge accurately represents the feature's status: fully functional but with room for UI/UX polish.

**Recommendation**: Keep Beta badge until Phase 3C enhancements (dedicated inventory page with advanced UI) are implemented.
