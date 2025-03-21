import asyncio
import websockets
import json
import requests
import os
import mimetypes
import logging
from typing import Optional, Dict
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ImageTaskTester:
    def __init__(self):
        # self.base_url = "http://localhost:8000/api/v1"
        self.base_url = "http://192.168.0.52:8000/api/v1"
        self.token = None
        self.api_key = None
        self.api_secret = None
        self.user_id = None
        self.token_file = "token.json"
        self.load_token()
        self.active_tasks = set()  # 添加任务集合来跟踪活动任务
        self.websocket = None
        self.monitor_task = None

    def load_token(self):
        """从文件加载token和API密钥"""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    self.token = data.get('token')
                    self.api_key = data.get('api_key')
                    self.api_secret = data.get('api_secret')
                    self.user_id = data.get('user_id')
                logger.info("Loaded credentials from file")
            except Exception as e:
                logger.error(f"Error loading token file: {e}")

    def save_token(self):
        """保存token和API密钥到文件"""
        try:
            with open(self.token_file, 'w') as f:
                json.dump({
                    'token': self.token,
                    'api_key': self.api_key,
                    'api_secret': self.api_secret,
                    'user_id': self.user_id
                }, f)
            logger.info("Saved credentials to file")
        except Exception as e:
            logger.error(f"Error saving token file: {e}")

    def login(self, username: str, password: str) -> bool:
        """登录获取token"""
        if self.token:
            logger.info("Using existing token")
            return True

        url = f"{self.base_url}/login"
        logger.info(f"Attempting to login with username: {username}")
        try:
            response = requests.post(
                url,
                data={
                    "username": username,
                    "password": password
                }
            )
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Login response: {data}")
                try:
                    self.token = data["access_token"]
                    self.user_id = data["user_id"]
                    self.save_token()
                    logger.info("Login successful")
                    return True
                except KeyError as e:
                    logger.error(f"Login response missing required field: {e}")
                    return False
            else:
                logger.error(f"Login failed: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Login request failed: {str(e)}")
            logger.error("Login failed")
            return False

    def create_api_key(self) -> bool:
        """创建API密钥"""
        if self.api_key and self.api_secret:
            logger.info("Using existing API key")
            return True

        url = f"{self.base_url}/apikeys"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            response = requests.post(
                url,
                json={"name": "test-key"},
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                self.api_key = data["key"]
                self.api_secret = data["secret"]
                self.save_token()
                logger.info(f"API key created: {self.api_key}")
                return True
            else:
                logger.error(f"Failed to create API key: {response.text}")
                return False
        except Exception as e:
            logger.error(f"API key creation failed: {str(e)}")
            return False

    def upload_image(self, image_path: str) -> Optional[str]:
        """上传图片并返回URL"""
        try:
            # 获取文件的 MIME 类型
            content_type = mimetypes.guess_type(image_path)[0]
            logger.info(f"Uploading image: {image_path}")
            
            # 准备文件和headers
            files = {
                'file': (
                    os.path.basename(image_path),
                    open(image_path, 'rb'),
                    content_type
                )
            }
            headers = {'Authorization': f'Bearer {self.token}'}
            
            # 发送请求
            response = requests.post(
                f"{self.base_url}/images/upload",
                files=files,
                headers=headers
            )
            
            if response.status_code == 200:
                image_data = response.json()
                print(f"Image data: {image_data}")
                logger.info(f"Image uploaded successfully: {image_data['url']}")
                return image_data['url'], image_data['id']
            else:
                logger.error(f"Image upload failed: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            return None
        finally:
            # 确保关闭文件
            if 'files' in locals() and 'file' in files:
                files['file'][1].close()

    async def submit_task(self, image_url: str, image_id: str) -> Optional[Dict]:
        """提交任务"""
        url = f"{self.base_url}/tasks/submit"
        params = {
            "api_key": self.api_key,
            "api_secret": self.api_secret
        }

        # 客照换脸
        # data = {
        #     "task_type": "face_swap_auto",
        #     "content": {
        #         "image_path": 'https://www.jiaphoto.net/Public/upload/2019-06-18/5d085600a806e.jpg',
        #         "face_image_path": "https://k.sinaimg.cn/www/dy/slidenews/24_img/2016_19/74485_1363976_499220.jpg/w640slw.jpg"
        #     }
        # }

        # 多人自动人脸脱敏 
        # data = {
        #     "task_type": "multi_face_desensitization_auto",
        #     "content": {
        #         "image_path": image_url
        #     }
        # }

        data = {
            "task_type": "single_face_desensitization_auto",
            "content": {
                "image_path": image_url
            }
        }


        # 超分
        # data = {
        #     "task_type": "image_upscale",
        #     "content": {
        #         "comfyui_task_id": "b6d143c3-a430-49d4-bb7a-6b1ca5e4d05c"
        #     }
        # }

        try:
            response = requests.post(url, params=params, json=data)
            if response.status_code == 200:
                task_data = response.json()
                logger.info(f"Task submitted successfully: {task_data['task_id']}")
                return task_data
            else:
                logger.error(f"Task submission failed: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error submitting task: {str(e)}")
            return None

    async def start_monitor(self):
        """启动全局任务监控"""
        ws_url = f"ws://192.168.0.52:8000/api/v1/tasks/ws/task/{self.user_id}?api_key={self.api_key}&api_secret={self.api_secret}"
        logger.info("Starting global task monitor")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                self.websocket = websocket
                logger.info(f"WebSocket connection established for user {self.user_id}")
                
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        logger.info("=== Message Details ===")
                        logger.info(f"Raw message: {message}")
                        logger.info(f"Parsed data: {data}")
                        logger.info("==================")
                        
                        # 处理任务状态更新
                        task_id = data.get("task_id")
                        status = data.get("result", {}).get("processed")
                        
                        if task_id and status:
                            if status == "successful":
                                logger.info(f"Task {task_id} completed successfully")
                                if task_id in self.active_tasks:
                                    self.active_tasks.remove(task_id)
                            elif status == "failed":
                                logger.error(f"Task {task_id} failed: {data.get('error')}")
                                if task_id in self.active_tasks:
                                    self.active_tasks.remove(task_id)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        
        except Exception as e:
            logger.error(f"Error in monitor: {e}", exc_info=True)
        finally:
            self.websocket = None
            logger.info("Monitor connection closed")

    async def process_single_image(self, image_path: str):
        """处理单张图片"""
        # 启动监控任务
        self.monitor_task = asyncio.create_task(self.start_monitor())
        logger.info("Started global monitor task")

        try:
            # 1. 上传图片
            logger.info(f"Processing image: {image_path}")
            upload_result = self.upload_image(image_path)
            if not upload_result:
                logger.error(f"Failed to upload image: {image_path}")
                return

            image_url, image_id = upload_result

            # 2. 提交任务
            task_data = await self.submit_task(image_url, image_id)
            if not task_data:
                logger.error(f"Failed to submit task for image: {image_path}")
                return

            # 3. 添加到活动任务
            task_id = task_data["task_id"]
            self.active_tasks.add(task_id)
            logger.info(f"Added task {task_id}")

            # 等待任务完成
            while self.active_tasks:
                logger.info(f"Waiting for task to complete...")
                await asyncio.sleep(1)

        finally:
            # 取消监控任务
            if self.monitor_task:
                self.monitor_task.cancel()
                try:
                    await self.monitor_task
                except asyncio.CancelledError:
                    pass
            logger.info("Task completed")

async def run_test():
    tester = ImageTaskTester()
    
    # 1. 登录
    if not tester.login("test", "test123"):
        logger.error("Login failed")
        return
    
    # 2. 创建API密钥
    if not tester.create_api_key():
        logger.error("Failed to create API key")
        return
    
    # 3. 处理单张图片
    image_path = "./input/test.jpg"  # 替换为你的图片路径
    logger.info(f"Starting to process image: {image_path}")
    await tester.process_single_image(image_path)

def main():
    """主函数"""
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
    finally:
        logger.info("Process completed")

if __name__ == "__main__":
    main() 