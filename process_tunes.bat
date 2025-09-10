@echo off
setlocal enabledelayedexpansion

REM ===================================================================
REM Auto Get Tunes - Main Processing Script
REM 
REM This Windows batch script orchestrates the complete music download
REM process by running both YouTube search and download/conversion phases.
REM 
REM Usage: process_tunes.bat <input_file.txt> <download_directory>
REM 
REM Author: Claude Sonnet 3.5 (Anthropic) under supervision of Guillaume Blain
REM ===================================================================

REM Parameter validation
if "%~1"=="" (
    echo [ERROR] Usage: %0 ^<search_file.txt^> ^<download_folder^>
    echo Example: %0 "my_project.txt" "F:\Music\MyProject"
    pause
    exit /b 1
)

if "%~2"=="" (
    echo [ERROR] Usage: %0 ^<search_file.txt^> ^<download_folder^>
    echo Example: %0 "my_project.txt" "F:\Music\MyProject"
    pause
    exit /b 1
)

REM Set variables for file paths and directories
set "SEARCH_FILE=%~1"
set "DOWNLOAD_PATH=%~2"
set "SCRIPT_DIR=%~dp0"
set "CODE_DIR=%SCRIPT_DIR%code\"

echo ===============================
echo AUTOMATIC TUNES PROCESSING
echo ===============================
echo Search file: %SEARCH_FILE%
echo Download directory: %DOWNLOAD_PATH%
echo Script directory: %SCRIPT_DIR%
echo Code directory: %CODE_DIR%
echo.

REM Verify that the search file exists
if not exist "%SEARCH_FILE%" (
    echo [ERROR] The search file '%SEARCH_FILE%' does not exist.
    pause
    exit /b 1
)

REM Create download directory if it doesn't exist
if not exist "%DOWNLOAD_PATH%" (
    echo [INFO] Creating download directory: %DOWNLOAD_PATH%
    mkdir "%DOWNLOAD_PATH%"
)

echo ===============================
echo STEP 1: YOUTUBE SEARCH AND DATABASE UPDATE
echo ===============================

REM Execute YouTube search script with database update
python "%CODE_DIR%update_db_from_txt.py" "%SEARCH_FILE%"

if !errorlevel! neq 0 (
    echo [ERROR] YouTube search failed.
    pause
    exit /b 1
)

echo.
echo ===============================
echo STEP 2: DOWNLOAD AND CONVERSION
echo ===============================

REM Execute conversion script with download directory
python "%CODE_DIR%conversion.py" "%DOWNLOAD_PATH%"

set "CONVERSION_RESULT=!errorlevel!"

if !CONVERSION_RESULT! neq 0 (
    echo.
    echo [WARNING] The conversion script ended with errors.
    echo However, some downloads may have succeeded.
    echo Check the folder: %DOWNLOAD_PATH%
) else (
    echo.
    echo [SUCCESS] Processing completed successfully!
    echo Files have been downloaded to: %DOWNLOAD_PATH%
)

echo.
echo ===============================
echo FINAL SUMMARY
echo ===============================
echo - Database updated: %CODE_DIR%tunes_database.json
echo - Download directory: %DOWNLOAD_PATH%
echo - You can now edit the database to add project information.
echo.

pause
