from schemas import ModelInfo
from config import base_path


# Scan models
model_list: list[ModelInfo] = []
model_root = base_path / "models"

for algo_dir in model_root.iterdir():
    if not algo_dir.is_dir():
        continue
    algo = algo_dir.name
    for scale_dir in algo_dir.iterdir():
        if scale_dir.is_dir():
            scale = int(scale_dir.name.replace("x", ""))
            for model_file in scale_dir.glob("*.onnx"):
                model_list.append(
                    ModelInfo(
                        name=str(model_file.stem),
                        path=str(model_file),
                        scale=scale,
                        algo=algo,
                    )
                )
