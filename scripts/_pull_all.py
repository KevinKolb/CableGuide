#!/usr/bin/env python3
"""
Pull All Channels Script
Automatically runs all channel scraper scripts in the scripts folder.
Dynamically discovers and executes all pull_*.py scripts.
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """Run all pull scripts in the scripts folder."""
    print("=" * 60)
    print("Running All Channel Scrapers")
    print("=" * 60)
    print()

    # Get the scripts directory
    script_dir = Path(__file__).parent.absolute()
    current_script = Path(__file__).name

    # Find all pull_*.py scripts
    pull_scripts = sorted(script_dir.glob('pull_*.py'))

    if not pull_scripts:
        print("No pull scripts found in the scripts folder.")
        return 1

    print(f"Found {len(pull_scripts)} channel scraper(s):")
    for script in pull_scripts:
        print(f"  - {script.name}")
    print()

    # Check if --mock flag was passed
    mock_flag = '--mock' if '--mock' in sys.argv or '-m' in sys.argv else ''

    # Run each script
    success_count = 0
    failed_scripts = []

    for script in pull_scripts:
        script_name = script.name
        print("=" * 60)
        print(f"Running: {script_name}")
        print("=" * 60)

        try:
            # Build command
            cmd = [sys.executable, str(script)]
            if mock_flag:
                cmd.append(mock_flag)

            # Run the script
            result = subprocess.run(
                cmd,
                cwd=script_dir,
                capture_output=False,
                text=True
            )

            if result.returncode == 0:
                success_count += 1
                print(f"✓ {script_name} completed successfully")
            else:
                failed_scripts.append(script_name)
                print(f"✗ {script_name} failed with exit code {result.returncode}")

        except Exception as e:
            failed_scripts.append(script_name)
            print(f"✗ {script_name} failed with error: {e}")

        print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"Total scripts: {len(pull_scripts)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed_scripts)}")

    if failed_scripts:
        print()
        print("Failed scripts:")
        for script in failed_scripts:
            print(f"  - {script}")

    print()
    print("=" * 60)
    print("All Done!")
    print("=" * 60)
    print()

    # Return non-zero if any scripts failed
    return 1 if failed_scripts else 0


if __name__ == '__main__':
    sys.exit(main())
