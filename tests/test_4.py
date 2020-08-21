from bdshare import get_market_inf_more_data
import datetime as dt


end = dt.datetime.now().date()
df = get_market_inf_more_data('2020-01-01', end, index='date')
print(df.to_string())
print(df.dtypes)
