@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ===============================
echo   ETF Tool MVP - 一键启动脚本
echo ===============================
echo.

REM 1. 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到 Python
    echo 请先安装 Python 3.8+：https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python 版本：%PYTHON_VERSION%

REM 2. 检查/创建虚拟环境
if not exist "venv" (
    echo 📦 创建虚拟环境...
    python -m venv venv
)

REM 3. 激活虚拟环境
echo 🔧 激活虚拟环境...
call venv\Scripts\activate.bat

REM 4. 安装/更新依赖
echo 📥 安装依赖（Flask）...
pip install -q flask

REM 5. 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  警告：未找到 Node.js，WeStock API 可能无法工作
    echo    如需使用 WeStock 数据，请安装 Node.js：https://nodejs.org/
) else (
    for /f %%i in ('node --version') do set NODE_VERSION=%%i
    echo ✅ Node.js 版本：%NODE_VERSION%
)

echo.
echo 🚀 启动 Flask 服务器...
echo    访问地址：<ADDRESS_REMOVED>
echo    按 Ctrl+C 停止服务器
echo.

REM 自动打开浏览器（Windows）
start http://localhost:5000/tools/westock-compare

REM 启动服务器
python app.py
