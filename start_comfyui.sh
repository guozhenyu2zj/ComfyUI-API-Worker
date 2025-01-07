#!/bin/bash

# 确保screen目录存在并有正确权限
mkdir -p /var/run/screen/S-$USER
chmod 700 /var/run/screen/S-$USER

# 清理可能存在的死亡会话
screen -wipe > /dev/null 2>&1

# 启动Clash的函数
start_clash() {
    if ! screen -list | grep -q "Clash"; then
        echo "创建新的Clash screen会话..."
        screen -dm -S Clash bash -c '
            cd ~/clash
            echo "启动Clash..."
            ./clash -f Nirvana_0515.yaml
        '
        # 等待确保会话创建成功
        sleep 2
        if screen -list | grep -q "Clash"; then
            echo "Clash已在后台启动"
        else
            echo "Clash启动失败"
            return 1
        fi
    fi
}

# 启动ComfyUI的函数
start_comfyui() {
    if ! screen -list | grep -q "ComfyUI"; then
        echo "创建新的ComfyUI screen会话..."
        screen -dm -S ComfyUI bash -c '
            source ~/miniconda3/etc/profile.d/conda.sh
            while true; do
                echo "启动ComfyUI..."
                conda activate ComfyUI
                cd /home/swgz/work/ComfyUI
                if python main.py --listen 0.0.0.0 --disable-smart-memory; then
                    echo "ComfyUI正常退出"
                else
                    echo "ComfyUI异常退出，错误代码: $?"
                fi
                echo "ComfyUI已停止，5秒后重启..."
                sleep 5
            done
        '
        # 等待确保会话创建成功
        sleep 2
        if screen -list | grep -q "ComfyUI"; then
            echo "ComfyUI已在后台启动"
        else
            echo "ComfyUI启动失败"
            return 1
        fi
    fi
}

# 启动服务
start_clash || exit 1
start_comfyui || exit 1

# 保持脚本运行并只监控ComfyUI服务
while true; do
    if ! screen -list | grep -q "ComfyUI"; then
        echo "ComfyUI会话丢失，重新启动..."
        start_comfyui || exit 1
    fi
    sleep 10
done  