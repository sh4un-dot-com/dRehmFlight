"""
Fetch a small example .tflite model and convert it to `model_data.h` using the
existing `convert_tflite_to_model_data.py` converter.

Usage:
  python tools/fetch_example_tflite.py --out Versions/dRehmFlight_Teensy_BETA_1.2/model_data.h

The script tries a few reliable public model URLs. If all fail, it prints manual steps.
"""
import argparse
import urllib.request
import sys
import os

CANDIDATES = [
    # small 'hello_world' style models
    'https://github.com/tensorflow/tflite-micro/raw/main/tensorflow/lite/micro/examples/micro_speech/micro_speech.tflite',
    'https://github.com/tensorflow/tflite-micro/raw/main/tensorflow/lite/micro/examples/hello_world/model.tflite',
    'https://storage.googleapis.com/download.tensorflow.org/models/tflite/micro/hello_world.tflite',
    'https://github.com/tensorflow/examples/raw/master/lite/examples/hello_world/model.tflite',
]


def download(url, target):
    try:
        print('Trying', url)
        with urllib.request.urlopen(url, timeout=20) as r:
            data = r.read()
            with open(target, 'wb') as f:
                f.write(data)
        print('Downloaded', url)
        return True
    except Exception as e:
        print('Failed to download from', url, '->', e)
        return False


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', default='Versions/dRehmFlight_Teensy_BETA_1.2/model_data.h')
    p.add_argument('--tmp', default='tools/tmp_model.tflite')
    args = p.parse_args()

    tmpfile = args.tmp
    success = False
    for url in CANDIDATES:
        if download(url, tmpfile):
            success = True
            break

    if not success:
        print('\nAll automated downloads failed.\n')
        print('Please obtain a small .tflite model (for example the TensorFlow Lite "hello_world" example)')
        print('and run: python tools/convert_tflite_to_model_data.py path/to/your_model.tflite')
        sys.exit(1)

    # convert to header
    print('Converting to model_data.h...')
    os.system('%s %s %s' % (sys.executable, 'tools/convert_tflite_to_model_data.py', args.out))
    print('Wrote', args.out)
    # cleanup
    try:
        os.remove(tmpfile)
    except Exception:
        pass
    print('Done.')
