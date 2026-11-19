# Resume Entry & Interview Preparation

> The numbers below come from the real-data run (`outputs/INSIGHTS_REPORT.md`, 99,441 orders).
> If you change the analysis, rerun `python/run_all.py` and update them. Use only numbers you can point to in that report.

## Resume entry (Projects section, listed first)

**E-Commerce Performance & Customer Analytics: Olist Marketplace (100k orders)** | [GitHub link]
*SQL (MySQL) · Python (pandas, SciPy) · Power BI (DAX) · Statistics*

- Designed a **star schema (2 fact, 5 dimension tables)** from 8 raw tables (~100k orders, ~96k customers), and wrote **30+ SQL queries** (CTEs, window functions: LAG, NTILE, RANK, running totals) for GMV, AOV, cohort retention, RFM and seller KPIs.
- Found that only **3% of customers make a repeat purchase** and month-1 cohort retention averages **0.46%**. Segmented customers with **RFM** and identified an "At Risk High-Value" group (14.7% of customers, 27.5% of GMV) for win-back campaigns.
- Showed that **late deliveries (6.8% of orders) cut the average review from 4.29 to 2.27 stars** and make a 1-2 star review **6.7x more likely**, confirmed with Mann-Whitney U and chi-square tests (p < 0.001).
- Built a **4-page Power BI dashboard (40+ DAX measures**: YoY/MoM, rolling averages, Pareto, cohort heat-map) and reconciled every KPI against the SQL results. Recommended state-level delivery SLAs and a second-purchase programme.

**Shorter (3 bullets) when space is tight:** keep bullets 1, 3 and 4.

### Skills line to add
`SQL: CTEs, window functions, joins (MySQL, SQLite) · Power BI: DAX, Power Query, star-schema modelling · Analytics: cohort analysis, RFM segmentation, funnel/KPI design, hypothesis testing · E-commerce KPIs: GMV, AOV, retention, repeat rate, conversion`

### Honesty rules
- Call it a **personal project on a public dataset**. Never call it client or company work.
- Don't write "increased revenue by X%". You recommended actions; you didn't implement them.
- If you change the analysis, rerun the pipeline and update the numbers.

---

## The 60-second project pitch (STAR format)
**Situation:** Olist is a Brazilian marketplace with ~100k orders over two years. I wanted to understand
what drives revenue and customer satisfaction.
**Task:** build the full analysis myself, from raw data to dashboard, and end with recommendations.
**Action:** I cleaned 8 raw tables in Python and modelled them as a star schema. I answered 18 business
questions in SQL using CTEs and window functions, built cohort and RFM analyses, tested the
delivery-review relationship statistically, and built a 4-page Power BI dashboard.
**Result:** the two big findings were that only 3% of customers come back, and that late deliveries
drop reviews from 4.29 to 2.27 stars. So I recommended a second-purchase programme and state-specific
delivery promises, starting with Alagoas (21.4% late).

---

## Likely interview questions (practise aloud)

**Data and cleaning**
1. *What was the hardest data-quality issue?*
   `customer_id` vs `customer_unique_id`. With the wrong key the repeat rate shows 0%.
2. *How did you handle duplicate reviews / missing categories / zero payments?* See the data quality table in the report.
3. *Why exclude 2016 and Sep-Oct 2018 from trends?* Those months are incomplete, so they would show fake drops.

**SQL (expect live coding)**
4. Write MoM growth (`LAG`). 5. Top N per group (`RANK` / `ROW_NUMBER` in a CTE).
6. Running total and Pareto share. 7. Cohort retention with a pivot (`CASE` inside `SUM`).
8. *WHERE vs HAVING?* 9. *RANK vs DENSE_RANK vs ROW_NUMBER?* 10. *LEFT JOIN to find orphans.*

**Power BI**
11. *Why a star schema? Why two fact tables?* 12. *What does CALCULATE do?* (it changes the filter context)
13. *Why a separate Date table, and why mark it as a date table?* (time intelligence needs a continuous calendar)
14. *Calculated column vs measure?* 15. *How did you check your numbers?* (reconciled against SQL)

**Statistics and business**
16. *Why Mann-Whitney and not a t-test?* (review scores are ordinal and skewed)
17. *Your p-value is tiny. So what?* With large samples, look at the effect size: here a 6.7x relative risk and a 2-star drop.
18. *Does lateness cause bad reviews?* Not proven, because the data is observational. I would A/B test the delivery promise.
19. *If you could pick one metric for leadership to watch, which?* Repeat-customer rate, because growth is acquisition-only.
20. *How would this change for an Indian e-commerce company?* COD share, return rate, tier-2/3 city logistics, festive-season peaks.

## Certifications that support this project
1. **Google Analytics Certification** (Skillshop, free): covers "digital commerce platforms".
2. **HackerRank SQL (Advanced)** (free).
3. **Microsoft PL-300 Power BI Data Analyst** (paid; the strongest analyst signal).
