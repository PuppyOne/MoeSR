import json
import os
import traceback
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status

from config import (
    ALLOWED_EXTENSIONS,
    gpuid,
    tileSize,
    base_path,
    base_url,
)
from core.onnx_infer import OnnxSRInfer
from core.global_state import state_manager
from core.process import process_image
from core.utils import progress_setter, upload_file
from schemas import ModelInfo


router = APIRouter(
    prefix="/run_process",
    tags=["run_process"],
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def py_run_process(
    scale: Annotated[int, Form(ge=1, le=16)],
    model: Annotated[str, Form(pattern="^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+$")],
    image: Annotated[UploadFile, File()],
    isSkipAlpha: Annotated[bool, Form()] = False,
):
    if state_manager.last_state == "processing":
        raise HTTPException(status_code=400, detail="A process is already running.")

    model_param = model
    if model_param and ":" in model_param:
        algoName, modelName = model_param.split(":", 1)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid model parameter format. Expected 'algo:model'.",
        )

    # 检查文件类型和大小
    filename = image.filename
    if not (
        filename
        and "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}.",
        )

    # contents = await image.read()
    # if len(contents) > MAX_FILE_SIZE:
    #     raise HTTPException(
    #         status_code=413,
    #         detail=f"File size exceeds limit of {MAX_FILE_SIZE / (1024 * 1024)} MB.",
    #     )

    try:
        state_manager.set_process_state("processing")
        # Save the uploaded file
        inputImage, outputPath, id = await upload_file(image)
        meta_path = outputPath / "meta.json"

        # find model info
        model_obj = ModelInfo("", "", 4, "")
        provider_options = None
        if gpuid >= 0:
            provider_options = [{"device_id": gpuid}]
        for m in state_manager.model_list:
            if m.name == modelName and m.algo == algoName:
                model_obj = m
                break

        # 写入 meta
        meta_data = {
            "status": "processing",
            "id": id,
            "model": model_obj.name,
            "algo": model_obj.algo,
            "scale": scale,
            "input": filename,
        }

        with open(meta_path, "w", encoding="utf-8") as meta_file:
            json.dump(meta_data, meta_file, ensure_ascii=False, indent=2)

        # init sr instance
        sr_instance = OnnxSRInfer(
            model_obj.path,
            model_obj.scale,
            model_obj.name,
            providers=["CUDAExecutionProvider"],
            provider_options=provider_options,
            progress_setter=progress_setter,
        )

        print(f"Using providers: {sr_instance.sess.get_providers()}")

        # skip alpha sr
        if isSkipAlpha:
            sr_instance.alpha_upsampler = "interpolation"

        output_path = process_image(
            sr_instance,
            inputImage,
            outputPath,
            tileSize,
            scale,
            model_obj,
        )
        # Ensure output_path is relative to base_path for correct URL
        rel_output_path = str(Path(output_path).relative_to(base_path))

        # 更新 meta.json 状态为 finished，并包含输出url
        meta_data["status"] = "finished"
        meta_data["outputUrl"] = f"{base_url}/{rel_output_path.replace(os.sep, '/')}"
        with open(meta_path, "w", encoding="utf-8") as meta_file:
            json.dump(meta_data, meta_file, ensure_ascii=False, indent=2)

        return {
            "status": "success",
            "id": id,
            "outputPath": output_path,
            "outputUrl": f"{base_url}/{rel_output_path.replace(os.sep, '/')}",
            "modelName": model_obj.name,
            "scale": model_obj.scale,
            "algo": model_obj.algo,
        }

    except Exception as e:
        error_message = traceback.format_exc()
        state_manager.show_error(error_message)
        state_manager.set_process_state("error")
        raise HTTPException(status_code=500, detail=str(e))
