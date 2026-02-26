#!/bin/bash
cd /Users/priya/Desktop/Lalmba_Capstone_Project/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 server.py