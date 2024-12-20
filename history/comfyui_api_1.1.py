import os
import requests
import json
import io
import time
import logging
import chardet
import random
from PIL import Image
from typing import Optional
from pydantic_settings import BaseSettings
from minio import Minio
from minio.error import S3Error
from datetime import timedelta

# 配置类
class Settings(BaseSettings):
    # COMFYUI_URL: str = "http://127.0.0.1:8188"
    COMFYUI_URL: str = "http://192.168.0.52:8188"
    MAX_ATTEMPTS: int = 60
    RETRY_DELAY: int = 5
    CLIENT_ID: str = "your_client_id"
    MINIO_URL: str = "img.sw.gz.cn"
    MINIO_ACCESS_KEY: str = "DMMEDkFR7k4ls37cvjSM"
    MINIO_SECRET_KEY: str = "oSPVOKYcG9YoKct7MjKg8IjOqV3J39Hl8sKcFwi2"
    BUCKET_NAME: str = "comfyui-output" #桶名称

settings = Settings()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ComfyUIClient:

    def __init__(self):
        self.temp_dir = './output'
        self.data_json_dir = './data/'
        os.makedirs(self.temp_dir, exist_ok=True)
        self.server_available = self.check_comfyui_server()
        self.tasks = [] 
        
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
            with open(workflow_api, 'rb') as f:
                raw_data = f.read()
                detected = chardet.detect(raw_data)
                encoding = detected['encoding']
            
            with open(workflow_api, 'r', encoding=encoding) as f:
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

    # def upload_image(self, file_path: str) -> Optional[str]:
    #     if not self.check_comfyui_server():
    #         logging.error("ComfyUI服务器不可用")
    #         return None

    #     try:
    #         with open(file_path, "rb") as file:
    #             filename = os.path.basename(file_path)
    #             files = {"image": (filename, file, "image/png")}
    #             response = requests.post(f"{settings.COMFYUI_URL}/upload/image", files=files, timeout=30)
            
    #         if response.status_code == 200:
    #             return response.json()['name']
    #         else:
    #             logging.error(f"上传到ComfyUI失败: {response.text}")
    #             return None
    #     except requests.RequestException as e:
    #         logging.error(f"上传请求异常: {str(e)}")
    #         return None
    #     except IOError as e:
    #         logging.error(f"文件读取错误: {str(e)}")
    #         return None
    #     except json.JSONDecodeError as e:
    #         logging.error(f"JSON解析错误: {str(e)}")
    #         return None
    #     except Exception as e:
    #         logging.error(f"未知错误: {str(e)}")
    #         return None

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
            logging.error("ComfyUI 服务器不可用，停止请求。")
            return {"status": 1, "message": "ComfyUI 服务器不可用"}
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
            logging.error("ComfyUI 服务器不可用，停止请求。")
            return {"status": 1, "message": "ComfyUI 服务器不可用"}

        try:
            response = requests.get(f"{settings.COMFYUI_URL}/history/{task_id}", timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                # logging.info(f"任务结果: {result}")
                print(f"任务结果: {result}")
                if task_id in result:
                    # 检查是否有错误信息
                    if result[task_id].get('status', {}).get('status_str') == 'error':
                        error_message = result[task_id].get('status', {})
                        logging.error(f"ComfyUI返回错误: {error_message}")
                        error_message = "ComfyUI返回错误"
                        return {"status": 1, "message": error_message}

                    outputs = result[task_id]['outputs']
                    if outputs and save_nodeID in outputs and outputs[save_nodeID]['images']:
                        image_filename = outputs[save_nodeID]['images'][0]['filename']
                        subfolder = outputs[save_nodeID]['images'][0]['subfolder']
                        image_url = f"{settings.COMFYUI_URL}/view?filename={image_filename}&subfolder={subfolder}&type=output"

                        #保存到 JSON 文件
                        if self.tasks:
                            print(self.tasks)
                            self.tasks['task_id'] = task_id
                            json_filename = self.data_json_dir + task_id
                            json_path = os.path.join(os.getcwd(), json_filename)  # 使用当前工作目录
                            with open(json_path, 'w', encoding='utf-8') as json_file:
                                json.dump(self.tasks, json_file, ensure_ascii=False, indent=4)

                        return image_url

                return None
            else:
                logging.error(f"获取任务结果失败: HTTP状态码 {response.status_code}")
                return {"status": 1, "message": "获取任务结果失败"}
        except requests.RequestException as e:
            logging.error(f"获取结果请求异常: {str(e)}")
            return {"status": 1, "message": "获取结果请求异常"}

    def process_workflow(self, task_name) -> Optional[dict]:
        task_id = self.queue_prompt(self.workflow)
        if not task_id:
            return {"status": 1, "message": "工作流执行失败"}

        for attempt in range(settings.MAX_ATTEMPTS):
            result = self.get_task_result(task_id, self.save_image_nodeID)
            if isinstance(result, dict) and result.get("status") == 1:
                # 如果返回的是错误信息，直接返回
                return result

            if result:
                try:
                    image_response = requests.get(result, timeout=30)
                    if image_response.status_code == 200:

                        # 清空 temp_dir 目录中的所有文件
                        for filename in os.listdir(self.temp_dir):
                            file_path = os.path.join(self.temp_dir, filename)
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                              
                        output_image = Image.open(io.BytesIO(image_response.content))
                        unique_filename = f"comfyui_output_{int(time.time())}_{task_id}.png"
                        output_path = os.path.join(self.temp_dir, unique_filename)
                        output_image.save(output_path, format="PNG")
                        file_path = settings.BUCKET_NAME+ '/' + task_name + '/' + unique_filename

                        # 上传到 MinIO
                        minio_url = self.upload_to_minio(output_path, task_name + '/' + unique_filename)
                        if minio_url:
                            self.tasks = []
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

    def process_face_swap(self, input_image: str, input_face: str) -> Optional[dict]:
        task_name = "face_swap"
        uploaded_file_nodeID = "111"
        uploaded_face_nodeID = "112"
        save_image_nodeID = '108'

        workflow_api = './api/face_swap.json'
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID
        
        # uploaded_file = self.upload_image(input_image)
        # uploaded_face = self.upload_image(input_face)

        uploaded_file = input_image
        uploaded_face = input_face

        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        if not uploaded_face:
            return {"status": 1, "message": "面部图片上传失败"}
        
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        self.workflow[uploaded_face_nodeID]["inputs"]["url"] = uploaded_face
        
        return self.process_workflow(task_name)

      
    def process_face_desensitization(self, input_image: str) -> Optional[str]:
        task_name = "face_desensitization"
        workflow_api = './api/人脸脱敏四合一.json'

        uploaded_file_nodeID = "539"
        save_image_nodeID = '367'
        
        self.tasks = {
            'url': input_image, 
            'task_id': '',
            'task_propmt': '', 
            'tasks_seed': {}
        }

        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID

        # 定义节点数据
        self.nodes = [
            [104, 129, 170, 528],
            [704, 711, 713, 725],
            [750, 757, 759, 771],
            [796, 803, 805, 817]
        ]

        # 遍历节点数据并生成随机数
        for i in range(len(self.nodes)):
            work_id = i + 1
            random_numbers = [random.randint(1, 4294967294) for _ in self.nodes[i]]

            self.tasks['tasks_seed'][work_id] = {
                'node_ids': self.nodes[i],
                'random_numbers': random_numbers
            }
            node_list = self.nodes[i]
            random_numbers_list = random_numbers
            for j in range(len(node_list)):
                self.workflow[str(node_list[j])]["inputs"]["seed"] = str(random_numbers_list[j])    
        
        # 上传输入图片
        # uploaded_file = self.upload_image(input_image)
        # if not uploaded_file:
        #     return {"status": 1, "message": "图片上传失败"}
        
        uploaded_file = input_image
        if not uploaded_file:
            return {"status": 1, "message": "图片上传失败"}
        
        # 修改工作流
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = uploaded_file
        return self.process_workflow(task_name)    

    def process_face_desensitization_upscale(self, task_id: str, work_id: str) -> Optional[str]:
        task_name = "face_desensitization_upscale"
        workflow_api = './api/人脸脱敏高清放大.json'
        uploaded_file_nodeID = "539"
        save_image_nodeID = '833'
        
        self.workflow = self.load_workflow(workflow_api)
        self.save_image_nodeID = save_image_nodeID
        
        task_file_path = os.path.join(self.data_json_dir, task_id)
        # 检查文件是否存在
        if not os.path.exists(task_file_path):
            return {"status": 1, "message": "未找到task_id任务"}
        with open(task_file_path, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
        
        
        # 根据 work_id 获取对应的节点 ID 和随机数
        work_data = task_data['tasks_seed'].get(work_id)
        
        if work_data is None:
            raise ValueError(f"Work ID {work_id} not found in task data.")
        

        random_numbers = work_data['random_numbers']
        nodes = [104, 129, 170, 528]
        
        for i in range(len(nodes)):
            self.workflow[str(nodes[i])]["inputs"]["seed"] = str(random_numbers[i])
        
        # 修改工作流
        input_image = task_data['url']
        self.workflow[uploaded_file_nodeID]["inputs"]["url"] = input_image
        
        return self.process_workflow(task_name)

if __name__ == "__main__":
    # image_path = './input/1.jpg'
    # face_image_path = './input/女人1.jpg' 

    image_path = 'https://ts1.cn.mm.bing.net/th/id/R-C.eed97557f689df2382b6a9fc85ed172e?rik=d%2fBN9fsXJ2nz2w&riu=http%3a%2f%2fup.bizhizu.com%2fpic%2fd1%2fb7%2fc1%2fd1b7c1c9d4362b4ed5a433e69a19b383.jpg&ehk=OafBZEPbO07cQidzqmNBh0FzR5lM78gdhBOg7%2bjNdis%3d&risl=&pid=ImgRaw&r=0'
    
    face_image_path = 'https://k.sinaimg.cn/www/dy/slidenews/24_img/2016_19/74485_1363976_499220.jpg/w640slw.jpg'

    client = ComfyUIClient()


    # 客片换脸
    # result = client.process_face_swap(image_path, face_image_path)
    # print(result)
    
    # # 客片人脸脱敏
    # result = client.process_face_desensitization(image_path)
    # print(result)
    
    task_id = 'ea69b0f1-119b-4d2b-8e59-e595bb0804ec'
    work_id = '1'

    result = client.process_face_desensitization_upscale(task_id, work_id)
    print(result)