@echo off
cd /d "e:\New folder\smart-farm"
echo ==================================================
echo   Pushing SmartFarm fixes to GitHub and Railway
echo ==================================================
git push origin main
echo.
echo ==================================================
echo   Push complete! Railway is deploying the fixes.
echo ==================================================
pause
