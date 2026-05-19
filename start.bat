@echo off
start http://localhost:8502
uv run streamlit run imagegen/app.py --server.port 8502