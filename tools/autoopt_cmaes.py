"""
A compact, dependency-free CMA-ES (diagonal/sep-CMA-like) optimizer for dRehmFlight.
- Optimizes Kp/Ki/Kd for ROLL, PITCH, or BOTH (3 or 6 parameters)
- Communicates with the flight controller over serial using APPLY_GAINS and AUTOOPT stream
- Bound support, CSV logging, and safe revert behavior

Usage (bench, props off):
  python tools/autoopt_cmaes.py --port COM3 --axis ROLL --iters 40 --pop 12

WARNING: bench test only (props removed). Use conservative sigma and bounds.
"""
import argparse
import math
import random
import time
import json
import serial
import os

OPT_PREFIX = 'OPT,'
REC_PREFIX = 'REC,'
GET_PID = 'GET PID\n'
APPLY_FMT = 'APPLY_GAINS {axis} {kp} {ki} {kd}\n'
SAVE_CMD = 'SAVE PARAMS\n'


def read_json_line(line):
    try:
        return json.loads(line)
    except Exception:
        return None


def get_pid(ser, timeout=1.0):
    ser.reset_input_buffer()
    ser.write(GET_PID.encode())
    t0 = time.time()
    while time.time() - t0 < timeout:
        line = ser.readline().decode(errors='ignore').strip()
        if line.startswith('{') and 'Kp_roll_angle' in line:
            try:
                return json.loads(line)
            except Exception:
                pass
    return None


def evaluate_cost(ser, duration):
    t0 = time.time()
    samples = []
    ser.timeout = 0.25
    while time.time() - t0 < duration:
        line = ser.readline().decode(errors='ignore').strip()
        if not line:
            continue
        if line.startswith(OPT_PREFIX):
            parts = line.split(',')
            try:
                roll = float(parts[3]); pitch = float(parts[4])
                samples.append(abs(roll) + abs(pitch))
            except Exception:
                pass
        elif line.startswith(REC_PREFIX):
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


def _append_csv_row(path, row, header=None):
    first = not os.path.exists(path)
    with open(path, 'a') as f:
        if first and header:
            f.write(header + '\n')
        f.write(','.join(map(str, row)) + '\n')


