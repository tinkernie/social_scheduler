import requests
import json
import time

def get_ohlc_data(symbol="BTCIRT", resolution="D", countback=200):
    """
    دریافت داده OHLCV از API نوبیتکس
    countback: تعداد کندل‌های مورد نظر (برای محاسبه EMA200 نیاز به حداقل 200 کندل دارید)
    """
    # محاسبه زمان جاری به صورت timestamp (seconds)
    to_time = int(time.time())
    
    # ساخت URL درخواست
    url = f"https://apiv2.nobitex.ir/market/udf/history"
    params = {
        "symbol": symbol,
        "resolution": resolution,
        "from": 1,  # مقداری پایین برای دریافت تمام داده‌های موجود
        "to": to_time,
        "countback": countback
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("s") == "ok":
            # تبدیل به فرمت قابل استفاده
            ohlc = {
                "timestamps": data.get("t", []),
                "open": [float(x) for x in data.get("o", [])],
                "high": [float(x) for x in data.get("h", [])],
                "low": [float(x) for x in data.get("l", [])],
                "close": [float(x) for x in data.get("c", [])],
                "volume": [float(x) for x in data.get("v", [])]
            }
            return ohlc
        else:
            print(f"خطا در دریافت داده: {data.get('s')}")
            return None
    except Exception as e:
        print(f"خطا در ارتباط با API: {e}")
        return None

# مثال استفاده
data = get_ohlc_data(countback=250)  # دریافت 250 کندل اخیر
if data:
    print(f"تعداد کندل‌های دریافت شده: {len(data['close'])}")
    print(f"آخرین قیمت بسته شدن: {data['close'][-1]:.2f} تومان")