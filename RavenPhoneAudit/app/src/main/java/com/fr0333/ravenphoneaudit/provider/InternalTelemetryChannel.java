package com.fr0333.ravenphoneaudit.provider;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;

public final class InternalTelemetryChannel extends ContentProvider {
    public static final String AUTHORITY = "com.fr0333.ravenphoneaudit.telemetry";
    public static final Uri RECEIPTS_URI = Uri.parse("content://" + AUTHORITY + "/receipts");

    private static volatile String lastReceipt = null;

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection,
                        String[] selectionArgs, String sortOrder) {
        MatrixCursor cursor = new MatrixCursor(new String[]{"receipt"});
        if (lastReceipt != null) {
            cursor.addRow(new Object[]{lastReceipt});
        }
        return cursor;
    }

    @Override
    public String getType(Uri uri) {
        return "application/vnd.fr0333.receipt+json";
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        if (values == null || !values.containsKey("receipt")) {
            throw new IllegalArgumentException("receipt field required");
        }
        lastReceipt = values.getAsString("receipt");
        return RECEIPTS_URI;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        lastReceipt = null;
        return 1;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        insert(uri, values);
        return 1;
    }
}
