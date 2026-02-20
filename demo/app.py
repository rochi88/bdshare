from flask import Flask, render_template, request, jsonify
from bdshare import get_basic_historical_data, get_current_trade_data
import plotly
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

app = Flask(__name__)
app.debug = True

# Predefined list of popular stocks (you can expand this)
POPULAR_STOCKS = {
    'ACI': 'ACI Limited',
    'GP': 'Grameenphone',
    'SQURPHARMA': 'Square Pharmaceuticals',
    'BEXIMCO': 'Beximco',
    'RENATA': 'Renata Limited',
    'BRACBANK': 'BRAC Bank',
    'EBL': 'Eastern Bank',
    'ISLAMIBANK': 'Islami Bank',
    'NBL': 'National Bank',
    'UCB': 'United Commercial Bank',
    'ORIONPHARM': 'Orion Pharma',
    'LANKABANGLA': 'LankaBangla Finance',
    'IDLC': 'IDLC Finance',
    'SAIFPOWER': 'Saif Powertec',
    'PDL': 'Prime Bank'
}

def get_available_tickers():
    """Get available tickers from current trade data"""
    try:
        df = get_current_trade_data()
        if not df.empty and 'trading_code' in df.columns:
            return sorted(df['trading_code'].unique().tolist())
    except:
        pass
    return list(POPULAR_STOCKS.keys())

