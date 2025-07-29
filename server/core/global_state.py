from schemas import ModelInfo, State
from config import base_path


class StateManager:
    def __init__(self) -> None:
        self.last_state: State = "idle"
        self.last_progress: float | None = None
        self.last_progress_set_time: float | None = None
        # Scan models
        self.model_list: list[ModelInfo] = []
        model_root = base_path / "models"

        for algo_dir in model_root.iterdir():
            if not algo_dir.is_dir():
                continue
            algo = algo_dir.name
            for scale_dir in algo_dir.iterdir():
                if scale_dir.is_dir():
                    scale = int(scale_dir.name.replace("x", ""))
                    for model_file in scale_dir.glob("*.onnx"):
                        self.model_list.append(
                            ModelInfo(
                                name=str(model_file.stem),
                                path=str(model_file),
                                scale=scale,
                                algo=algo,
                            )
                        )

    def show_error(self, error_text: str) -> None:
        # eel.showError(error_text)
        print(f"Error: {error_text}")

    def set_process_state(self, state: State) -> None:
        # eel.handleSetProcessState(state)
        global last_state
        print(f"Process State: {state}")
        last_state = state


state_manager = StateManager()
