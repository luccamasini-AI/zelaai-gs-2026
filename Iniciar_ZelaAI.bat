@echo off
cd /d "%~dp0"
title ZelaAI - Inicializador Completo (FastAPI + Streamlit)

echo ============================================================================
echo   ZelaAI - Global Solution FIAP 2026/2 (CitizenTech)
echo   Inicializando sistema e abrindo navegador...
echo ============================================================================
echo.

if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
    )
)

echo [1/3] Verificando ambiente Python...
python -c "import fastapi, uvicorn, streamlit, plotly, httpx" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Instalando bibliotecas necessarias. Aguarde...
    python -m pip install -r backend/requirements.txt -r frontend/requirements.txt
)

echo [2/3] Verificando servidor Back-end FastAPI (Porta 8000)...
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    start "ZelaAI - FastAPI (8000)" /min cmd /c "python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
    ping 127.0.0.1 -n 3 >nul
)

echo [3/3] Abrindo ZelaAI no seu navegador (http://localhost:8501)...
netstat -ano | findstr ":8501" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    explorer "http://localhost:8501"
    exit /b 0
)

start "" cmd /c "ping 127.0.0.1 -n 4 >nul & explorer ""http://localhost:8501"""
python -m streamlit run frontend/app.py --server.port 8501 --server.headless true
