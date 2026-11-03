-- 第二课：O2O 清洗与 15 天核销标签。可重复执行，只创建/更新本项目视图。
-- raw 原始表保留。重复行为先标记审计，不凭字段相同就删除真实领券记录。
USE coupon_growth;

-- A. 原始文本标准化：NULLIF 把文本 null/空串转为 SQL NULL。
CREATE OR REPLACE VIEW v_o2o_normalized AS
SELECT row_id,
 NULLIF(NULLIF(TRIM(User_id),'null'),'') AS user_id,
 NULLIF(NULLIF(TRIM(Merchant_id),'null'),'') AS merchant_id,
 NULLIF(NULLIF(TRIM(Coupon_id),'null'),'') AS coupon_id,
 NULLIF(NULLIF(TRIM(Discount_rate),'null'),'') AS discount_text,
 NULLIF(NULLIF(TRIM(Distance),'null'),'') AS distance_text,
 NULLIF(NULLIF(TRIM(Date_received),'null'),'') AS received_text,
 NULLIF(NULLIF(TRIM(`Date`),'null'),'') AS consumed_text
FROM o2o_offline_raw;

-- B. 转日期、识别折扣类型。文件日期已在入库前独立校验为有效日历日期。
-- 保留 ID 的文本类型，ID 用于关联，不用于数学运算。
CREATE OR REPLACE VIEW v_o2o_typed AS
SELECT n.*,
 CASE WHEN received_text REGEXP '^[0-9]{8}$'
      THEN STR_TO_DATE(received_text,'%Y%m%d') END AS received_date,
 CASE WHEN consumed_text REGEXP '^[0-9]{8}$'
      THEN STR_TO_DATE(consumed_text,'%Y%m%d') END AS consumed_date,
 CASE WHEN distance_text REGEXP '^[0-9]+$'
      THEN CAST(distance_text AS UNSIGNED) END AS distance_code,
 CASE WHEN discount_text IS NULL THEN 'no_coupon_discount'
      WHEN discount_text REGEXP '^[0-9]+:[0-9]+$' THEN 'threshold'
      WHEN discount_text REGEXP '^(0[.][0-9]+|1([.]0+)?)$' THEN 'rate'
      ELSE 'invalid' END AS discount_type,
 CASE WHEN discount_text REGEXP '^[0-9]+:[0-9]+$'
      THEN CAST(SUBSTRING_INDEX(discount_text,':',1) AS DECIMAL(12,2)) END AS min_spend,
 CASE WHEN discount_text REGEXP '^[0-9]+:[0-9]+$'
      THEN CAST(SUBSTRING_INDEX(discount_text,':',-1) AS DECIMAL(12,2)) END AS reduction_amount,
 CASE WHEN discount_text REGEXP '^(0[.][0-9]+|1([.]0+)?)$'
      THEN CAST(discount_text AS DECIMAL(10,6)) END AS pay_rate
FROM v_o2o_normalized n;

-- C. 业务字段和异常标志；DATEDIFF 计算消费日与领取日间隔。
CREATE OR REPLACE VIEW v_o2o_clean AS
SELECT t.*,
 CASE WHEN coupon_id IS NOT NULL AND received_date IS NOT NULL THEN 1 ELSE 0 END AS is_coupon_receipt,
 DATEDIFF(consumed_date,received_date) AS days_to_redeem,
 CASE WHEN discount_type='threshold' AND min_spend>0
      AND reduction_amount>0 AND reduction_amount<=min_spend
      THEN ROUND(reduction_amount/min_spend,6)
      WHEN discount_type='rate' AND pay_rate>0 AND pay_rate<=1
      THEN 1-pay_rate END AS nominal_discount_fraction,
 CASE WHEN (received_text IS NOT NULL AND received_date IS NULL)
        OR (consumed_text IS NOT NULL AND consumed_date IS NULL)
        OR (consumed_date<received_date)
        OR (coupon_id IS NOT NULL AND received_date IS NULL)
        OR (received_date IS NOT NULL AND coupon_id IS NULL)
        OR discount_type='invalid'
        OR (distance_text IS NOT NULL AND (distance_code IS NULL OR distance_code>10))
        OR (coupon_id IS NOT NULL AND discount_text IS NULL)
        OR (discount_type='threshold' AND
            (min_spend<=0 OR reduction_amount<=0 OR reduction_amount>min_spend))
        OR (discount_type='rate' AND pay_rate<=0)
      THEN 1 ELSE 0 END AS quality_issue
FROM v_o2o_typed t;

-- D. 观察窗口。不能用每次运行时的今天作为历史标签截止日。
-- 2016-06-30 为本文件分析所采用的观察截止日；最大交易日与之相符，
-- 不代表单靠最大日期就证明事件采集完整，仍受源数据覆盖范围约束。
CREATE OR REPLACE VIEW v_o2o_labeled AS
SELECT c.*,
 DATE('2016-06-30') AS observation_end,
 CASE WHEN is_coupon_receipt=1 AND quality_issue=0
           AND DATE_ADD(received_date,INTERVAL 15 DAY)<=DATE('2016-06-30')
      THEN 1 ELSE 0 END AS label_observable,
 CASE WHEN is_coupon_receipt=0 OR quality_issue=1 THEN NULL
      WHEN DATE_ADD(received_date,INTERVAL 15 DAY)>DATE('2016-06-30') THEN NULL
      WHEN days_to_redeem BETWEEN 0 AND 15 THEN 1
      ELSE 0 END AS redeemed_15d
FROM v_o2o_clean c;

-- E. 验收：视图行数应与原表一致，不能因为清洗丢掉未知含义的记录。
SELECT 'raw' AS layer, COUNT(*) AS row_count FROM o2o_offline_raw
UNION ALL SELECT 'labeled',COUNT(*) FROM v_o2o_labeled;

SELECT MIN(received_date) AS first_received,MAX(received_date) AS last_received,
       MIN(consumed_date) AS first_consumed,MAX(consumed_date) AS last_consumed,
       SUM(quality_issue) AS quality_issue_rows,
       SUM(is_coupon_receipt) AS coupon_receipts,
       SUM(label_observable) AS observable_receipts,
       SUM(redeemed_15d=1) AS redeemed_within_15d
FROM v_o2o_labeled;

-- F. 重复审计：相同字段可能是多张同券，缺乏原始记录 ID 时不贸然删除。
SELECT COUNT(*) AS duplicate_groups,SUM(record_count-1) AS extra_identical_rows
FROM (
 SELECT COUNT(*) AS record_count
 FROM o2o_offline_raw
 GROUP BY User_id,Merchant_id,Coupon_id,Discount_rate,Distance,Date_received,`Date`
 HAVING COUNT(*)>1
) d;

-- G. 查看样本和标签分布，不在本课把核销解释为增量效果。
SELECT row_id,user_id,coupon_id,discount_text,discount_type,
       min_spend,reduction_amount,pay_rate,nominal_discount_fraction,
       received_date,consumed_date,days_to_redeem,label_observable,redeemed_15d
FROM v_o2o_labeled WHERE is_coupon_receipt=1 ORDER BY row_id LIMIT 20;

SELECT label_observable,redeemed_15d,COUNT(*) AS records
FROM v_o2o_labeled GROUP BY label_observable,redeemed_15d
ORDER BY label_observable,redeemed_15d;
