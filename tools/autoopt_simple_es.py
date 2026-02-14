"""
Simple offboard optimizer (very small ES) for dRehmFlight
- Connects to the flight controller over serial
- Reads `OPT,` telemetry (or `REC,` / `GET STATUS`) to evaluate cost
- Perturbs PID gains (roll) and keeps improvements

Usage:
  python tools/autoopt_simple_es.py --port COM3 --baud 500000 --axis ROLL

WARNING: Use on bench with props removed. This script is a minimal demo, not a production optimizer.
"""
import argparse
import json
import random
import time
import re
from collections import deque
import serial

OPT_PREFIX = 'OPT,'
REC_PREFIX = 'REC,'
STATUS_CMD = 'GET STATUS\n'
GET_PID = 'GET PID\n'
SAVE_CMD = 'SAVE PARAMS\n'
SET_FMT = 'SET {key} {val}\n'
APPLY_FMT = 'APPLY_GAINS {axis} {kp} {ki} {kd}\n'


def parse_args():
    p = argparse.ArgumentParser(description='Simple evolutionary optimizer for dRehmFlight')
    p.add_argument('--port', required=True)
    p.add_argument('--baud', type=int, default=500000)
    p.add_argument('--axis', choices=['ROLL','PITCH','BOTH'], default='ROLL')
    p.add_argument('--window', type=float, default=3.0, help='seconds to evaluate each candidate')
    p.add_argument('--iters', type=int, default=20)
    p.add_argument('--scale', type=float, default=0.2, help='relative perturbation scale (stddev for gaussian)')
    p.add_argument('--pop', type=int, default=1, help='population size for each generation (1 = single-step ES)')
    p.add_argument('--method', choices=['es','cmaes'], default='es', help='optimization method: ES (default) or CMAES-like adaptive ES')
    p.add_argument('--min-gain', type=float, default=0.0, help='minimum allowed gain value')
    p.add_argument('--max-gain', type=float, default=5.0, help='maximum allowed gain value')
    p.add_argument('--log-file', default='tools/autoopt_results.csv', help='CSV log file for trials')
    p.add_argument('--tol', type=float, default=1e-4, help='minimum relative improvement to count')
    p.add_argument('--patience', type=int, default=6, help='generations without improvement before early stop')
    p.add_argument('--include-motors', action='store_true', help='include motor saturation in cost if REC/OPT contains motor fields')
    return p.parse_args()


def read_json_line(line):
    try:
        return json.loads(line)
    except Exception:
        return None


def get_pid(ser, timeout=1.0):
    ser.reset_input_buffer()
    ser.write(GET_PID.encode())
    t0 = time.time()
    buf = ''
    while time.time() - t0 < timeout:
        line = ser.readline().decode(errors='ignore').strip()
        if line.startswith('{') and 'Kp_roll_angle' in line:
            try:
                return json.loads(line)
            except Exception:
                # older firmware prints JSON without keys; skip
                pass
    return None


def evaluate_cost(ser, duration):
    """Collect OPT or REC telemetry for `duration` seconds and compute a simple cost.
    Cost = mean(|roll| + |pitch|) over samples (lower is better)
    """
    t0 = time.time()
    samples = []
    ser.timeout = 0.2
    while time.time() - t0 < duration:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue
        if line.startswith(OPT_PREFIX):
            # OPT,t_ms,loop_us,roll,pitch,yaw,...
            parts = line.split(',')
            try:
                roll = float(parts[3]); pitch = float(parts[4])
                samples.append(abs(roll) + abs(pitch))
            except Exception:
                pass
        elif line.startswith(REC_PREFIX):
            # REC,t_ms,roll,pitch,yaw,...
            parts = line.split(',')
            try:
                roll = float(parts[2]); pitch = float(parts[3])
                samples.append(abs(roll) + abs(pitch))
            except Exception:
                pass
        elif line.startswith('{'):
            j = read_json_line(line)
            if j and 'roll' in j and 'pitch' in j:
                samples.append(abs(j['roll']) + abs(j['pitch']))
    if not samples:
        return float('inf')
    return sum(samples) / len(samples)


