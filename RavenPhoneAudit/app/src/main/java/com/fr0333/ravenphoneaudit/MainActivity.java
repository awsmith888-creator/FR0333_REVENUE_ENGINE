package com.fr0333.ravenphoneaudit;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.StatFs;
import android.provider.Settings;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import java.text.DecimalFormat;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;

public class MainActivity extends Activity {
    private static final String REQUIRED_SECURITY_PATCH = "2026-08-05";
    private LinearLayout body;
    private String lastReport = "";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        render();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (body != null) renderAuditRows();
    }

    private void render() {
        int pad = dp(18);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(Color.rgb(16, 19, 18));

        body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setPadding(pad, dp(24), pad, dp(32));
        scroll.addView(body);
        setContentView(scroll);

        TextView title = text("RAVEN PHONE AUDIT", 28, Color.WHITE, true);
        body.addView(title);
        TextView subtitle = text("Local-only Pixel / Android update verifier", 15, Color.rgb(190, 198, 196), false);
        subtitle.setPadding(0, dp(4), 0, dp(18));
        body.addView(subtitle);

        renderAuditRows();
    }

    private void renderAuditRows() {
        while (body.getChildCount() > 2) body.removeViewAt(2);

        String model = Build.MODEL;
        String hardware = Build.HARDWARE;
        String androidVersion = Build.VERSION.RELEASE;
        String patch = Build.VERSION.SECURITY_PATCH;
        String build = Build.DISPLAY;

        StatFs stat = new StatFs(Environment.getDataDirectory().getPath());
        long total = stat.getTotalBytes();
        long free = stat.getAvailableBytes();
        long used = total - free;

        boolean patchPass = patchAtLeast(patch, REQUIRED_SECURITY_PATCH);

        addRow("DEVICE", model, "VERIFIED");
        addRow("HARDWARE", hardware, "VERIFIED");
        addRow("ANDROID", androidVersion, "VERIFIED");
        addRow("SECURITY PATCH", emptyToUnknown(patch), patchPass ? "CURRENT" : "ACTION REQUIRED");
        addRow("BUILD", emptyToUnknown(build), "CAPTURED");
        addRow("STORAGE", gb(used) + " GB / " + gb(total) + " GB used", free > (5L * 1024 * 1024 * 1024) ? "HEADROOM PASS" : "LOW SPACE");

        TextView gate = text(
                patchPass
                        ? "FULL PASS — security patch is at or newer than " + REQUIRED_SECURITY_PATCH
                        : "UPDATE GAP — security patch is older than " + REQUIRED_SECURITY_PATCH,
                17,
                patchPass ? Color.rgb(183, 240, 198) : Color.rgb(255, 196, 175),
                true);
        gate.setPadding(0, dp(18), 0, dp(12));
        body.addView(gate);

        addButton("CHECK SYSTEM UPDATE", v -> openIntent(new Intent("android.settings.SYSTEM_UPDATE_SETTINGS"), Settings.ACTION_SETTINGS));
        addButton("OPEN PLAY SYSTEM UPDATE", v -> openIntent(new Intent("android.settings.MODULE_UPDATE_SETTINGS"), Settings.ACTION_SECURITY_SETTINGS));
        addButton("OPEN PLAY APP UPDATES", v -> openPlayUpdates());
        addButton("REFRESH AUDIT", v -> renderAuditRows());
        addButton("COPY AUDIT", v -> copyAudit());

        lastReport = "PHONE UPDATE AUDIT\n"
                + "DEVICE = " + model + "\n"
                + "HARDWARE = " + hardware + "\n"
                + "ANDROID = " + androidVersion + "\n"
                + "SECURITY PATCH = " + emptyToUnknown(patch) + "\n"
                + "BUILD = " + emptyToUnknown(build) + "\n"
                + "STORAGE = " + gb(used) + " GB / " + gb(total) + " GB used\n"
                + "REFERENCE PATCH = " + REQUIRED_SECURITY_PATCH + "\n"
                + "RESULT = " + (patchPass ? "FULL PASS — CURRENT" : "UPDATE GAP — ACTION REQUIRED") + "\n";
    }

    private void addRow(String label, String value, String state) {
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(16), dp(14), dp(16), dp(14));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.setMargins(0, 0, 0, dp(8));
        card.setLayoutParams(lp);
        card.setBackgroundColor(Color.rgb(40, 44, 43));

        TextView l = text(label, 13, Color.rgb(185, 191, 190), true);
        TextView v = text(value, 20, Color.WHITE, true);
        TextView s = text(state, 13,
                state.contains("REQUIRED") || state.contains("LOW") ? Color.rgb(255, 196, 175) : Color.rgb(183, 240, 198),
                true);
        s.setPadding(0, dp(5), 0, 0);
        card.addView(l);
        card.addView(v);
        card.addView(s);
        body.addView(card);
    }

    private void addButton(String label, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setText(label);
        b.setTextSize(15);
        b.setAllCaps(false);
        b.setGravity(Gravity.CENTER);
        b.setOnClickListener(listener);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                dp(54));
        lp.setMargins(0, dp(7), 0, 0);
        b.setLayoutParams(lp);
        body.addView(b);
    }

    private void openPlayUpdates() {
        Intent market = new Intent(Intent.ACTION_VIEW, Uri.parse("market://myapps"));
        try {
            startActivity(market);
        } catch (ActivityNotFoundException e) {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://play.google.com/store/apps")));
        }
    }

    private void openIntent(Intent primary, String fallbackAction) {
        try {
            startActivity(primary);
        } catch (ActivityNotFoundException e) {
            startActivity(new Intent(fallbackAction));
        }
    }

    private void copyAudit() {
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("Raven Phone Audit", lastReport));
        Toast.makeText(this, "Audit copied", Toast.LENGTH_SHORT).show();
    }

    private boolean patchAtLeast(String patch, String required) {
        try {
            return !LocalDate.parse(patch).isBefore(LocalDate.parse(required));
        } catch (DateTimeParseException | NullPointerException e) {
            return false;
        }
    }

    private String gb(long bytes) {
        double g = bytes / 1073741824.0;
        return new DecimalFormat("0.0").format(g);
    }

    private String emptyToUnknown(String s) {
        return (s == null || s.trim().isEmpty()) ? "UNKNOWN" : s;
    }

    private TextView text(String value, int sp, int color, boolean bold) {
        TextView tv = new TextView(this);
        tv.setText(value);
        tv.setTextSize(sp);
        tv.setTextColor(color);
        if (bold) tv.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        return tv;
    }

    private int dp(int n) {
        return (int) (n * getResources().getDisplayMetrics().density + 0.5f);
    }
}
