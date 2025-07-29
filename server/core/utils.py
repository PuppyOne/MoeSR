from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile
from werkzeug.utils import secure_filename

from config import base_path
from .global_state import state_manager


def seconds_to_hms(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    return f"{int(hours):0>2d}:{int(minutes):0>2d}:{int(seconds):0>2d}"


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


def progress_setter(progress,current_time,total_img_num,processed_img_num):
    try:
        global last_progress,last_progress_set_time
        progress_percent = round(progress*100)
        total_progress_percent = round((processed_img_num+progress)/total_img_num*100)
        etr_str = '--:--:--'
        total_etr_str = '--:--:--'
        if state_manager.last_progress is not None and state_manager.last_progress_set_time:
            etr = (current_time-state_manager.last_progress_set_time) * (1-state_manager.last_progress)/(progress-state_manager.last_progress)
            total_etr = (current_time-state_manager.last_progress_set_time) * (total_img_num-processed_img_num-state_manager.last_progress)/(progress-state_manager.last_progress)
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
