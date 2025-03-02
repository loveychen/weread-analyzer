from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_random
from tqdm import tqdm
from typing import Dict, Any, List

from PyQt5.QtNetwork import QNetworkCookie
import requests
from PyQt5.QtWidgets import QApplication
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import sys
import time
import pandas as pd
from PyQt5.QtCore import QTimer


"""
所有微信读书 API 信息参考自 https://github.com/Higurashi-kagome/pythontools/tree/master/wereader

包括：
- 登录接口："https://i.weread.qq.com/user/notebooks"
- 获取书架图书信息（bookid）："https://i.weread.qq.com/shelf/sync?userVid=" + str(userVid) + "&synckey=0&lectureSynckey=0"
- 获取图书信息："https://i.weread.qq.com/book/info?bookId=" + bookId
- 获取图书章节信息："https://i.weread.qq.com/book/chapterInfos?" + "bookIds=" + bookId + "&synckeys=0"
- 获取图书中的标注："https://i.weread.qq.com/book/bookmarklist?bookId=" + bookId
- 获取图书中的个人想法："https://i.weread.qq.com/review/list?bookId=" + bookId + "&listType=11&mine=1&synckey=0&listMode=0"
- 获取图书的热门标注："https://i.weread.qq.com/book/bestbookmarks?bookId=" + bookId
"""

class WeReadHelper:
    def __init__(self):
        self.session = requests.Session()
        self.cookies: Dict[str, str] = {}
        self.bookshelf = []
        self.ua = UserAgent().chrome  # 初始化 fake_useragent

    def login_with_qrcode(self, force_login: bool = False) -> None:
        """使用二维码登录微信读书"""
        # 创建 PyQt5 应用实例
        app = QApplication(sys.argv)
        view = QWebEngineView()
        # 获取当前的 QWebEngineProfile
        profile = view.page().profile()
        cookie_store = profile.cookieStore()

        # 强制登陆时，清除缓存和cookie存储
        if force_login:
            self.cookies.clear()  # 清空 internal cookie 字典
            profile.clearHttpCache()  # 清除 HTTP 缓存
            profile.clearAllVisitedLinks()  # 清除访问历史记录
            print("已强制清空 cookies 和缓存")

        # 初始化 cookies_loaded 为 False
        self.cookies_loaded = False
        
        # 加载目标页面
        view.load(QUrl("https://weread.qq.com/"))
        view.show()

        def on_cookie_added(cookie: QNetworkCookie) -> None:
            """捕获新增的 Cookie 并更新到 cookies 字典中"""
            cookie_name = cookie.name().data().decode()
            cookie_value = cookie.value().data().decode()
            self.cookies[cookie_name] = cookie_value
            print(f"[Cookie 捕获] {cookie_name} = {cookie_value}")
            
            self.cookies_loaded = True

        # 绑定 cookieAdded 信号到处理函数
        cookie_store.cookieAdded.connect(on_cookie_added)

        def on_load_finished(ok: bool) -> None:
            """当页面加载完成后，标记可以获取 cookies"""
            if ok:
                print("页面加载完成")
                self.cookies_loaded = True

        view.loadFinished.connect(on_load_finished)

        # 设置超时等待机制
        timer = QTimer()
        timer.setSingleShot(True)

        def quit_app():
            if not self.cookies_loaded:
                print("二维码扫码超时，未完成登录。")
            app.quit()

        timer.timeout.connect(quit_app)
        timer.start(1000 * 60 * 5)  # 超时时间为 5 分钟

        app.exec_()

        # 如果 cookies 没有加载成功，抛出超时异常
        if not self.cookies_loaded:
            raise Exception("登录超时，请重试")


    def get_bookshelf(self) -> list:
        """获取书架上的书籍列表"""
        url = "https://i.weread.qq.com/shelf/sync"
        headers = {
            "User-Agent": self.ua,  # 使用 fake_useragent 随机生成 User-Agent
        }

        response = self.session.get(url, headers=headers, cookies=self.cookies)
        if response.status_code == 200:
            data = response.json()
            self.bookshelf = data.get("books", [])
            return self.bookshelf
        return []

    @retry(stop=stop_after_attempt(3), wait=wait_random(min=30, max=300))
    def get_book_info(self, book_id: str) -> dict:
        """获取特定书籍的详细信息"""
        url = f"https://i.weread.qq.com/book/info?bookId={book_id}"
        headers = {
            "User-Agent": self.ua,  # 使用 fake_useragent 随机生成 User-Agent
        }

        response = self.session.get(url, headers=headers, cookies=self.cookies)
        if response.status_code == 200:
            return response.json()
        return {}

    @retry(stop=stop_after_attempt(3), wait=wait_random(min=30, max=300))
    def get_best_bookmarks(self, book_id: str) -> list:
        """获取特定书籍的热门标注"""
        url = "https://i.weread.qq.com/book/bestbookmarks?bookId={book_id}"
        headers = {
            "User-Agent": self.ua,  # 使用 fake_useragent 随机生成 User-Agent
        }
        response = self.session.get(
            url.format(book_id=book_id), headers=headers, cookies=self.cookies
        )
        if response.status_code == 200:
            return response.json()
        return {}

    @retry(stop=stop_after_attempt(3), wait=wait_random(min=30, max=300))
    def get_chapter_infos(self, book_id: str) -> list:
        """获取特定书籍的章节信息"""
        url = f"https://i.weread.qq.com/book/chapterInfos?bookIds={book_id}&synckeys=0"
        headers = {
            "User-Agent": self.ua,  # 使用 fake_useragent 随机生成 User-Agent
        }
        response = self.session.get(url, headers=headers, cookies=self.cookies)
        if response.status_code == 200:
            return response.json()
        return {}


