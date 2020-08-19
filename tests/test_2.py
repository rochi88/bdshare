from bdshare import get_basic_hist_data

# get specific instrument data
df = get_basic_hist_data('2020-01-01', '2020-03-25', 'BATBC')
print(df.to_string())
print(df.dtypes)
