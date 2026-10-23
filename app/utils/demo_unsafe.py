# R20 DEMO ONLY - never merge. A deliberately unsafe line to show bandit failing in CI.
import subprocess


def run_report(name):
    # command injection: the user-controlled name goes straight into a shell command
    return subprocess.call('generate-report ' + name, shell=True)
