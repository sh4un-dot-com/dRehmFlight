# Quick smoke test for the Bayesian optimizer in simulation mode
# Run: python tools/test_autoopt_bayes.py

import subprocess
import sys

cmd = [sys.executable, 'tools/autoopt_bayes.py', '--simulate', '--axis', 'ROLL', '--iters', '6', '--init-samples', '4', '--candidates', '80']
print('Running:', ' '.join(cmd))
proc = subprocess.run(cmd)
print('Exit code:', proc.returncode)
