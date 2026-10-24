@echo off
setlocal EnableDelayedExpansion

echo ==========================================
echo   NexaFlow - Starting Application
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node 18+
    pause
    exit /b 1
)

echo ✅ Python and Node.js found
echo.

:: Backend setup
echo 📦 Setting up backend...
cd backend

if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing backend dependencies...
pip install -q -r requirements.txt

:: Check if database exists
if not exist "nexaflow.db" (
    echo 🌱 Seeding database ^(first run^)...
    python seed.py
) else (
    echo ✅ Database already exists
)

echo.
echo 🚀 Starting backend server on http://localhost:8000
start "NexaFlow Backend" cmd /c "venv\Scripts\activate.bat && python main.py"

cd ..

:: Frontend setup
echo.
echo 📦 Setting up frontend...
cd frontend

if not exist "node_modules" (
    echo Installing frontend dependencies...
    call npm install
)

echo.
echo 🚀 Starting frontend server on http://localhost:5173
start "NexaFlow Frontend" cmd /c "npm run dev"

cd ..

echo.
echo ==========================================
echo   ✅ NexaFlow is running!
echo ==========================================
echo.
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8000
echo.
echo   Two terminal windows have been opened.
echo   Close them to stop the servers.
echo.
echo   Opening browser in 3 seconds...
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo Press any key to exit this window...
pause >nul
