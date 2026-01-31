@echo off
setlocal
echo 🚀 Alicia 正在为你启动 Image_PixSwap...

:: 读取配置文件 config.ini
set "CONFIG_FILE=%~dp0config.ini"
set "PYTHON_EXE="

if exist "%CONFIG_FILE%" (
    for /f "tokens=1* delims==" %%A in ('type "%CONFIG_FILE%" ^| findstr /b /i "python_path="') do set "PYTHON_EXE=%%B"
)

:: 检查是否成功获取 PYTHON_EXE
if not defined PYTHON_EXE (
    echo [错误] 未在 config.ini 中找到 python_path，或配置文件不存在。
    echo 请确保 %CONFIG_FILE% 存在且包含 python_path=... 设置。
    pause
    exit /b
)

:: 检查 Python 解释器是否存在 (如果是 python 命令则跳过路径检查)
if /i not "%PYTHON_EXE%"=="python" (
    if not exist "%PYTHON_EXE%" (
        echo [错误] 找不到指定的 Python 路径: "%PYTHON_EXE%"
        pause
        exit /b
    )
)

:: 运行程序，%* 确保你依然可以把文件夹直接拖到这个 .bat 图标上进行处理
"%PYTHON_EXE%" "image_converter.py" %*

if %errorlevel% neq 0 (
    echo 发生错误，可能是环境配置问题。
    pause
)