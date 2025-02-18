import time
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from loguru import logger

class SupabaseWorker:
    def __init__(self, supabase_url: str, supabase_anon_key: str, log_file: str = "worker.log"):
        """
        初始化 Supabase Worker
        
        Args:
            supabase_url: Supabase 项目 URL
            supabase_anon_key: Supabase 匿名密钥
            log_file: 日志文件路径
        """
        if not supabase_url or not supabase_anon_key:
            raise ValueError("Supabase URL 和 anon key 不能为空")
        
        # 配置日志
        logger.add(log_file, rotation="500 MB")
        
        self.supabase: Client = create_client(supabase_url, supabase_anon_key)
        self.worker_id = None
        self.session = None

    def login(self, email: str, password: str) -> bool:
        """
        登录获取 worker 身份
        
        Args:
            email: 用户邮箱
            password: 用户密码
            
        Returns:
            bool: 登录是否成功
        """
        try:
            auth_response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            self.worker_id = auth_response.user.id
            self.session = auth_response.session
            
            # 设置认证令牌
            self.supabase.postgrest.auth(self.session.access_token)
            
            # 验证用户是否是 worker 角色
            user_metadata = auth_response.user.user_metadata
            logger.info(f"用户元数据: {user_metadata}")
            
            if not user_metadata or user_metadata.get('role') != 'worker':
                raise ValueError("该用户不是 worker 角色")
            
            logger.info(f"Worker {self.worker_id} 登录成功")
            return True
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return False

    def refresh_session(self) -> bool:
        """
        刷新会话令牌
        
        Returns:
            bool: 刷新是否成功
        """
        try:
            # 刷新会话
            auth_response = self.supabase.auth.refresh_session()
            if not auth_response:
                return False
            
            # 更新会话和认证令牌
            self.session = auth_response.session
            self.supabase.postgrest.auth(self.session.access_token)
            return True
        except Exception as e:
            logger.error(f"刷新会话失败: {str(e)}")
            return False

    def get_next_task(self, task_type_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        获取下一个可用任务
        
        Args:
            task_type_ids: 可选的任务类型ID列表，如果指定则只获取这些类型的任务
            
        Returns:
            Dict[str, Any] | None: 任务信息或 None（如果没有可用任务）
        """
        try:
            # 确保已登录
            if not self.session:
                raise ValueError("请先登录")
            
            # 刷新会话
            if not self.refresh_session():
                raise ValueError("会话刷新失败")

            params = {}
            if task_type_ids:
                params["p_task_type_ids"] = task_type_ids

            response = self.supabase.postgrest.rpc(
                'get_next_available_task',
                params
            ).execute()
            
            if response.data and len(response.data) > 0:
                task = response.data[0]
                logger.info(f"获取到新任务: {task['id']}")
                return task
            return None
        except Exception as e:
            logger.error(f"获取任务失败: {str(e)}")
            return None

    def save_task_result(self, task_id: str, result_data: Dict[str, Any], error_message: str = None) -> bool:
        """
        保存任务结果
        
        Args:
            task_id: 任务ID
            result_data: 结果数据
            error_message: 错误信息
            
        Returns:
            bool: 保存是否成功
        """
        try:
            self.supabase.table('task_results').insert({
                'task_id': task_id,
                'result_data': result_data,
                'error_message': error_message
            }).execute()
            logger.info(f"任务 {task_id} 结果已保存")
            return True
        except Exception as e:
            logger.error(f"保存任务结果失败: {str(e)}")
            return False

    def mark_task_success(self, task_id: str, notes: str = "任务处理成功") -> bool:
        """
        标记任务为成功
        
        Args:
            task_id: 任务ID
            notes: 状态说明
            
        Returns:
            bool: 更新是否成功
        """
        try:
            self.supabase.table('task_status').insert({
                'task_id': task_id,
                'status': 'completed',
                'changed_by': self.worker_id,
                'notes': notes
            }).execute()
            logger.info(f"任务 {task_id} 已标记为成功")
            return True
        except Exception as e:
            logger.error(f"标记任务成功状态失败: {str(e)}")
            return False

    def mark_task_failed(self, task_id: str, error_message: str) -> bool:
        """
        标记任务为失败
        
        Args:
            task_id: 任务ID
            error_message: 错误信息
            
        Returns:
            bool: 更新是否成功
        """
        try:
            self.supabase.table('task_status').insert({
                'task_id': task_id,
                'status': 'failed',
                'changed_by': self.worker_id,
                'notes': error_message
            }).execute()
            logger.info(f"任务 {task_id} 已标记为失败")
            return True
        except Exception as e:
            logger.error(f"标记任务失败状态失败: {str(e)}")
            return False 