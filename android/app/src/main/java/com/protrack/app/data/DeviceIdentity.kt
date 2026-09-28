package com.protrack.app.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.protrack.app.domain.export.PackageSigner
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.MessageDigest
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.UUID

/**
 * هوية الجهاز: مفتاح ECDSA P-256 داخل Android Keystore + معرّف ثابت للجهاز.
 */
class DeviceInfoProvider(private val context: Context) {

    private val prefs = context.getSharedPreferences("protrack_device", Context.MODE_PRIVATE)

    val signer: PackageSigner by lazy { AndroidKeystoreSigner() }

    fun deviceId(): String {
        val existing = prefs.getString("device_id", null)
        if (existing != null) return existing
        val id = UUID.randomUUID().toString()
        prefs.edit().putString("device_id", id).apply()
        return id
    }

    fun publicKeyB64(): String = signer.publicKeyBase64()

    fun fingerprint(): String {
        val digest = MessageDigest.getInstance("SHA-256")
            .digest(publicKeyB64().toByteArray(Charsets.UTF_8))
        return digest.take(4).joinToString("") { "%02X".format(it) }
    }
}

class AndroidKeystoreSigner(private val alias: String = "protrack_device_key") : PackageSigner {

    private val keyStore: KeyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    init {
        if (!keyStore.containsAlias(alias)) {
            val kpg = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore")
            val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .build()
            kpg.initialize(spec)
            kpg.generateKeyPair()
        }
    }

    override fun sign(data: ByteArray): ByteArray {
        val key = (keyStore.getEntry(alias, null) as KeyStore.PrivateKeyEntry).privateKey
        val signature = Signature.getInstance("SHA256withECDSA")
        signature.initSign(key)
        signature.update(data)
        return signature.sign()
    }

    override fun publicKeyBase64(): String {
        val cert = keyStore.getCertificate(alias) ?: throw IllegalStateException("device key missing")
        return Base64.encodeToString(cert.publicKey.encoded, Base64.NO_WRAP)
    }
}
