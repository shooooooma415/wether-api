from fastapi import FastAPI
from typing import Optional
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}





def scrape_weather_info(city: str = "東京"):
    """
    天気情報をスクレイピングする関数
    
    Args:
        city (str): 都市名 (デフォルトは東京)
    
    Returns:
        dict: 天気情報を含む辞書
    """
    try:
        # 都市名に基づいてURLを生成（今回は東京をデフォルトとする）
        url = f"https://tenki.jp/forecast/3/16/4410/13113/"  # 東京・千代田区の天気予報URL
        
        # リクエストを送信
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # エラーチェック
        
        # BeautifulSoupでHTMLを解析
        soup = BeautifulSoup(response.content, "html.parser")
        
        # 天気情報の抽出
        today_forecast = soup.select_one(".forecast-days-wrap .today-weather")
        if today_forecast:
            weather_text = today_forecast.select_one(".weather-telop").text.strip() if today_forecast.select_one(".weather-telop") else "不明"
            
            # 気温の取得
            temp_high = today_forecast.select_one(".high-temp .value").text.strip() if today_forecast.select_one(".high-temp .value") else "不明"
            temp_low = today_forecast.select_one(".low-temp .value").text.strip() if today_forecast.select_one(".low-temp .value") else "不明"
            
            # 降水確率の取得
            precip_prob = []
            precip_rows = today_forecast.select(".precip-table tbody tr")
            if precip_rows:
                for row in precip_rows[1:2]:  # 2行目（降水確率）を取得
                    for cell in row.select("td"):
                        precip_prob.append(cell.text.strip())
            
            # 結果の辞書を作成
            weather_info = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "city": city,
                "weather": weather_text,
                "temperature": {
                    "max": temp_high,
                    "min": temp_low
                },
                "precipitation_probability": precip_prob if precip_prob else ["--", "--", "--", "--"],
                "source": "tenki.jp"
            }
            return weather_info
        else:
            return {"error": "天気情報を取得できませんでした"}
    except Exception as e:
        return {"error": f"スクレイピングエラー: {str(e)}"}


@app.get("/wether/")
def read_wether(date: Optional[str] = None, city: Optional[str] = None):
    """
    日付と都市名をクエリパラメータとして受け取り、天気情報を返すエンドポイント
    
    例: /wether?date=2025-05-07&city=Tokyo
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    if city is None:
        city = "東京"
    
    # 実際に天気情報をスクレイピングして取得
    weather_info = scrape_weather_info(city)
    
    # 日付情報を更新
    weather_info["date"] = date
    
    return weather_info