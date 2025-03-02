
import openai

from .weread_helper import WeReadHelper

def process_bookshelf_data(bookshelf):
    """处理书架数据，提取需要分析的信息"""
    processed_data = []
    
    for book in bookshelf:
        book_info = {
            'id': book.get('bookId'),
            'title': book.get('title'),
            'author': book.get('author'),
            'category': book.get('category'),
            'intro': book.get('intro', ''),
            'reading_progress': book.get('readingProgress', 0),
            'reading_time': book.get('readingTime', 0),
        }
        processed_data.append(book_info)
    
    return processed_data



def analyze_books_with_llm(api_key, books_data):
    """使用大模型API分析书籍并进行归类和排序推荐"""
    openai.api_key = api_key
    
    # 构建提示词
    prompt = """
    我有以下书籍信息，请帮我:
    1. 按照主题和类型对这些书籍进行归类
    2. 根据阅读进度、内容相关性和难易度，推荐一个合理的阅读顺序
    3. 给出每本书的简短评价和阅读建议
    
    书籍信息如下:
    """
    
    # 添加书籍信息
    for book in books_data:
        prompt += f"""
        书名: {book['title']}
        作者: {book['author']}
        分类: {book['category']}
        简介: {book['intro']}
        阅读进度: {book['reading_progress']}%
        阅读时长: {book['reading_time']}分钟
        """
    
    # 调用API
    response = openai.ChatCompletion.create(
        model="gpt-4",  # 可以根据需要选择不同的模型
        messages=[
            {"role": "system", "content": "你是一位专业的读书顾问和图书分析专家，擅长对各类书籍进行分类和推荐阅读顺序。"},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content



def save_analysis_results(analysis, output_file="book_analysis.md"):
    """保存分析结果到Markdown文件"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# 微信读书书架分析报告")
        f.write(analysis)
    print(f"分析结果已保存到 {output_file}")


def get_book_notes(helper, book_id):
    """获取特定书籍的笔记"""
    url = f"https://i.weread.qq.com/book/bookmarklist?bookId={book_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    response = helper.session.get(url, headers=headers, cookies=helper.cookies)
    if response.status_code == 200:
        return response.json()
    return {}


def main():
    # 初始化微信读书助手
    helper = WeReadHelper()
    
    # 登录
    print("请扫描二维码登录微信读书...")
    helper.login_with_qrcode()
    
    # 获取书架数据
    print("正在获取书架数据...")
    bookshelf = helper.get_bookshelf()
    
    if not bookshelf:
        print("获取书架数据失败或书架为空")
        return
    
    # 处理数据
    print("正在处理书籍数据...")
    processed_data = process_bookshelf_data(bookshelf)
    
    # 使用大模型分析
    print("正在使用AI分析书籍...")
    api_key = "your_openai_api_key"  # 替换为您的API密钥
    analysis_result = analyze_books_with_llm(api_key, processed_data)
    
    # 保存分析结果
    save_analysis_results(analysis_result)
    
    print("书籍分析完成!")



if __name__ == "__main__":
    main()
