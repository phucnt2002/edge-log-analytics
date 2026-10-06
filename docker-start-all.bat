@echo off
echo ====================================================================
echo   KHOI DONG TOAN BO HE THONG EDGE & CLOUD BANG DOCKER COMPOSE
echo ====================================================================
docker compose up --build -d
echo.
echo [OK] Da khoi dong thanh cong tat ca cac dich vu!
echo.
echo   * Edge Gateway 01 (Dashboard) : http://localhost:8001
echo   * Edge Gateway 02 (Dashboard) : http://localhost:8002
echo   * Prometheus Central Scraper  : http://localhost:9090
echo   * Grafana Fleet Dashboard     : http://localhost:3000 (User/Pass: admin / admin)
echo   * Cloud Parquet Receiver      : http://localhost:5000
echo.
echo Xem log truc tiep : docker compose logs -f
echo Dung toan bo he   : docker compose down
echo ====================================================================
