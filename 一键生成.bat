@echo off
:: 设置编码为 UTF-8，防止中文变乱码
chcp 65001 >nul
title 万步网数据生成器
:: 设置字体颜色为亮绿色，看起来比较有科技感
color 0A

:: 自动切换到脚本所在的目录
cd /d "%~dp0"

echo ========================================
echo       万步网人类行为模拟器 - 自动上传
echo ========================================
echo [*] 正在检查环境并启动生成脚本...
echo.

:: 执行 Python 脚本
:: 注意：如果你双击后闪退，请把下面的 python 替换成你的完整路径
:: 例如：E:\Anaconda\envs\workenv\python.exe generator.py
python generator.py

echo.
echo ========================================
echo [*] 任务执行完毕！请检查上方是否有报错。
echo [*] 按键盘任意键即可关闭本窗口...
pause >nul
