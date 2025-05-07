from fastapi import FastAPI, Request, BackgroundTasks, Header
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage
from starlette.exceptions import HTTPException
import os
import requests
from bs4 import BeautifulSoup
from pprint import pprint
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

# 環境変数のロード
load_dotenv()

app = FastAPI()

LINE_BOT_API = LineBotApi(os.environ["ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/callback")
async def callback(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature=Header(None),
):
    body = await request.body()

    try:
        background_tasks.add_task(
            handler.handle, body.decode("utf-8"), x_line_signature
        )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    return "ok"

@handler.add(MessageEvent)
def handle_message(event: MessageEvent):
    """
    LINEメッセージイベントを処理する関数
    """
    if isinstance(event.message, TextMessage):
        # テキストメッセージの場合
        text = event.message.text
        
        # 「今日の天気」というメッセージの場合は大阪の天気を返す
        if text == "天気" or text == "今日の天気":
            weather_info = scrape_weather_info("大阪")
            reply_text = f"今日の大阪の天気は{weather_info['weather']}です。最高気温は{weather_info['temperature']['max']}℃、最低気温は{weather_info['temperature']['min']}℃です。"
            LINE_BOT_API.reply_message(event.reply_token, TextMessage(text=reply_text))
        
        # 「今日の[都市名]の天気」というパターンを検出
        elif text.startswith("今日の") and text.endswith("の天気"):
            # 「今日の」と「の天気」を除去して都市名を抽出
            city = text[3:-3]  # 「今日の」と「の天気」を削除
            weather_info = scrape_weather_info(city)
            
            # エラーがあった場合
            if "error" in weather_info:
                reply_text = f"{city}の天気情報を取得できませんでした。"
            else:
                reply_text = f"今日の{city}の天気は{weather_info['weather']}です。最高気温は{weather_info['temperature']['max']}℃、最低気温は{weather_info['temperature']['min']}℃です。"
            
            LINE_BOT_API.reply_message(event.reply_token, TextMessage(text=reply_text))
        
        else:
            # その他のテキストメッセージに対してはそのまま返信
            LINE_BOT_API.reply_message(event.reply_token, TextMessage(text=text))

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

