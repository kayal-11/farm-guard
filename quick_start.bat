@echo off
REM FarmGuard Quick Start Script for Windows

echo ==========================================
echo FarmGuard Setup Script
echo ==========================================
echo.

REM Check Python installation
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is installed
    python --version
) else (
    echo [ERROR] Python is not installed. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check PostgreSQL installation
echo.
echo Checking PostgreSQL installation...
psql --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] PostgreSQL is installed
    psql --version
) else (
    echo [ERROR] PostgreSQL is not installed. Please install PostgreSQL 12+
    pause
    exit /b 1
)

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv
if %errorlevel% equ 0 (
    echo [OK] Virtual environment created
) else (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

REM Activate virtual environment
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt
if %errorlevel% equ 0 (
    echo [OK] Dependencies installed
) else (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo.
    echo Creating .env file...
    (
        echo SECRET_KEY=change-this-secret-key-in-production
        echo DATABASE_URL=postgresql://farmguard_user:password@localhost:5432/farmguard
        echo FLASK_ENV=development
        echo FLASK_DEBUG=True
    ) > .env
    echo [OK] .env file created
    echo [WARNING] Please update the DATABASE_URL in .env with your PostgreSQL credentials
)

REM Create directory structure
echo.
echo Creating directory structure...
if not exist templates mkdir templates
if not exist static mkdir static
echo [OK] Directories created

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Update .env file with your PostgreSQL credentials
echo 2. Move HTML files to templates\ folder
echo 3. Move styles.css to static\ folder
echo 4. Create PostgreSQL database using pgAdmin or command line:
echo    CREATE DATABASE farmguard;
echo    CREATE USER farmguard_user WITH PASSWORD 'your_password';
echo    GRANT ALL PRIVILEGES ON DATABASE farmguard TO farmguard_user;
echo 5. Run the application:
echo    python app.py
echo.
echo Access the application at: http://localhost:5000
echo.
echo Demo credentials:
echo   Farmer: FARM001 / password123
echo   Vet: VET001 / password123
echo   Authority: AUTH001 / password123
echo.
pause