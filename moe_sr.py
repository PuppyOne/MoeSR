import math
import os
from threading import Thread
import traceback
from pathlib import Path
import json
from typing import Any
from uuid import UUID, uuid4

from flask import Flask, request
from flask_cors import CORS
import numpy as np
import cv2

from onnx_infer import OnnxSRInfer

from werkzeug.utils import secure_filename

class ModelInfo:
    def __init__(self, name, path, scale, algo):
        self.name = name
        self.path = path
        self.scale = scale
        self.algo = algo


# Global Vars
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
BASE_URL = os.getenv('BASE_URL', 'http://localhost:9000')
gpuid = 0
tileSize = 192
inputType= 'Image'
model_list = []

def get_base_path():
    """从环境变量获取挂载点"""
    oss_path = os.getenv('BASE_PATH')
    if oss_path:
        return Path(oss_path)
    return Path.cwd()  # 默认使用当前工作目录

base_path = get_base_path()

tasks: dict[UUID, dict[str, Any]] = {}
last_progress = None
last_progress_set_time = None
# Scan models
model_root = Path('models')
for algo in ['real-esrgan', 'real-hatgan']:
    for folder in [p for p in (model_root / algo).iterdir() if p.is_dir()]:
        for f in folder.glob('*.onnx'):
            model_list.append(ModelInfo(str(f.stem), str(f), int(folder.stem.replace('x', '')), algo))

# eel.init('webui', custom_js_func=['handleSetProgress', 'showError', 'handleSetProcessState'])
# prepare electron app
# main_js = open('electron_app/main.js')
# main_js_str = main_js.read()
# main_js.close()
# main_js_str_custom_port = re.sub('http://localhost:.*/', f'http://localhost:{port}/', main_js_str)
# main_js = open('electron_app/main.js', 'w', encoding='utf-8')
# main_js.write(main_js_str_custom_port)
# main_js.close()

app= Flask(__name__)
CORS(app)

# @eel.expose
@app.get('/model_list')
def py_get_model_list():
    algo_name=request.args.get('algo')
    if not algo_name:
        return [m.name for m in model_list]
    models = [m.name for m in model_list if m.algo == algo_name]
    return models

# @eel.expose
def py_get_settings():
    setting_file = open(base_path / 'settings.json', 'r', encoding='utf-8')
    settings = json.load(setting_file)
    setting_file.close()
    return settings

# @eel.expose
def py_save_settings(new_settings):
    setting_file = open(base_path / 'settings.json', 'w', encoding='utf-8')
    settings = json.dumps(new_settings,ensure_ascii=False)
    setting_file.write(settings)
    setting_file.close()
    return 0

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
        if last_progress_set_time:
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


last_state = 'idle'
def set_process_state(state):
    # eel.handleSetProcessState(state)
    print(f"Process State: {state}")
    global last_state
    last_state = state


