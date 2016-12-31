from flask import Flask
from flask import request

app = Flask(__name__)

@app.route("/sinvertwebmonitor/InverterService/InverterService.asmx/CollectInverterData", methods=['POST'])
def dataCollector():
	data = request.form['xmlData']
	print(data)
	# parseData. Take a look at ElementTree

if __name__ == "__main__":
	app.run(host=192.168.0.212, port=80)