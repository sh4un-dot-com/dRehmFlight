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
        import importlib
        mavgen = importlib.import_module('pymavlink.generator.mavgen')
    except Exception:
        print_instructions(args.out)
        # Non-fatal: repository ships a minimal stub; allow script to exit cleanly
        raise SystemExit(0)

    print('Generating MAVLink headers for dialect:', args.dialect)
    try:
        os.makedirs(args.out, exist_ok=True)
        # Build opts and locate the XML dialect file shipped with pymavlink
        try:
            # Choose wire protocol 2.0 by default
            opts = mavgen.Opts(args.out, mavgen.DEFAULT_WIRE_PROTOCOL, language='C', validate=False)
        except Exception:
            opts = mavgen.Opts(args.out, '2.0', language='C', validate=False)

        # locate builtin dialect xml (pymavlink ships dialects in generator/dialects)
        dialects_dir = os.path.join(os.path.dirname(os.path.realpath(mavgen.__file__)), '..', 'dialects')
        xml_path = os.path.join(dialects_dir, 'v20', args.dialect + '.xml')
        if not os.path.exists(xml_path):
            # fallback to message_definitions tree
            mdef = os.path.join(os.path.dirname(os.path.realpath(mavgen.__file__)), '..', '..', 'message_definitions')
            xml_path = os.path.join(mdef, 'v1.0', args.dialect + '.xml')

        if not os.path.exists(xml_path):
            raise FileNotFoundError('Dialect XML not found for %s (checked %s)' % (args.dialect, xml_path))

        # Call the mavgen API: it expects (opts, [xml_files])
        # Use absolute path to the XML file to avoid cross-drive relpath errors on Windows
        abs_xml = os.path.abspath(xml_path)
        mavgen.mavgen(opts, [abs_xml])
        print('Generated headers in', args.out)
    except Exception as e:
        print('MAVLink header generation failed:', e)
        print_instructions(args.out)
        raise SystemExit(0)
