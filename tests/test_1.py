from bdshare import get_current_trade_data

df = get_current_trade_data() # get specific instrument data
print(df.to_string())