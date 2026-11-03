-- 第四课 / Step 5：优惠券使用规律。先生成固定数据快照，避免每次重复解析百万条记录。
USE coupon_growth;

-- 快照对应原文件 SHA256 85ed49fd...，观察截至2016-06-30。
-- IF NOT EXISTS 防止重复插入；若日后原始数据/清洗规则变化，需显式建立新版本快照。
CREATE TABLE IF NOT EXISTS o2o_analysis_20160630 AS
SELECT row_id,user_id,merchant_id,coupon_id,discount_type,min_spend,
       nominal_discount_fraction,distance_code,received_date,
       days_to_redeem,redeemed_15d
FROM v_o2o_labeled WHERE label_observable=1;

-- 每行复制到各个分析维度，GROUP BY 后得到各组领券量与核销量。
-- 使用距离编码，不将编码擅自解释为精确公里数。
CREATE TABLE IF NOT EXISTS lesson4_behavior_summary AS
SELECT dimension,bucket,COUNT(*) AS receipts,SUM(redeemed_15d) AS redemptions,
       ROUND(100.00000000*SUM(redeemed_15d)/COUNT(*),4) AS rate_pct
FROM (
 SELECT 'discount_type' AS dimension,discount_type AS bucket,redeemed_15d
 FROM o2o_analysis_20160630
 UNION ALL
 SELECT 'discount_band',CASE
  WHEN nominal_discount_fraction IS NULL THEN 'unknown'
  WHEN nominal_discount_fraction<=0.10 THEN '01_0_to_10pct'
  WHEN nominal_discount_fraction<=0.20 THEN '02_10_to_20pct'
  WHEN nominal_discount_fraction<=0.30 THEN '03_20_to_30pct'
  WHEN nominal_discount_fraction<=0.50 THEN '04_30_to_50pct'
  ELSE '05_over_50pct' END,redeemed_15d FROM o2o_analysis_20160630
 UNION ALL
 SELECT 'distance_band',CASE
  WHEN distance_code IS NULL THEN '07_unknown'
  WHEN distance_code=0 THEN '01_code_0'
  WHEN distance_code=1 THEN '02_code_1'
  WHEN distance_code<=3 THEN '03_code_2_3'
  WHEN distance_code<=5 THEN '04_code_4_5'
  ELSE '05_code_6_10' END,redeemed_15d FROM o2o_analysis_20160630
 UNION ALL
 SELECT 'month',DATE_FORMAT(received_date,'%Y-%m'),redeemed_15d FROM o2o_analysis_20160630
 UNION ALL
 SELECT 'weekday',CAST(WEEKDAY(received_date)+1 AS CHAR),redeemed_15d FROM o2o_analysis_20160630
 UNION ALL
 SELECT 'merchant',merchant_id,redeemed_15d FROM o2o_analysis_20160630
) dimensional GROUP BY dimension,bucket;

-- 验收：每个维度分组总量都应等于整体，不能漏掉距离缺失组。
SELECT dimension,SUM(receipts) AS receipts,SUM(redemptions) AS redemptions,
       SUM(receipts)=1053282 AND SUM(redemptions)=64395 AS passed
FROM lesson4_behavior_summary GROUP BY dimension ORDER BY dimension;

SELECT * FROM lesson4_behavior_summary WHERE dimension<>'merchant'
ORDER BY dimension,bucket;

-- 防止小样本高核销率霸榜：先限定至少1000条领券记录，再显示前10商家。
-- 只是探索性排名，不代表可因果解释的商家营销能力。
SELECT * FROM lesson4_behavior_summary WHERE dimension='merchant' AND receipts>=1000
ORDER BY rate_pct DESC,receipts DESC,bucket LIMIT 10;

-- 折扣内看距离：用同类型券进行简单分层，观察总体差异是否仍有研究价值。
-- 仍不能控制所有用户/商家差异，不是因果结论。
SELECT discount_type,CASE WHEN distance_code=0 THEN 'code_0'
                        WHEN distance_code IS NULL THEN 'unknown' ELSE 'code_1_10' END AS distance_group,
       COUNT(*) AS receipts,SUM(redeemed_15d) AS redemptions,
       ROUND(100.00000000*SUM(redeemed_15d)/COUNT(*),4) AS rate_pct
FROM o2o_analysis_20160630 GROUP BY discount_type,distance_group
ORDER BY discount_type,distance_group;