def convert_to_native_types(obj):
    """
    Recursively convert numpy/pandas data types to Python native types
    """
    if pd.isna(obj):
        return None
    elif isinstance(obj, (np.integer, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return [convert_to_native_types(x) for x in obj]
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, pd.Series):
        return [convert_to_native_types(x) for x in obj.tolist()]
    elif isinstance(obj, dict):
        return {key: convert_to_native_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_native_types(x) for x in obj]
    else:
        return obj

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder for numpy and pandas data types"""
    def default(self, obj):
        return convert_to_native_types(obj)

def prepare_dataframe_for_json(df):
    """Convert all columns in DataFrame to native Python types"""
    if df.empty:
        return df
    
    # Create a copy to avoid modifying the original
    df_clean = df.copy()
    
    # Convert each column to native types
    for col in df_clean.columns:
        # Handle numeric columns
        if df_clean[col].dtype in [np.int64, np.int32]:
            # Convert to Python int, handling NaN values
            df_clean[col] = df_clean[col].apply(lambda x: int(x) if pd.notna(x) else None)
        elif df_clean[col].dtype in [np.float64, np.float32]:
            # Convert to Python float, handling NaN values
            df_clean[col] = df_clean[col].apply(lambda x: float(x) if pd.notna(x) else None)
        elif pd.api.types.is_datetime64_any_dtype(df_clean[col]):
            # Convert datetime to string
            df_clean[col] = df_clean[col].apply(lambda x: x.isoformat() if pd.notna(x) else None)
        elif df_clean[col].dtype == object:
            # Handle object columns (mixed types)
            df_clean[col] = df_clean[col].apply(lambda x: convert_to_native_types(x))
    
    return df_clean

def safe_dataframe_conversion(df):
    """
    Safe conversion of DataFrame to native Python types without ambiguous boolean comparisons
    """
    if df.empty:
        return {}
    
    data_dict = {}
    for col in df.columns:
        # Convert each column to list first, then clean individual values
        col_data = df[col].tolist()
        cleaned_data = []
        for item in col_data:
            if pd.isna(item):
                cleaned_data.append(None)
            elif isinstance(item, (np.integer, np.int32, np.int64)):
                cleaned_data.append(int(item))
            elif isinstance(item, (np.floating, np.float32, np.float64)):
                cleaned_data.append(float(item))
            elif isinstance(item, pd.Timestamp):
                cleaned_data.append(item.isoformat())
            else:
                cleaned_data.append(item)
        data_dict[col] = cleaned_data
    
    return data_dict

@app.route('/')
def index():
    tickers = get_available_tickers()
    
    # Default values
    default_ticker = 'ACI'
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    return render_template('index.html', 
                         tickers=tickers,
                         default_ticker=default_ticker,
                         start_date=start_date,
                         end_date=end_date,
                         popular_stocks=POPULAR_STOCKS)

@app.route('/get_stock_data')
def get_stock_data():
    """API endpoint to get stock data"""
    try:
        # Get parameters from request
        ticker = request.args.get('ticker', 'ACI')
        start_date = request.args.get('start_date', '2024-10-01')
        end_date = request.args.get('end_date', '2025-09-26')
        chart_type = request.args.get('chart_type', 'candlestick')
        
        print(f"Fetching data for {ticker} from {start_date} to {end_date}")
        
        # Get stock data
        df = get_basic_historical_data(start_date, end_date, ticker)
        
        if df.empty:
            return jsonify({'error': 'No data found for the selected parameters'})
        
        print(f"Retrieved {len(df)} records")
        print(f"Columns: {df.columns.tolist()}")
        
        # Convert date column to datetime if it's not already
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
        
        # Use safe conversion method
        data_dict = safe_dataframe_conversion(df)
        
        # Create graphs based on chart type
        if chart_type == 'candlestick':
            graphs = [
                {
                    'data': [
                        {
                            'x': data_dict['date'],
                            'open': data_dict['open'],
                            'high': data_dict['high'],
                            'low': data_dict['low'],
                            'close': data_dict['close'],
                            'type': 'candlestick',
                            'name': ticker,
                            'increasing_line_color': '#2E8B57',
                            'decreasing_line_color': '#DC143C'
                        },
                    ],
                    'layout': {
                        'title': f'{ticker} - Candlestick Chart',
                        'xaxis': {'title': 'Date', 'type': 'date'},
                        'yaxis': {'title': 'Price (BDT)'},
                        'template': 'plotly_white',
                        'height': 500
                    }
                }
            ]
        elif chart_type == 'line':
            graphs = [
                {
                    'data': [
                        {
                            'x': data_dict['date'],
                            'y': data_dict['close'],
                            'mode': 'lines',
                            'type': 'scatter',
                            'name': 'Close Price',
                            'line': {'color': '#1f77b4', 'width': 2}
                        },
                    ],
                    'layout': {
                        'title': f'{ticker} - Closing Price',
                        'xaxis': {'title': 'Date', 'type': 'date'},
                        'yaxis': {'title': 'Price (BDT)'},
                        'template': 'plotly_white',
                        'height': 500
                    }
                }
            ]
        elif chart_type == 'ohlc':
            graphs = [
                {
                    'data': [
                        {
                            'x': data_dict['date'],
                            'open': data_dict['open'],
                            'high': data_dict['high'],
                            'low': data_dict['low'],
                            'close': data_dict['close'],
                            'type': 'ohlc',
                            'name': ticker,
                            'increasing_line_color': '#2E8B57',
                            'decreasing_line_color': '#DC143C'
                        },
                    ],
                    'layout': {
                        'title': f'{ticker} - OHLC Chart',
                        'xaxis': {'title': 'Date', 'type': 'date'},
                        'yaxis': {'title': 'Price (BDT)'},
                        'template': 'plotly_white',
                        'height': 500
                    }
                }
            ]
        else:
            # Multiple charts view
            volume_data = data_dict.get('volume', [])
            graphs = [
                {
                    'data': [
                        {
                            'x': data_dict['date'],
                            'open': data_dict['open'],
                            'high': data_dict['high'],
                            'low': data_dict['low'],
                            'close': data_dict['close'],
                            'type': 'candlestick',
                            'name': ticker,
                            'increasing_line_color': '#2E8B57',
                            'decreasing_line_color': '#DC143C'
                        },
                    ],
                    'layout': {
                        'title': f'{ticker} - Candlestick Chart',
                        'xaxis': {'title': 'Date', 'type': 'date'},
                        'yaxis': {'title': 'Price (BDT)'},
                        'template': 'plotly_white',
                        'height': 400
                    }
                },
                {
                    'data': [
                        {
                            'x': data_dict['date'],
                            'y': volume_data,
                            'type': 'bar',
                            'name': 'Volume',
                            'marker': {'color': 'rgba(100, 100, 100, 0.5)'}
                        },
                    ],
                    'layout': {
                        'title': f'{ticker} - Trading Volume',
                        'xaxis': {'title': 'Date', 'type': 'date'},
                        'yaxis': {'title': 'Volume'},
                        'template': 'plotly_white',
                        'height': 300
                    }
                },
                {
                    'data': [
                        {
                            'x': data_dict['date'],
                            'y': data_dict['close'],
                            'mode': 'lines+markers',
                            'type': 'scatter',
                            'name': 'Close Price',
                            'line': {'color': '#FF6347', 'width': 2},
                            'marker': {'size': 4}
                        },
                    ],
                    'layout': {
                        'title': f'{ticker} - Closing Price Trend',
                        'xaxis': {'title': 'Date', 'type': 'date'},
                        'yaxis': {'title': 'Price (BDT)'},
                        'template': 'plotly_white',
                        'height': 400
                    }
                }
            ]
        
        # Add IDs for each graph
        ids = ['graph-{}'.format(i + 1) for i, _ in enumerate(graphs)]
        
        # Convert to JSON using custom encoder
        graphJSON = json.dumps(convert_to_native_types(graphs), cls=NumpyEncoder)
        
        # Calculate statistics with proper type conversion
        stats = {}
        if not df.empty:
            try:
                # Get individual values safely
                if 'close' in df.columns:
                    close_values = df['close'].dropna()
                    if len(close_values) > 0:
                        current_price = convert_to_native_types(close_values.iloc[-1])
                        first_price = convert_to_native_types(close_values.iloc[0]) if len(close_values) > 1 else current_price
                    else:
                        current_price = None
                        first_price = None
                else:
                    current_price = None
                    first_price = None
                
                if current_price is not None and first_price is not None:
                    price_change = float(current_price) - float(first_price)
                    percent_change = (price_change / float(first_price) * 100) if first_price != 0 else 0
                else:
                    price_change = 0
                    percent_change = 0
                
                # Get high/low values safely
                if 'high' in df.columns:
                    high_values = df['high'].dropna()
                    period_high = convert_to_native_types(high_values.max()) if len(high_values) > 0 else None
                else:
                    period_high = None
                
                if 'low' in df.columns:
                    low_values = df['low'].dropna()
                    period_low = convert_to_native_types(low_values.min()) if len(low_values) > 0 else None
                else:
                    period_low = None
                
                # Get volume safely
                if 'volume' in df.columns:
                    volume_values = df['volume'].dropna()
                    total_volume = convert_to_native_types(volume_values.sum()) if len(volume_values) > 0 else None
                else:
                    total_volume = None
                
                stats = {
                    'current_price': current_price,
                    'price_change': price_change,
                    'percent_change': percent_change,
                    'high': period_high,
                    'low': period_low,
                    'volume': total_volume
                }
                
            except (ValueError, TypeError, Exception) as e:
                print(f"Error calculating statistics: {e}")
                import traceback
                print(traceback.format_exc())
                stats = {
                    'current_price': None,
                    'price_change': 0,
                    'percent_change': 0,
                    'high': None,
                    'low': None,
                    'volume': None
                }
        
        response_data = {
            'graphs': graphJSON,
            'ids': ids,
            'stats': convert_to_native_types(stats),
            'data_points': len(df)
        }
        
        print("Successfully prepared response data")
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        error_msg = f"Error in get_stock_data: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        return jsonify({'error': error_msg})

@app.route('/get_ticker_info')
def get_ticker_info():
    """Get information about available tickers"""
    tickers = get_available_tickers()
    ticker_info = {}
    
    for ticker in tickers:
        ticker_info[ticker] = POPULAR_STOCKS.get(ticker, ticker)
    
    return jsonify(convert_to_native_types(ticker_info))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999)