#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أداة توقيع/تحقق للتطوير (ECDSA P-256) — ProTrack Phase 0.

الاستخدام:
    python tools/sign_dev.py keygen [--out contract/samples/dev_key.json]
    python tools/sign_dev.py sign <file> [--key ...] [--out file.sig]
    python tools/sign_dev.py verify <file> <sig-file> [--key ...]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ecdsa_min  # noqa: E402

DEFAULT_KEY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contract", "samples", "dev_key.json"
)


def load_key(path):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    return {"d": int(d["d"], 16), "x": int(d["x"], 16), "y": int(d["y"], 16)}


def save_key(path, key):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "note": "DEV KEY ONLY — ProTrack sample tooling",
                "d": format(key["d"], "x"),
                "x": format(key["x"], "x"),
                "y": format(key["y"], "x"),
            },
            f,
            indent=2,
        )


def main():
    ap = argparse.ArgumentParser(description="ProTrack dev signing tool (ECDSA P-256)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("keygen")
    p.add_argument("--out", default=DEFAULT_KEY)

    p = sub.add_parser("sign")
    p.add_argument("file")
    p.add_argument("--key", default=DEFAULT_KEY)
    p.add_argument("--out", default=None)

    p = sub.add_parser("verify")
    p.add_argument("file")
    p.add_argument("sig")
    p.add_argument("--key", default=DEFAULT_KEY)

    args = ap.parse_args()

    if args.cmd == "keygen":
        key = ecdsa_min.generate_key()
        save_key(args.out, key)
        print("key written:", args.out)
        print("device.public_key (base64 SPKI):", ecdsa_min.public_key_spki_b64(key))
        return 0

    if args.cmd == "sign":
        key = load_key(args.key)
        with open(args.file, "rb") as f:
            data = f.read()
        sig_b64 = ecdsa_min.sign_b64(data, key)
        if args.out:
            with open(args.out, "w", encoding="ascii") as f:
                f.write(sig_b64)
            print("signature written:", args.out)
        else:
            print(sig_b64)
        return 0

    if args.cmd == "verify":
        key = load_key(args.key)
        pub = ecdsa_min.public_key_spki_b64(key)
        with open(args.file, "rb") as f:
            data = f.read()
        with open(args.sig, "r", encoding="ascii") as f:
            sig_b64 = f.read().strip()
        ok = ecdsa_min.verify_b64(pub, data, sig_b64)
        print("VERIFIED" if ok else "INVALID")
        return 0 if ok else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
