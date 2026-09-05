package com.fr0333.ravenphoneaudit.provider;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

public final class InternalTelemetryChannel extends ContentProvider {
    public static final String AUTHORITY = "com.fr0333.ravenphoneaudit.telemetry";
    public static final Uri RECEIPTS_URI = Uri.parse("content://" + AUTHORITY + "/receipts");

    private static volatile String lastReceipt = null;

    @Override
    public boolean onCreate() {
        return true;
    }

    @Nullable
    @Override
    public Cursor query(@NonNull Uri uri, @Nullable String[] projection,
                        @Nullable String selection, @Nullable String[] selectionArgs,
                        @Nullable String sortOrder) {
        MatrixCursor cursor = new MatrixCursor(new String[]{"receipt"});
        if (lastReceipt != null) {
            cursor.addRow(new Object[]{lastReceipt});
        }
        return cursor;
    }

    @Nullable
    @Override
    public String getType(@NonNull Uri uri) {
        return "application/vnd.fr0333.receipt+json";
    }

    @Nullable
    @Override
    public Uri insert(@NonNull Uri uri, @Nullable ContentValues values) {
        if (values == null || !values.containsKey("receipt")) {
            throw new IllegalArgumentException("receipt field required");
        }
        lastReceipt = values.getAsString("receipt");
        return RECEIPTS_URI;
    }

    @Override
    public int delete(@NonNull Uri uri, @Nullable String selection,
                      @Nullable String[] selectionArgs) {
        lastReceipt = null;
        return 1;
    }

    @Override
    public int update(@NonNull Uri uri, @Nullable ContentValues values,
                      @Nullable String selection, @Nullable String[] selectionArgs) {
        insert(uri, values);
        return 1;
    }
}
