# Template Filter Fix - Registration Page

## Issue Fixed
**Date**: October 2, 2025  
**Error**: `TemplateSyntaxError: Invalid filter: 'div'`  
**Location**: `/tournaments/register-modern/<slug>/`

## Problem
The `modern_register.html` template was using the `|div` filter on line 41:
```django
{{ context.registration_closes_in.seconds|div:3600 }}h
```

However, the template wasn't loading the `dict_extras` template tag library that contains the custom `div` filter.

## Solution
Added the missing template tag load at the top of the template:

```django
{% load dict_extras %}
```

## Custom Filters Available

The `dict_extras` template tag library provides these custom filters:

### 1. `div` - Division
```django
{{ value|div:divisor }}
```
**Example**: `{{ 7200|div:3600 }}` → `2.0`

### 2. `mul` - Multiplication
```django
{{ value|mul:multiplier }}
```
**Example**: `{{ 50|mul:2 }}` → `100`

### 3. `get_item` - Dictionary Access
```django
{{ dict|get_item:"key" }}
```
**Example**: `{{ my_dict|get_item:"name" }}` → value of `my_dict['name']`

## Where These Filters Are Used

### `div` filter:
- `templates/tournaments/modern_register.html` - Calculate hours from seconds
- `templates/teams/_stats_blocks.html` - Calculate win percentages
- `templates/ecommerce/product_detail.html` - Calculate review percentages

### `mul` filter:
- `templates/teams/_stats_blocks.html` - Calculate percentages
- `templates/ecommerce/product_detail.html` - Calculate rating distributions

## How to Use in New Templates

If you need these math filters in your templates:

```django
{% extends "base.html" %}
{% load static %}
{% load dict_extras %}  {# <-- Add this line #}

{# Now you can use div, mul, get_item filters #}
{{ seconds|div:60 }}  {# Convert seconds to minutes #}
{{ percentage|mul:100 }}  {# Convert decimal to percentage #}
```

## Related Files

- **Filter Definition**: `apps/siteui/templatetags/dict_extras.py`
- **Template Fixed**: `templates/tournaments/modern_register.html`
- **Other Templates Using Filters**: 
  - `templates/teams/_stats_blocks.html`
  - `templates/ecommerce/product_detail.html`

## Testing

To verify the fix works:

1. Visit any tournament registration page: `/tournaments/register-modern/{slug}/`
2. Page should load without errors
3. If tournament has registration deadline, countdown should display properly
4. Example: "Closes in 2d 5h" (days and hours)

## Alternative Solution (If Needed)

If you prefer not to use custom filters, you can format the time in the view instead:

```python
# In the view
if context.registration_closes_in:
    days = context.registration_closes_in.days
    hours = context.registration_closes_in.seconds // 3600
    context_dict["closes_in_formatted"] = f"{days}d {hours}h"
```

```django
{# In template #}
<span>Closes in {{ closes_in_formatted }}</span>
```

## Status
✅ **FIXED** - Template now loads correctly with all required filters

---

**Fixed By**: GitHub Copilot  
**Date**: October 2, 2025  
**Version**: 1.0
