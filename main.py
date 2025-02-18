from comfyui_api import ComfyUIClient
import time
import os
import mimetypes
import asyncio
import websockets
import json
import requests
import os
import logging
from typing import Optional, Dict
from pathlib import Path


def upload_image(image_path: str):
    """上传图片并返回URL"""
    try:
        # 获取文件的 MIME 类型
        content_type = mimetypes.guess_type(image_path)[0]
        print(f"Uploading image: {image_path}")
        
        # 准备文件和headers
        files = {
            'file': (
                os.path.basename(image_path),
                open(image_path, 'rb'),
                content_type
            )
        }

        MinIO_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3MzkwMDg1NTMsInN1YiI6IjEifQ.VURfKY7NyPIsnIJz9P-ElZz-HMlF7nqnX4Am5eQ7wO0'
        base_url = "http://192.168.0.52:8000/api/v1"

        headers = {'Authorization': f'Bearer {MinIO_TOKEN}'}
        
        # 发送请求
        response = requests.post(
            f"{base_url}/images/upload",
            files=files,
            headers=headers
        )
        
        if response.status_code == 200:
            image_data = response.json()
            print(f"Image data: {image_data}")
            print(f"Image uploaded successfully: {image_data['url']}")
            return image_data['url'], image_data['id']
        else:
            print(f"Image upload failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error uploading image: {str(e)}")
        return None
    finally:
        # 确保关闭文件
        if 'files' in locals() and 'file' in files:
            files['file'][1].close()

def test():
    # image_folder = "/home/swgz/work/ComfyUI/input/images"
    image_folder = "/home/swgz/work/comfyui_api/input/人脸匿名样片4"
    client = ComfyUIClient()

    if not client.server_available:
        print("ComfyUI 服务器不可用，请检查配置或服务器状态。")
        exit()

    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(image_folder, filename)
            print(f"正在处理图片: {image_path}")
            # 上传到 MinIO
            result = upload_image(image_path) 
            minio_url = result[0] 

            # 记录开始时间
            start_time = time.time()
            print(f"图片minio_url: {minio_url}")
            result = client.process_multiple_face_desensitization_auto(minio_url)
            print(result)
            # 记录结束时间
            end_time = time.time()

            # 计算耗时
            elapsed_time = end_time - start_time

            print(f"耗时: {elapsed_time:.2f} 秒")

# 主函数
if __name__ == "__main__":

    client = ComfyUIClient()

    image_path = 'https://n.sinaimg.cn/sinakd10111/325/w1242h1483/20201118/8b70-kcysmrw5280926.jpg'

    face_image_path = 'https://pic1.zhimg.com/v2-ddc98982b76a61236672a9fca809dd6c_720w.jpg?source=172ae18b'
    
    task_id = '9eae9df7-eac6-4c0d-9df9-e7f4f83f8ba1'
    work_id = '1'

    # 记录开始时间
    start_time = time.time()

    # 客片换脸
    # result = client.process_face_swap_thumbnail(image_path, face_image_path)
    # print(result)

    # result = client.process_face_swap(task_id, work_id)
    # print(result)

    # # 客片人脸脱敏
    # result = client.process_face_desensitization_thumbnail(image_path)
    # print(result)

    # result = client.process_face_desensitization(task_id, work_id)
    # print(result)

    # result = client.process_image_upscale(task_id)
    # print(result)

    # image_path = 'https://www.jiaphoto.net/Public/upload/2019-06-18/5d085600a806e.jpg'
    # image_path = 'https://ts1.cn.mm.bing.net/th/id/R-C.63fe5d4a3b0d4fe29a39cc24d80d63c8?rik=%2f5S7WyLaiRlm8A&riu=http%3a%2f%2fcdn.muxi520.com%2f2022-06-24%2fcky5rvxfxjobra1zm7.jpg&ehk=DtjWIrLVKeInWT3YX%2bWZUd9Rg%2fKUGAwki6wVJuiYgH8%3d&risl=&pid=ImgRaw&r=0'
    
    # face_image_path = 'https://ts1.cn.mm.bing.net/th/id/R-C.5f10d21d142995f1e28c791d9a8fdc24?rik=WMQ89o3a%2bYYq5Q&riu=http%3a%2f%2fp1.qhimg.com%2ft010e22b8490821150f.jpg%3f1200*800&ehk=hqeRq5HPWFHQTJvCHcmKkVT3RM9RSS8oQgiVx6Wq%2fOU%3d&risl=&pid=ImgRaw&r=0'
    
    # order = [1, 2] 
    
    # result = client.process_multiple_face_swap_fast(image_path, face_image_path)
    # print(result)

    # result = client.process_multiple_face_desensitization_fast(image_path)
    # print(result)

    # result = client.process_multiple_face_swap(image_path, face_image_path, order)
    # print(result) 

    # result = client.process_multiple_face_desensitization(image_path, order)
    # print(result)

    result = client.process_multiple_face_desensitization_auto(image_path)
    print(result)
    
    # result = client.process_face_swap_auto(image_path, face_image_path)
    # print(result)

    # test()

    # 记录结束时间
    end_time = time.time()

    # 计算耗时
    elapsed_time = end_time - start_time

    print(f"耗时: {elapsed_time:.2f} 秒")