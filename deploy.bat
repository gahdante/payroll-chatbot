@echo off
echo 🚀 Deploying Payroll Chatbot to GitHub...
echo.

echo 📋 Step 1: Initializing Git...
git init

echo 📋 Step 2: Adding files...
git add .

echo 📋 Step 3: Making first commit...
git commit -m "Initial commit: Payroll Chatbot API"

echo 📋 Step 4: Connecting to GitHub...
git remote add origin https://github.com/gahdante/payroll-chatbot.git

echo 📋 Step 5: Pushing to GitHub...
git branch -M main
git push -u origin main

echo.
echo ✅ Deploy completed successfully!
echo 🌐 Repository: https://github.com/gahdante/payroll-chatbot
echo.
echo 📝 Next steps:
echo 1. Configure your OpenAI API key in the repository
echo 2. Update README.md with setup instructions
echo 3. Add GitHub Actions for CI/CD (optional)
echo.
pause
