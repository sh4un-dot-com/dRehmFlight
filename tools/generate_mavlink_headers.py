"""
Helper: attempt to generate MAVLink C headers for use in the firmware.
- If `pymavlink` is available it can generate headers from a dialect XML; otherwise
  this script prints instructions for the user to add MAVLink headers manually.

Note: This script does not add headers automatically to the repo; it helps automation
when running locally with `pymavlink` installed. This helper is intentionally
non-fatal: the repository includes a minimal stub at `src/Mavlink/gen/mavlink.h`.
"""
import argparse
import os

def print_instructions(out):
    print('pymavlink not available or generation failed.')
    print('Install pymavlink locally and run this script to generate headers:')
    print('  pip install pymavlink')
    print('  python tools/generate_mavlink_headers.py --out', out)
    print('Or copy generated headers into', out)
    print('A minimal stub header is already present at src/Mavlink/gen/mavlink.h')

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dialect', default='common', help='MAVLink XML dialect (default: common)')
    p.add_argument('--out', default='src/Mavlink/gen', help='output directory for generated headers')
    args = p.parse_args()

    try:
        # import lazily to avoid failing in environments without pymavlink
        import subprocess
        from pymavlink.generator import mavgen
    except Exception as e:
        print_instructions(args.out)
        # Non-fatal: repository ships a minimal stub; allow script to exit cleanly
        raise SystemExit(0)

    print('Generating MAVLink headers for dialect:', args.dialect)
    try:
        os.makedirs(args.out, exist_ok=True)
        # Call mavgen API; different pymavlink versions may expose different signatures
        try:
            mavgen.mavgen(args.dialect, language='C', output=args.out)
        except TypeError:
            # fallback: call mavgen directly if module is callable
            mavgen(args.dialect, language='C', output=args.out)
        print('Generated headers in', args.out)
    except Exception as e:
        print('MAVLink header generation failed:', e)
        print_instructions(args.out)
        raise SystemExit(0)