def apply_and_evaluate(ser, axis, kp, ki, kd, duration, timeout=0.2):
    """Apply gains (APPLY_GAINS) and return evaluated cost over duration seconds."""
    cmd = APPLY_FMT.format(axis=axis, kp=kp, ki=ki, kd=kd)
    ser.write(cmd.encode())
    time.sleep(0.25)
    cost = evaluate_cost(ser, duration)
    return cost


def _clamp_gain(v, lo, hi):
    return max(lo, min(hi, v))


def _append_csv_row(path, row, header=None):
    import os
    first = not os.path.exists(path)
    with open(path, 'a') as f:
        if first and header:
            f.write(header + "\n")
        f.write(','.join(map(str, row)) + "\n")


def main():
    args = parse_args()
    ser = serial.Serial(args.port, args.baud, timeout=0.2)
    time.sleep(1.0)
    pid = get_pid(ser)
    if not pid:
        print('Failed to read PID (GET PID), aborting')
        return
    print('Current PID:', pid)

    # make best dict flexible for BOTH
    best = pid.copy()

    # start OPT stream
    ser.write(b'AUTOOPT START\n')
    time.sleep(0.1)

    # baseline
    baseline = evaluate_cost(ser, args.window)
    best_cost = baseline
    print('Baseline cost:', baseline)

    # CSV header
    csv_header = 'ts,iter,cand,axis,kp,ki,kd,cost'

    no_improve = 0

    try:
        for it in range(1, args.iters + 1):
            generation_best = None
            generation_best_cost = float('inf')

            # population of candidates
            for cand in range(args.pop):
                # sample perturbation factor(s) gaussian around 1.0
                # sampling: support both plain ES and a CMAES-like adaptive sigma mode
                if 'sigma' not in locals():
                    sigma = args.scale
                def sample_mult(v):
                    return v * max(0.0, random.gauss(1.0, sigma))

                if args.axis == 'BOTH':
                    # mutate both roll & pitch (independently)
                    kp_r = sample_mult(best['Kp_roll_angle'])
                    ki_r = sample_mult(best['Ki_roll_angle'])
                    kd_r = sample_mult(best['Kd_roll_angle'])
                    kp_p = sample_mult(best['Kp_pitch_angle'])
                    ki_p = sample_mult(best['Ki_pitch_angle'])
                    kd_p = sample_mult(best['Kd_pitch_angle'])
                else:
                    axis = args.axis
                    if axis == 'ROLL':
                        kp_r = sample_mult(best['Kp_roll_angle'])
                        ki_r = sample_mult(best['Ki_roll_angle'])
                        kd_r = sample_mult(best['Kd_roll_angle'])
                        kp_p, ki_p, kd_p = best['Kp_pitch_angle'], best['Ki_pitch_angle'], best['Kd_pitch_angle']
                    else:
                        kp_p = sample_mult(best['Kp_pitch_angle'])
                        ki_p = sample_mult(best['Ki_pitch_angle'])
                        kd_p = sample_mult(best['Kd_pitch_angle'])
                        kp_r, ki_r, kd_r = best['Kp_roll_angle'], best['Ki_roll_angle'], best['Kd_roll_angle']

                # clamp
                kp_r = _clamp_gain(kp_r, args.min_gain, args.max_gain)
                ki_r = _clamp_gain(ki_r, args.min_gain, args.max_gain)
                kd_r = _clamp_gain(kd_r, args.min_gain, args.max_gain)
                kp_p = _clamp_gain(kp_p, args.min_gain, args.max_gain)
                ki_p = _clamp_gain(ki_p, args.min_gain, args.max_gain)
                kd_p = _clamp_gain(kd_p, args.min_gain, args.max_gain)

                # apply candidate(s) and evaluate
                if args.axis == 'BOTH':
                    # apply pitch then roll (APPLY_GAINS accepts axis-specific)
                    ser.write(APPLY_FMT.format(axis='ROLL', kp=kp_r, ki=ki_r, kd=kd_r).encode())
                    time.sleep(0.05)
                    ser.write(APPLY_FMT.format(axis='PITCH', kp=kp_p, ki=ki_p, kd=kd_p).encode())
                    time.sleep(0.2)
                    cost = evaluate_cost(ser, args.window)
                    cand_kp, cand_ki, cand_kd = kp_r, ki_r, kd_r
                    cand_axis = 'BOTH'
                else:
                    cand_axis = args.axis
                    if cand_axis == 'ROLL':
                        cost = apply_and_evaluate(ser, 'ROLL', kp_r, ki_r, kd_r, args.window)
                        cand_kp, cand_ki, cand_kd = kp_r, ki_r, kd_r
                    else:
                        cost = apply_and_evaluate(ser, 'PITCH', kp_p, ki_p, kd_p, args.window)
                        cand_kp, cand_ki, cand_kd = kp_p, ki_p, kd_p

                ts = int(time.time())
                print(f'Gen {it} cand {cand+1}/{args.pop} axis={cand_axis} kp={cand_kp:.5f} ki={cand_ki:.5f} kd={cand_kd:.5f} cost={cost:.5f}')
                _append_csv_row(args.log_file, [ts, it, cand+1, cand_axis, cand_kp, cand_ki, cand_kd, cost], header=csv_header)

                if cost < generation_best_cost:
                    generation_best_cost = cost
                    generation_best = {'axis': cand_axis, 'kp': cand_kp, 'ki': cand_ki, 'kd': cand_kd}

            # end population
            # Decide whether to accept generation_best
            improved = False
            if generation_best_cost < best_cost - args.tol:
                improved = True
                best_cost = generation_best_cost
                if generation_best['axis'] in ('ROLL', 'BOTH'):
                    best['Kp_roll_angle'] = generation_best['kp']
                    best['Ki_roll_angle'] = generation_best['ki']
                    best['Kd_roll_angle'] = generation_best['kd']
                if generation_best['axis'] in ('PITCH', 'BOTH'):
                    # for BOTH case the stored fields are the roll-values we used earlier; preserve symmetry
                    if generation_best['axis'] == 'BOTH':
                        # when BOTH we mutated both axes; we need to fetch current pitch from device to log
                        # (we cannot extract pitch candidate directly for BOTH in generation_best) - leave pitch unchanged for now
                        pass
                    else:
                        best['Kp_pitch_angle'] = generation_best['kp']
                        best['Ki_pitch_angle'] = generation_best['ki']
                        best['Kd_pitch_angle'] = generation_best['kd']
                # persist to flight controller
                if generation_best['axis'] in ('ROLL', 'BOTH'):
                    ser.write(APPLY_FMT.format(axis='ROLL', kp=best['Kp_roll_angle'], ki=best['Ki_roll_angle'], kd=best['Kd_roll_angle']).encode())
                    time.sleep(0.05)
                if generation_best['axis'] in ('PITCH', 'BOTH'):
                    ser.write(APPLY_FMT.format(axis='PITCH', kp=best['Kp_pitch_angle'], ki=best['Ki_pitch_angle'], kd=best['Kd_pitch_angle']).encode())
                    time.sleep(0.05)
                ser.write(SAVE_CMD.encode())
                print(f'Generation {it} -> improvement accepted (best_cost={best_cost:.5f})')
                no_improve = 0
            else:
                no_improve += 1
                print(f'Generation {it} -> no improvement (best_cost={best_cost:.5f})')

            if no_improve >= args.patience:
                print('Early stopping: no improvement for', args.patience, 'generations')
                break

            # adapt sigma if using CMAES-like method
            if args.method == 'cmaes':
                # small adaptive step-size: shrink on improvement, expand on stagnation
                if improved:
                    sigma = max(1e-4, sigma * 0.95)
                else:
                    sigma = min(2.0, sigma * 1.05)
                print(f'  [method=cmaes] sigma={sigma:.5f}')

        # finished iterations
        print('Optimization finished. Best cost=', best_cost)
        print('Best PID:', best)
    finally:
        ser.write(b'AUTOOPT STOP\n')
        ser.close()

if __name__ == '__main__':
    main()
