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
        import pymavlink
        from pymavlink.dialects import mavlink10
    except Exception:
        print('pymavlink not installed. To generate MAVLink headers locally install pymavlink: pip install pymavlink')
        print('Alternatively, copy generated MAVLink headers into', args.out)
        raise SystemExit(1)

    print('pymavlink present — generating headers is environment-specific. See pymavlink docs.')
    print('This helper is a placeholder; if you want, I can generate a minimal set and add it to the repo.')
