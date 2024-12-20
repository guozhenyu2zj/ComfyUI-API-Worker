#!/bin/bash

# 停止现有的 Celery 进程
pkill -9 -f 'celery'

# 启动 Celery worker 处理任务
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n face_swap@GPU-4070 -Q face_swap --concurrency=1 --loglevel=INFO >> logs/face_swap.log 2>&1&
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n face_desensitization@GPU-4070 -Q face_desensitization --concurrency=1 --loglevel=INFO >> logs/face_desensitization.log 2>&1&
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n face_swap_thumbnail@GPU-4070 -Q face_swap_thumbnail --concurrency=1 --loglevel=INFO >> logs/face_swap_thumbnail.log 2>&1&
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n face_desensitization_thumbnail@GPU-4070 -Q face_desensitization_thumbnail --concurrency=1 --loglevel=INFO >> logs/face_desensitization_thumbnail.log 2>&1&
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n image_upscale@GPU-4070 -Q image_upscale --concurrency=1 --loglevel=INFO >> logs/image_upscale.log 2>&1&

# 启动新的 worker 处理多脸脱敏任务（快速模式） 
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n multi_face_desensitization_fast@GPU-4070 -Q multi_face_desensitization_fast --concurrency=1 --loglevel=INFO >> logs/multi_face_desensitization_fast.log 2>&1&

# 启动新的 worker 处理多脸换脸任务（快速模式） 
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n multi_face_swap_fast@GPU-4070 -Q multi_face_swap_fast --concurrency=1 --loglevel=INFO >> logs/multi_face_swap_fast.log 2>&1&

# 启动新的 worker 处理多脸脱敏任务
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n multi_face_desensitization@GPU-4070 -Q multi_face_desensitization --concurrency=1 --loglevel=INFO >> logs/multi_face_desensitization.log 2>&1&

# 启动新的 worker 处理多脸换脸任务
/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n multi_face_swap@GPU-4070 -Q multi_face_swap --concurrency=1 --loglevel=INFO >> logs/multi_face_swap.log 2>&1&

/home/swgz/miniconda3/envs/ComfyUI/bin/python -m celery -A tasks worker -n multi_face_desensitization_auto@GPU-4070 -Q multi_face_desensitization_auto --concurrency=1 --loglevel=INFO >> logs/multi_face_desensitization_auto.log 2>&1&
