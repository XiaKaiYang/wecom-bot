@echo off
chcp 65001 >nul
title 企业微信 LongCat AI 自动化服务
cd /d "%~dp0"

echo =======================================================
echo          正在启动 企业微信 LongCat AI 自动化机器人...
echo =======================================================
echo.

python bot.py

echo.
echo 进程已结束。
pause
