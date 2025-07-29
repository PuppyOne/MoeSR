from dataclasses import dataclass
import json
import os
import math
import traceback
from pathlib import Path
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, status
from werkzeug.utils import secure_filename
import numpy as np
import cv2
import onnxruntime as ort

from .onnx_infer import OnnxSRInfer

@dataclass(frozen=True, slots=True)
class ModelInfo:
    name: str
    path: str
    scale: int
    algo: str

State = Literal['idle', 'processing', 'finished', 'error', 'cancel']


# Global Vars
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
gpuid = 0
tileSize = 192
inputType= 'Image'

# From env
base_url = os.getenv('BASE_URL', 'http://localhost:9000')
base_path = Path(os.getenv('BASE_PATH','./'))
is_production = os.getenv('production') == 'true'

last_state: State = 'idle'
last_progress: float | None = None
last_progress_set_time: float | None = None
# Scan models
model_list: list[ModelInfo] = []
model_root = base_path / 'models'
for algo_dir in model_root.iterdir():
    if not algo_dir.is_dir():
        continue
    algo = algo_dir.name
    for scale_dir in algo_dir.iterdir():
        if scale_dir.is_dir():
            scale = int(scale_dir.name.replace('x', ''))
            for model_file in scale_dir.glob('*.onnx'):
                model_list.append(
                    ModelInfo(
                        name=str(model_file.stem),
                        path=str(model_file),
                        scale=scale,
                        algo=algo,
                    )
                )

app = FastAPI()
if not is_production:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
    )

@app.get('/models')
def get_models():
    """返回按 algo 分类的 model 名称列表"""
    result: dict[str, list[str]] = {}
    for model in model_list:
        result.setdefault(model.algo, []).append(model.name)
    return result


# @eel.expose
# def py_get_settings():
#     setting_file = open('settings.json','r',encoding='utf-8')
#     settings = json.load(setting_file)
#     setting_file.close()
#     return settings

# @eel.expose
# def py_save_settings(new_settings):
#     setting_file = open('settings.json','w',encoding='utf-8')
#     settings = json.dumps(new_settings,ensure_ascii=False)
#     setting_file.write(settings)
#     setting_file.close()
#     return 0

def seconds_to_hms(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    return f"{int(hours):0>2d}:{int(minutes):0>2d}:{int(seconds):0>2d}"

def progress_setter(progress,current_time,total_img_num,processed_img_num):
    try:
        global last_progress,last_progress_set_time
        progress_percent = round(progress*100)
        total_progress_percent = round((processed_img_num+progress)/total_img_num*100)
        etr_str = '--:--:--'
        total_etr_str = '--:--:--'
        if last_progress is not None and last_progress_set_time:
            etr = (current_time-last_progress_set_time) * (1-last_progress)/(progress-last_progress)
            total_etr = (current_time-last_progress_set_time) * (total_img_num-processed_img_num-last_progress)/(progress-last_progress)
            etr_str = seconds_to_hms(etr)
            total_etr_str = seconds_to_hms(total_etr)
        progress_str = f'{progress_percent}% ETR:{etr_str}'
        total_progress_str = f'{total_progress_percent}% ETR:{total_etr_str}'
        # eel.handleSetProgress(progress_percent,progress_str,total_progress_str)
        last_progress = progress
        last_progress_set_time = current_time

        print(f"Progress: {progress_str}, Total Progress: {total_progress_str}, Processed: {processed_img_num}/{total_img_num}")
    except Exception as e:
        print(f"Error in progress_setter: {str(e)}")
        # eel.showError(f"Error in progress_setter: {str(e)}")
        return False


def show_error(error_text):
    # eel.showError(error_text)
    print(f"Error: {error_text}")


def set_process_state(state: State):
    # eel.handleSetProcessState(state)
    global last_state
    print(f"Process State: {state}")
    last_state = state


@app.post('/run_process', status_code=status.HTTP_201_CREATED)
async def py_run_process(
    scale: Annotated[int, Form(ge=1, le=16)],
    model: Annotated[str, Form(pattern='^[a-zA-Z0-9_-]+:[a-zA-Z0-9_-]+$')],
    image: Annotated[UploadFile, File()],
    isSkipAlpha: Annotated[bool, Form()] = False,
):
    global last_state
    if last_state == 'processing':
        raise HTTPException(status_code=400, detail="A process is already running.")

    model_param = model
    if model_param and ':' in model_param:
        algoName, modelName = model_param.split(':', 1)
    else:
        raise HTTPException(status_code=400, detail="Invalid model parameter format. Expected 'algo:model'.")

    # 检查文件类型和大小
    filename = image.filename
    if not (filename and '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
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
        set_process_state('processing')
        # Save the uploaded file
        inputImage, outputPath, id = await upload_file(image)
        meta_path = outputPath / "meta.json"

        # find model info
        model_obj = ModelInfo('', '', 4, '')
        provider_options = None
        if gpuid >= 0:
            provider_options = [{'device_id': gpuid}]
        for m in model_list:
            if m.name == modelName and m.algo == algoName:
                model_obj = m
                break

        # 写入 meta
        meta_data = {
            "status": 'processing',
            "id": id,
            "model": model_obj.name,
            "algo": model_obj.algo,
            "scale": scale,
            "input": filename,
        }

        with open(meta_path, "w", encoding="utf-8") as meta_file:
            json.dump(meta_data, meta_file, ensure_ascii=False, indent=2)

        # init sr instance
        sr_instance = OnnxSRInfer(model_obj.path, model_obj.scale, model_obj.name, providers=['CUDAExecutionProvider'],
                                    provider_options=provider_options, progress_setter=progress_setter)

        print(f'Using providers: {sr_instance.sess.get_providers()}')

        # skip alpha sr
        if isSkipAlpha:
            sr_instance.alpha_upsampler = 'interpolation'

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
            'status': 'success',
            'id': id,
            'outputPath': output_path,
            'outputUrl': f"{base_url}/{rel_output_path.replace(os.sep, '/')}",
            'modelName': model_obj.name,
            'scale': model_obj.scale,
            'algo': model_obj.algo,
        }

    except Exception as e:
        error_message = traceback.format_exc()
        show_error(error_message)
        set_process_state('error')
        raise HTTPException(status_code=500, detail=str(e))


async def upload_file(file: UploadFile) -> tuple[Path, Path, str]:
    # Generate a unique folder path
    unique_id = str(uuid4())
    folder_path = base_path / unique_id
    folder_path.mkdir(parents=True, exist_ok=True)

    # Generate input file name
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="missing file name.",
        )
    original_filename = secure_filename(file.filename)
    file_ext = original_filename.rsplit('.', 1)[1].lower()
    input_filename = f"input.{file_ext}"
    input_path = folder_path / input_filename

    # Save file
    with open(input_path, "wb") as f:
        f.write(await file.read())

    return input_path, folder_path, unique_id


