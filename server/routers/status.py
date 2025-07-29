from fastapi import APIRouter

from core.global_state import state_manager


router = APIRouter(prefix='/status', tags=['status'])


@router.get('')
def get_task_status():
    """获取任务状态"""
    return {
        'status': state_manager.last_state,
        'last_progress': state_manager.last_progress,
        'last_progress_set_time': state_manager.last_progress_set_time,
    }
