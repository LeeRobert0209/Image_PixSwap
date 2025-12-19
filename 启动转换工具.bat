@echo off
cd /d "%~dp0"

:: 检查是否安装了依赖
pip install --upgrade -r requirements.txt >nul 2>&1

:: 运行主程序，并传递所有参数（支持拖拽文件夹）
python "image_converter.py" %*

if %errorlevel% neq 0 (
    echo 发生错误，请检查 Python 是否安装或环境变量配置。
    pause
)