def process_image(
    sr_instance: OnnxSRInfer,
    inputImage: str | Path,
    outputPath: str | Path,
    tileSize: int,
    scale: int,
    model: ModelInfo,
    resizeTo: str | None = None,
) -> str:
    """sr process"""
    img_in=base_path / inputImage

    # for img_in in imgs_in:
    img = cv2.imdecode(np.fromfile(img_in,dtype=np.uint8),cv2.IMREAD_UNCHANGED)
    h, w, c = img.shape
    sr_img = sr_instance.universal_process_pipeline(
        img, tile_size=tileSize)
    target_h = None
    target_w = None
    # scale >model scale: re process
    if scale > model.scale and model.scale != 1:
        # calc process times
        scale_log = math.log(scale, model.scale)
        total_times = math.ceil(scale_log)
        # calc target size
        if total_times != int(scale_log):
            target_h = h*scale
            target_w = w*scale

        for t in range(total_times-1):
            sr_img = sr_instance.universal_process_pipeline(sr_img, tile_size=tileSize)
    elif scale < model.scale:
        target_h = h*scale
        target_w = w*scale
    # size in parameters first
    if resizeTo:
        if 'x' in resizeTo:
            param_w = int(resizeTo.split('x')[0])
            target_w = param_w
            target_h = int(h * param_w / w)
        elif '/' in resizeTo:
            ratio = int(resizeTo.split('/')[0]) / int(resizeTo.split('/')[1])
            target_w = int(w * ratio)
            target_h = int(h * ratio)
    if target_w:
        img_out = cv2.resize(sr_img, (target_w, target_h)) # type: ignore
    else:
        img_out = sr_img
    # save
    img_in_name = Path(img_in).stem
    img_in_ext = Path(img_in).suffix
    final_output_path = base_path / Path(outputPath) / f'{img_in_name}_MoeSR_{model.name}.png'
    if final_output_path.exists():
        final_output_path = base_path / Path(outputPath) / f'{img_in_name}_{img_in_ext}_MoeSR_{model.name}.png'
    # cv2.imwrite(str(final_output_path), img_out)
    cv2.imencode('.png',img_out)[1].tofile(final_output_path)
    sr_instance.processed_img_num += 1

    set_process_state('finished')
    return str(Path(outputPath) / f'{Path(img_in).stem}_MoeSR_{model.name}.png')

@app.get('/status')
def get_task_status():
    """获取任务状态"""
    return {
        'status': last_state,
        'last_progress': last_progress,
        'last_progress_set_time': last_progress_set_time,
    }

@app.get("/health")
async def health_check():
    available_providers = ort.get_available_providers()

    gpu_info = {
        "onnxruntime_providers": available_providers,
        "cuda_available": "CUDAExecutionProvider" in available_providers,
        "tensorrt_available": "TensorrtExecutionProvider" in available_providers,
    }

    return {
        "status": "OK",
        "gpu_support": gpu_info,
    }

@app.get('/tasks/{task_id}')
async def get_task(task_id: str):
    """获取任务状态"""
    meta_path = base_path / task_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Task not found.")

    with open(meta_path, "r", encoding="utf-8") as meta_file:
        return json.load(meta_file)
