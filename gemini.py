import google.generativeai as genai
import os

# 配置 API 密鑰
api_key = 'AIzaSyBE_AGHv3ncVmHrI0UI6M6tVGyFQ3CZrtY'
genai.configure(api_key=api_key)

def chatting(strategy_name, data):
    """
    使用 Gemini 模型分析策略數據
    """
    prompt = f"""
    請根據以下數據分析交易策略 '{strategy_name}' 的表現：
    
    {data}
    
    評估策略的淨利潤、回撤、交易總數、勝率、獲利因子及平均盈虧，並提供具體的結論。
    
    最後，提出兩個關鍵問題，例如影響績效的主要因素或數據的計算方式，並提供可能的參考答案，讓使用者對照思考。
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        response = model.generate_content(prompt)
        response.resolve()
        return response.text
    except Exception as e:
        return f"Gemini 產生內容時發生錯誤：{e}"

def parse_txt_file(file_path):
    """
    讀取並解析 analysis_results.txt
    """
    if not os.path.exists(file_path):
        print(f"❌ 找不到檔案：{file_path}")  # 🔴 確保 Flask 真的有找到檔案
        return "找不到分析結果檔案！請先執行策略分析。"

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = file.read()

        # 解析出策略名稱
        first_line = data.split("\n")[0]  # 讀取第一行策略名稱
        strategy_name = first_line.replace("---", "").strip()  # 移除 "---"

        print(f" 讀取策略：{strategy_name}")  # 🔵 確保程式有正確讀取策略名稱

        return chatting(strategy_name, data)
    except Exception as e:
        print(f" 讀取檔案時發生錯誤：{e}")
        return f"讀取檔案時發生錯誤：{e}"

if __name__ == "__main__":
    result = parse_txt_file("analysis_results.txt")
    print(result)  # 🔵 確保 `gemini.py` 真的輸出結果
