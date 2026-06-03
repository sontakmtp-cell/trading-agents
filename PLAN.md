# Kế Hoạch: Thêm Binance Spot Mode Cho TradingAgents

## Tóm Tắt
- Giữ kiến trúc hiện tại: CLI → `TradingAgentsGraph` → LangGraph agents → tool wrappers → `dataflows.interface.route_to_vendor`.
- Thêm vendor `binance` cho dữ liệu thị trường crypto Spot, mặc định v1 dùng Binance Spot USDT pairs như `BTCUSDT`, `ETHUSDT`.
- Không dùng Yahoo Finance trong luồng Binance. Vì app Python không gọi trực tiếp được plugin Codex, phần implement sẽ gọi Binance public REST API tương ứng với các endpoint plugin đã xác nhận.

## Thay Đổi Chính
- Thêm module dataflow Binance, ví dụ `tradingagents/dataflows/binance.py`, dùng `requests` sẵn có để lấy:
  - exchange info để validate symbol và status `TRADING`;
  - daily kline để tạo OHLCV `Date/Open/High/Low/Close/Volume`;
  - 24h ticker/order book metadata nếu cần đưa vào market report.
- Đăng ký `binance` trong `VENDOR_LIST` và `VENDOR_METHODS` cho:
  - `get_stock_data`;
  - `get_indicators`, bằng cách tái dùng `stockstats` trên OHLCV Binance;
  - `get_verified_market_snapshot`, thông qua `load_ohlcv` hoặc một loader vendor-aware.
- Thêm config:
  - `data_vendors.core_stock_apis = "binance"` cho Binance mode;
  - `data_vendors.technical_indicators = "binance"`;
  - không route `fundamental_data` sang Binance vì Binance không có báo cáo tài chính cổ phiếu.
- Cập nhật CLI:
  - ví dụ ticker đổi từ `BTC-USD` sang `BTCUSDT`;
  - crypto mode mặc định bỏ Fundamentals Analyst như hiện tại;
  - nếu chọn Binance mode thì chỉ chạy `market`, `social/news` nếu không còn phụ thuộc Yahoo, hoặc bỏ news/social ở v1 để bảo đảm “không lấy Yahoo”.
- Cập nhật identity/context:
  - không gọi `yfinance.Ticker(...).info` khi `asset_type="crypto"` hoặc khi vendor là `binance`;
  - context sẽ ghi rõ đây là crypto Spot pair trên Binance, không phải công ty.
- Cập nhật reflection/benchmark:
  - không dùng Yahoo để tính pending return cho Binance symbols;
  - dùng Binance OHLCV để tính raw return;
  - alpha benchmark v1 mặc định bỏ qua hoặc dùng `BTCUSDT` làm benchmark khi symbol không phải BTC.

## Test Plan
- Unit test Binance symbol normalization:
  - `btc-usdt`, `BTC/USDT`, `BTCUSDT` đều ra `BTCUSDT`;
  - symbol không tồn tại trả sentinel `NO_DATA_AVAILABLE`, không để agent bịa dữ liệu.
- Unit test Binance kline parser:
  - mảng kline Binance chuyển đúng thành DataFrame/CSV có `Date, Open, High, Low, Close, Volume`;
  - không dùng dữ liệu sau `analysis_date`.
- Unit test routing:
  - `route_to_vendor("get_stock_data", ...)` gọi Binance khi config là `binance`;
  - fallback không làm rơi về Yahoo trong Binance mode.
- Unit test crypto CLI:
  - `BTCUSDT` được detect là crypto;
  - Fundamentals Analyst bị loại khỏi selection;
  - prompt/examples hiển thị Binance symbol.
- Snapshot test:
  - `build_verified_market_snapshot("BTCUSDT", date)` dùng OHLCV Binance và vẫn tính RSI/MACD/Bollinger như luồng cũ.
- Smoke test:
  - chạy một phân tích nhẹ với analyst `market` cho `BTCUSDT`, mock Binance REST để không phụ thuộc mạng thật.

## Giả Định Đã Khóa
- V1 làm “Thêm mode Binance”, không tách app mới và không xóa Yahoo/Alpha Vantage khỏi repo.
- V1 chỉ tập trung Binance Spot USDT.
- Không trading thật, không API key Binance, không đặt lệnh; chỉ đọc public market data.
- News/social/fundamentals không được dùng Yahoo trong Binance mode; nếu chưa có nguồn Binance tương đương thì v1 bỏ các analyst đó thay vì lấy dữ liệu sai nguồn.
