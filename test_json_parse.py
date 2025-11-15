#!/usr/bin/env python3
"""
Test script to verify we can extract JSON from PowerShell mixed output.
"""

import re
import json

# Simulate the actual output we get from PowerShell (ANSI codes from Select-String output)
mixed_output = """[33;1mWARNING: Some warning[0m
[Exchange] Authenticating...
[Exchange] Authenticated
[7m{[0m
[7m  "Status": "Success",[0m
[7m  "ChecksExecuted": 91,[0m
[7m  "Results": [[0m
[7m    {[0m
[7m      "TechType": "M365",[0m
[7m      "Status": "Fail"[0m
[7m    }[0m
[7m  ][0m
[7m}[0m
"""

def extract_json_from_mixed_output(text: str) -> str:
    """
    Extract JSON from PowerShell output that contains ANSI codes and mixed streams.

    Strategy:
    1. Remove ANSI escape codes
    2. Find the JSON object (starts with { and ends with })
    3. Return clean JSON string
    """
    # Remove ANSI escape codes
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_text = ansi_escape.sub('', text)

    print(f"Clean text:\n{clean_text}\n")

    # Find JSON object - look for first '{' and last '}'
    # Must be at start of line to avoid matching JSON inside log messages
    json_start = -1
    json_end = -1
    brace_count = 0

    for i, char in enumerate(clean_text):
        if char == '{' and json_start == -1:
            # Check if this is at the start of a line (preceded by newline or start of string)
            if i == 0 or clean_text[i-1] == '\n':
                json_start = i
                brace_count = 1
                print(f"Found JSON start at position {i}")
        elif json_start != -1:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    print(f"Found JSON end at position {i}")
                    break

    if json_start != -1 and json_end != -1:
        return clean_text[json_start:json_end]

    print(f"json_start={json_start}, json_end={json_end}")
    return None


def main():
    print("Testing JSON extraction from mixed PowerShell output...\n")

    # Test extraction
    json_str = extract_json_from_mixed_output(mixed_output)

    if json_str:
        print("✅ Successfully extracted JSON:")
        print(json_str)
        print()

        # Try to parse it
        try:
            data = json.loads(json_str)
            print("✅ Successfully parsed JSON:")
            print(f"  Status: {data['Status']}")
            print(f"  ChecksExecuted: {data['ChecksExecuted']}")
            print(f"  Results count: {len(data['Results'])}")
            print()
            return True
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            return False
    else:
        print("❌ Failed to extract JSON from output")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
