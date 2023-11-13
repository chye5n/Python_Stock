import datetime
from flask import Flask, render_template, request, redirect, url_for
import requests
from urllib.parse import urlencode, unquote
from dotenv import load_dotenv
import os
import xml.etree.ElementTree as ET
import json

import time
import board
import busio
import digitalio

from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306

import subprocess

load_dotenv()
myKey = os.environ.get("myKEY")

app = Flask(__name__)

# Define the Reset Pin
oled_reset = digitalio.DigitalInOut(board.D4)

# Display Parameters
WIDTH = 128
HEIGHT = 64
BORDER = 5

# Display Refresh
LOOPTIME = 1.0

# Use for I2C.
i2c = board.I2C()
oled = adafruit_ssd1306.SSD1306_I2C(WIDTH, HEIGHT, i2c, addr=0x3C, reset=oled_reset)

# Clear display.
oled.fill(0)
oled.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
image = Image.new("1", (oled.width, oled.height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a white background
draw.rectangle((0, 0, oled.width, oled.height), outline=255, fill=255)

font = ImageFont.truetype("PixelOperator.ttf", 16)

date = []
price = []


def getStockInfo(stock_name, date):
    url = "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo"
    queryString = "?" + urlencode(
        {
            "ServiceKey": unquote(myKey),
            "numOfRows": "100",
            "pageNo": "1",
            "basDt": date.strftime("%Y%m%d"),
            "stock_name": stock_name,
        }
    )

    try:
        response = requests.get(url + queryString)
        response.raise_for_status()

        response_text = response.content.decode("utf-8")
        root = ET.fromstring(response_text)
        item_list = root.findall(".//item")

        stocks = []

        for item in item_list:
            st_name = item.find("itmsNm").text
            if stock_name == st_name:
                stock_price = item.find("clpr").text  # 종가
                stock_change = item.find("vs").text  # 전일 대비
                stock_change_rate = item.find("fltRt").text  # 전일대비 등락률
                stock_high_price = item.find("hipr").text  # 하루 중 최고가
                stock_low_price = item.find("lopr").text  # 하루 중 최저가
                stock = {
                    "stock_name": st_name,
                    "stock_price": stock_price,
                    "stock_change": stock_change,
                    "stock_change_rate": stock_change_rate,
                    "stock_high_price": stock_high_price,
                    "stock_low_price": stock_low_price,
                    "stockdate": date,
                }
                stocks.append(stock)
                break

        return stocks
    except (requests.exceptions.RequestException, ET.ParseError) as e:
        print("An error occurred:", e)
        return []


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        stock_name = request.form["stock_name"]
        return redirect(url_for("search_results", stock_name=stock_name))
    else:
        return render_template("index.html")


@app.route("/search_results")
def search_results():
    stock_name = request.args.get("stock_name")
    stock_date = datetime.datetime.now().date() - datetime.timedelta(days=3)
    stock_date2 = datetime.datetime.now().date() - datetime.timedelta(days=3)
    stocks = getStockInfo(stock_name, stock_date)
    stocks2 = getStockInfo(stock_name, stock_date2)
    if stocks:
        date.append(stocks[0]["stockdate"].strftime("%Y%m%d"))
        price.append(str(stocks[0]["stock_price"]))
        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
        draw.text(
            (0, 0),
            date[0] + " : " + price[0],
            font=font,
            fill=255,
        )

        oled.image(image)
        oled.show()

    return render_template(
        "index.html", stocks=stocks, stock_name=stock_name, stocks2=stocks2
    )


@app.route("/prev", methods=["GET"])
def prev():
    stock_name = request.args.get("stock_name")
    stock_date = request.args.get("stock_date")
    stock_date = stock_date.replace("-", "")
    stock_date = datetime.datetime.strptime(stock_date, "%Y%m%d").date()
    prev_date = stock_date - datetime.timedelta(days=1)
    stocks = getStockInfo(stock_name, prev_date)
    stock_date2 = datetime.datetime.now().date() - datetime.timedelta(days=3)
    stocks2 = getStockInfo(stock_name, stock_date2)

    if stocks:
        if len(date) == 4:
            del date[1]
            del price[1]
        date.append(stocks[0]["stockdate"].strftime("%Y%m%d"))
        price.append(str(stocks[0]["stock_price"]))
        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
        if len(date) >= 1:
            draw.text(
                (0, 0),
                date[0] + " : " + price[0],
                font=font,
                fill=255,
            )
        if len(date) >= 2:
            draw.text(
                (0, 16),
                date[1] + " : " + price[1],
                font=font,
                fill=255,
            )
        if len(date) >= 3:
            draw.text(
                (0, 32),
                date[2] + " : " + price[2],
                font=font,
                fill=255,
            )
        if len(date) >= 4:
            draw.text(
                (0, 48),
                date[3] + " : " + price[3],
                font=font,
                fill=255,
            )

        oled.image(image)
        oled.show()

    return render_template(
        "index.html", stocks=stocks, stock_name=stock_name, stocks2=stocks2
    )


@app.route("/next", methods=["GET"])
def next():
    stock_name = request.args.get("stock_name")
    stock_date = request.args.get("stock_date")
    stock_date = stock_date.replace("-", "")
    stock_date = datetime.datetime.strptime(stock_date, "%Y%m%d").date()
    next_date = stock_date + datetime.timedelta(days=1)
    stocks = getStockInfo(stock_name, next_date)
    stock_date2 = datetime.datetime.now().date() - datetime.timedelta(days=3)
    stocks2 = getStockInfo(stock_name, stock_date2)
    return render_template(
        "index.html", stocks=stocks, stock_name=stock_name, stocks2=stocks2
    )


def format_date(value, format="%Y-%m-%d"):
    return value.strftime(format)


# app.jinja_env.filters["date"] = format_date

if __name__ == "__main__":
    app.run(host="0.0.0.0")
