from flask import Flask, render_template
from bdshare import get_basic_hist_data

import datetime
import plotly
import json

app = Flask(__name__)
app.debug = True


@app.route('/')
def index():
    # get current date
    # start_date = datetime.date.now() - datetime.timedelta(days=2*365)
    # current_date = datetime.date.today()
    df = get_basic_hist_data('2022-10-01','2024-09-26','ACI')
				
    graphs = [
        dict(
            data=[
                dict(
                    x=df['date'],
					open=df['open'],
					high=df['high'],
					low=df['low'],
					close=df['close'],
                    type='candlestick'
                ),
            ],
            layout=dict(
                title='first graph'
            )
        ),

        dict(
            data=[
                dict(
                    x=df['date'],
                    y=df['close'],
					mode='lines+markers',
                    type='scatter'
                ),
            ],
            layout=dict(
                title='second graph'
            )
        )
    ]
				
	# Add "ids" to each of the graphs to pass up to the client
    # for templating
    ids = ['graph-{}'.format(i+1) for i, _ in enumerate(graphs)]

    # Convert the figures to JSON
    # PlotlyJSONEncoder appropriately converts pandas, datetime, etc
    # objects to their JSON equivalents
    graphJSON = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
	
    return render_template('index.html', ids=ids, graphJSON=graphJSON)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)
