pub type EntityId = [u8; 16];
pub type TransitionHash = [u8; 32];
pub type RepairKey = [u8; 48];

/// Deterministic composite latch key for one entity and one candidate transition.
///
/// Layout:
/// - bytes 0..16  = entity_id
/// - bytes 16..48 = candidate_transition_hash
pub fn repair_key(
    entity_id: &EntityId,
    candidate_transition_hash: &TransitionHash,
) -> RepairKey {
    let mut key = [0u8; 48];
    key[..16].copy_from_slice(entity_id);
    key[16..].copy_from_slice(candidate_transition_hash);
    key
}
