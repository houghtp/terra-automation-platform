# Tag Selector Component

A reusable tag/multi-select dropdown component that looks like a regular form field.

## Quick Start

### 1. Include in your form template:

```jinja2
{# Define your tag options #}
{% set tag_options = [
  {'value': 'urgent', 'label': 'Urgent'},
  {'value': 'priority', 'label': 'Priority'},
  {'value': 'client', 'label': 'Client Work'}
] %}

{# Set selected values (for edit forms) #}
{% set selected_values = item.tags if item and item.tags else [] %}

{# Include the component #}
{% include 'components/ui/tag_selector.html' %}
```

### 2. Ensure table-base.js is loaded:

The component depends on `initializeTagSelector()` function from `table-base.js`.

## Customization Options

You can customize the component by setting variables before including it:

```jinja2
{% set selector_id = 'myCustomSelector' %}  {# Unique ID #}
{% set field_name = 'categories' %}         {# Form field name #}
{% set label = 'Categories' %}              {# Field label #}
{% set placeholder = 'Choose categories...' %} {# Placeholder text #}
{% set col_class = 'col-12' %}              {# Bootstrap column class #}
{% set help_text = 'Select multiple items' %} {# Help text #}

{% include 'components/ui/tag_selector.html' %}
```

## Backend Integration

### Form Processing:
```python
# In your route handler
form = await request.form()
tags = form.getlist("tags")  # Gets multiple values
# tags will be ['urgent', 'priority'] etc.
```

### Model Storage:
```python
# Store as JSON array
tags = Column(JSON, default=list)

# In your to_dict() method
def to_dict(self):
    return {
        'tags': self.tags or [],  # Ensure always returns a list
        # ... other fields
    }
```

### Table Display:
```javascript
// In your table column config
{
  title: "Tags",
  field: "tags",
  formatter: function (cell) {
    const tags = cell.getValue() || [];
    // if (!Array.isArray(tags) || tags.length === 0) {
    //   return '<span class="text-muted">No tags</span>';
    // }
    return tags.map(tag =>
      `<span class="type-badge ${tag.toLowerCase().replace(/\s+/g, '-')}">${tag}</span>`
    ).join(' ');
  }
}
```

## CSS Classes

The component uses these CSS classes (defined in `tabulator-unified.css`):

- `.tag-selector` - Main dropdown trigger
- `.tag-display` - Display area for selected tags
- `.selected-tag` - Individual tag badges in the selector
- `.type-badge` - Table display badges (with color variants)

## Multiple Selectors in One Form

You can have multiple tag selectors by using unique IDs:

```jinja2
{# First selector #}
{% set selector_id = 'primaryTags' %}
{% set field_name = 'primary_tags' %}
{% set label = 'Primary Tags' %}
{% include 'components/ui/tag_selector.html' %}

{# Second selector #}
{% set selector_id = 'secondaryTags' %}
{% set field_name = 'secondary_tags' %}
{% set label = 'Secondary Tags' %}
{% include 'components/ui/tag_selector.html' %}
```

## Troubleshooting

- **Tags not showing**: Ensure `table-base.js` is loaded before the form
- **Edit mode not working**: Check that `selected_values` contains the correct array
- **Styling issues**: Verify `tabulator-unified.css` is loaded
- **Multiple forms**: Use unique `selector_id` for each instance