def cmales_optimize(args):
    ser = serial.Serial(args.port, args.baud, timeout=0.2)
    time.sleep(1.0)
    pid = get_pid(ser)
    if not pid:
        print('Failed to read PID (GET PID), aborting')
        return
    print('Current PID:', pid)

    # build initial mean vector m
    if args.axis == 'ROLL':
        m = [pid['Kp_roll_angle'], pid['Ki_roll_angle'], pid['Kd_roll_angle']]
    elif args.axis == 'PITCH':
        m = [pid['Kp_pitch_angle'], pid['Ki_pitch_angle'], pid['Kd_pitch_angle']]
    else:  # BOTH
        m = [pid['Kp_roll_angle'], pid['Ki_roll_angle'], pid['Kd_roll_angle'], pid['Kp_pitch_angle'], pid['Ki_pitch_angle'], pid['Kd_pitch_angle']]

    d = len(m)
    sigma = args.sigma
    # diagonal variances (start small but not zero)
    v = [max(1e-6, (abs(x) + 1e-3) * 0.5) for x in m]

    lam = max(4, args.pop)
    mu = max(1, lam // 2)
    # recombination weights (log-based)
    weights = [max(0.0, math.log(mu + 0.5) - math.log(i + 1)) for i in range(mu)]
    s = sum(weights)
    weights = [w / s for w in weights]
    mu_eff = 1.0 / sum([w * w for w in weights])

    # learning rates (sep-CMA-like simplification)
    c_sigma = (mu_eff + 2) / (d + mu_eff + 3)
    d_sigma = 1 + 2 * max(0, math.sqrt((mu_eff - 1) / (d + 1)) - 1) + c_sigma
    c_v = 2.0 / (d + 4.0)  # diagonal covariance learning rate

    p_sigma = [0.0] * d

    best_cost = float('inf')
    best_params = list(m)

    ser.write(b'AUTOOPT START\n')
    time.sleep(0.1)

    csv_header = 'ts,gen,idx,cost,params'

    for gen in range(1, args.iters + 1):
        # sample lambda offspring
        offspring = []  # tuples (params, y_vector)
        for k in range(lam):
            z = [random.gauss(0, 1) for _ in range(d)]
            y = [math.sqrt(v_i) * z_i for v_i, z_i in zip(v, z)]
            x = [m_i + sigma * y_i for m_i, y_i in zip(m, y)]
            # clamp to bounds
            for i in range(d):
                x[i] = max(args.min_gain, min(args.max_gain, x[i]))
            offspring.append((x, y))

        # evaluate offspring
        results = []
        for idx, (x, y) in enumerate(offspring):
            # apply to flight controller (axis-wise)
            if args.axis == 'ROLL':
                cmd = APPLY_FMT.format(axis='ROLL', kp=x[0], ki=x[1], kd=x[2])
                ser.write(cmd.encode()); time.sleep(0.05)
            elif args.axis == 'PITCH':
                cmd = APPLY_FMT.format(axis='PITCH', kp=x[0], ki=x[1], kd=x[2])
                ser.write(cmd.encode()); time.sleep(0.05)
            else:  # BOTH
                cmd1 = APPLY_FMT.format(axis='ROLL', kp=x[0], ki=x[1], kd=x[2])
                cmd2 = APPLY_FMT.format(axis='PITCH', kp=x[3], ki=x[4], kd=x[5])
                ser.write(cmd1.encode()); time.sleep(0.02)
                ser.write(cmd2.encode()); time.sleep(0.05)

            cost = evaluate_cost(ser, args.window)
            print(f'Gen {gen} cand {idx+1}/{lam} cost={cost:.5f}')
            _append_csv_row(args.log_file, [int(time.time()), gen, idx+1, cost, x], header=csv_header)
            results.append((cost, x, y))

        # sort by cost ascending
        results.sort(key=lambda r: r[0])
        # update mean m (weighted recombination)
        m_new = [0.0] * d
        for i in range(mu):
            w = weights[i]
            x_i = results[i][1]
            for j in range(d):
                m_new[j] += w * x_i[j]

        # update paths and sigma (using elementwise normalization by sqrt(v))
        y_w = [ (m_new[j] - m[j]) / sigma for j in range(d) ]
        # normalized y for p_sigma update
        y_normed = [ y_w[j] / math.sqrt(max(1e-12, v[j])) for j in range(d) ]
        coef = math.sqrt(c_sigma * (2 - c_sigma) * mu_eff)
        for j in range(d):
            p_sigma[j] = (1 - c_sigma) * p_sigma[j] + coef * y_normed[j]
        # update sigma
        norm_p = math.sqrt(sum([p_sigma_j * p_sigma_j for p_sigma_j in p_sigma]))
        expected_norm = math.sqrt(d) * (1.0 - 1.0/(4.0*d) + 1.0/(21.0*d*d))
        sigma *= math.exp((c_sigma / d_sigma) * (norm_p / expected_norm - 1.0))

        # update diagonal variance v
        # v = (1 - c_v) * v + c_v * sum_i w_i * ((x_i - m)/sigma)^2
        new_v = [ (1 - c_v) * v_j for v_j in v ]
        for i in range(mu):
            w = weights[i]
            x_i = results[i][1]
            for j in range(d):
                delta = (x_i[j] - m[j]) / sigma
                new_v[j] += c_v * w * (delta * delta)
        v = [ max(1e-12, vv) for vv in new_v ]

        # accept new mean
        m = list(m_new)

        # check best in this generation
        gen_best_cost, gen_best_params, _ = results[0]
        if gen_best_cost < best_cost:
            best_cost = gen_best_cost
            best_params = list(gen_best_params)
            print(f'Gen {gen} -> new best cost={best_cost:.5f} (saving to FC)')
            # persist to FC
            if args.axis == 'ROLL':
                ser.write(APPLY_FMT.format(axis='ROLL', kp=best_params[0], ki=best_params[1], kd=best_params[2]).encode())
            elif args.axis == 'PITCH':
                ser.write(APPLY_FMT.format(axis='PITCH', kp=best_params[0], ki=best_params[1], kd=best_params[2]).encode())
            else:
                ser.write(APPLY_FMT.format(axis='ROLL', kp=best_params[0], ki=best_params[1], kd=best_params[2]).encode()); time.sleep(0.02)
                ser.write(APPLY_FMT.format(axis='PITCH', kp=best_params[3], ki=best_params[4], kd=best_params[5]).encode())
            ser.write(SAVE_CMD.encode())

    ser.write(b'AUTOOPT STOP\n')
    ser.close()
    print('CMA-ES optimization finished. Best cost=', best_cost)
    print('Best params =', best_params)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', required=True)
    p.add_argument('--baud', type=int, default=500000)
    p.add_argument('--axis', choices=['ROLL','PITCH','BOTH'], default='ROLL')
    p.add_argument('--iters', type=int, default=40)
    p.add_argument('--pop', type=int, default=12)
    p.add_argument('--sigma', type=float, default=0.2)
    p.add_argument('--window', type=float, default=3.0)
    p.add_argument('--min-gain', type=float, default=0.0)
    p.add_argument('--max-gain', type=float, default=5.0)
    p.add_argument('--log-file', default='tools/autoopt_cmaes_results.csv')
    args = p.parse_args()
    cmales_optimize(args)
