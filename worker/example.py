import os
import time
import signal
import sys
from typing import Dict, Any
from dotenv import load_dotenv
from supabase_worker import SupabaseWorker

def process_task(task: Dict[str, Any], worker: SupabaseWorker) -> bool:
    """
    处理单个任务
    
    Args:
        task: 任务信息
        worker: SupabaseWorker 实例
        
    Returns:
        bool: 处理是否成功
    """
    task_id = task['id']
    task_type = task['type_id']
    input_data = task['input_data']

    try:
        # TODO: 根据不同的任务类型实现具体的处理逻辑
        # 这里只是一个示例
        result_data = {
            'processed_at': str(time.time()),
            'input_data': input_data,
            'output': f"已处理任务类型 {task_type} 的输入数据"
        }
        
        # 保存结果
        if not worker.save_task_result(task_id, result_data):
            return False
            
        # 标记任务成功
        if not worker.mark_task_success(task_id, "任务处理成功"):
            return False
            
        return True
        
    except Exception as e:
        error_msg = str(e)
        print(f"处理任务 {task_id} 失败: {error_msg}")
        # 保存错误结果
        worker.save_task_result(task_id, {}, error_msg)
        # 标记任务失败
        worker.mark_task_failed(task_id, error_msg)
        return False

def main_loop(worker: SupabaseWorker, interval: int = 5):
    """
    主工作循环
    
    Args:
        worker: SupabaseWorker 实例
        interval: 轮询间隔（秒）
    """
    print("开始工作循环")
    task_type_ids_str = os.getenv("TASK_TYPE_IDS")  # 获取任务类型ID列表
    task_type_ids = None
    if task_type_ids_str:
        task_type_ids = [id.strip() for id in task_type_ids_str.split(',') if id.strip()]
        print(f"将只处理任务类型: {task_type_ids}")
    
    def force_exit(signum, frame):
        """强制退出程序"""
        print("\n正在停止工作进程...")
        sys.exit(0)
    
    # 注册信号处理
    signal.signal(signal.SIGINT, force_exit)
    signal.signal(signal.SIGTERM, force_exit)
    
    while True:
        try:
            # 获取新任务，传入任务类型ID列表
            task = worker.get_next_task(task_type_ids)
            if task:
                print(f"开始处理任务: {task['id']}")
                process_task(task, worker)
            else:
                print("没有可用的任务，等待中...")
                time.sleep(interval)
                    
        except Exception as e:
            print(f"工作循环发生错误: {str(e)}")
            time.sleep(interval)

if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()
    
    # 获取配置
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
    worker_email = os.getenv("WORKER_EMAIL")
    worker_password = os.getenv("WORKER_PASSWORD")
    task_type_ids_str = os.getenv("TASK_TYPE_IDS")  # 新增：从环境变量加载任务类型ID列表
    
    if not all([supabase_url, supabase_anon_key, worker_email, worker_password]):
        print("请确保所有必需的环境变量都已设置")
        sys.exit(1)
    
    try:
        # 初始化 worker
        worker = SupabaseWorker(
            supabase_url=supabase_url,
            supabase_anon_key=supabase_anon_key,
            log_file="example_worker.log"
        )
        
        # 登录
        if not worker.login(worker_email, worker_password):
            print("登录失败")
            sys.exit(1)
            
        # 启动主循环，传入任务类型ID列表
        main_loop(worker)
        
    except KeyboardInterrupt:
        print("\n收到键盘中断信号")
    except Exception as e:
        print(f"发生错误: {str(e)}")
    finally:
        print("工作进程已停止")
        sys.exit(0) 