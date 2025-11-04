# Form Components Documentation

This document provides comprehensive usage guidelines for all reusable form components in the DeltaCrown project.

## Table of Contents

1. [Setup](#setup)
2. [Form Input](#form-input)
3. [Textarea](#textarea)
4. [Select/Dropdown](#selectdropdown)
5. [Checkbox](#checkbox)
6. [Radio Buttons](#radio-buttons)
7. [File Upload](#file-upload)
8. [Best Practices](#best-practices)

---

## Setup

### Required Package

These components use `django-widget-tweaks` for enhanced form field rendering. Install it:

```bash
pip install django-widget-tweaks
```

Add to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'widget_tweaks',
    # ...
]
```

### Load Template Tags

In any template using these components, load the widget_tweaks library:

```django
{% load widget_tweaks %}
```

---

## Form Input

**Component:** `templates/components/form_input.html`

**Supported Input Types:** text, email, password, number, tel, url, date, time, datetime-local

### Usage with Django Form

```django
{% include 'components/form_input.html' with 
    field=form.email 
    label="Email Address"
    type="email"
    placeholder="you@example.com"
    help_text="We'll never share your email"
    icon="fa-envelope"
    required=True
%}
```

### Usage without Django Form (Manual)

```django
{% include 'components/form_input.html' with 
    id="username"
    name="username"
    type="text"
    label="Username"
    placeholder="Choose a username"
    value="johndoe"
    required=True
    icon="fa-user"
    help_text="3-20 characters, letters and numbers only"
%}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `field` | Django field | No* | Django form field object |
| `id` | string | No* | HTML id attribute (required if no field) |
| `name` | string | No* | HTML name attribute (required if no field) |
| `label` | string | No | Label text above input |
| `type` | string | No | Input type (default: 'text') |
| `placeholder` | string | No | Placeholder text |
| `value` | string | No | Default value |
| `icon` | string | No | FontAwesome icon class (e.g., 'fa-envelope') |
| `icon_right` | string | No | Icon to show on right side of input |
| `required` | boolean | No | Mark field as required |
| `readonly` | boolean | No | Make field read-only |
| `disabled` | boolean | No | Disable the field |
| `help_text` | string | No | Help text below input |
| `error` | string | No | Error message to display |
| `input_classes` | string | No | Additional CSS classes for input |
| `extra_classes` | string | No | Additional CSS classes for wrapper |
| `autocomplete` | string | No | Autocomplete attribute |
| `pattern` | string | No | Validation pattern (regex) |
| `min` | number | No | Minimum value (for number inputs) |
| `max` | number | No | Maximum value (for number inputs) |
| `step` | number | No | Step increment (for number inputs) |
| `maxlength` | number | No | Maximum character length |

*Either `field` OR both `id` and `name` must be provided.

### Examples

**Email Input with Icon:**
```django
{% include 'components/form_input.html' with 
    field=form.email 
    label="Email"
    icon="fa-envelope"
    placeholder="your@email.com"
%}
```

**Password Input with Strength Indicator (custom):**
```django
{% include 'components/form_input.html' with 
    field=form.password 
    label="Password"
    type="password"
    icon="fa-lock"
    help_text="Minimum 8 characters"
%}
```

**Number Input with Min/Max:**
```django
{% include 'components/form_input.html' with 
    id="age"
    name="age"
    type="number"
    label="Age"
    min="13"
    max="120"
    required=True
%}
```

---

## Textarea

**Component:** `templates/components/form_textarea.html`

### Usage with Django Form

```django
{% include 'components/form_textarea.html' with 
    field=form.bio 
    label="Biography"
    placeholder="Tell us about yourself..."
    help_text="Maximum 500 characters"
    rows=4
    maxlength=500
    show_counter=True
    required=True
%}
```

### Usage without Django Form

```django
{% include 'components/form_textarea.html' with 
    id="description"
    name="description"
    label="Description"
    placeholder="Enter description..."
    rows=6
    maxlength=1000
    show_counter=True
%}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `field` | Django field | No* | Django form field object |
| `id` | string | No* | HTML id attribute |
| `name` | string | No* | HTML name attribute |
| `label` | string | No | Label text above textarea |
| `placeholder` | string | No | Placeholder text |
| `value` | string | No | Default value |
| `icon` | string | No | FontAwesome icon class |
| `rows` | number | No | Number of rows (default: 4) |
| `required` | boolean | No | Mark field as required |
| `readonly` | boolean | No | Make field read-only |
| `disabled` | boolean | No | Disable the field |
| `maxlength` | number | No | Maximum character length |
| `show_counter` | boolean | No | Show character counter (requires maxlength) |
| `help_text` | string | No | Help text below textarea |
| `error` | string | No | Error message to display |
| `input_classes` | string | No | Additional CSS classes |
| `extra_classes` | string | No | Additional CSS classes for wrapper |

### Example with Character Counter

```django
{% include 'components/form_textarea.html' with 
    field=form.team_description 
    label="Team Description"
    rows=5
    maxlength=500
    show_counter=True
    help_text="Describe your team's playstyle and goals"
%}
```

---

## Select/Dropdown

**Component:** `templates/components/form_select.html`

### Usage with Django Form

```django
{% include 'components/form_select.html' with 
    field=form.country 
    label="Country"
    help_text="Select your country"
    icon="fa-globe"
    required=True
%}
```

### Usage without Django Form

```django
{% include 'components/form_select.html' with 
    id="game"
    name="game"
    label="Select Game"
    placeholder="Choose a game..."
    options=game_list
    value="valorant"
    required=True
%}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `field` | Django field | No* | Django form field object |
| `id` | string | No* | HTML id attribute |
| `name` | string | No* | HTML name attribute |
| `label` | string | No | Label text above select |
| `placeholder` | string | No | Placeholder option text |
| `options` | list | No* | List of options (required if no field) |
| `value` | string | No | Selected value |
| `icon` | string | No | FontAwesome icon class |
| `required` | boolean | No | Mark field as required |
| `disabled` | boolean | No | Disable the field |
| `multiple` | boolean | No | Allow multiple selections |
| `help_text` | string | No | Help text below select |
| `error` | string | No | Error message to display |
| `input_classes` | string | No | Additional CSS classes |
| `extra_classes` | string | No | Additional CSS classes for wrapper |

### Options Format

Simple list:
```python
options = ['Valorant', 'eFootball', 'League of Legends']
```

List of dictionaries:
```python
options = [
    {'value': 'valorant', 'label': 'Valorant'},
    {'value': 'efootball', 'label': 'eFootball'},
    {'value': 'lol', 'label': 'League of Legends'},
]
```

### Example

```django
{% include 'components/form_select.html' with 
    id="timezone"
    name="timezone"
    label="Timezone"
    icon="fa-clock"
    placeholder="Select timezone..."
    options=timezone_choices
    required=True
%}
```

---

## Checkbox

**Component:** `templates/components/form_checkbox.html`

### Usage with Django Form

```django
{% include 'components/form_checkbox.html' with 
    field=form.agree_terms 
    label="I agree to the Terms and Conditions"
    help_text="Please read our terms before continuing"
    required=True
%}
```

### Usage without Django Form

```django
{% include 'components/form_checkbox.html' with 
    id="remember_me"
    name="remember_me"
    label="Remember me for 30 days"
    checked=True
%}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `field` | Django field | No* | Django form field object |
| `id` | string | No* | HTML id attribute |
| `name` | string | No* | HTML name attribute |
| `label` | string | No | Label text next to checkbox |
| `value` | string | No | Value when checked (default: 'on') |
| `checked` | boolean | No | Check the checkbox by default |
| `required` | boolean | No | Mark field as required |
| `disabled` | boolean | No | Disable the checkbox |
| `help_text` | string | No | Help text below checkbox |
| `error` | string | No | Error message to display |
| `input_classes` | string | No | Additional CSS classes |
| `extra_classes` | string | No | Additional CSS classes for wrapper |

### Examples

**Terms Agreement:**
```django
{% include 'components/form_checkbox.html' with 
    field=form.terms 
    label="I have read and agree to the Terms of Service"
    required=True
%}
```

**Newsletter Subscription:**
```django
{% include 'components/form_checkbox.html' with 
    id="newsletter"
    name="newsletter"
    label="Subscribe to weekly tournament updates"
    help_text="You can unsubscribe at any time"
%}
```

---

## Radio Buttons

**Component:** `templates/components/form_radio.html`

### Usage with Django Form

```django
{% include 'components/form_radio.html' with 
    field=form.notification_preference 
    label="Notification Preferences"
    help_text="How would you like to receive notifications?"
    layout="vertical"
    required=True
%}
```

### Usage without Django Form

```django
{% include 'components/form_radio.html' with 
    name="payment_method"
    label="Payment Method"
    options=payment_options
    value="credit_card"
    layout="horizontal"
%}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `field` | Django field | No* | Django form field object |
| `id` | string | No | Base id for radio buttons |
| `name` | string | No* | HTML name attribute (required if no field) |
| `label` | string | No | Label text above radio group |
| `icon` | string | No | FontAwesome icon class |
| `options` | list | No* | List of options (required if no field) |
| `value` | string | No | Selected value |
| `layout` | string | No | 'vertical' or 'horizontal' (default: vertical) |
| `required` | boolean | No | Mark field as required |
| `disabled` | boolean | No | Disable all radio buttons |
| `help_text` | string | No | Help text above options |
| `error` | string | No | Error message to display |
| `input_classes` | string | No | Additional CSS classes |
| `extra_classes` | string | No | Additional CSS classes for wrapper |

### Options Format

Simple list:
```python
options = ['Email', 'SMS', 'Push Notification']
```

List of dictionaries:
```python
options = [
    {'value': 'email', 'label': 'Email'},
    {'value': 'sms', 'label': 'SMS'},
    {'value': 'push', 'label': 'Push Notification'},
]
```

### Examples

**Vertical Layout (Default):**
```django
{% include 'components/form_radio.html' with 
    name="account_type"
    label="Account Type"
    options=account_types
    layout="vertical"
%}
```

**Horizontal Layout:**
```django
{% include 'components/form_radio.html' with 
    name="gender"
    label="Gender"
    options=gender_choices
    layout="horizontal"
%}
```

---

## File Upload

**Component:** `templates/components/form_file.html`

### Usage with Django Form

```django
{% include 'components/form_file.html' with 
    field=form.avatar 
    label="Profile Picture"
    help_text="Max size: 2MB. Accepted: JPG, PNG, GIF"
    accept="image/*"
    max_size="2"
    preview=True
    required=True
%}
```

### Usage without Django Form

```django
{% include 'components/form_file.html' with 
    id="team_logo"
    name="team_logo"
    label="Upload Team Logo"
    accept=".jpg,.jpeg,.png,.svg"
    max_size="5"
    preview=True
%}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `field` | Django field | No* | Django form field object |
| `id` | string | No* | HTML id attribute |
| `name` | string | No* | HTML name attribute |
| `label` | string | No | Label text above file input |
| `icon` | string | No | FontAwesome icon class |
| `accept` | string | No | File type filter (e.g., 'image/*', '.pdf') |
| `max_size` | number | No | Maximum file size in MB |
| `preview` | boolean | No | Show image preview after selection |
| `multiple` | boolean | No | Allow multiple file selection |
| `required` | boolean | No | Mark field as required |
| `disabled` | boolean | No | Disable the field |
| `help_text` | string | No | Help text in upload area |
| `error` | string | No | Error message to display |
| `input_classes` | string | No | Additional CSS classes |
| `extra_classes` | string | No | Additional CSS classes for wrapper |

### Examples

**Avatar Upload with Preview:**
```django
{% include 'components/form_file.html' with 
    field=form.profile_picture 
    label="Profile Picture"
    accept="image/jpeg,image/png,image/gif"
    max_size="2"
    preview=True
    help_text="Square images work best"
%}
```

**Document Upload:**
```django
{% include 'components/form_file.html' with 
    id="contract"
    name="contract"
    label="Upload Contract"
    accept=".pdf,.doc,.docx"
    max_size="10"
    help_text="Max 10MB - PDF or Word documents only"
%}
```

**Multiple Files:**
```django
{% include 'components/form_file.html' with 
    id="screenshots"
    name="screenshots"
    label="Upload Screenshots"
    accept="image/*"
    multiple=True
    help_text="You can select multiple images"
%}
```

---

## Best Practices

### 1. Consistent Labeling

Always provide clear, descriptive labels for better UX:

```django
{# Good #}
{% include 'components/form_input.html' with 
    field=form.email 
    label="Email Address"
%}

{# Avoid #}
{% include 'components/form_input.html' with 
    field=form.email 
%}
```

### 2. Use Icons Appropriately

Icons enhance recognition but shouldn't replace labels:

```django
{% include 'components/form_input.html' with 
    field=form.email 
    label="Email Address"
    icon="fa-envelope"
%}
```

### 3. Provide Help Text

Help users understand what's expected:

```django
{% include 'components/form_input.html' with 
    field=form.username 
    label="Username"
    help_text="3-20 characters, letters and numbers only"
%}
```

### 4. Mark Required Fields

Always indicate required fields:

```django
{% include 'components/form_input.html' with 
    field=form.username 
    label="Username"
    required=True
%}
```

### 5. Use Appropriate Input Types

Choose the right input type for better mobile experience:

```django
{# Use type="email" for email inputs #}
{% include 'components/form_input.html' with 
    field=form.email 
    type="email"
%}

{# Use type="tel" for phone numbers #}
{% include 'components/form_input.html' with 
    field=form.phone 
    type="tel"
%}
```

### 6. File Upload Validation

Always specify accepted file types and size limits:

```django
{% include 'components/form_file.html' with 
    field=form.avatar 
    accept="image/jpeg,image/png"
    max_size="2"
    help_text="JPG or PNG only, max 2MB"
%}
```

### 7. Accessibility

- Always provide labels (required for screen readers)
- Use appropriate ARIA attributes
- Ensure keyboard navigation works
- Maintain sufficient color contrast

### 8. Error Handling

Components automatically display Django form errors. For manual forms, pass error messages:

```django
{% include 'components/form_input.html' with 
    id="username"
    name="username"
    error="This username is already taken"
%}
```

### 9. Form Validation

Use HTML5 validation attributes:

```django
{% include 'components/form_input.html' with 
    field=form.age 
    type="number"
    min="13"
    max="120"
    required=True
%}
```

### 10. Responsive Design

All components are mobile-responsive by default. Test on multiple screen sizes.

---

## Example: Complete Registration Form

```django
{% load widget_tweaks %}

<form method="post" enctype="multipart/form-data" class="space-y-4">
    {% csrf_token %}
    
    {# Avatar Upload #}
    {% include 'components/form_file.html' with 
        field=form.avatar 
        label="Profile Picture"
        accept="image/*"
        preview=True
    %}
    
    {# Username #}
    {% include 'components/form_input.html' with 
        field=form.username 
        label="Username"
        icon="fa-user"
        required=True
    %}
    
    {# Email #}
    {% include 'components/form_input.html' with 
        field=form.email 
        label="Email Address"
        type="email"
        icon="fa-envelope"
        required=True
    %}
    
    {# Password #}
    {% include 'components/form_input.html' with 
        field=form.password 
        label="Password"
        type="password"
        icon="fa-lock"
        required=True
    %}
    
    {# Country #}
    {% include 'components/form_select.html' with 
        field=form.country 
        label="Country"
        icon="fa-globe"
        required=True
    %}
    
    {# Bio #}
    {% include 'components/form_textarea.html' with 
        field=form.bio 
        label="Biography"
        rows=4
        maxlength=500
        show_counter=True
    %}
    
    {# Notification Preference #}
    {% include 'components/form_radio.html' with 
        field=form.notifications 
        label="Notification Preferences"
        layout="vertical"
    %}
    
    {# Newsletter #}
    {% include 'components/form_checkbox.html' with 
        field=form.newsletter 
        label="Subscribe to newsletter"
    %}
    
    {# Terms #}
    {% include 'components/form_checkbox.html' with 
        field=form.terms 
        label="I agree to the Terms of Service"
        required=True
    %}
    
    {# Submit Button #}
    <button type="submit" class="btn btn-primary w-full">
        Create Account
    </button>
</form>
```

---

## Troubleshooting

### Component Not Rendering

- Ensure `django-widget-tweaks` is installed
- Verify it's added to `INSTALLED_APPS`
- Check that template paths are correct

### Styles Not Applied

- Run `npm run build:css` to compile Tailwind
- Check that `main.css` is loaded in base template
- Verify dark mode classes are working

### JavaScript Features Not Working

- Ensure FontAwesome icons are loaded
- Check browser console for JavaScript errors
- Verify unique IDs for components with JS features

---

For more information, refer to the [Design System Documentation](./DESIGN_SYSTEM.md).
