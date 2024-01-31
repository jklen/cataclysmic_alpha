from alpaca.data.live import CryptoDataStream, StockDataStream

paper_key = 'PK03QP4W74VY401Y2OEF'
paper_secret = 'HDcvk9sAJ6ftJGN9BNg8dHYg4d3Yb01PvIROmGhM'

stock_stream = CryptoDataStream(paper_key, paper_secret )
# async handler
async def quote_data_handler(data):
    # quote data will arrive here
    print(data)

stock_stream.subscribe_quotes(quote_data_handler, "BTC/USD")

stock_stream.run()

#%%
