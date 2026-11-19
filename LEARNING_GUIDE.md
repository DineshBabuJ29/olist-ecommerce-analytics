# Learning Guide: Own This Project Before You Put It on Your Resume

The code works. Your job now is to understand it well enough to rebuild any part of it in an
interview without notes. Plan on **about 3 weeks at 2-3 hours a day**.
Don't add the project to your resume until you finish Week 3.

Rule for every file: **read it, run it, change something, and predict the result before you rerun.**

---

## Week 1: Data and Python (pipeline steps 1, 3, 4, 5)

### Day 1: Understand the dataset (no code yet)
- Open each raw CSV in Excel and look at 20 rows.
- Read `docs/DATA_DICTIONARY.md` and draw the table relationships on paper from memory.
- **Check yourself:** why is `customer_unique_id` different from `customer_id`? What would go
  wrong if you counted `customer_id`?

### Day 2-3: `python/s01_clean_transform.py` (ETL)
- Run it and read the printed audit (`outputs/data_quality_report.csv`).
- For every cleaning rule, write down in one line *what the problem was* and *why this fix was chosen*.
- Exercises:
  1. Change the late definition to "late by 2+ days". How does the late rate change?
  2. Count how many orders have more than one seller.
- **Concepts:** `merge` (join types), `groupby().agg()`, `drop_duplicates`, datetime `.dt`,
  `np.where`, `pd.cut`, nullable `Int64`.

### Day 4: `python/s03_eda_sales.py` (EDA and charts)
- Run it and open every chart in `outputs/figures/`.
- For each chart, write one sentence: *"This chart shows ___, which means the business should ___."*
- Exercise: add a chart of AOV by state.

### Day 5: `python/s04_customer_analytics.py` (cohorts and RFM)
- Recalculate one cohort cell by hand in Excel (pick a small cohort) and confirm it matches.
- **Check yourself:** why does F use fixed tiers instead of quintiles?
- Exercise: add a segment "Big Spenders, one order" (F = 1, M = 5).

### Day 6: `python/s05_statistical_tests.py`
- Learn: null vs alternative hypothesis, p-value, why Mann-Whitney instead of a t-test
  (ordinal, non-normal data), chi-square for two categorical variables, and effect size vs p-value
  (with 90k rows almost anything is "significant", so effect size tells you whether it matters).
- **Check yourself:** "The p-value is < 0.001. Does that prove late delivery *causes* bad reviews?"
  (No: it's observational data. Name a possible confounder, e.g. remote states have both longer
  delivery times and different products.)

### Day 7: Review
Explain the whole pipeline aloud in 3 minutes, without notes. Record yourself and listen back.

---

## Week 2: SQL (the most-tested skill for this role)

### Day 8: Set up MySQL
1. Install **MySQL Community Server 8 + MySQL Workbench** (free, from dev.mysql.com).
2. Run `sql/01_schema_mysql.sql`, then `sql/02_load_mysql.sql` (follow the notes at the top of that file).
3. Check that the row counts match the Python printout.

> Short on time? `data/olist.db` (SQLite) already has everything loaded. Open it with
> **DB Browser for SQLite** and run the same queries. The SQL is written to work in both databases.

### Day 9-13: One SQL file per day (03 to 08)
For each query:
1. Read the business question in the header comment.
2. **Cover the SQL and write your own version first.** Then compare.
3. Run it and check that the result matches `outputs/sql_results/`.

Concepts in order of interview frequency:

| Concept | Where to practise it |
|---|---|
| JOIN types, GROUP BY / HAVING | 03 orphan checks, 07 delivery_by_state |
| CASE WHEN, conditional aggregation | 05 repeat summary, 05 cohort pivot |
| CTEs (`WITH`) | almost every query |
| `SUM() OVER ()` share of total | 03 status distribution, 04 revenue_by_state |
| Running total, `ROWS BETWEEN` | 04 monthly_trend, 06 category pareto |
| `LAG` (MoM growth) | 04 monthly_trend |
| `RANK` / `DENSE_RANK` / `NTILE` | 04 state rank, 05 RFM, 06 seller deciles |
| Self-join | 04 yoy_jan_aug |

### Day 14: Timed practice
Write these from a blank page, 15 minutes each:
1. Top 5 categories by revenue in 2018, with each one's share of 2018 revenue.
2. Month-over-month order growth.
3. The % of customers whose second order came within 90 days of their first.
   (New query: use `purchase_day_num` and `LEAD()`.)

Then practise on HackerRank/LeetCode SQL (medium level) and earn the **HackerRank SQL (Advanced)** badge.

---

## Week 3: Power BI and the story

### Day 15-18: Build the dashboard
Follow `powerbi/POWERBI_BUILD_GUIDE.md` step by step. Type the DAX yourself rather than pasting
it, at least for `CALCULATE`, the time-intelligence measures and the Pareto measure.

### Day 19: Reconcile
Make sure every card on your dashboard matches `outputs/INSIGHTS_REPORT.md`. Fix any difference
and write down what caused it.

### Day 20: GitHub
1. Create a public repo, e.g. `olist-ecommerce-analytics`.
2. Push everything except raw and processed data (`.gitignore` already handles that).
3. Add the dashboard screenshots to `powerbi/screenshots/` and check that the README shows them.
4. Pin the repo on your GitHub profile.

### Day 21: Interview rehearsal
Practise the questions in `docs/RESUME_AND_INTERVIEW.md` aloud.

---

## "Do I really understand it?" checklist
- [ ] I can define GMV, AOV, repeat rate, cohort retention and late rate in one sentence each.
- [ ] I can draw the star schema and explain why there are two fact tables.
- [ ] I can write the MoM growth and Pareto queries from memory.
- [ ] I can explain why the F score uses fixed tiers.
- [ ] I can explain the p-value and the effect size, and why this isn't proof of causation.
- [ ] I can name 3 recommendations and the number behind each one.
- [ ] I know one thing I would do next with more data (e.g. an A/B test of the delivery promise).
