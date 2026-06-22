# 汽车出海数据看板 / Auto Export Dashboard

爬取英国与德国市场 2025-2026 年汽车品牌月度销量数据，并以交互式看板展示。

## 项目结构

```
├── scraper/
│   ├── uk_scraper.py        # 英国 SMMT 数据爬取
│   ├── germany_scraper.py   # 德国 KBA 数据爬取
│   └── requirements.txt
├── data/                    # 爬取结果（JSON）
├── dashboard/
│   └── index.html           # 看板前端
└── outputs/                 # 导出报表
```

## 数据来源

- **英国**：[SMMT](https://www.smmt.co.uk/vehicle-data/car-registrations/) — 新车注册月度数据
- **德国**：[KBA](https://www.kba.de/DE/Statistik/Fahrzeuge/Neuzulassungen/neuzulassungen_node.html) — 新车注册月度数据
- 备选：ACEA、carsalesbase.com、bestsellingcarsblog.com

## 快速开始

```bash
# 安装 Python 依赖
pip install -r scraper/requirements.txt

# 运行爬虫
python scraper/uk_scraper.py
python scraper/germany_scraper.py

# 打开看板
start dashboard/index.html
```

## 技术栈

| 层       | 技术               |
| -------- | ------------------ |
| 爬虫     | Python + requests + BeautifulSoup4 |
| 数据处理 | pandas             |
| 看板     | HTML5 + Chart.js   |

## 状态

2025 全年数据已收录，2026 年数据持续更新中。
