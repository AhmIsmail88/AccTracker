# -*- coding: utf-8 -*-
"""ecdsa_min.py — ECDSA P-256 (secp256r1) sign/verify for ProTrack Phase 0.

يستخدم مكتبة `cryptography` إن كانت متاحة، وإلا تنفيذاً داخلياً مكافئاً
(pure Python). صيغة التوقيع: DER (ECDSA-Sig-Value).
المفتاح العام يُنقل بصيغة X.509 SubjectPublicKeyInfo (base64) كما في
manifest.device.public_key.
"""
import base64
import hashlib
import secrets

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    HAVE_CRYPTOGRAPHY = True
except Exception:
    HAVE_CRYPTOGRAPHY = False

# ---- P-256 domain parameters ----
P = 0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
A = P - 3
B = 0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B
N = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551
GX = 0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296
GY = 0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5
G = (GX, GY)

# SPKI DER prefix for id-ecPublicKey + prime256v1, followed by 0x04 || X || Y (65 bytes)
_SPKI_PREFIX = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d030107034200")


def _inv(x, m=P):
    return pow(x % m, -1, m)


def _point_add(p1, p2):
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    x1, y1 = p1
    x2, y2 = p2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if p1 == p2:
        lam = (3 * x1 * x1 + A) * _inv(2 * y1) % P
    else:
        lam = (y2 - y1) * _inv(x2 - x1) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def _point_mul(k, point):
    result = None
    addend = point
    while k:
        if k & 1:
            result = _point_add(result, addend)
        addend = _point_add(addend, addend)
        k >>= 1
    return result


def _int_to_bytes(n, size=None):
    if size is None:
        size = max(1, (n.bit_length() + 7) // 8)
    return n.to_bytes(size, "big")


def _der_len(l):
    if l < 0x80:
        return bytes([l])
    enc = _int_to_bytes(l)
    return bytes([0x80 | len(enc)]) + enc


def _der_encode_sig(r, s):
    def der_int(x):
        b = _int_to_bytes(x)
        if b[0] & 0x80:
            b = b"\x00" + b
        return b"\x02" + _der_len(len(b)) + b

    body = der_int(r) + der_int(s)
    return b"\x30" + _der_len(len(body)) + body


def _der_read_tlv(data, idx=0):
    tag = data[idx]
    idx += 1
    l = data[idx]
    idx += 1
    if l & 0x80:
        nbytes = l & 0x7F
        l = int.from_bytes(data[idx:idx + nbytes], "big")
        idx += nbytes
    return tag, data[idx:idx + l], idx + l


def _der_decode_sig(data):
    tag, body, _ = _der_read_tlv(data, 0)
    if tag != 0x30:
        raise ValueError("bad DER signature: SEQUENCE expected")
    t1, v1, nxt = _der_read_tlv(body, 0)
    t2, v2, _end = _der_read_tlv(body, nxt)
    if t1 != 0x02 or t2 != 0x02:
        raise ValueError("bad DER signature: INTEGERs expected")
    return int.from_bytes(v1, "big"), int.from_bytes(v2, "big")


# ---- pure python implementation ----
def _pure_keygen():
    d = secrets.randbelow(N - 1) + 1
    x, y = _point_mul(d, G)
    return {"d": d, "x": x, "y": y}


def _pure_sign(data, key):
    z = int.from_bytes(hashlib.sha256(data).digest(), "big")
    d = key["d"]
    while True:
        k = secrets.randbelow(N - 1) + 1
        rx = _point_mul(k, G)[0] % N
        if rx == 0:
            continue
        s = (_inv(k, N) * (z + rx * d)) % N
        if s == 0:
            continue
        return _der_encode_sig(rx, s)


def _pure_verify(data, sig_der, x, y):
    try:
        r, s = _der_decode_sig(sig_der)
    except Exception:
        return False
    if not (1 <= r < N and 1 <= s < N):
        return False
    z = int.from_bytes(hashlib.sha256(data).digest(), "big")
    w = _inv(s, N)
    u1 = (z * w) % N
    u2 = (r * w) % N
    point = _point_add(_point_mul(u1, G), _point_mul(u2, (x, y)))
    if point is None:
        return False
    return point[0] % N == r


def _pure_spki_from_pub(x, y):
    return _SPKI_PREFIX + b"\x04" + _int_to_bytes(x, 32) + _int_to_bytes(y, 32)


def _pure_pub_from_spki(spki_der):
    if not spki_der.startswith(_SPKI_PREFIX):
        raise ValueError("unsupported public key format (P-256 SPKI expected)")
    point = spki_der[len(_SPKI_PREFIX):]
    if len(point) != 65 or point[0] != 0x04:
        raise ValueError("bad EC point encoding")
    return int.from_bytes(point[1:33], "big"), int.from_bytes(point[33:65], "big")


# ---- public API ----
def generate_key():
    if HAVE_CRYPTOGRAPHY:
        wk = ec.generate_private_key(ec.SECP256R1())
        nums = wk.private_numbers()
        return {"d": nums.private_value, "x": nums.public_numbers.x, "y": nums.public_numbers.y}
    return _pure_keygen()


def public_key_spki_b64(key):
    if HAVE_CRYPTOGRAPHY:
        wk = ec.derive_private_key(key["d"], ec.SECP256R1())
        der = wk.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        return base64.b64encode(der).decode("ascii")
    return base64.b64encode(_pure_spki_from_pub(key["x"], key["y"])).decode("ascii")


def sign(data, key):
    """Returns DER-encoded ECDSA P-256 signature over sha256(data)."""
    if HAVE_CRYPTOGRAPHY:
        wk = ec.derive_private_key(key["d"], ec.SECP256R1())
        return wk.sign(data, ec.ECDSA(hashes.SHA256()))
    return _pure_sign(data, key)


def sign_b64(data, key):
    return base64.b64encode(sign(data, key)).decode("ascii")


def verify(spki_b64, data, sig_der, force_pure=False):
    try:
        spki_der = base64.b64decode(spki_b64)
    except Exception:
        return False
    if HAVE_CRYPTOGRAPHY and not force_pure:
        try:
            pubkey = serialization.load_der_public_key(spki_der)
            pubkey.verify(sig_der, data, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
        except Exception:
            pass  # fall through to the pure implementation
    try:
        x, y = _pure_pub_from_spki(spki_der)
    except Exception:
        return False
    return _pure_verify(data, sig_der, x, y)


def verify_b64(spki_b64, data, sig_b64, force_pure=False):
    try:
        sig_der = base64.b64decode(sig_b64)
    except Exception:
        return False
    return verify(spki_b64, data, sig_der, force_pure=force_pure)


def fingerprint(spki_b64):
    return hashlib.sha256(base64.b64decode(spki_b64)).hexdigest()[:8].upper()
