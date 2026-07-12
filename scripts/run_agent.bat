@echo off
cd /d "C:\Users\Ben\Downloads\Lighttowergroupsite\scripts"
"C:\Users\Ben\AppData\Local\Programs\Python\Python313\python.exe" daily_news_agent.py --selection-mode daily-top-news --articles 30 >> agent_run.log 2>&1
