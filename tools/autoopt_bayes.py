"""
Lightweight Bayesian-style optimizer for dRehmFlight (surrogate + EI acquisition).
- Surrogate: separable quadratic regression (no external deps)
- Acquisition: approximate Expected Improvement using surrogate mean + residual variance
- Safe, bounded search; supports simulation mode for unit testing

Usage (bench, props OFF):
  python tools/autoopt_bayes.py --port COM3 --axis ROLL --iters 30 --init 6 --cands 100

Simulation test:
  python tools/autoopt_bayes.py --simulate --axis ROLL
"""
import argparse
import math
import random
import time
import json
import os

OPT_PREFIX = 'OPT,'
REC_PREFIX = 'REC,'
GET_PID = 'GET PID\n'
APPLY_FMT = 'APPLY_GAINS {axis} {kp} {ki} {kd}\n'
SAVE_CMD = 'SAVE PARAMS\n'

# ------------------------- utility math (no numpy) -------------------------

def mat_mul(A, B):
    # A: n x m, B: m x p -> C: n x p
    n = len(A); m = len(A[0]); p = len(B[0])
    C = [[0.0]*p for _ in range(n)]
    for i in range(n):
        for k in range(m):
            aik = A[i][k]
            if aik == 0.0: continue
            for j in range(p):
                C[i][j] += aik * B[k][j]
    return C


def mat_transpose(A):
    return list(map(list, zip(*A)))


def mat_solve(A, b):
    # Solve Ax = b using Gaussian elimination with partial pivoting (A square)
    n = len(A)
    # build augmented matrix
    M = [row[:] + [b_i] for row, b_i in zip([r[:] for r in A], b)]
    for k in range(n):
        # pivot
        piv = max(range(k, n), key=lambda i: abs(M[i][k]))
        if abs(M[piv][k]) < 1e-12:
            raise RuntimeError('Singular matrix in mat_solve')
        M[k], M[piv] = M[piv], M[k]
        # normalize
        pivot = M[k][k]
        for j in range(k, n+1):
            M[k][j] /= pivot
        for i in range(n):
            if i == k: continue
            factor = M[i][k]
            if factor == 0.0: continue
            for j in range(k, n+1):
                M[i][j] -= factor * M[k][j]
    return [M[i][n] for i in range(n)]

# ------------------------- surrogate: separable quadratic -------------------------

def build_design_matrix(X):
    # X: list of d-dim vectors
    # basis: [1, x1, x2, ..., x_d, x1^2, x2^2, ..., x_d^2]
    D = len(X[0])
    Phi = []
    for x in X:
        row = [1.0]
        for xi in x: row.append(xi)
        for xi in x: row.append(xi*xi)
        Phi.append(row)
    return Phi


def fit_quadratic_surrogate(X, y):
    # returns coefficients c for basis above (m = 1 + D + D)
    Phi = build_design_matrix(X)
    PT = mat_transpose(Phi)
    PT_P = mat_mul(PT, Phi)
    PT_y = mat_mul(PT, [[val] for val in y])
    PT_y = [row[0] for row in PT_y]
    try:
        coeffs = mat_solve(PT_P, PT_y)
    except Exception:
        # fallback to zeros
        coeffs = [0.0] * (1 + len(X[0]) * 2)
    return coeffs


def surrogate_predict(coeffs, x):
    v = 1.0
    for xi in x: v += coeffs[len(coeffs) - 1] * 0  # no-op to avoid unused
    # evaluate
    out = coeffs[0]
    D = (len(coeffs) - 1) // 2
    for i in range(D): out += coeffs[1 + i] * x[i]
    for i in range(D): out += coeffs[1 + D + i] * x[i] * x[i]
    return out

# ------------------------- acquisition: Expected Improvement -------------------------

def normal_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def expected_improvement(mu, sigma, f_best):
    # minimization
    if sigma <= 1e-8:
        return max(0.0, f_best - mu)
    z = (f_best - mu) / sigma
    return (f_best - mu) * normal_cdf(z) + sigma * normal_pdf(z)

# ------------------------- flight I/O helpers -------------------------

def parse_opt_line(line):
    # OPT,t_ms,loop_us,roll,pitch,yaw,...
    try:
        parts = line.split(',')
        roll = float(parts[3]); pitch = float(parts[4])
        return abs(roll) + abs(pitch)
    except Exception:
        return None


