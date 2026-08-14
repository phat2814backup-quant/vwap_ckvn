@echo off
title Push VWAP CKVN App to GitHub
cd /d "%~dp0"

echo [1/4] Dang kiem tra kho luu tru Git (Git init)...
if not exist .git (
    echo Chua co thu muc .git. Dang khoi tao Git repository...
    git init
    git branch -M main
) else (
    echo Kho luu tru Git da duoc khoi tao.
)

echo.
echo [2/4] Dang kiem tra lien ket GitHub Remote...
git remote | findstr "origin" >nul
if errorlevel 1 (
    echo Chua co lien ket remote 'origin'.
    echo Dang thiet lap remote origin toi: https://github.com/phat2814backup-quant/vwap_ckvn.git
    git remote add origin https://github.com/phat2814backup-quant/vwap_ckvn.git
) else (
    echo Da co lien ket remote 'origin'.
)

echo.
echo [3/4] Dang chuan bi commit du lieu...
git add .
set commit_msg=
set /p commit_msg="Nhap noi dung commit (Nhan Enter de lay mac dinh: 'Update VWAP App'): "
if "%commit_msg%"=="" set commit_msg="Update VWAP App"

git commit -m "%commit_msg%"

echo.
echo [4/4] Dang day ma nguon len GitHub (nhanh main)...
git push -u origin main

if errorlevel 1 (
    echo.
    echo [LOI] Day ma nguon len GitHub that bai. Vui long kiem tra lai ket noi hoac quyen ghi (credential).
) else (
    echo.
    echo [THANH CONG] Da day ma nguon vwap_ckvn len GitHub thanh cong!
)

echo.
pause
