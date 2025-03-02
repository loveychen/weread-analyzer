import pandas as pd
import requests
import json
from typing import List, Dict, Any
import os

API_ENDPOINT = "https://qwen.aliyun.com/v1/models/Qwen/generation"


class BookShelfAnalyzer:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", None)
        if self.api_key is None:
            self.api_key = input("请输入您的OpenAI API密钥：")
        self.books = []
    
    def load_books_from_csv(self, file_path: str) -> List[Dict[str, Any]]:
        """从CSV文件加载书籍数据"""
        df = pd.read_csv(file_path)
        self.books = df.to_dict('records')
        print(f"已加载 {len(self.books)} 本书籍")
        return self.books
    
    def analyze_book(self, book: Dict[str, Any]) -> Dict[str, Any]:
        """调用大模型分析单本书籍"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        prompt = f"""
        分析以下书籍，并提供：
        1. 最合适的分类（可多选）：文学、科技、历史、哲学、心理、商业、艺术、科学、教育、其他
        2. 阅读优先级（1-5，5最高）
        3. 适合的阅读场景
        4. 预计完成所需时间（小时）
        
        书籍信息：
        标题：{book.get('title', '未知')}
        作者：{book.get('author', '未知')}
        简介：{book.get('description', '未知')}
        当前阅读进度：{book.get('progress', '0')}%
        
        请以JSON格式返回结果。
        """
        
        data = {
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        
        response = requests.post(API_ENDPOINT, headers=headers, json=data)
        result = response.json()
        
        # 解析大模型返回的JSON结果
        analysis = json.loads(result['choices'][0]['message']['content'])
        book.update(analysis)
        
        return book
    
    def analyze_all_books(self) -> List[Dict[str, Any]]:
        """分析所有书籍"""
        analyzed_books = []
        for book in self.books:
            analyzed_book = self.analyze_book(book)
            analyzed_books.append(analyzed_book)
        
        self.books = analyzed_books
        return analyzed_books
    
    def get_categorized_books(self) -> Dict[str, List[Dict]]:
        """按类别归类书籍"""
        categories = {}
        for book in self.books:
            for category in book.get('categories', ['未分类']):
                if category not in categories:
                    categories[category] = []
                categories[category].append(book)
        
        return categories
    
    def get_reading_order(self) -> List[Dict]:
        """获取推荐阅读顺序"""
        # 按优先级排序
        return sorted(self.books, key=lambda x: x.get('priority', 0), reverse=True)
    
    def generate_reading_plan(self) -> str:
        """生成阅读计划"""
        reading_order = self.get_reading_order()
        categories = self.get_categorized_books()
        
        # 调用大模型生成个性化阅读计划
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        prompt = f"""
        基于以下书籍分析结果，生成一个合理的阅读计划：
        
        优先阅读书籍：{json.dumps([b.get('title') for b in reading_order[:5]], ensure_ascii=False)}
        已分类书籍：{json.dumps({k: [b.get('title') for b in v] for k, v in categories.items()}, ensure_ascii=False)}
        
        请给出：
        1. 每周阅读建议
        2. 阅读搭配策略（如专注一类vs交叉阅读）
        3. 如何根据场景安排不同书籍
        """
        
        data = {
            "model": "qwen-plus",
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = requests.post(API_ENDPOINT, headers=headers, json=data)
        result = response.json()
        
        return result['choices'][0]['message']['content']

# 使用示例
def planning_reading_plan(books_fname: str = "books.json"):
    analyzer = BookShelfAnalyzer()
    
    # 加载书籍数据（假设已导出为CSV）
    analyzer.load_books_from_csv("weread_books.csv")
    
    # 分析所有书籍
    analyzer.analyze_all_books()
    
    # 获取分类结果
    categories = analyzer.get_categorized_books()
    print(f"书籍分类完成，共 {len(categories)} 个类别")
    
    # 获取阅读顺序
    reading_order = analyzer.get_reading_order()
    print("推荐阅读顺序：")
    for i, book in enumerate(reading_order[:10]):
        print(f"{i+1}. {book.get('title')} (优先级: {book.get('priority')})")
    
    # 生成阅读计划
    plan = analyzer.generate_reading_plan()
    print("阅读计划：")
    print(plan)


if __name__ == "__main__":
    import fire
    fire.Fire(planning_reading_plan)
