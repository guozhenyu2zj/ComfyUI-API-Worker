# Supabase Worker

这是一个基于 Python 的 Worker 程序，用于处理 Supabase 数据库中的任务队列。Worker 会定期检查是否有新的任务，并根据任务类型执行相应的处理逻辑。

## 功能特点

- 自动轮询任务队列
- 支持任务状态管理（完成/失败）
- 结果保存和错误处理
- 会话自动刷新
- 完整的日志记录

## 环境要求

- Python 3.7+
- 必要的 Python 包（见下方安装说明）

## 安装

1. 安装依赖包：

```bash
pip install supabase loguru python-dotenv
```

2. 配置环境变量：

复制 `.env.example` 文件为 `.env`，并填写以下配置：

```env
SUPABASE_URL=你的_SUPABASE_URL
SUPABASE_ANON_KEY=你的_SUPABASE_ANON_KEY
WORKER_EMAIL=worker用户邮箱
WORKER_PASSWORD=worker用户密码
```

## 使用方法

1. 确保已正确配置环境变量
2. 运行示例程序：

```bash
python example.py
```

## 核心类：SupabaseWorker

`SupabaseWorker` 类提供以下主要方法：

- `login(email, password)`: 登录并获取 worker 身份
- `get_next_task()`: 获取下一个可用任务
- `save_task_result(task_id, result_data, error_message)`: 保存任务处理结果
- `mark_task_success(task_id, notes)`: 标记任务为成功
- `mark_task_failed(task_id, error_message)`: 标记任务为失败

## 自定义任务处理

在 `example.py` 中的 `process_task` 函数中实现具体的任务处理逻辑：

```python
def process_task(task: Dict[str, Any], worker: SupabaseWorker) -> bool:
    task_id = task['id']
    task_type = task['type_id']
    input_data = task['input_data']
    
    # 在这里实现具体的任务处理逻辑
    ...
```

## 日志

程序运行日志默认保存在：
- 示例程序日志：`example_worker.log`
- Worker 类日志：`worker.log`

## 错误处理

程序包含完整的错误处理机制：
- 任务处理失败会自动记录错误信息
- 网络异常会自动重试
- 会话过期会自动刷新

## 安全退出

程序支持以下方式安全退出：
- Ctrl+C 键盘中断
- SIGTERM 信号 