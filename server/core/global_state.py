from schemas import State


class StateManager:
    def __init__(self) -> None:
        self.last_state: State = "idle"
        self.last_progress: float | None = None
        self.last_progress_set_time: float | None = None

    def show_error(self, error_text: str) -> None:
        # eel.showError(error_text)
        print(f"Error: {error_text}")

    def set_process_state(self, state: State) -> None:
        # eel.handleSetProcessState(state)
        global last_state
        print(f"Process State: {state}")
        last_state = state


state_manager = StateManager()
