from fastapi import APIRouter

from core.global_state import state_manager


router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def get_models():
    """返回按 algo 分类的 model 名称列表"""
    result: dict[str, list[str]] = {}
    for model in state_manager.model_list:
        result.setdefault(model.algo, []).append(model.name)
    return result
