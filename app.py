from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from lxml import etree
from io import StringIO
from time import sleep
from utils import simulate_tournament, get_std
app = Flask(__name__)
cors = CORS(app)


def get_request(link):
  r = requests.get(link)
  sleep(0.5)
  return r


def get_rtgs(num):
  r = get_request('https://www.pdga.com/player/' + num + '/details')

  html = r.content.decode("utf-8")
  parser = etree.HTMLParser()

  tree = etree.parse(StringIO(html), parser=parser)
  root = tree.getroot()

  rounds = tree.xpath('.//*[contains(@class, "evaluated included odd") or contains(@class, "evaluated included even")]')
    
  rtgs = []
  for rd in rounds:
    rtgs.append(int(rd.xpath('.//*[contains(@class, "round-rating") or contains(@class, "round-rating double-weighted-round")]')[0].text))

  return rtgs

@app.route("/")
def hello_world ():
  return "Hello World!"

@app.route("/get-divisions", methods=['POST'])
def get_divisions ():

  parser = etree.HTMLParser()

  e_id = request.json.get("t_id")

  r = get_request('https://www.pdga.com/tour/event/' + e_id)

  html = r.content.decode("utf-8")

  tree = etree.parse(StringIO(html), parser=parser)
  root = tree.getroot()

  status = tree.xpath('//td[@class="status"]')
  if (len(status)==0):
    return jsonify({}), 556
  if (status[0].text != "Sanctioned"):
    return jsonify({}), 555


  divs = []

  for d in tree.xpath('//*[@class="division"]'):
    divs.append(d.get('id'))

  return jsonify({'tournament_divisions': divs}), 200


@app.route("/generate-report", methods=['POST'])
def handle_data_request ():

  parser = etree.HTMLParser()

  e_id = request.json.get("t_id")
  num_rounds = request.json.get("rounds")
  div = request.json.get("current_div")

  r = get_request('https://www.pdga.com/tour/event/' + e_id)

  html = r.content.decode("utf-8")

  tree = etree.parse(StringIO(html), parser=parser)
  root = tree.getroot()
  parent = tree.xpath(f'//details[.//*[@id="{div}"]]')[0]
  player_elements = parent.xpath('.//*[contains(@class, "even") or contains(@class, "odd")]')

  players = {}

  for p in player_elements:
    rtg = int(p[2].text)
    num = p[1].text
    name = p[0][0].text
    rtgs = get_rtgs(num)
    std = get_std(rtgs)
    players[num]=(rtg, std, name)

  win_avg, cash_avg, sorted_win_percentage = simulate_tournament(players, num_rounds, 10000)

  win_avg = round(win_avg, 2)

  return jsonify({'sorted_win_percentage': sorted_win_percentage, 'win_avg': win_avg, 'cash_avg': cash_avg}), 200

