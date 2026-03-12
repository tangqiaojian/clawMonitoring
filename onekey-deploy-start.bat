@echo off
setlocal
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File ".\scripts\onekey-deploy-start.ps1"
