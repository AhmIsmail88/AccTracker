#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ProTrack Phase 0 — full automated checks (stdlib-only).

الاستخدام:  python tests/run_tests.py
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = os.path.join(ROOT, "tools")
SAMPLES = os.path.join(ROOT, "contract", "samples")
TMP = os.path.join(HERE, "_tmp")

sys.path.insert(0, TOOLS)
import ecdsa_min  # noqa: E402
import xlsx_min  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def status_of(stdout):
    for line in stdout.splitlines():
        if line.startswith("STATUS: "):
            return line.split(":", 1)[1].strip()
    return None


def main():
    results = []
    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)

    # 0) ECDSA self-test
    key = ecdsa_min.generate_key()
    data = b"protrack-selftest"
    sig = ecdsa_min.sign(data, key)
    pub = ecdsa_min.public_key_spki_b64(key)
    ok = ecdsa_min.verify(pub, data, sig)
    ok = ok and not ecdsa_min.verify(pub, b"tampered", sig)
    bad_sig = sig[:-1] + bytes([sig[-1] ^ 1])
    ok = ok and not ecdsa_min.verify(pub, data, bad_sig)
    results.append(("ecdsa sign/verify roundtrip + tamper detect", ok))
    if getattr(ecdsa_min, "HAVE_CRYPTOGRAPHY", False):
        ok2 = ecdsa_min.verify(pub, data, sig, force_pure=True)
        results.append(("ecdsa pure-path cross-check (vs cryptography)", ok2))

    # 1) xlsx roundtrip
    wb = xlsx_min.write_workbook_bytes([("A", [["h1", "h2"], [1, "x"]]), ("B", [["q"], [None]])])
    rd = xlsx_min.read_workbook(wb)
    ok = (
        rd.get("A", [[], [], []])[1][0] == 1
        and rd.get("A", [[], [], []])[1][1] == "x"
        and rd.get("B", [[]])[0][0] == "q"
    )
    results.append(("xlsx write/read roundtrip", ok))

    # 2) build samples
    r = run([sys.executable, os.path.join(TOOLS, "make_sample_package.py")])
    results.append(("sample packages built", r.returncode == 0))
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)

    def check(label, name, expected, db=None):
        cmd = [sys.executable, os.path.join(TOOLS, "validate_package.py"), os.path.join(SAMPLES, name)]
        if db:
            cmd += ["--seen-db", db]
        r2 = run(cmd)
        s = status_of(r2.stdout)
        ok2 = s == expected
        results.append((label, ok2))
        if not ok2:
            print("---- validator output (%s) ----" % name)
            print(r2.stdout)
            print(r2.stderr)

    db1 = os.path.join(TMP, "seen_valid.json")
    check("valid -> PASS", "valid_package.zip", "PASS", db1)
    check("tampered -> FAIL", "tampered_package.zip", "FAIL")
    check("duplicate -> DUPLICATE", "valid_package.zip", "DUPLICATE", db1)
    check("unsigned -> REJECT", "unsigned_package.zip", "REJECT")
    check("invalid photo -> FLAG", "invalid_photo_package.zip", "FLAG")
    check("hierarchy conflict -> FLAG", "hierarchy_conflict_package.zip", "FLAG")

    # 3) make sure signature verification actually executed (not skipped)
    r3 = run([sys.executable, os.path.join(TOOLS, "validate_package.py"), os.path.join(SAMPLES, "valid_package.zip")])
    results.append(("signature verification executed (ECDSA P-256)", "signature verified" in r3.stdout))

    print()
    print("================== TEST SUMMARY ==================")
    all_ok = True
    for name, ok in results:
        print(("  PASS  " if ok else "  FAIL  ") + "- " + name)
        all_ok = all_ok and ok
    print("==================================================")
    print("ALL TESTS PASSED" if all_ok else "SOME TESTS FAILED")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
