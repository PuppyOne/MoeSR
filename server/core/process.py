import math
from pathlib import Path

import numpy as np
import cv2

from schemas import ModelInfo
from config import base_path
from .global_state import state_manager
from .onnx_infer import OnnxSRInfer


def process_image(
    sr_instance: OnnxSRInfer,
    inputImage: str | Path,
    output_path: str | Path,
    tileSize: int,
    scale: int,
    model: ModelInfo,
    resizeTo: str | None = None,
) -> None:
    """sr process"""
    img_in = base_path / inputImage

    # for img_in in imgs_in:
    img = cv2.imdecode(np.fromfile(img_in, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    h, w, c = img.shape
    sr_img = sr_instance.universal_process_pipeline(img, tile_size=tileSize)
    target_h = None
    target_w = None
    # scale >model scale: re process
    if scale > model.scale and model.scale != 1:
        # calc process times
        scale_log = math.log(scale, model.scale)
        total_times = math.ceil(scale_log)
        # calc target size
        if total_times != int(scale_log):
            target_h = h * scale
            target_w = w * scale

        for t in range(total_times - 1):
            sr_img = sr_instance.universal_process_pipeline(sr_img, tile_size=tileSize)
    elif scale < model.scale:
        target_h = h * scale
        target_w = w * scale
    # size in parameters first
    if resizeTo:
        if "x" in resizeTo:
            param_w = int(resizeTo.split("x")[0])
            target_w = param_w
            target_h = int(h * param_w / w)
        elif "/" in resizeTo:
            ratio = int(resizeTo.split("/")[0]) / int(resizeTo.split("/")[1])
            target_w = int(w * ratio)
            target_h = int(h * ratio)
    if target_w:
        img_out = cv2.resize(sr_img, (target_w, target_h))  # type: ignore
    else:
        img_out = sr_img
    # save
    cv2.imencode(".png", img_out)[1].tofile(output_path)
    sr_instance.processed_img_num += 1

    state_manager.set_process_state("finished")
