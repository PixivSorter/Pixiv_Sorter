from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime
from typing import IO, Any

import cloudscraper  # type: ignore[import]
from requests.structures import CaseInsensitiveDict

from utils import JsonDict, ParamDict, ParsedJson, PixivError, Response

# from typeguard import typechecked


# @typechecked
class BasePixivAPI:
    client_id = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
    client_secret = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
    hash_secret = "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"

    def __init__(self, **requests_kwargs: Any) -> None:
        """initialize requests kwargs if need be"""
        self.user_id: int | str = 0
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.hosts = "https://app-api.pixiv.net"

        # self.requests = requests.Session()
        self.requests = cloudscraper.create_scraper()  # fix due to #140
        self.additional_headers = CaseInsensitiveDict(requests_kwargs.pop("headers", {}))  # type: CaseInsensitiveDict[Any]
        self.requests_kwargs = requests_kwargs

    def set_additional_headers(self, headers: ParamDict) -> None:
        """manually specify additional headers. will overwrite API default headers in case of collision"""
        self.additional_headers = CaseInsensitiveDict(headers)

    # 设置HTTP的Accept-Language (用于获取tags的对应语言translated_name)
    # language: en-us, zh-cn, ...
    def set_accept_language(self, language: str) -> None:
        """set header Accept-Language for all requests (useful for get tags.translated_name)"""
        self.additional_headers["Accept-Language"] = language

    @classmethod
    def parse_json(cls, json_str: str | bytes) -> ParsedJson:
        """parse str into JsonDict"""
        return json.loads(json_str, object_hook=JsonDict)

    def require_auth(self) -> None:
        if self.access_token is None:
            raise PixivError("Authentication required! Call login() or set_auth() first!")

    def requests_call(
        self,
        method: str,
        url: str,
        headers: ParamDict | CaseInsensitiveDict[Any] | None = None,
        params: ParamDict | None = None,
        data: ParamDict | None = None,
        stream: bool = False,
    ) -> Response:
        """requests http/https call for Pixiv API"""
        merged_headers = self.additional_headers.copy()
        if headers:
            # Use the headers in the parameter to override the
            # additional_headers setting.
            merged_headers.update(headers)
        try:
            if method == "GET":
                return self.requests.get(
                    url,
                    params=params,
                    headers=merged_headers,
                    stream=stream,
                    **self.requests_kwargs,
                )
            elif method == "POST":
                return self.requests.post(
                    url,
                    params=params,
                    data=data,
                    headers=merged_headers,
                    stream=stream,
                    **self.requests_kwargs,
                )
            elif method == "DELETE":
                return self.requests.delete(
                    url,
                    params=params,
                    data=data,
                    headers=merged_headers,
                    stream=stream,
                    **self.requests_kwargs,
                )
            else:
                msg = f"Unknown method: {method}"
                raise PixivError(msg)
        except Exception as e:
            msg = f"requests {method} {url} error: {e}"
            raise PixivError(msg)

    def set_auth(self, access_token: str, refresh_token: str | None = None) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token

    def login(self, username: str, password: str) -> Any:
        return self.auth(username=username, password=password)

    def set_client(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret

    def auth(
        self,
        username: str | None = None,
        password: str | None = None,
        refresh_token: str | None = None,
        headers: ParamDict = None,
    ) -> ParsedJson:
        """Login with password, or use the refresh_token to acquire a new bearer token"""
        local_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
        headers_ = CaseInsensitiveDict(headers or {})
        headers_["x-client-time"] = local_time
        headers_["x-client-hash"] = hashlib.md5((local_time + self.hash_secret).encode("utf-8")).hexdigest()
        # Allow mock UA due to #171: https://github.com/upbit/pixivpy/issues/171
        if "user-agent" not in headers_:
            headers_["app-os"] = "ios"
            headers_["app-os-version"] = "14.6"
            headers_["user-agent"] = "PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)"

        # noinspection PyUnresolvedReferences
        if not hasattr(self, "hosts") or self.hosts == "https://app-api.pixiv.net":
            auth_hosts = "https://oauth.secure.pixiv.net"
        else:
            # noinspection PyUnresolvedReferences
            auth_hosts = self.hosts  # BAPI解析成IP的场景
            headers_["host"] = "oauth.secure.pixiv.net"
        url = f"{auth_hosts}/auth/token"
        data = {
            "get_secure_url": 1,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        if username and password:
            data["grant_type"] = "password"
            data["username"] = username
            data["password"] = password
        elif refresh_token or self.refresh_token:
            data["grant_type"] = "refresh_token"
            data["refresh_token"] = refresh_token or self.refresh_token
        else:
            raise PixivError("[ERROR] auth() but no password or refresh_token is set.")

        r = self.requests_call("POST", url, headers=headers_, data=data)
        if r.status_code not in {200, 301, 302}:
            if data["grant_type"] == "password":
                msg = f"[ERROR] auth() failed! check username and password.\nHTTP {r.status_code}: {r.text}"
                raise PixivError(
                    msg,
                    header=r.headers,
                    body=r.text,
                )
            else:
                msg = f"[ERROR] auth() failed! check refresh_token.\nHTTP {r.status_code}: {r.text}"
                raise PixivError(
                    msg,
                    header=r.headers,
                    body=r.text,
                )

        token = None
        try:
            # get access_token
            token = self.parse_json(r.text)
            self.user_id = token.response.user.id
            self.access_token = token.response.access_token
            self.refresh_token = token.response.refresh_token
        except json.JSONDecodeError:
            msg = f"Get access_token error! Response: {token}"
            raise PixivError(
                msg,
                header=r.headers,
                body=r.text,
            )

        # return auth/token response
        return token

    def download(
        self,
        url: str,
        prefix: str = "",
        path: str = os.path.curdir,
        name: str | None = None,
        replace: bool = False,
        fname: str | IO[bytes] | None = None,
        referer: str = "https://app-api.pixiv.net/",
    ) -> bool:
        """Download image to file (use 6.0 app-api)"""
        if hasattr(fname, "write"):
            # A file-like object has been provided.
            file = fname
        else:
            # Determine file path by parameters.
            name = prefix + str(name or fname or os.path.basename(url))
            file = os.path.join(path, name)
            if os.path.exists(file) and not replace:
                return False

        with self.requests_call("GET", url, headers={"Referer": referer}, stream=True) as response:
            if isinstance(file, str):
                with open(file, "wb") as out_file:
                    shutil.copyfileobj(response.raw, out_file)
            else:
                shutil.copyfileobj(response.raw, file)  # type: ignore[arg-type]
        return True

class ExtendedPixivAPI(BasePixivAPI):
    def get_user_illusts(self, user_id: int, illust_type: str = "illust", offset: int = 0) -> list[str]:
        """
        指定したPixivユーザーのイラストのURLを取得します。
        
        :param user_id: PixivユーザーのID
        :param illust_type: 取得する作品の種類 ("illust" または "manga")
        :param offset: ページネーション用のオフセット
        :return: イラストのURLリスト
        """
        self.require_auth()
        
        url = f"{self.hosts}/v1/user/illusts"
        params = {
            "user_id": user_id,
            "type": illust_type,
            "offset": offset,
        }
        response = self.requests_call("GET", url, params=params)
        
        if response.status_code != 200:
            raise PixivError(f"Failed to fetch user illusts: {response.text}")
        
        data = self.parse_json(response.text)
        illusts = data.get("illusts", [])
        
        # 各イラストのURLを取得
        urls = [illust["image_urls"]["large"] for illust in illusts if "image_urls" in illust]
        return urls


'''class ExtendedPixivAPI(BasePixivAPI):
    def get_illust_likes(self, illust_id: int) -> int:
        """
        指定したイラストのいいね数を取得します。
        
        :param illust_id: 対象イラストのID
        :return: いいね数（ブックマーク数）
        """
        self.require_auth()
        
        url = f"{self.hosts}/v1/illust/detail"
        params = {"illust_id": illust_id}
        response = self.requests_call("GET", url, params=params)
        
        if response.status_code != 200:
            raise PixivError(f"Failed to fetch illust details: {response.text}")
        
        data = self.parse_json(response.text)
        illust_details = data.get("illust", {})
        
        # いいね数を取得
        total_likes = illust_details.get("total_bookmarks", 0)
        return total_likes'''


# APIインスタンスの作成
api = ExtendedPixivAPI()
api.set_auth(access_token="MVLbOVxVs-dEzW6IEaZILTGzSeLSGHdkqOLY-7BHa28", refresh_token="kOdU-W_J4-k-ehLOkOKq1Z4UVTOwfJuAnNJWeeUcW7k")

# 指定したユーザーのイラストを取得
user_id = 366411  # 対象ユーザーのID
try:
    illust_urls = api.get_user_illusts(user_id)
    for url in illust_urls:
        print(url)
except PixivError as e:
    print(f"Error: {e}")