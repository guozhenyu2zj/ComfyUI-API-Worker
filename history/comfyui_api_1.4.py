import os
import requests
import json
import io
import time
import logging
import chardet
import random
import ollama
import base64
from io import BytesIO
from PIL import Image
from typing import Optional
from pydantic_settings import BaseSettings
from minio import Minio
from minio.error import S3Error
from datetime import timedelta

# 配置类
class Settings(BaseSettings):
    # COMFYUI_URL: str = "http://127.0.0.1:8188"
    # COMFYUI_URL: str = "http://192.168.0.158:8188"
    COMFYUI_URL: str = "http://192.168.0.52:8188"
    MAX_ATTEMPTS: int = 100
    RETRY_DELAY: int = 5
    CLIENT_ID: str = "your_client_id"
    MINIO_URL: str = "img.sw.gz.cn"
    MINIO_ACCESS_KEY: str = "DMMEDkFR7k4ls37cvjSM"
    MINIO_SECRET_KEY: str = "oSPVOKYcG9YoKct7MjKg8IjOqV3J39Hl8sKcFwi2"
    BUCKET_NAME: str = "comfyui-output" #桶名称
    API_ENDPOINT: str = "http://192.168.0.52:8007/detect_faces"

settings = Settings()



class ComfyUIClient:
    def __init__(self):
        self.temp_dir = './output'
        self.data_json_dir = './data/database.json'
        os.makedirs(self.temp_dir, exist_ok=True)
        self.server_available = self.check_comfyui_server()
        self.tasks = {}
        self.task_id = ""
        self.task_name = ""
        self.image_data = ""
        self.ollama_model = 'minicpm-v:latest'
        # self.ollama_host = "http://192.168.0.158:11434"
        self.ollama_host = "http://localhost:11434"
        
        # 配置日志
        self.comfyui_logger = logging.getLogger('comfyui')
        self.comfyui_logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler('comfyui.log', mode='w')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.comfyui_logger.addHandler(file_handler)
              
        # 初始化 MinIO 客户端
        self.minio_client = Minio(
            settings.MINIO_URL,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=True
        )

    @staticmethod
    def load_workflow(workflow_api):
        try:
            with open(workflow_api, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载工作流失败: {str(e)}")
            raise

    @staticmethod
    def check_comfyui_server():
        try:
            response = requests.get(settings.COMFYUI_URL, timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def save_task_info(self) -> Optional[str]:
        json_filename = os.path.join(os.getcwd(), self.data_json_dir)
        if not os.path.exists(json_filename):
            with open(json_filename, 'w', encoding='utf-8') as json_file:
                    json.dump({}, json_file, ensure_ascii=False, indent=4)
        with open(json_filename, 'r', encoding='utf-8') as json_file:
            data_tasks = json.load(json_file)
            data_tasks[self.task_id] = self.tasks
            data_tasks[self.task_id]['task_name'] = self.task_name
            data_tasks[self.task_id]['result_url'] = self.result_url
            print(f"任务 ID {self.task_id} 已添加。")

        try:
            with open(json_filename, 'w', encoding='utf-8') as json_file:
                if len(data_tasks) > 100:
                    keys_to_remove = list(data_tasks.keys())[:50]  
                    for key in keys_to_remove:
                        del data_tasks[key]
                    print(f"删除前五十条任务记录")
                json.dump(data_tasks, json_file, ensure_ascii=False, indent=4)
                print(f"任务已成功写入")
        except Exception as e:
            print(f"写入文件时发生错误: {e}")

    def upload_to_minio(self, file_path: str, object_name: str) -> Optional[str]:
        try:
            self.minio_client.fput_object(settings.BUCKET_NAME, object_name, file_path)
            expires = timedelta(days=7)
            url = self.minio_client.presigned_get_object(settings.BUCKET_NAME, object_name, expires=expires)
            return url
        except S3Error as e:
            logging.error(f"MinIO 上传失败: {e}")
            return None

    def queue_prompt(self, prompt: dict) -> Optional[str]:
        if not self.check_comfyui_server():
            logging.error("ComfyUI 服务器请求失败。")
            return {"status": 1, "message": "ComfyUI 服务器请求失败，请稍后再试"}

        payload = {
            "prompt": prompt,
            "client_id": settings.CLIENT_ID
        }

        try:
            response = requests.post(f"{settings.COMFYUI_URL}/prompt", json=payload, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('prompt_id')
            else:
                logging.error(f"ComfyUI请求失败: {response.text}")
                return None
        except requests.RequestException as e:
            logging.error(f"生成请求异常: {str(e)}")
            return None

    def get_task_result(self, task_id: str, save_nodeID: str) -> Optional[str]:
        if not self.check_comfyui_server():
            # logging.error("ComfyUI 服务器请求失败。")
            return {"status": 1, "message": "ComfyUI 服务器请求失败，请稍后再试"}

        try:
            response = requests.get(f"{settings.COMFYUI_URL}/history/{task_id}", timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                self.comfyui_logger.info("任务结果: {}")
                # print("任务结果: {}")
                
                if task_id in result:
                    
                    print(f"ComfyUI task_id={task_id} 返回任务结果")

                    # 检查是否有错误信息
                    if result[task_id].get('status', {}).get('status_str') == 'error':
                        error_message = result[task_id].get('status', {})
                        logging.error(f"ComfyUI返回错误: {error_message}")
                        error_message = "ComfyUI返回错误"
                        return {"status": 1, "message": error_message}

                    outputs = result[task_id]['outputs']
                    self.comfyui_logger.info(f"任务结果: {outputs}")
                    
                    try:
                      SaveImage = outputs[save_nodeID]['images']
                    except:
                        return {"status": 1, "message": "任务完成，返回图片失败"}

                    if outputs and save_nodeID in outputs and SaveImage:
                        image_filename = outputs[save_nodeID]['images'][0]['filename']
                        subfolder = outputs[save_nodeID]['images'][0]['subfolder']
                        image_url = f"{settings.COMFYUI_URL}/view?filename={image_filename}&subfolder={subfolder}&type=output"
                        self.task_id = task_id      
                        return image_url

                return None
            else:
                logging.error(f"获取任务结果失败: HTTP状态码 {response.status_code}")
                return {"status": 1, "message": "获取任务结果失败"}
        except requests.RequestException as e:
            logging.error(f"获取结果请求异常: {str(e)}")
            return {"status": 1, "message": "获取结果请求异常"}

    def process_workflow(self) -> Optional[dict]:
        task_id = self.queue_prompt(self.workflow)
        if not task_id:
            return {"status": 1, "message": "工作流执行失败"}

        for attempt in range(settings.MAX_ATTEMPTS):
            result = self.get_task_result(task_id, self.save_image_nodeID)
            if isinstance(result, dict) and result.get("status") == 1:
                return result

            if result:
                try:
                    image_response = requests.get(result, timeout=30)
                    if image_response.status_code == 200:

                        # 清理 temp_dir 目录
                        files = os.listdir(self.temp_dir)
                        image_files = [f for f in files if os.path.isfile(os.path.join(self.temp_dir, f)) and os.path.splitext(f)[1].lower() in {'.png', '.jpg'}]
                        if len(image_files) > 10:
                          image_files.sort(key=lambda x: os.path.getctime(os.path.join(self.temp_dir, x)))
                          for filename in image_files[:1]:  # 删除前 1 张
                              file_path = os.path.join(self.temp_dir, filename)
                              os.remove(file_path)
                              print(f"删除文件: {file_path}")
                
                        Image.MAX_IMAGE_PIXELS = None 
                        output_image = Image.open(io.BytesIO(image_response.content))
                        
                        unique_filename = f"comfyui_output_{int(time.time())}_{task_id}.png"
                        output_path = os.path.join(self.temp_dir, unique_filename)
                        output_image.save(output_path, format="PNG")
                        file_path = settings.BUCKET_NAME+ '/' + self.task_name + '/' + unique_filename

                        # 上传到 MinIO
                        minio_url = self.upload_to_minio(output_path, self.task_name + '/' + unique_filename)
                        if minio_url:
                            self.result_url = minio_url
                            self.save_task_info()
                            # self.tasks = []
                            return {"status": 0, "url": minio_url , "task_id" : task_id, "file_path" : file_path}
                        else:
                            return {"status": 1, "message": "上传到 MinIO 失败"}
                    else:
                        logging.error(f"下载图片失败: HTTP状态码 {image_response.status_code}")
                        return {"status": 1, "message": "下载图片失败"}
                except requests.RequestException as e:
                    logging.error(f"下载图片时发生错误: {str(e)}")
                    return {"status": 1, "message": "下载图片时发生错误"}
            time.sleep(settings.RETRY_DELAY)

        logging.error("处理图片超时")
        return {"status": 1, "message": "处理图片超时"}
    
    
    # 检测人脸数量
    def detect_faces(self, image_url: str) -> int:
        try:
            response = requests.get(image_url, stream=True)
            response.raise_for_status() 
            image_data = BytesIO(response.content)
            files = {"file": ("image.jpg", image_data, response.headers.get('Content-Type', 'image/jpeg'))}

            api_response = requests.post(settings.API_ENDPOINT, files=files)

            if api_response.status_code == 200:
                api_response_json = api_response.json()  
                num_faces = api_response_json.get("num_faces")
                faces = api_response_json.get("faces")
                print(f"检测到 {num_faces} 张人脸")
                return {"num_faces": num_faces, "faces": faces}
            elif api_response.status_code == 422:
                print(f"验证错误: {api_response.json()}")
                return 0  
            else:
                print(f"错误: {api_response.status_code} - {api_response.text}")
                return 0  

        except Exception as e:
            print(f"人脸检测失败: {e}")
            return 0  

    # 获取图片的尺寸           
    def get_image_longest_side(self, image_url: str) -> Optional[int]:
        try:
            response = requests.get(image_url, stream=True)
            response.raise_for_status()  # 检查 HTTP 状态码

            self.image_data = BytesIO(response.content)
            img = Image.open(self.image_data)
            width, height = img.size
            longest_side = max(width, height)
            return longest_side

        except requests.exceptions.RequestException as e:
            print(f"下载图片失败: {e}")
            return None
        except Exception as e:
            print(f"处理图片失败: {e}")
            return None
    
    # 使用 Ollama 询问图片中的信息
    def ask_ollama_about_image(self, prompt: str) -> str:
        try:
            img = Image.open(self.image_data)
            if img.mode == 'RGBA':
                img = img.convert('RGB')  # 转换为 RGB 模式
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            base64_image = base64.b64encode(buffered.getvalue()).decode()
            if not base64_image:
                return None
            
            host = os.environ.get("OLLAMA_HOST", self.ollama_host)
            client = ollama.Client(host=host)
            response = client.chat(
                model = self.ollama_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [base64_image],
                    }
                ],
            )
            return response['message']['content']
        except Exception as e:
            print(f"Ollama 询问失败: {e}")
            return None

    # 客片人脸脱敏 缩略图
    def process_face_desensitization_thumbnail(self, input_image: str) -> Optional[str]:
        self.task_name = "face_desensitization_thumbnail"
        workflow_api = './api/人脸脱敏/人脸脱敏.json'

        uploaded_file_nodeID = "637"
        save_image_nodeID = '367'
        
        self.tasks = {
            'image_url': input_image,
            'result_url': "",  
        }

        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID
        
        uploaded_file = input_image
        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        
        # 修改工作流
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        return self.process_workflow()    

    # 客片换脸 缩略图
    def process_face_swap_thumbnail(self, input_image: str, input_face: str) -> Optional[dict]:
        self.task_name = "face_swap_thumbnail"
        workflow_api = './api/客照换脸/客照换脸.json'

        uploaded_file_nodeID = "637"
        uploaded_face_nodeID = "639"
        save_image_nodeID = '367'

        self.tasks = {
            'image_url': input_image, 
            'face_url': input_face,
            'result_url': "",  
        }
                
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        uploaded_file = input_image
        uploaded_face = input_face

        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        if not uploaded_face:
            return {"status": 1, "message": "面部图片上传失败"}
        
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        self.workflow[uploaded_face_nodeID]["inputs"]["url"] = uploaded_face
        
        return self.process_workflow()

    # 客片人脸脱敏
    def process_face_desensitization(self, task_id: str, work_id: str) -> Optional[str]:
        self.task_name = "face_desensitization"
        json_files = {
            "1": "人脸脱敏/人脸脱敏task-1.json",
            "2": "人脸脱敏/人脸脱敏task-2.json",
            "3": "人脸脱敏/人脸脱敏task-3.json",
            "4": "人脸脱敏/人脸脱敏task-4.json"
        }
         # 根据 work-id 选择对应的 JSON 文件
        if work_id not in json_files:
            return {"status": 1, "message": "没有对应的工作流"}
        workflow_api = './api/'+json_files[work_id]
        
        uploaded_file_nodeID = '639'
        save_image_nodeID = '637'
        
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        self.tasks = {
            'result_url': "", 
        }

        # 读取 JSON 文件
        json_filename = os.path.join(os.getcwd(), self.data_json_dir)
        with open(json_filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            if task_id in data:
                data_json = data[task_id]
                image_url =  data_json["image_url"]
            else:
                return {"status": 1, "message": "未找到task_id任务"}
        
        print("Image URL:", image_url)

        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = image_url
        
        return self.process_workflow()

    # 客片换脸
    def process_face_swap(self, task_id: str, work_id: str) -> Optional[dict]:
        self.task_name = "face_swap"
        json_files = {
            "1": "客照换脸/客照换脸-task1.json",
            "2": "客照换脸/客照换脸-task2.json",
            "3": "客照换脸/客照换脸-task3.json",
            "4": "客照换脸/客照换脸-task4.json"
        }
        
        # 根据 work-id 选择对应的 JSON 文件
        if work_id not in json_files:
            return {"status": 1, "message": "没有对应的工作流"}
        workflow_api = './api/'+json_files[work_id]
        
        uploaded_file_nodeID = '637'
        uploaded_face_nodeID = '639'
        save_image_nodeID = '806'
        
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        # 读取 JSON 文件
        json_filename = os.path.join(os.getcwd(), self.data_json_dir)
        with open(json_filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            if task_id in data:
                data_json = data[task_id]
                image_url =  data_json["image_url"]
                face_url =  data_json["face_url"]
            else:
                return {"status": 1, "message": "未找到task_id任务"}
        
        print("Image URL:", image_url)
        print("Face URL:", face_url)

        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = image_url
        self.workflow[uploaded_face_nodeID]["inputs"]["url"] = face_url
        
        return self.process_workflow()

    # 照片高清放大
    def process_image_upscale(self, task_id: str) -> Optional[str]:
        settings.COMFYUI_URL = "http://192.168.0.158:8188"
        self.task_name = "image_upscale"
        workflow_api = './api/高清放大_脱敏.json'
        
        uploaded_file_nodeID = '4'
        save_image_nodeID = '3'
        
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        # 读取 JSON 文件
        json_filename = os.path.join(os.getcwd(), self.data_json_dir)
        with open(json_filename, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            if task_id in data:
                data_json = data[task_id]
                image_url =  data_json["result_url"]
            else:
                return {"status": 1, "message": "未找到task_id任务"}
        
        print("Image URL:", image_url)

        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = image_url
        
        return self.process_workflow()

    # 多重人脸快速脱敏
    def process_multiple_face_desensitization_fast(self, input_image: str) -> Optional[str]:
        self.task_name = "multiple_face_desensitization_fast"
        workflow_api = './api/人脸脱敏/多重人脸快速脱敏.json'

        uploaded_file_nodeID = "502"
        save_image_nodeID = '503'
        
        self.tasks = {
            'image_url': input_image,
            'result_url': "",  
        }

        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID
        
        uploaded_file = input_image
        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        
        # 修改工作流
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        return self.process_workflow()    

    # 多人快速换脸
    def process_multiple_face_swap_fast(self, input_image: str, input_face: str) -> Optional[dict]:
        self.task_name = "multiple_face_swap_fast"
        workflow_api = './api/客照换脸/多人快速换脸.json'

        uploaded_file_nodeID = "484"
        uploaded_face_nodeID = "485"
        save_image_nodeID = '483'

        self.tasks = {
            'image_url': input_image, 
            'face_url': input_face,
            'result_url': "",  
        }
                
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        uploaded_file = input_image
        uploaded_face = input_face

        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        if not uploaded_face:
            return {"status": 1, "message": "面部图片上传失败"}
        
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        self.workflow[uploaded_face_nodeID]["inputs"]["url"] = uploaded_face
        
        return self.process_workflow()

    # 多人换脸（细致）
    def process_multiple_face_swap(self, input_image: str, input_face: str, order: list) -> Optional[dict]:

        self.task_name = "multiple_face_swap"
        workflow_api = './api/客照换脸/多人细致换脸.json'

        uploaded_file_nodeID = "905"
        uploaded_face_nodeID = "904"
        index_num_nodeID = "865"
        save_image_nodeID = '902'

        self.tasks = {
            'image_url': input_image, 
            'face_url': input_face,
            'result_url': "",  
        }
                
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        uploaded_file = input_image
        uploaded_face = input_face

        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        if not uploaded_face:
            return {"status": 1, "message": "面部图片上传失败"}
        
        # self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        self.workflow[uploaded_face_nodeID]["inputs"]["url"] = uploaded_face
        
        for i in range(len(order)):
          
            print(f"更换第{order[i]}张人脸。")
            if i == 0:
                current_image = uploaded_file
            else:
                current_image = self.result_url

            self.workflow[index_num_nodeID]["inputs"]["Number"] = str(order[i] - 1)
            self.workflow[uploaded_file_nodeID]["inputs"]["url"] = current_image

            result = self.process_workflow()

            if result.get("status") == 0:
                print(f"生成图{self.result_url}") 
            else:
                return result

        return {"status": 0, "url": self.tasks['result_url'], "task_id": result['task_id'], "file_path": result['file_path']}

    # 多重人脸脱敏
    def process_multiple_face_desensitization(self, input_image: str, order: list) -> Optional[dict]:

        self.task_name = "multiple_face_desensitization"
        workflow_api = './api/人脸脱敏/多重人脸细致脱敏.json'

        uploaded_file_nodeID = "920"
        index_num_nodeID = "865"
        save_image_nodeID = '902'

        self.tasks = {
            'image_url': input_image, 
            'result_url': "",  
        }
                
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        uploaded_file = input_image

        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        
        for i in range(len(order)):
          
            print(f"更换第{order[i]}张人脸。")
            if i == 0:
                current_image = uploaded_file
            else:
                current_image = self.result_url

            self.workflow[index_num_nodeID]["inputs"]["Number"] = str(order[i] - 1)
            self.workflow[uploaded_file_nodeID]["inputs"]["url"] = current_image

            result = self.process_workflow()

            if result.get("status") == 0:
                print(f"生成图{self.result_url}") 
            else:
                return result

        return {"status": 0, "url": self.tasks['result_url'], "task_id": result['task_id'], "file_path": result['file_path']}        

    # 多重人脸脱敏 自动
    def process_multiple_face_desensitization_auto(self, input_image: str) -> Optional[dict]:
        settings.COMFYUI_URL = "http://192.168.0.52:8188"
        
        longest_side = self.get_image_longest_side(input_image)
        if longest_side:
            print(f"图片最长边: {longest_side} 像素")
        

        self.tasks = {
            'image_url': input_image, 
            'result_url': "",  
        }
        
        workflow_api = './api/人脸匿名化/人脸匿名化-谷歌API.json'

        uploaded_file_nodeID = "238"
        save_image_nodeID = '237'  

        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID
        uploaded_file = input_image
        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file

        print(f"执行工作流{workflow_api}")
        result = self.process_workflow()
        if result.get("status") == 0:
            print(f"生成图{self.result_url}") 
        else:
            return result

        return {"status": 0, "url": self.tasks['result_url'], "task_id": result['task_id'], "file_path": result['file_path']} 

    # # 多重人脸脱敏 自动
    # def process_multiple_face_desensitization_auto(self, input_image: str) -> Optional[dict]:
    #     settings.COMFYUI_URL = "http://192.168.0.52:8188"
        
    #     self.task_name = "multiple_face_desensitization_auto"
    #     face_data = self.detect_faces(input_image)
    #     if not face_data:
    #         return {"status": 1, "message": f"人脸检测失败"}

    #     face_count = face_data["num_faces"]
    #     faces = face_data["faces"]

    #     order = list(range(1, face_count + 1))
    #     print(order)

    #     longest_side = self.get_image_longest_side(input_image)
    #     if longest_side:
    #         print(f"图片最长边: {longest_side} 像素")

    #     faces_max_side = 0
    #     faces_min_side = float('inf') 
    #     extend_num = 10
        
    #     for face in faces:
    #         box = face["box"]
    #         width = abs(box[2] - box[0])
    #         height = abs(box[3] - box[1])
    #         max_side = max(width, height)
    #         min_side = min(width, height)
    #         faces_max_side = int(max(faces_max_side, max_side))
    #         faces_min_side = int(min(faces_min_side, min_side))
    #         # print(box,max_side,min_side)

    #     print(f"人脸最长边: {faces_max_side}像素, 人脸最短边: {faces_min_side}像素")
        
    #     side_length = longest_side
    #     extend_num = int(faces_max_side * 0.2)
    #     faces_max_side = faces_max_side + extend_num * 2
    #     print(f"裁剪图最长边: {faces_max_side}像素")  

    #     # # 确保裁剪图最长边不超过 1024
    #     # if faces_max_side > 1024:
    #     #     scale_factor = 1024 / faces_max_side
    #     #     side_length = int(side_length * scale_factor)
    #     #     extend_num = int(extend_num * scale_factor)
    #     #     print(f"超过1024像素")
        
    #     # print(f"Resize 生成图最长边 : {side_length}像素, 遮罩扩展边长 : {extend_num}像素")
            
    #     self.tasks = {
    #         'image_url': input_image, 
    #         'result_url': "",  
    #     }

    #     if face_count == 1:
    #         side_length = 2048
    #         extend_num = 156
    #         print(f"Resize 生成图最长边 : {side_length}像素, 遮罩扩展边长 : {extend_num}像素")

    #         prompt = '''
    #         You are a professional photographer, please generate a detailed description for guiding photography based on the facial features in the image, including accurate age, race, makeup, light, the direction in which the eyes are looking, mouth movements, expressions, accessories, and according to your professional knowledge. 
    #         '''
    #         # prompt = '''
    #         # Only use keywords to output the gender and age of the characters and facial expressions, accessories in the image. For example: "boy, 2 years old, neutral"
    #         # '''
    #         ollama_answer = self.ask_ollama_about_image(prompt)
    #         if ollama_answer:
    #             print(ollama_answer)
            
    #         workflow_api = './api/人脸匿名化/人脸匿名化-单人.json'

    #         uploaded_file_nodeID = "238"
    #         prompt_nodeID = "286"
    #         save_image_nodeID = '237'  
    #         side_length_nodeID = '150' 
    #         extend_num_nodeID = "283"  

    #         self.workflow = self.load_workflow(workflow_api)
    #         self.save_image_nodeID = save_image_nodeID
    #         uploaded_file = input_image
    #         if not uploaded_file:
    #             return {"status": 1, "message": "图片上传失败"}
    #         self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
    #         self.workflow[prompt_nodeID]["inputs"]["text"] = ollama_answer
    #         self.workflow[side_length_nodeID]["inputs"]["side_length"] = side_length
    #         self.workflow[extend_num_nodeID]["inputs"]["Number"] = extend_num

    #         print(f"执行工作流{workflow_api}")
    #         result = self.process_workflow()
    #         if result.get("status") == 0:
    #             print(f"生成图{self.result_url}") 
    #         else:
    #             return result

    #     elif face_count > 1:
    #         workflow_api = './api/人脸匿名化/人脸匿名化.json' 
            
    #         if side_length < 2048 or face_count <= 3:
    #             side_length = 2048
    #             extend_num = 156
    #             print(f"Resize 生成图最长边 : {side_length}像素, 遮罩扩展边长 : {extend_num}像素")
    #         else:
    #             print(f"生成图最长边 : {side_length}像素, 遮罩扩展边长 : {extend_num}像素")

    #         uploaded_file_nodeID = "238"
    #         index_num_nodeID = "127"
    #         save_image_nodeID = '237'    
    #         side_length_nodeID = '150'
    #         extend_num_nodeID = "283"

    #         self.workflow = self.load_workflow(workflow_api)
    #         self.save_image_nodeID = save_image_nodeID

    #         uploaded_file = input_image

    #         if not uploaded_file:
    #             return {"status": 1, "message": "图片上传失败"}
            
    #         for i in range(len(order)):
              
    #             print(f"更换第{order[i]}张人脸。")
    #             if i == 0:
    #                 current_image = uploaded_file
    #             else:
    #                 current_image = self.result_url

    #             print(current_image)
    #             print(f"输入原图{current_image}。")
    #             self.workflow[index_num_nodeID]["inputs"]["Number"] = str(order[i] - 1)
    #             self.workflow[uploaded_file_nodeID]["inputs"]["url"] = current_image
    #             self.workflow[side_length_nodeID]["inputs"]["side_length"] = side_length
    #             self.workflow[extend_num_nodeID]["inputs"]["Number"] = extend_num

    #             print(f"执行工作流{workflow_api}")

    #             result = self.process_workflow()

    #             if result.get("status") == 0:
    #                 print(f"生成图{self.result_url}") 
    #             else:
    #                 return result

    #     return {"status": 0, "url": self.tasks['result_url'], "task_id": result['task_id'], "file_path": result['file_path']}   

    # 客片换脸 自动
    def process_face_swap_auto(self, input_image: str, input_face: str) -> Optional[dict]:
        settings.COMFYUI_URL = "http://192.168.0.158:8188"
        
        self.task_name = "face_swap_auto"

        longest_side = self.get_image_longest_side(input_image)
        workflow_api = './api/客照换脸/客照换脸-单人-1920.json'

        uploaded_file_nodeID = "637"
        uploaded_face_nodeID = "639"
        save_image_nodeID = '806'

        self.tasks = {
            'image_url': input_image, 
            'face_url': input_face,
            'result_url': "",  
        }
                
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID
        print(f"执行工作流{workflow_api}")

        uploaded_file = input_image
        uploaded_face = input_face

        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        if not uploaded_face:
            return {"status": 1, "message": "面部图片上传失败"}
        
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        self.workflow[uploaded_face_nodeID]["inputs"]["url"] = uploaded_face
        
        return self.process_workflow()
