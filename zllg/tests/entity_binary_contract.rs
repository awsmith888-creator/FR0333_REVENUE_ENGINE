use zllg::entity_binary::{repair_key, EntityId, TransitionHash};

#[test]
fn repair_key_is_exact_binary_concatenation() {
    let entity_id: EntityId = [0x11; 16];
    let transition_hash: TransitionHash = [0x22; 32];

    let key = repair_key(&entity_id, &transition_hash);

    assert_eq!(&key[..16], &entity_id);
    assert_eq!(&key[16..], &transition_hash);
}

#[test]
fn repair_key_distinguishes_competing_candidates_for_same_entity() {
    let entity_id: EntityId = [0x33; 16];
    let candidate_a: TransitionHash = [0x44; 32];
    let candidate_b: TransitionHash = [0x55; 32];

    assert_ne!(repair_key(&entity_id, &candidate_a), repair_key(&entity_id, &candidate_b));
}

#[test]
fn repair_key_distinguishes_entities_for_same_candidate() {
    let entity_a: EntityId = [0x66; 16];
    let entity_b: EntityId = [0x77; 16];
    let transition_hash: TransitionHash = [0x88; 32];

    assert_ne!(repair_key(&entity_a, &transition_hash), repair_key(&entity_b, &transition_hash));
}