def evaluate_cost_from_serial(ser, duration):
    t0 = time.time(); samples = []
    ser.timeout = 0.2
    while time.time() - t0 < duration:
        line = ser.readline().decode(errors='ignore').strip()
        if not line: continue
        if line.startswith(OPT_PREFIX) or line.startswith(REC_PREFIX):
            val = parse_opt_line(line)
            if val is not None: samples.append(val)
        elif line.startswith('{'):
            try:
                j = json.loads(line); samples.append(abs(j['roll']) + abs(j['pitch']))
            except Exception:
                pass
    if not samples: return float('inf')
    return sum(samples) / len(samples)

# ------------------------- optimizer (main) -------------------------

def bayes_optimize(args):
    # communication with FC if not simulate
    if not args.simulate:
        import serial
        ser = serial.Serial(args.port, args.baud, timeout=0.2)
        time.sleep(1.0)
        pid = None
        # try read PID
        ser.write(GET_PID.encode())
        t0 = time.time()
        while time.time() - t0 < 1.0:
            line = ser.readline().decode(errors='ignore').strip()
            if line.startswith('{') and 'Kp_roll_angle' in line:
                try: pid = json.loads(line); break
                except Exception: pass
        if not pid:
            print('WARN: GET PID failed; continuing with defaults')
            pid = {'Kp_roll_angle':0.2,'Ki_roll_angle':0.3,'Kd_roll_angle':0.05,'Kp_pitch_angle':0.2,'Ki_pitch_angle':0.3,'Kd_pitch_angle':0.05}
    else:
        ser = None
        pid = {'Kp_roll_angle':0.2,'Ki_roll_angle':0.3,'Kd_roll_angle':0.05,'Kp_pitch_angle':0.2,'Ki_pitch_angle':0.3,'Kd_pitch_angle':0.05}

    # parameter vector depending on axis
    if args.axis == 'ROLL':
        x0 = [pid['Kp_roll_angle'], pid['Ki_roll_angle'], pid['Kd_roll_angle']]
    elif args.axis == 'PITCH':
        x0 = [pid['Kp_pitch_angle'], pid['Ki_pitch_angle'], pid['Kd_pitch_angle']]
    else:
        x0 = [pid['Kp_roll_angle'], pid['Ki_roll_angle'], pid['Kd_roll_angle'], pid['Kp_pitch_angle'], pid['Ki_pitch_angle'], pid['Kd_pitch_angle']]

    D = len(x0)
    bounds = [(args.min_gain, args.max_gain)] * D

    # initial samples (random around x0)
    X = []
    Y = []
    for i in range(max(1, args.init_samples)):
        if args.simulate:
            x = [max(bounds[j][0], min(bounds[j][1], x0[j] * (1.0 + random.uniform(-0.2, 0.2)))) for j in range(D)]
            # synthetic objective: simple quadratic bowl centered near good gains
            y = sum((xi - (x0[j]*0.9))**2 for j, xi in enumerate(x))
        else:
            x = [max(bounds[j][0], min(bounds[j][1], x0[j] * (1.0 + random.uniform(-0.2, 0.2)))) for j in range(D)]
            # apply gains to FC
            if args.axis == 'ROLL':
                ser.write(APPLY_FMT.format(axis='ROLL', kp=x[0], ki=x[1], kd=x[2]).encode()); time.sleep(0.1)
            elif args.axis == 'PITCH':
                ser.write(APPLY_FMT.format(axis='PITCH', kp=x[0], ki=x[1], kd=x[2]).encode()); time.sleep(0.1)
            else:
                ser.write(APPLY_FMT.format(axis='ROLL', kp=x[0], ki=x[1], kd=x[2]).encode()); time.sleep(0.05)
                ser.write(APPLY_FMT.format(axis='PITCH', kp=x[3], ki=x[4], kd=x[5]).encode()); time.sleep(0.1)
            y = evaluate_cost_from_serial(ser, args.window)
        X.append(x); Y.append(y)
        print(f'init sample {i+1}/{args.init_samples} y={y:.5f}')

    f_best = min(Y)
    best_x = X[Y.index(f_best)]

    # main loop
    csv_header = 'ts,iter,cand,mu,sigma,ei,cost,params'
    for it in range(1, args.iters+1):
        # fit surrogate
        coeffs = fit_quadratic_surrogate(X, Y)
        # residual-based variance estimate
        preds = [surrogate_predict(coeffs, x) for x in X]
        resid_var = 1e-6
        if len(Y) - len(coeffs) > 0:
            ss = sum((yy - pp)**2 for yy, pp in zip(Y, preds))
            resid_var = ss / max(1, (len(Y) - len(coeffs)))
        sigma_hat = math.sqrt(max(1e-12, resid_var))

        # propose several candidates by sampling around best_x and evaluate EI using surrogate
        candidates = []
        for c in range(args.candidates):
            cand = []
            for d in range(D):
                r = random.gauss(0, args.proposal_std)
                v = best_x[d] * (1.0 + r)
                v = max(bounds[d][0], min(bounds[d][1], v))
                cand.append(v)
            mu = surrogate_predict(coeffs, cand)
            ei = expected_improvement(mu, sigma_hat, f_best)
            candidates.append((ei, cand, mu))
        candidates.sort(key=lambda z: -z[0])

        # evaluate top-K candidates (K=1 by default)
        topk = candidates[:args.eval_topk]
        improved = False
        for idx, (ei, cand, mu) in enumerate(topk):
            if args.simulate:
                cost = sum((ci - (x0[j]*0.9))**2 for j, ci in enumerate(cand))
            else:
                if args.axis == 'ROLL':
                    ser.write(APPLY_FMT.format(axis='ROLL', kp=cand[0], ki=cand[1], kd=cand[2]).encode()); time.sleep(0.1)
                elif args.axis == 'PITCH':
                    ser.write(APPLY_FMT.format(axis='PITCH', kp=cand[0], ki=cand[1], kd=cand[2]).encode()); time.sleep(0.1)
                else:
                    ser.write(APPLY_FMT.format(axis='ROLL', kp=cand[0], ki=cand[1], kd=cand[2]).encode()); time.sleep(0.05)
                    ser.write(APPLY_FMT.format(axis='PITCH', kp=cand[3], ki=cand[4], kd=cand[5]).encode()); time.sleep(0.1)
                cost = evaluate_cost_from_serial(ser, args.window)

            ts = int(time.time())
            _row = [ts, it, idx+1, mu, sigma_hat, ei, cost, cand]
            with open(args.log_file, 'a') as f:
                if os.stat(args.log_file).st_size == 0:
                    f.write(csv_header + '\n')
                f.write(','.join(map(str, _row)) + '\n')

            print(f'Iter {it} cand {idx+1} mu={mu:.4f} ei={ei:.6f} cost={cost:.5f}')

            X.append(cand); Y.append(cost)
            if cost < f_best - args.tol:
                f_best = cost; best_x = cand; improved = True
                print('  -> improvement, saving to FC')
                if not args.simulate:
                    ser.write(SAVE_CMD.encode()); time.sleep(0.05)
        if not improved:
            print(f'Iter {it}: no improvement (best={f_best:.5f})')

    if not args.simulate:
        ser.write(b'AUTOOPT STOP\n'); ser.close()
    print('Bayes-style optimization finished. best=', f_best, 'params=', best_x)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', required=False)
    p.add_argument('--baud', type=int, default=500000)
    p.add_argument('--axis', choices=['ROLL','PITCH','BOTH'], default='ROLL')
    p.add_argument('--iters', type=int, default=20)
    p.add_argument('--init-samples', type=int, default=6)
    p.add_argument('--candidates', type=int, default=200)
    p.add_argument('--eval-topk', type=int, default=1)
    p.add_argument('--proposal-std', type=float, default=0.1)
    p.add_argument('--window', type=float, default=3.0)
    p.add_argument('--min-gain', type=float, default=0.0)
    p.add_argument('--max-gain', type=float, default=5.0)
    p.add_argument('--log-file', default='tools/autoopt_bayes_results.csv')
    p.add_argument('--tol', type=float, default=1e-4)
    p.add_argument('--simulate', action='store_true', help='run in simulation mode (no FC)')
    p.add_argument('--candidates-per-iter', type=int, default=200)
    args = p.parse_args()
    # alias
    args.candidates = args.candidates_per_iter if hasattr(args, 'candidates_per_iter') else args.candidates
    bayes_optimize(args)
