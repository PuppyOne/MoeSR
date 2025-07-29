import json
from fastapi import APIRouter, HTTPException

from config import base_path


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("/{task_id}")
async def get_task(task_id: str):
    """获取任务状态"""
    meta_path = base_path / task_id / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail="Task not found.")

    with open(meta_path, "r", encoding="utf-8") as meta_file:
        return json.load(meta_file)
