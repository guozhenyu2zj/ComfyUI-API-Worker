from celery import Celery
from config import *
import time
from comfyui_api import ComfyUIClient

app = Celery('tasks',
             broker=f'pyamqp://{broker_user}:{broker_pwd}@{broker_hostname}:{broker_port}/{broker_vhost}',
             backend=f'redis://{backend_hostname}:{backend_port}/{backend_db_num}'
            )

app.conf.update(
    task_routes = {
        'tasks.process_face_swap': {'queue': 'face_swap'},
        'tasks.process_face_swap_thumbnail': {'queue': 'face_swap_thumbnail'},
        'tasks.process_image_upscale': {'queue': 'image_upscale'},
        'tasks.process_face_desensitization': {'queue': 'face_desensitization'},
        'tasks.process_face_desensitization_thumbnail': {'queue': 'face_desensitization_thumbnail'},
        'tasks.process_multiple_face_desensitization_fast': {'queue': 'multi_face_desensitization_fast'},
        'tasks.process_multiple_face_swap_fast': {'queue': 'multi_face_swap_fast'},
        'tasks.process_multiple_face_desensitization': {'queue': 'multi_face_desensitization'},
        'tasks.process_multiple_face_swap': {'queue': 'multi_face_swap'},
        'tasks.process_multiple_face_desensitization_auto': {'queue': 'multi_face_desensitization_auto'},
        'tasks.process_face_swap_auto': {'queue': 'face_swap_auto'},
    },
)

app.conf.timezone = 'Asia/Shanghai'

@app.task
def process_face_desensitization_thumbnail(image_path, **kwargs):
    client = ComfyUIClient()  
    result = client.process_face_desensitization_thumbnail(image_path)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

@app.task
def process_face_desensitization(comfyui_task_id, work_id, **kwargs):
    client = ComfyUIClient()  
    result = client.process_face_desensitization(comfyui_task_id, work_id)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

@app.task
def process_face_swap_thumbnail(image_path, face_image_path, **kwargs):
    client = ComfyUIClient()  
    result = client.process_face_swap_thumbnail(image_path, face_image_path)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

@app.task
def process_face_swap(comfyui_task_id, work_id, **kwargs):
    client = ComfyUIClient()  
    result = client.process_face_swap(comfyui_task_id, work_id)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

@app.task
def process_image_upscale(comfyui_task_id, **kwargs):
    client = ComfyUIClient()  
    result = client.process_image_upscale(comfyui_task_id)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

# 任务6 多重人脸快速脱敏
@app.task
def process_multiple_face_desensitization_fast(image_path, **kwargs):
    client = ComfyUIClient()  
    result = client.process_multiple_face_desensitization_fast(image_path)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

# 任务7 多人快速换脸
@app.task
def process_multiple_face_swap_fast(image_path, face_image_path, **kwargs):
    client = ComfyUIClient()  
    result = client.process_multiple_face_swap_fast(image_path, face_image_path)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

# 任务8 多重人脸脱敏（细致）
@app.task
def process_multiple_face_desensitization(image_path, order, **kwargs):
    client = ComfyUIClient()  
    result = client.process_multiple_face_desensitization(image_path, order)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

# 任务9 多人换脸（细致）
@app.task
def process_multiple_face_swap(image_path, face_image_path, order, **kwargs):
    client = ComfyUIClient()  
    result = client.process_multiple_face_swap(image_path, face_image_path, order)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

@app.task
def process_multiple_face_desensitization_auto(image_path, **kwargs):
    client = ComfyUIClient()  
    result = client.process_multiple_face_desensitization_auto(image_path)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result

@app.task
def process_face_swap_auto(image_path, face_image_path, **kwargs):
    client = ComfyUIClient()  
    result = client.process_face_swap_auto(image_path, face_image_path)
    status = result["status"]
    if status != 0:
        raise ValueError(result["message"])
    return result