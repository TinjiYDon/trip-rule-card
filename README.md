# 规则卡

携程首届高校 AI Hackathon 作品。嵌在门票「立即预订」之前。

一个人、一天、一个景区：算什么票、种草和在售是否一致、何时放票、优惠能否叠加。散文先分句、抽槽、校验，再执行。对照有两路朴素读法：看见免票就下结论，以及只信文中第一个数字。

**交稿先读**：[docs/交稿说明.md](docs/交稿说明.md) · 评测报告：[docs/report.html](docs/report.html)

## 跑起来

```powershell
cd rule-card
python eval/check_corpus.py
python -m unittest tests.test_pipeline
python eval/run_eval.py
python eval/render_report.py
python demo/server.py
```

浏览器打开 http://127.0.0.1:8765

打交稿包：

```powershell
python tools/pack_submission.py
```

## 当前数字（以 `eval/latest.json` 为准）

- 页面 16 条，有标注 15 条；已核对官网 **5** 条  
- 只看种草 0.133 · 只读第一个数字 0.333 · 编译执行 **1.0**  
- 留出且有标注 4 条：编译执行 1.0  
- 1 条立牌页没有数字，不进分母  

这些数字只说明当前语料上三条读法的差距，不能写成全国成绩。

## 已核对官网

| 馆 | 要点 |
|---|---|
| 故宫博物院 | 未满 18 周岁免费；提前 7 日 20:00 |
| 中国科学技术馆 | 8 岁或 1.3 米以下免；未满 18 优惠 |
| 中国国家博物馆 | 免费预约；提前 7 日 17:00 放票 |
| 上海博物馆特展 | 6 岁及以下免；6–18 优惠 |
| 东方明珠（留出） | 1 米以下免；1–1.3 米或 6 岁及以下半价 |

其余为规则类型例句，`verified: false`，答辩时不得说成现行价。

## 范围

做：六步编译执行、三路对照、错因、可改原文的预订前四格、评测报告、交稿包。  
不做：行程规划、问道套壳、真下单、自训模型。

数据流见 `docs/数据流.md`。扩展见 `docs/可扩展性.md`。获奖对照见 `docs/获奖对照.md`。
