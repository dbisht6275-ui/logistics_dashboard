@echo off
cd /d D:\SUGAMREPORTS_STREAMLIT
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
pause