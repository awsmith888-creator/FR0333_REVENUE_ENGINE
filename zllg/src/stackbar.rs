#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StackbarMetrics {
    pub ingest_count: u64,
    pub assert_pass: u64,
    pub assert_fail: u64,
    pub hold_count: u64,
    pub oldest_hold_age: String,
    pub canonical_append_count: u64,
    pub task_receipt_count: u64,
    pub receipt_failures: u64,
    pub ledger_sync_lag: u64,
    pub raven_count: u64,
    pub steward_count: u64,
    pub colonel_count: u64,
    pub sophie_count: u64,
    pub system_state: String,
}

pub fn render_cli(metrics: &StackbarMetrics) -> String {
    format!(
        "RAVEN STACKBAR\n\n\
INGEST ............ {}\n\
ASSERT PASS ....... {}\n\
ASSERT FAIL ....... {}\n\
HOLD .............. {}\n\
OLDEST HOLD ....... {}\n\
CANONICAL ......... {}\n\
RECEIPTED ......... {}\n\
RECEIPT FAIL ...... {}\n\
LEDGER LAG ........ {}\n\
RAVEN/STW/COL/SOPH  {} / {} / {} / {}\n\
SYSTEM ............ {}",
        metrics.ingest_count,
        metrics.assert_pass,
        metrics.assert_fail,
        metrics.hold_count,
        metrics.oldest_hold_age,
        metrics.canonical_append_count,
        metrics.task_receipt_count,
        metrics.receipt_failures,
        metrics.ledger_sync_lag,
        metrics.raven_count,
        metrics.steward_count,
        metrics.colonel_count,
        metrics.sophie_count,
        metrics.system_state,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn cli_snapshot_contains_integrity_metrics() {
        let output = render_cli(&StackbarMetrics {
            ingest_count: 14_200,
            assert_pass: 14_031,
            assert_fail: 169,
            hold_count: 169,
            oldest_hold_age: "00:17:42".to_string(),
            canonical_append_count: 13_998,
            task_receipt_count: 13_998,
            receipt_failures: 0,
            ledger_sync_lag: 0,
            raven_count: 1,
            steward_count: 4,
            colonel_count: 32,
            sophie_count: 13_961,
            system_state: "ACTIVE".to_string(),
        });

        assert!(output.contains("HOLD .............. 169"));
        assert!(output.contains("OLDEST HOLD ....... 00:17:42"));
        assert!(output.contains("RECEIPT FAIL ...... 0"));
        assert!(output.contains("RAVEN/STW/COL/SOPH  1 / 4 / 32 / 13961"));
        assert!(output.contains("SYSTEM ............ ACTIVE"));
    }
}
