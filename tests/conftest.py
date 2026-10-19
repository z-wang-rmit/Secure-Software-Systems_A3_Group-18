# Test-only settings shared by every test file
import base64
import os

# R06: a throwaway AES key for tests (CI has no .env). Never used outside tests.
os.environ.setdefault('ROLL_KEY', base64.b64encode(b'0' * 32).decode())
