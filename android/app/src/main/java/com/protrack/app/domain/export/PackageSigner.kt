package com.protrack.app.domain.export

import java.security.KeyPair
import java.security.Signature
import java.util.Base64

/** واجهة توقيع الجهاز (ECDSA P-256 → DER). */
interface PackageSigner {
    fun sign(data: ByteArray): ByteArray
    fun publicKeyBase64(): String
}

/** تنفيذ JCA — يُستخدم في فحوص الوحدة؛ الجهاز يستخدم Android Keystore. */
class JcaPackageSigner(private val keyPair: KeyPair) : PackageSigner {

    override fun sign(data: ByteArray): ByteArray =
        Signature.getInstance("SHA256withECDSA").run {
            initSign(keyPair.private)
            update(data)
            sign()
        }

    override fun publicKeyBase64(): String =
        Base64.getEncoder().encodeToString(keyPair.public.encoded)
}
