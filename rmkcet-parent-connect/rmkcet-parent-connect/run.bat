@echo off
echo ============================================
echo   RMKCET Parent Connect - Launcher
echo ============================================
echo.

IF NOT EXIST venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt --quiet

echo Running database migration...
python migrate_db.py

echo.
echo Starting RMKCET Parent Connect...
echo Default login: admin@rmkcet.ac.in / Admin@123
echo.
streamlit run app.py --server.port 8501

pause
