from pixivpy3 import *
import os
import shutil

#インスタンスの作成
class collectIllustInfo():
    def auth(self, user_id, refresh_token):
        self.instance = AppPixivAPI()
        self.instance.auth(refresh_token = refresh_token)

        #変数の定義

        self.user_id = user_id

        self.illusts_all = []
        self.offset = 0

        self.illust_title = []
        self.illust_id = []
        self.illust_bookmark = []
        self.illust_tag = []
        self.illust_judge = []

    #イラスト情報の取得
    def get_list(self):
        while True:
            illusts_info = self.instance.user_illusts(self.user_id, type=None, offset=self.offset)
            for illust in illusts_info.illusts:
                self.illust_title.append(illust.title)
                self.illust_id.append(illust.id)
                self.illust_bookmark.append(illust.total_bookmarks)
                self.illust_tag.append(illust.tags)
                self.illust_judge.append(illust.x_restrict)
            self.illusts_all.extend(illusts_info["illusts"])

            if len(illusts_info['illusts']) < 30:
                break

            self.offset += 30

    #並べ替え
    def sort_list(self, content):
        exclude_number = []
        exclude_number = [i for i in range(len(self.illust_judge)) if self.illust_judge[i] != 0]

        illust_all_data = list(zip(self.illust_title, self.illust_id, map(int, self.illust_bookmark)))
        illust_all_data_general = [data for i, data in enumerate(illust_all_data) if i not in exclude_number]
        illust_all_data_R18 = [data for i, data in enumerate(illust_all_data) if i in exclude_number]

        illust_all_data.sort(key=lambda x: x[2], reverse=True)
        illust_all_data_general.sort(key=lambda x: x[2], reverse=True)
        illust_all_data_R18.sort(key=lambda x: x[2], reverse=True)

        if content == 0:
            return illust_all_data
        elif content == 1:
            return illust_all_data_general
        elif content == 2:
            return illust_all_data_R18

    def download_thumbnail(self, data, content):
        if content == 0:
            file_name = 'all'
        elif content == 1:
            file_name = 'general'
        elif content == 2:
            file_name = 'R18'

        thumbnail_file = f'.../tmp/{self.user_id}/{file_name}/'

        try:
            os.makedirs(thumbnail_file)
        except FileExistsError:
            shutil.rmtree(f'.../tmp/{self.user_id}/{file_name}')
            os.mkdir(thumbnail_file)

        if len(data) <= 15:
            for_renge = len(data)
        else:
            for_renge = 15

        for i in range(for_renge):
            illust_detail = ''
            thumbnail_url = ''
            
            download_id = data[i][1]

            illust_detail = self.instance.illust_detail(download_id)
            thumbnail_url = illust_detail['illust']['image_urls']['square_medium']

            old_path = self.instance.download(thumbnail_url, thumbnail_file, i)
            
            temp_path = old_path.split('/')
            
            temp_path.pop(-1)
            temp_path.append(f'{i+1}.jpg')

            new_path = '/'.join(temp_path)

            os.rename(old_path,new_path)
    
    def get_maker(self, user_id):
        user_info = self.instance.user_detail(user_id)
        return user_info





