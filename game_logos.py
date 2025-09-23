# get_game_logos.py
import os, zipfile, time, sys
from pathlib import Path

import requests

OUT_DIR = Path("logos")
ZIP_NAME = "game_logos.zip"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DeltaCrown-LogoFetcher/1.0"
TIMEOUT = 60

FILES = {
    "valorant.svg": "https://en.wikipedia.org/wiki/Special:FilePath/Valorant%20logo.svg",
    "efootball.svg": "https://commons.wikimedia.org/wiki/Special:FilePath/EFootball_logo.svg",
    "pubg.svg": "https://commons.wikimedia.org/wiki/Special:FilePath/PlayerUnknown%27s_Battlegrounds_Logo.svg",
    "freefire.png": "https://en.wikipedia.org/wiki/Special:FilePath/Logo_of_Garena_Free_Fire.png",
    "codm.svg": "https://commons.wikimedia.org/wiki/Special:FilePath/Call_of_Duty_Mobile_2023_logo.svg",
    "mlbb.svg": "https://en.wikipedia.org/wiki/Special:FilePath/Mobile-legends-logo.svg",
    "csgo.svg": "https://commons.wikimedia.org/wiki/Special:FilePath/Counter-Strike_Global_Offensive.svg",
    "fc26.svg": "https://commons.wikimedia.org/wiki/Special:FilePath/EA_Sports_FC_logo.svg",
}

def fetch(url, out):
    for attempt in range(1, 4):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT, allow_redirects=True)
            if r.status_code == 200 and r.content:
                out.write_bytes(r.content)
                return True
        except requests.RequestException:
            pass
        time.sleep(0.8 * attempt)
    return False

def main():
    OUT_DIR.mkdir(exist_ok=True, parents=True)
    ok, fail = [], []

    for name, url in FILES.items():
        out_path = OUT_DIR / name
        print(f"Downloading {name} ...")
        if fetch(url, out_path):
            ok.append(name)
        else:
            fail.append(name)

    with zipfile.ZipFile(ZIP_NAME, "w", zipfile.ZIP_DEFLATED) as z:
        for p in OUT_DIR.iterdir():
            if p.is_file():
                z.write(p, arcname=p.name)

    print("\n=== Download Report ===")
    for n in ok: print(f"[OK] {n}")
    for n in fail: print(f"[FAIL] {n}")
    print(f"\n✅ Done. Created: {Path(ZIP_NAME).resolve()}")

if __name__ == "__main__":
    try:
        import requests  # noqa
    except Exception:
        print("Install dependency first: pip install requests", file=sys.stderr)
        sys.exit(1)
    main()
