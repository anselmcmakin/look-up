# Look Up engine installer v1.0.0: download, verify sha256, install, init. Fails loudly; installs nothing unless every file verifies.
import hashlib, os, subprocess, sys, urllib.request
TAG = "v1.0.0"
BASE = os.environ.get("LOOKUP_BASE_URL", "https://raw.githubusercontent.com/anselmcmakin/look-up/" + TAG).rstrip("/")
D = os.environ.get("LOOKUP_DIR", "/workspace/look-up")
SHA = {
 "engine/card.py": "1e59e990852f9fa8373b321ff68b2c41de9948e1acf6c4ad03eac585200f10ba",
 "engine/core.py": "5212eaa900b73a869b83fa1e358cd3b73cb4f3a0f90bc70f09e0cda04f89e016",
 "engine/events.py": "17031d24328bc8e24d2884f20413e2677a645c2f05956159a40039ba443c9ddf",
 "engine/facts.py": "91ef4c36edfdbc8e7881ffa9552c5feb33b77d0bc699d0989915e510733687c2",
 "engine/facts_sky.py": "97122a7e61ca07f7b67e51c1d4713d3dcd22a15b651d24dc0aa24c3cd54036b3",
 "engine/highlight.py": "12cdea2fe48811f3d56b283f947506ec42aac4a3aca4478583d1be35243ef2b1",
 "engine/hours.py": "27db564c6827824543910848b1fd4726ff7e05e2f0e73ff0b7b9db202e4c9e48",
 "engine/night.py": "c9f6d4bf6dfad43239a9d8b8bbeacd8aa6b2d9a06c5952745aed672d96e05e19",
 "engine/sky.py": "6db9e1538c66232e61711df97f2b9c326a1b7fe662f7465cfa4fa04f6b9dc5fd",
 "engine/stars.py": "3e0678d31888963bb9f2dec305d8087b5db9870974a8d71954b1a16bd8ba67c7",
 "engine/tonight.py": "0537808c33acee2f877489ed99dce1e24413e5d2b778371007706512c0639499",
 "engine/words.py": "d9fd97fd67470a0ab63f5171a6c43f00d2390da9edf7cde695dbc761a0fcf0ab",
}
def die(m): print("LOOK UP INSTALL FAILED: " + m, file=sys.stderr); sys.exit(1)
if "{" in BASE: die("the download URL still contains a placeholder: " + BASE)
got = {}
for p, want in SHA.items():
    u = BASE + "/" + p
    try:
        with urllib.request.urlopen(u, timeout=60) as r: b = r.read()
    except Exception as e: die(f"could not download {u} ({e}). Nothing was installed.")
    h = hashlib.sha256(b).hexdigest()
    if h != want: die(f"checksum mismatch for {p}: expected {want}, got {h}. Nothing was installed.")
    got[p.split("/")[-1]] = b
try: import skyfield, timezonefinder, PIL, pillow_heif, exifread, matplotlib, requests  # noqa: F401
except ImportError:
    pk = ["skyfield", "timezonefinder", "Pillow", "pillow-heif", "exifread", "matplotlib", "requests"]
    pip = [sys.executable, "-m", "pip", "install", "-q"]
    if subprocess.call(pip + pk) and subprocess.call(pip + ["--break-system-packages"] + pk): die("pip could not install the Python libraries.")
os.makedirs(D, exist_ok=True)
if os.path.exists(D + "/ENGINE"): os.remove(D + "/ENGINE")
for n, b in got.items():
    with open(f"{D}/{n}.part", "wb") as f: f.write(b)
    os.replace(f"{D}/{n}.part", f"{D}/{n}")
r = subprocess.run([sys.executable, D + "/core.py", "init"], capture_output=True, text=True)
if r.returncode: die("core.py init failed: " + r.stderr[-600:])
open(D + "/ENGINE", "w").write("look-up " + TAG + "\n")
print(f"Look Up engine {TAG} installed: {len(got)} files verified in {D}")
