from bdshare import get_basic_hist_data
import datetime as dt


end = dt.datetime.now().date()
df = get_basic_hist_data(end, end,'BATBC') # get specific instrument data
print(df.to_string())
print(df.dtypes)