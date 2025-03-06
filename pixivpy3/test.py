from bookmark_api import ExtendedPixivAPI
from utils import JsonDict, ParamDict, ParsedJson, PixivError, Response

# APIインスタンスの作成
api = ExtendedPixivAPI()
api.set_auth(access_token="your_access_token", refresh_token="your_refresh_token")

# 指定したユーザーのイラストを取得
user_id = 366411  # 対象ユーザーのID
try:
    illust_urls = api.get_user_illusts(user_id)
    for url in illust_urls:
        print(url)
except PixivError as e:
    print(f"Error: {e}")
