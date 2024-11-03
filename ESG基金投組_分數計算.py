import pandas as pd
import datetime

# 定義 Function
def calculate_whiskers(sub_df):
    """ 計算盒鬚圖的統計值 """
    Q1 = sub_df.quantile(0.25)
    Q3 = sub_df.quantile(0.75)
    IQR = Q3 - Q1
    lower_whisker = max(sub_df[sub_df >= (Q1 - 1.5 * IQR)].min(), Q1 - 1.5 * IQR)
    upper_whisker = min(sub_df[sub_df <= (Q3 + 1.5 * IQR)].max(), Q3 + 1.5 * IQR)
    
    return pd.Series({
        "Q1": Q1,
        "Median": sub_df.median(),
        "Q3": Q3,
        "IQR": IQR,
        "Lower Whisker": lower_whisker,
        "Upper Whisker": upper_whisker
    })

def categorize_score(score, Q1, Q2, Q3, lower_whisker, upper_whisker):
    """ 將分數分類為 0-5 分 """
    if score < lower_whisker:
        return 0 # 低於盒鬚圖下鬚的值分數為 0
    elif lower_whisker <= score < Q1:
        return 1 # 介於盒鬚圖下鬚與第一分位數之間的分數為 1
    elif Q1 <= score < Q2:
        return 2 # 介於第一分位數與中位數之間的分數為 2
    elif Q2 <= score < Q3:
        return 3 # 介於中位數與第三分位數之間的分數為 3
    elif Q3 <= score <= upper_whisker:
        return 4 # 介於第三分位數與盒鬚圖上鬚之間的分數為 4
    else:
        return 5 # 高於盒鬚圖上鬚的值分數為 5

def categorize_row(row, stats):
    """ 進行分數評分 """
    categorized = {}
    for col in numeric_cols:
        if row[col] == 0:
            categorized[col] = 0 # 原資料為 0 的欄位不進行分類
        else:
            Q1 = stats[col]['Q1']
            Median = stats[col]['Median']
            Q3 = stats[col]['Q3']
            Lower_Whisker = stats[col]['Lower Whisker']
            Upper_Whisker = stats[col]['Upper Whisker']
            categorized[col] = categorize_score(row[col], Q1, Median, Q3, Lower_Whisker, Upper_Whisker)
    return pd.Series(categorized)

def calculate_total_score(row):
    """ 計算 ESG 總分 """
    industry = row['SASB主產業']
    weights = industry_weights.get(industry, {'E_score': 0.33, 'S_score': 0.33, 'G_score': 0.34}) # 預設權重
    total_score = (
        row['E_score'] * weights['E_score'] +
        row['S_score'] * weights['S_score'] +
        row['G_score'] * weights['G_score']
    )
    return round(total_score, 2)

# 產業權重設定
industry_weights = {
    '消費品': {'E_score': 0.19, 'S_score': 0.42, 'G_score': 0.39},
    '提煉與礦產加工': {'E_score': 0.39, 'S_score': 0.25, 'G_score': 0.36},
    '金融': {'E_score': 0.12, 'S_score': 0.41, 'G_score': 0.47},
    '食品與飲料': {'E_score': 0.31, 'S_score': 0.39, 'G_score': 0.30},
    '醫療保健': {'E_score': 0.18, 'S_score': 0.53, 'G_score': 0.29},
    '公共建設': {'E_score': 0.28, 'S_score': 0.30, 'G_score': 0.42},
    '可再生資源與替代能源': {'E_score': 0.35, 'S_score': 0.22, 'G_score': 0.43},
    '資源轉化': {'E_score': 0.30, 'S_score': 0.30, 'G_score': 0.40},
    '服務': {'E_score': 0.22, 'S_score': 0.48, 'G_score': 0.30},
    '科技與通訊': {'E_score': 0.24, 'S_score': 0.38, 'G_score': 0.38},
    '運輸': {'E_score': 0.32, 'S_score': 0.29, 'G_score': 0.39},
}

# 讀取資料
df = pd.read_csv('ESG基金投組_個股ESG資料_20241103.csv')
df = df.drop(columns=[col for col in df.columns if 'Y/N' in col]) # 刪除欄位中含有 Y/N 的欄位
numeric_cols = df.iloc[:, 8:].select_dtypes(include='number').columns # 選擇數值型欄位

# 分別針對每個產業的數值型欄位計算盒鬚圖統計值
grouped_stats = df.groupby('SASB主產業')[numeric_cols].apply(lambda x: x.apply(calculate_whiskers))

# 分別針對每個產業的數值型欄位進行分數評分
df_categorized = df.groupby('SASB主產業').apply(
    lambda group: group.apply(
        lambda row: categorize_row(row, grouped_stats.loc[row['SASB主產業']]), 
        axis=1
    )
)

# 計算 ESG 分數
E_cols = [col for col in df_categorized.columns if col.startswith('E')]
S_cols = [col for col in df_categorized.columns if col.startswith('S')]
G_cols = [col for col in df_categorized.columns if col.startswith('G')]

df_categorized['E_score'] = df_categorized[E_cols].sum(axis=1)
df_categorized['S_score'] = df_categorized[S_cols].sum(axis=1)
df_categorized['G_score'] = df_categorized[G_cols].sum(axis=1)

# 合併資料
df_esg = pd.concat([
    df.iloc[:, :9].reset_index(drop=True), 
    df_categorized.reset_index(drop=True)
], axis=1)

# 計算 ESG 總分並輸出
df_esg['Total_score'] = df_esg.apply(calculate_total_score, axis=1)
date = datetime.datetime.now().strftime('%Y%m%d')
df_esg.to_csv(f'ESG基金投組_個股分數_{date}.csv', index=False)