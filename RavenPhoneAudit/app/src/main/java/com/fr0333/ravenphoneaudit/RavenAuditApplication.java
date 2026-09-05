package com.fr0333.ravenphoneaudit;

import android.app.Application;
import android.util.Log;

public final class RavenAuditApplication extends Application {
    private static volatile TaxonomyBridgeVerifier.Result bridgeResult;

    @Override
    public void onCreate() {
        super.onCreate();
        bridgeResult = TaxonomyBridgeVerifier.verifyAndPublish(this);
        if (bridgeResult.pass) {
            Log.i("fr0333", "[TaxonomyBridge] PASS spec_hash=" + bridgeResult.hash);
            Log.i("fr0333", "[TaxonomyBridge] secure_telemetry_manifest_receipt_channel READY");
        } else {
            Log.e("fr0333", "[TaxonomyBridge] FAIL state=" + bridgeResult.state + " spec_hash=" + bridgeResult.hash);
        }
    }

    public static TaxonomyBridgeVerifier.Result getBridgeResult() {
        return bridgeResult;
    }
}
