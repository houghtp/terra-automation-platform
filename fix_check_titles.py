#!/usr/bin/env python3
"""
Fix truncated titles in PowerShell check metadata.

This script updates the Title field in CIS_METADATA blocks to match the CSV.
"""
import csv
import json
import re
from pathlib import Path

# Paths
CSV_FILE = Path("app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0.csv")
CHECKS_DIR = Path("app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/checks")

def load_csv_titles():
    """Load correct titles from CSV file."""
    with open(CSV_FILE, 'r') as f:
        reader = csv.DictReader(f)
        return {row['Recommendation ID']: row['Title'] for row in reader}

def update_check_file(ps1_file: Path, csv_titles: dict) -> tuple[bool, str]:
    """
    Update a single PowerShell check file with correct title from CSV.

    Returns:
        (updated: bool, message: str)
    """
    content = ps1_file.read_text()

    # Extract metadata block
    match = re.search(
        r'(# CIS_METADATA_START\s*\n)({.*?})(\s*\nCIS_METADATA_END #>)',
        content,
        re.DOTALL
    )

    if not match:
        return False, "No metadata block found"

    try:
        # Parse metadata JSON
        metadata = json.loads(match.group(2))
        rec_id = metadata.get('RecommendationId')

        if not rec_id:
            return False, "No RecommendationId in metadata"

        if rec_id not in csv_titles:
            return False, f"RecommendationId {rec_id} not found in CSV"

        csv_title = csv_titles[rec_id]
        ps1_title = metadata.get('Title', '')

        # Check if title needs updating
        if ps1_title == csv_title:
            return False, "Title already correct"

        # Update title in metadata
        metadata['Title'] = csv_title

        # Rebuild metadata JSON (formatted for readability)
        new_json = json.dumps(metadata)

        # Replace metadata block in file
        new_content = content[:match.start()] + \
                      match.group(1) + \
                      new_json + \
                      match.group(3) + \
                      content[match.end():]

        # Write updated content
        ps1_file.write_text(new_content)

        return True, f"Updated: '{ps1_title}' → '{csv_title}'"

    except json.JSONDecodeError as e:
        return False, f"Failed to parse metadata JSON: {e}"
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main execution."""
    print("=" * 100)
    print("FIXING TRUNCATED TITLES IN POWERSHELL CHECK METADATA")
    print("=" * 100)
    print()

    # Load CSV titles
    print(f"Loading titles from CSV: {CSV_FILE}")
    csv_titles = load_csv_titles()
    print(f"Loaded {len(csv_titles)} titles from CSV")
    print()

    # Find all PowerShell check files
    ps1_files = list(CHECKS_DIR.rglob('*.ps1'))
    print(f"Found {len(ps1_files)} PowerShell check files")
    print()

    # Process each file
    updated_count = 0
    skipped_count = 0
    error_count = 0

    print("-" * 100)
    for ps1_file in sorted(ps1_files):
        relative_path = ps1_file.relative_to(CHECKS_DIR)
        updated, message = update_check_file(ps1_file, csv_titles)

        if updated:
            print(f"✓ {relative_path}")
            print(f"  {message}")
            updated_count += 1
        elif "already correct" in message:
            skipped_count += 1
        else:
            print(f"✗ {relative_path}")
            print(f"  {message}")
            error_count += 1

    print("-" * 100)
    print()
    print("SUMMARY:")
    print(f"  Total files:        {len(ps1_files)}")
    print(f"  ✓ Updated:          {updated_count}")
    print(f"  - Already correct:  {skipped_count}")
    print(f"  ✗ Errors:           {error_count}")
    print()

    if updated_count > 0:
        print("✓ Title fix completed successfully!")
        print()
        print("NEXT STEPS:")
        print("1. Review the changes with: git diff app/features/msp/cspm/")
        print("2. Run a test scan to verify titles appear correctly")
        print("3. Commit the changes")
    else:
        print("No files needed updating.")

if __name__ == "__main__":
    main()
