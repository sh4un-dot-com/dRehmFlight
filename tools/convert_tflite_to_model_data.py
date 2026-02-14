"""
Convert a .tflite flatbuffer into a C header `model_data.h` suitable for inclusion
in the firmware when building with TensorFlow Lite Micro (USE_TFLM=1).

Usage:
  python tools/convert_tflite_to_model_data.py model.tflite Versions/dRehmFlight_Teensy_BETA_1.2/model_data.h

The generated header contains `const unsigned char model_data[]` and
`const unsigned int model_data_len`.
"""
import argparse
import os


def write_c_header(in_path, out_path):
    with open(in_path, 'rb') as f:
        data = f.read()
    arr_lines = []
    line = ''
    for i, b in enumerate(data):
        line += '0x%02x,' % b
        if (i + 1) % 12 == 0:
            arr_lines.append(line)
            line = ''
    if line:
        arr_lines.append(line)

    header = []
    header.append('// Generated model_data.h — do not edit by hand')
    header.append('#include <stdint.h>')
    header.append('static const unsigned char model_data[] = {')
    for l in arr_lines:
        header.append('  ' + l)
    header.append('};')
    header.append('static const unsigned int model_data_len = %d;' % len(data))

    with open(out_path, 'w') as f:
        f.write('\n'.join(header))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Convert .tflite -> model_data.h')
    p.add_argument('tflite', help='input .tflite file')
    p.add_argument('out', nargs='?', default='Versions/dRehmFlight_Teensy_BETA_1.2/model_data.h', help='output header path')
    args = p.parse_args()

    if not os.path.exists(args.tflite):
        print('ERROR: tflite file not found:', args.tflite)
        raise SystemExit(1)
    write_c_header(args.tflite, args.out)
    print('Wrote', args.out)
