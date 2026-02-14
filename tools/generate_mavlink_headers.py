"""
Helper: attempt to generate MAVLink C headers for use in the firmware.
- If `pymavlink` is available it can generate headers from a dialect XML; otherwise
  this script prints instructions for the user to add MAVLink headers manually.

Note: This script does not add headers automatically to the repo; it helps automation
when running locally with `pymavlink` installed.
"""
import argparse
import shutil
import os

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dialect', default='common', help='MAVLink XML dialect (default: common)')
    p.add_argument('--out', default='src/Mavlink/gen', help='output directory for generated headers')
    args = p.parse_args()

    try:
        from pymavlink.generator import mavgen
    except Exception as e:
        print('pymavlink generator not available:', e)
        raise SystemExit(1)

    print('Generating MAVLink headers for dialect:', args.dialect)
    # Use mavgen command
    cmd = [sys.executable, '-c', 'import sys; sys.path.insert(0, \"C:\\\\Users\\\\shaun\\\\scoop\\\\apps\\\\python313\\\\current\\\\Lib\\\\site-packages\"); from pymavlink.generator.mavgen import mavgen; mavgen(\"' + args.dialect + '\", language=\"C\", output=\"' + args.out + '\")']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print('Generated headers in', args.out)
    else:
        print('Failed to generate:', result.stderr)
        raise SystemExit(1)
