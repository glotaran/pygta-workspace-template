@echo off
setlocal

pushd "%~dp0"

where uv >nul 2>&1
if errorlevel 1 (
    echo uv is required on PATH. See https://docs.astral.sh/uv for installation instructions.
    echo.
    pause
    popd
    exit /b 1
)

uv run --script "%~dp0bootstrap.py" %*
set "BOOTSTRAP_EXIT_CODE=%errorlevel%"

if not "%BOOTSTRAP_EXIT_CODE%"=="0" (
    echo.
    echo bootstrap.py failed with exit code %BOOTSTRAP_EXIT_CODE%.
    pause
)

popd
exit /b %BOOTSTRAP_EXIT_CODE%
