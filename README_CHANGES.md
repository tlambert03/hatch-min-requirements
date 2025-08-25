# Issue #5 Fix: Compatibility with pyproject-fmt

## Problem
The original implementation used string manipulation to modify `pyproject.toml`:

```python
# OLD - problematic approach
table_header = "[project.optional-dependencies]"
min_reqs_text = f"{table_header}\n{extra_name} = [\n"
# ... build string ...
modified_pyproject_text = pyproject_text.replace(table_header, min_reqs_text, 1)
```

This caused issues when used with formatters like `pyproject-fmt` because:

1. **Poor formatting preservation**: String manipulation doesn't respect the original formatting style
2. **Brittle parsing**: Relies on exact string matching rather than semantic TOML understanding  
3. **Limited robustness**: Doesn't handle all possible TOML variations correctly

## Solution
Replaced string manipulation with proper TOML library (`tomlkit`) that:

1. **Preserves formatting**: Maintains the original file's style and structure
2. **Semantic parsing**: Uses proper TOML parsing instead of text manipulation
3. **Robust handling**: Works with all valid TOML variations
4. **Backward compatibility**: Includes fallback for environments without `tomlkit`

## Key Changes

### Dependencies
- Added `tomlkit` to `dependencies` in `pyproject.toml`

### Implementation
- **Primary path**: Uses `tomlkit` when available for format-preserving TOML manipulation
- **Fallback path**: Improved string manipulation for environments without `tomlkit`
- **Preserves existing optional dependencies**: No longer replaces entire sections
- **Maintains all functionality**: Backward compatible with existing behavior

### Example Behavior

**Before (problematic)**:
```python
# Would replace entire [project.optional-dependencies] section
# Could break existing entries depending on formatting
```

**After (fixed)**:
```python
# Parses TOML properly
doc = tomlkit.parse(pyproject_text)

# Preserves existing structure
if "optional-dependencies" not in doc["project"]:
    doc["project"]["optional-dependencies"] = tomlkit.table()

# Adds entry without breaking existing ones
doc["project"]["optional-dependencies"][extra_name] = min_reqs

# Writes back with preserved formatting
tomlkit.dumps(doc)
```

## Testing
Added comprehensive tests in `tests/test_patch_pyproject_formatting.py` that verify:

- Existing optional dependencies are preserved
- Various formatting styles work correctly
- New functionality doesn't break existing behavior
- Both with and without existing optional-dependencies sections

## Benefits
1. **Compatible with pyproject-fmt**: Works correctly with formatted TOML files
2. **Preserves user formatting**: Maintains the style users prefer
3. **More robust**: Handles edge cases better than string manipulation
4. **Future-proof**: Uses standard TOML library for parsing/writing
5. **Backward compatible**: Doesn't break existing functionality