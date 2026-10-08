@echo off
REM Double-cliquez sur ce fichier pour lancer le site Mon Mall.
REM Il doit etre dans le dossier "mall", a cote de run.py.
REM Pour arreter le site : fermez cette fenetre noire.
title Mon Mall
cd /d "%~dp0"

REM 1) Verifie que le fichier est au bon endroit
if not exist "run.py" (
    echo [ERREUR] run.py introuvable dans : %cd%
    echo Deplacez lancer_site.bat dans le dossier "mall", a cote de run.py.
    echo.
    pause
    exit /b
)

REM 2) Cree l'environnement venv s'il n'existe pas
set VENV=%~dp0..\venv
if not exist "%VENV%\Scripts\python.exe" (
    echo Creation de l'environnement Python, patientez...
    python -m venv "%VENV%"
    if errorlevel 1 (
        echo [ERREUR] Python n'est pas installe ou pas trouve.
        pause
        exit /b
    )
)
set PY=%VENV%\Scripts\python.exe

REM 3) Installe Flask s'il manque
"%PY%" -c "import flask" 2>nul
if errorlevel 1 (
    echo Installation de Flask, patientez...
    "%PY%" -m pip install -r requirements.txt
)

REM 4) Ouvre le navigateur 4 secondes apres le demarrage
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:5000"

echo.
echo ================================================
echo  Le site demarre. LAISSEZ CETTE FENETRE OUVERTE.
echo  Adresse : http://127.0.0.1:5000
echo  Admin   : admin@mall.tn / admin123
echo ================================================
echo.
"%PY%" run.py
echo.
echo [Le site s'est arrete. Lisez le message ci-dessus.]
pause
