from fastapi import APIRouter
import onnxruntime as ort


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
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