def parse_star_info(starDetails) -> str:
    star_map = {
        "one": "一星",
        "two": "二星",
        "three": "三星",
        "four": "四星",
        "five": "五星",
    }

    return "；".join(
        [f"{star_map[k]}: {v}" for k, v in starDetails.items() if k in star_map]
    )


def parse_new_rating_info(newRatingInfo) -> str:
    new_rating_map = {
        "good": "推荐",
        "fair": "一般",
        "poor": "不行",
    }

    return "；".join(
        [
            f"{new_rating_map[k]}: {v}"
            for k, v in newRatingInfo.items()
            if k in new_rating_map
        ]
    )


def parse_hot_bookmarks(bookmarks: Dict[str, Any], top_k: int = 10) -> str:
    """
    解析热门标注信息

    Args:
        bookmarks: 热门标注信息列表
        top_k: 要返回的标注数量
    Returns:
        解析后的标注信息字符串
    """

    hot_bookmarks = bookmarks.get("items", [])
    total_count = bookmarks.get("totalCount", 0)

    top_k_bookmarks = hot_bookmarks[:top_k]

    # result = {
    #     "total_hot_bookmarks": total_count,
    #     "top_k": top_k,
    #     "top_k_bookmarks": [
    #     {
    #         "index": idx + 1,
    #         "text": bookmark["markText"],
    #         "totalCount": bookmark["totalCount"],
    #     }

    #     for idx, bookmark in enumerate(top_k_bookmarks)
    #     ],
    # }

    # return json.dumps(result, ensure_ascii=False, indent=4)

    return "\n".join(
        [
            f"{idx + 1}. {bookmark['markText']} ({bookmark['totalCount']})"
            for idx, bookmark in enumerate(top_k_bookmarks)
        ]
    )
def parse_chapter_infos(chapter_infos: Dict[str, Any]) -> str:
    """
    解析章节信息
    Args:
        chapter_infos: 章节信息列表
    Returns:
        解析后的章节信息字符串
    """
    try:
        chapter_infos = "\n".join(
            [
                f"{idx + 1}. {chapter['title']}"
                for idx, chapter in enumerate(chapter_infos["data"][0]["updated"])
            ]
        )
        return chapter_infos
    except Exception as e:
        return ""