# @eel.expose
@app.post('/run_process')
def py_run_process():
    if last_state == 'processing':
        return {'error': 'A process is already running.'}, 400

    set_process_state('processing')
    # modelName, tileSize, scale, isSkipAlpha, resizeTo: str, inputType, inputImage, outputPath, gpuid,algoName
    # modelName = request.args.get('modelName')
    # tileSize = request.args.get('tileSize', type=int)
    scale = request.form.get('scale', type=int)
    isSkipAlpha = request.form.get('isSkipAlpha', 'false').lower() == 'true'
    # resizeTo = request.args.get('resizeTo')
    # inputType = request.args.get('inputType')
    # inputImage = request.args.get('inputImage')
    # outputPath = request.args.get('outputPath')
    # # gpuid = request.args.get('gpuid', '-1')
    # algoName = request.args.get('algoName')

    model_param = request.form.get('model')
    if model_param and '-' in model_param:
        algoName, modelName = model_param.split(':', 1)

    # 检查必填参数
    required_params = [modelName, tileSize, scale, inputType, algoName] # inputImage, outputPath,
    if any(p is None or p == '' for p in required_params):
        return {'error': 'Missing required query parameters.'}, 400

    # 检查请求中是否有文件部分
    if 'image' not in request.files:
        return {'error': 'No image part in request'}, 400

    file = request.files['image']

    # 检查是否选择了文件
    if file.filename is None or file.filename == '':
        return {'error': 'No selected file'}, 400

    # 检查文件类型和大小
    if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
        return {'error': 'Invalid file type'}, 400

    if file.content_length > MAX_FILE_SIZE:
        return {'error': 'File size exceeds limit'}, 413

    try:

        inputImage,outputPath = upload_image(file)
        print(f"Input image: {inputImage}, Output path: {outputPath}")

        # find model info
        model = ModelInfo('', '', 4, '')
        provider_options = None
        if gpuid >= 0:
            provider_options = [{'device_id': gpuid}]
        for m in model_list:
            if m.name == modelName and m.algo == algoName:
                model = m
                break
        # init sr instance
        sr_instance = OnnxSRInfer(model.path, model.scale, model.name,
                                    provider_options=provider_options, progress_setter=progress_setter)
        # skip alpha sr
        if isSkipAlpha:
            sr_instance.alpha_upsampler = 'interpolation'

        # task_thread = Thread(
        #     target=process_image,
        #     args=(
        #         task_id,
        #         sr_instance,
        #         inputImage,
        #         outputPath,
        #         tileSize,
        #         scale,
        #         model,
        #         resizeTo,
        #     ),
        # )
        # task_thread.start()
        output_path = process_image(
            sr_instance,
            inputImage,
            outputPath,
            tileSize,
            scale,
            model,
        )

        # Ensure output_path is relative to base_path for correct URL
        rel_output_path = str(Path(output_path).relative_to(base_path))
        return {
            'status': 'success',
            'outputPath': output_path,
            'outputUrl': f"{BASE_URL}/{rel_output_path.replace(os.sep, '/')}",
            'modelName': model.name,
            'scale': model.scale,
            'algo': model.algo,
        }, 201

        # batch process
        # imgs_in = []
        # if inputType == 'Folder':
        #     input_folder = Path(inputImage)
        #     for f in input_folder.glob('*.jpg'):
        #         imgs_in.append(f)
        #     for f in input_folder.glob('*.png'):
        #         imgs_in.append(f)
        # else:
        # imgs_in = [inputImage]
        # sr_instance.total_img_num = len(imgs_in)
        # sr_instance.processed_img_num = 0

    except Exception as e:
        error_message = traceback.format_exc()
        show_error(error_message)
        set_process_state('error')
        return {
            'error': error_message
        }, 500

def upload_image(file) -> tuple[Path, Path]:
    # 生成唯一文件夹
    unique_id = str(uuid4())
    folder_path = base_path / unique_id
    folder_path.mkdir(parents=True, exist_ok=True)

    # 生成安全的文件名
    original_filename = secure_filename(file.filename)
    file_ext = original_filename.rsplit('.', 1)[1].lower()
    input_filename = f"input.{file_ext}"
    input_path = folder_path / input_filename

    # 保存输入图片
    file.save(input_path)

    return input_path, folder_path


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
        img_out = cv2.resize(sr_img, (target_w, target_h))
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

@app.get('/task/<task_id>')
def get_task_status(task_id: str):
    """获取任务状态"""
    # task_id = UUID(task_id)
    # if task_id in tasks:
    #     task_info = tasks[task_id]
    #     return {
    #         'status': task_info.get('status', 'unknown'),
    #         'progress': task_info.get('progress', 0),
    #         'result': task_info.get('result', None),
    #     }
    # return {'status': 'not found'}, 404
    return {
        'status': last_state,
        'last_progress': last_progress,
        'last_progress_set_time': last_progress_set_time,
    }


# eel.start('index.html', mode='custom', cmdline_args=['electron/electron.exe', 'electron_app/main.js'], port=port)
# eel.start('index.html', mode='custom', cmdline_args=['E:/python/MoeSR/electron/electron.exe', 'webui/main.js'], port=port)
# py_run_process('RealESRGAN_x4plus', 256, 4, False, '', 'Image', 'test.png', 'output', '-1', 'real-esrgan')
# py_run_process('x4_Anime_6B-Official', 64, 4, False, None, 'Image', 'input.jpg', '.', '0', 'real-esrgan')
if __name__ == '__main__':
    if os.getenv('production') == 'true':
        app.run(host='0.0.0.0', port=9000)
    else:
        app.run(debug=True)
