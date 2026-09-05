package com.fr0333.ravenphoneaudit;

import android.content.ContentValues;
import android.content.Context;
import android.content.res.AssetManager;
import android.net.Uri;

import com.fr0333.ravenphoneaudit.provider.InternalTelemetryChannel;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

public final class TaxonomyBridgeVerifier {
    public static final String SPEC_ASSET = "FR0333_RUNTIME_FAILURE_TAXONOMY_0_2.machine.json";
    public static final String FALLBACK_ASSET = "manifest_receipt_fallback.json";
    public static final String AUTHORITATIVE_HASH = "1419f8152205bdca006bcd8c63526909ac0f17ee6fa122ad56954da5297c9818";
    public static final String EXPECTED_RECORD_ID = "FR0333.RUNTIME.FAILURE.TAXONOMY.0.2";
    public static final String EXPECTED_STATE = "FROZEN_BASELINE_AFTER_ECHO";

    private TaxonomyBridgeVerifier() {}

    public static Result verifyAndPublish(Context context) {
        try {
            byte[] specBytes = readAsset(context.getAssets(), SPEC_ASSET);
            String actualHash = sha256(specBytes);
            if (!AUTHORITATIVE_HASH.equals(actualHash)) {
                return Result.fail("SPEC_HASH_MISMATCH", actualHash);
            }

            JSONObject spec = new JSONObject(new String(specBytes, StandardCharsets.UTF_8));
            if (!EXPECTED_RECORD_ID.equals(spec.optString("record_id"))) {
                return Result.fail("SPEC_RECORD_ID_MISMATCH", actualHash);
            }
            if (!EXPECTED_STATE.equals(spec.optString("state"))) {
                return Result.fail("SPEC_STATE_MISMATCH", actualHash);
            }

            byte[] fallbackBytes = readAsset(context.getAssets(), FALLBACK_ASSET);
            JSONObject fallback = new JSONObject(new String(fallbackBytes, StandardCharsets.UTF_8));
            if (!AUTHORITATIVE_HASH.equals(fallback.optString("expected_spec_hash"))) {
                return Result.fail("FALLBACK_HASH_BINDING_MISMATCH", actualHash);
            }
            if (!"secure_telemetry_manifest_receipt_channel".equals(fallback.optString("channel_name"))) {
                return Result.fail("RECEIPT_CHANNEL_NAME_MISMATCH", actualHash);
            }
            if (!InternalTelemetryChannel.AUTHORITY.equals(fallback.optString("authority"))) {
                return Result.fail("PROVIDER_AUTHORITY_MISMATCH", actualHash);
            }

            JSONObject receipt = new JSONObject();
            receipt.put("bridge", "FR0333.ANDROID.TAXONOMY.BRIDGE.0.1");
            receipt.put("spec_record_id", EXPECTED_RECORD_ID);
            receipt.put("spec_hash", actualHash);
            receipt.put("spec_hash_match", true);
            receipt.put("receipt_channel", fallback.optString("channel_name"));
            receipt.put("provider_authority", InternalTelemetryChannel.AUTHORITY);
            receipt.put("state", "READY_FOR_VECTOR1");

            ContentValues values = new ContentValues();
            values.put("receipt", receipt.toString());
            Uri out = context.getContentResolver().insert(InternalTelemetryChannel.RECEIPTS_URI, values);
            if (out == null) {
                return Result.fail("RECEIPT_WRITE_FAILED", actualHash);
            }
            return Result.pass(actualHash, receipt.toString());
        } catch (Exception e) {
            return Result.fail("INITIALIZATION_EXCEPTION:" + e.getClass().getSimpleName() + ":" + String.valueOf(e.getMessage()), null);
        }
    }

    private static byte[] readAsset(AssetManager assets, String name) throws Exception {
        try (InputStream in = assets.open(name); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buffer = new byte[4096];
            int n;
            while ((n = in.read(buffer)) != -1) {
                out.write(buffer, 0, n);
            }
            return out.toByteArray();
        }
    }

    private static String sha256(byte[] bytes) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        byte[] hash = digest.digest(bytes);
        StringBuilder sb = new StringBuilder();
        for (byte b : hash) sb.append(String.format("%02x", b));
        return sb.toString();
    }

    public static final class Result {
        public final boolean pass;
        public final String state;
        public final String hash;
        public final String receipt;

        private Result(boolean pass, String state, String hash, String receipt) {
            this.pass = pass;
            this.state = state;
            this.hash = hash;
            this.receipt = receipt;
        }

        public static Result pass(String hash, String receipt) {
            return new Result(true, "PASS", hash, receipt);
        }

        public static Result fail(String state, String hash) {
            return new Result(false, state, hash, null);
        }
    }
}
