use thiserror::Error;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TaskState {
    Pending,
    Asserted,
    Staged,
    Executed,
    Receipted,
    Hold,
    Failed,
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum TaskLifecycleError {
    #[error("invalid task transition: {from:?} -> {to:?}")]
    InvalidTransition { from: TaskState, to: TaskState },
}

pub fn transition(from: TaskState, to: TaskState) -> Result<TaskState, TaskLifecycleError> {
    let allowed = matches!(
        (from, to),
        (TaskState::Pending, TaskState::Asserted)
            | (TaskState::Pending, TaskState::Hold)
            | (TaskState::Pending, TaskState::Failed)
            | (TaskState::Asserted, TaskState::Staged)
            | (TaskState::Asserted, TaskState::Hold)
            | (TaskState::Asserted, TaskState::Failed)
            | (TaskState::Staged, TaskState::Executed)
            | (TaskState::Staged, TaskState::Hold)
            | (TaskState::Staged, TaskState::Failed)
            | (TaskState::Executed, TaskState::Receipted)
            | (TaskState::Executed, TaskState::Hold)
            | (TaskState::Executed, TaskState::Failed)
    );

    if allowed {
        Ok(to)
    } else {
        Err(TaskLifecycleError::InvalidTransition { from, to })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn happy_path_reaches_receipted_in_order() {
        let state = transition(TaskState::Pending, TaskState::Asserted).unwrap();
        let state = transition(state, TaskState::Staged).unwrap();
        let state = transition(state, TaskState::Executed).unwrap();
        let state = transition(state, TaskState::Receipted).unwrap();
        assert_eq!(state, TaskState::Receipted);
    }

    #[test]
    fn task_cannot_skip_directly_to_receipted() {
        let result = transition(TaskState::Pending, TaskState::Receipted);
        assert_eq!(
            result,
            Err(TaskLifecycleError::InvalidTransition {
                from: TaskState::Pending,
                to: TaskState::Receipted,
            })
        );
    }

    #[test]
    fn hold_is_allowed_before_receipt() {
        assert_eq!(
            transition(TaskState::Asserted, TaskState::Hold).unwrap(),
            TaskState::Hold
        );
    }
}
