@echo off
cd /d "C:\Users\Ben\Downloads\Lighttowergroupsite\scripts"
"C:\Users\Ben\AppData\Local\Programs\Python\Python313\python.exe" daily_news_agent.py --selection-mode bucketed-volume --no-limit >> agent_run.log 2>&1