def export_weread_library(
    output_file: str = "data/books.json",
    start_index: int = 0,
    detailed_books: str = "data/books.json",
    force_login: bool = False,
) -> None:
    """
    导出微信读书书架上的书籍信息及热门评论

    Args:
        output_file: 导出的JSON文件路径
        start_index: 开始导出的书籍索引
        detailed_books: 已经下载过的带详细信息的书籍
    """
    helper = WeReadHelper()
    helper.login_with_qrcode(force_login=force_login)

    bookshelf = helper.get_bookshelf()

    print(f"书籍总数 {len(bookshelf)}")

    book_infos = []
    if start_index > len(bookshelf):
        print("start_idx 大于书架书籍数量，将使用书架书籍数量作为起始索引")
        return

    detailed_book_map = {}

    try:
        # 已经下载过的带详细信息的书籍
        detailed_books = pd.read_json(detailed_books)
        for _, book in detailed_books.iterrows():
            detailed_book_map[book["bookId"]] = book["info"]
        print(f"已有 {len(detailed_books)} 本书籍已同步详情数据！！！")
    except FileNotFoundError:
        print("未找到已下载的书籍信息文件，将重新下载书籍信息")

    # 修改：增加进度条和计数器
    for i, book in enumerate(tqdm(bookshelf[start_index:], desc="处理书籍进度")):
        try:
            book_id = book["bookId"]
            book_title = book["title"]

            # 获取书籍基本信息, secret = 1 表示是自己上传的私有书籍
            if (secret := book.get("secret", 0)) == 1:
                book_info = {}
            elif book_info := detailed_book_map.get(book_id, {}):
                # print(f"books {book_id} - {book_title} with detailed info")
                book_info = book_info
            else:
                book_info = helper.get_book_info(book_id)
                time.sleep(0.5)

            if not book_info:
                print(f"获取书籍 {book_id} - {book_title} 信息失败")

            if book_info and "bookmarks" not in book_info:
                book_info["bookmarks"] = helper.get_best_bookmarks(book_id)
                # print(book_info)
                time.sleep(0.5)

            if book_info and "chapter_infos" not in book_info:
                book_info["chapter_infos"] = helper.get_chapter_infos(book_id)
                print(book_info["chapter_infos"])
                time.sleep(0.5)

            # 这个字段没有任何意义，删除掉
            if "coverBoxInfo" in book_info:
                del book_info["coverBoxInfo"]

            book["info"] = book_info

            book_infos.append(
                {
                    "bookId": book["bookId"],
                    "title": book["title"],
                    "author": book["author"],
                    "translator": book.get("translator", ""),
                    "publishTime": book["publishTime"].split()[0]
                    if book["publishTime"]
                    else "",
                    "price": book["price"],
                    "category": book.get("category", ""),
                    "publisher": book_info.get("publisher", ""),
                    "isbn": book_info.get("isbn", ""),
                    "secret": secret,
                    "chapters": book_info.get("chapterSize", 0),
                    "words": book_info.get("totalWords", 0),
                    "stars": book_info.get("star", 0),
                    "ratingCount": book_info.get("ratingCount", 0),
                    "ratingDetail": parse_star_info(book_info.get("ratingDetail", {})),
                    "newRating": f"{round(book_info.get('newRating', 0) / 10, 1)} %",
                    "newRatingCount": book_info.get("newRatingCount", 0),
                    "newRatingDetail": parse_new_rating_info(
                        book_info.get("newRatingDetail", {})
                    ),
                    "intro": book_info.get("intro", ""),
                    "AISummary": book_info.get("AISummary", ""),
                    "chapterInfos": parse_chapter_infos(
                        book_info.get("chapter_infos", {})
                    ),
                    "hotBookmarks": parse_hot_bookmarks(book_info.get("bookmarks", {})),
                    
                }
            )
        except Exception as e:
            print(f"处理书籍 {book_id} 时出错: {e}, book details: {book}")

        # 修改：每10本书籍打印一次详情
        if i % 50 == 0:
            tqdm.write(f"书名: {book['title']}")
            tqdm.write(f"作者: {book['author']}")
            tqdm.write("-" * 50)

    print(f"书籍信息已保存到 {output_file} 文件中")
    df = pd.DataFrame(bookshelf)
    df.to_json(output_file, orient="records", indent=4, force_ascii=False)

    df2 = pd.DataFrame(book_infos)
    df2.to_excel(f"{output_file}.xlsx", index=False)


if __name__ == "__main__":
    from fire import Fire

    Fire(export_weread_library)
