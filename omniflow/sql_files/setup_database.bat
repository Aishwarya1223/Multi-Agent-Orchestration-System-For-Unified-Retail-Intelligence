@echo off
REM =====================================================
REM ShipStream Database Setup Script
REM =====================================================

echo =====================================================
echo ShipStream Database Setup
echo =====================================================
echo.

REM Check if MySQL is available
mysql --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: MySQL is not installed or not in PATH
    echo Please install MySQL and add it to your PATH
    pause
    exit /b 1
)

echo MySQL found. Proceeding with database setup...
echo.

REM Option menu
echo Choose setup option:
echo 1. Complete database setup (recommended)
echo 2. Generate SQL from JSON and import
echo 3. Only generate SQL from JSON
echo 4. Exit
echo.
set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" goto complete_setup
if "%choice%"=="2" goto json_setup
if "%choice%"=="3" goto json_only
if "%choice%"=="4" goto end
goto invalid_choice

:complete_setup
echo.
echo Setting up complete database with dummy data...
mysql -u root -p < shipstream_data_import.sql
if %errorlevel% equ 0 (
    echo.
    echo ✅ Database setup completed successfully!
    echo 📊 Summary:
    echo    - 20 Forward shipments
    echo    - 8 NDR events  
    echo    - 5 Reverse shipments
    echo    - 3 Exchange shipments
    echo    - 5 Warehouses
) else (
    echo ❌ Database setup failed. Please check your MySQL credentials.
)
goto end

:json_setup
echo.
echo Generating SQL from JSON data...
python generate_shipment_sql.py
if %errorlevel% equ 0 (
    echo ✅ SQL generated successfully!
    echo.
    echo Importing generated data...
    mysql -u root -p < shipstream_data_from_json.sql
    if %errorlevel% equ 0 (
        echo ✅ Data import completed successfully!
    ) else (
        echo ❌ Data import failed. Please check your MySQL credentials.
    )
) else (
    echo ❌ SQL generation failed.
)
goto end

:json_only
echo.
echo Generating SQL from JSON data only...
python generate_shipment_sql.py
if %errorlevel% equ 0 (
    echo ✅ SQL generated successfully!
    echo 📁 File: shipstream_data_from_json.sql
    echo You can manually import this file using:
    echo mysql -u root -p < shipstream_data_from_json.sql
) else (
    echo ❌ SQL generation failed.
)
goto end

:invalid_choice
echo.
echo Invalid choice. Please run the script again and choose 1-4.

:end
echo.
echo =====================================================
echo Setup complete!
echo =====================================================
echo.
echo To verify the installation, connect to MySQL and run:
echo USE shipstream;
echo SELECT COUNT(*) as total_shipments FROM shipments;
echo.
pause
