"""Start a real HTTP application process and verify readiness."""
import subprocess,sys,time,urllib.request
from pathlib import Path

def test_real_server_launch():
    path=Path('evidence/launch_test.log')
    with path.open('w') as log:
        p=subprocess.Popen([sys.executable,'-m','streamlit','run','app.py','--server.port=8512','--server.headless=true'],stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+25; healthy=False
            while time.monotonic()<deadline:
                if p.poll() is not None: break
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8512/_stcore/health',timeout=1) as response:
                        healthy=response.status==200
                    if healthy: break
                except OSError: time.sleep(.2)
            assert healthy, path.read_text()
            with urllib.request.urlopen('http://127.0.0.1:8512/',timeout=3) as response:
                assert b'<html' in response.read().lower()
        finally:
            p.terminate()
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
