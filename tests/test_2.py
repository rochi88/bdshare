from bdshare import get_basic_hist_data

df = get_basic_hist_data('2008-01-01','2020-03-25','BATBC') # get specific instrument data
print(df.to_string())
print(df.dtypes)