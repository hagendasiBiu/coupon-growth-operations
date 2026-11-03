-- 第七课 / Step 8：按时间构建预测样本。特征仅使用各月1日零点之前的事件。
USE coupon_growth;

CREATE OR REPLACE VIEW v_model_history_events AS
SELECT s.feature_asof,t.user_id,t.merchant_id,t.received_date,t.distance_code,
 CASE WHEN t.days_to_redeem>=0
       AND DATE_ADD(t.received_date,INTERVAL t.days_to_redeem DAY)<s.feature_asof
      THEN DATE_ADD(t.received_date,INTERVAL t.days_to_redeem DAY) END AS known_consumed_date,
 CASE WHEN DATE_ADD(t.received_date,INTERVAL 15 DAY)<s.feature_asof THEN 1 ELSE 0 END AS mature
FROM o2o_analysis_20160630 t
JOIN (SELECT DATE('2016-03-01') AS feature_asof
      UNION ALL SELECT DATE('2016-04-01')
      UNION ALL SELECT DATE('2016-05-01')
      UNION ALL SELECT DATE('2016-06-01')) s
ON t.received_date<s.feature_asof;

CREATE TABLE IF NOT EXISTS model_user_features_v1
(feature_asof DATE NOT NULL,user_id VARCHAR(32) NOT NULL,PRIMARY KEY(feature_asof,user_id))
AS SELECT a.*,
 ROUND(1.00000000*hist_mature_redemptions_15d/NULLIF(hist_mature_receipts,0),6) AS hist_mature_redemption_rate,
 DATEDIFF(feature_asof,last_receipt_date) AS days_since_last_receipt,
 DATEDIFF(feature_asof,last_known_redemption_date) AS days_since_last_known_redemption
FROM (
 SELECT feature_asof,user_id,COUNT(*) AS hist_receipts,
 COUNT(known_consumed_date) AS hist_known_redemptions,SUM(mature) AS hist_mature_receipts,
 SUM(CASE WHEN mature=1 AND DATEDIFF(known_consumed_date,received_date) BETWEEN 0 AND 15 THEN 1 ELSE 0 END)
     AS hist_mature_redemptions_15d,
 SUM(CASE WHEN received_date>=DATE_SUB(feature_asof,INTERVAL 7 DAY) THEN 1 ELSE 0 END) AS recent7_receipts,
 SUM(CASE WHEN received_date>=DATE_SUB(feature_asof,INTERVAL 30 DAY) THEN 1 ELSE 0 END) AS recent30_receipts,
 COUNT(DISTINCT merchant_id) AS hist_merchant_count,
 ROUND(AVG(CAST(distance_code AS DECIMAL(12,6))),6) AS hist_mean_distance_code,
 MAX(received_date) AS last_receipt_date,MAX(known_consumed_date) AS last_known_redemption_date
 FROM v_model_history_events GROUP BY feature_asof,user_id
) a;

-- 每月上半月作为目标记录；月中后半段作为标签观察间隔，不随机拆行。
CREATE TABLE IF NOT EXISTS model_samples_v1
(row_id BIGINT UNSIGNED NOT NULL PRIMARY KEY)
AS SELECT t.row_id,t.user_id,t.merchant_id,t.coupon_id,
 CAST(DATE_FORMAT(t.received_date,'%Y-%m-01') AS DATE) AS feature_asof,t.received_date,
 CASE WHEN t.received_date<'2016-05-01' THEN 'train'
      WHEN t.received_date<'2016-06-01' THEN 'validation' ELSE 'test' END AS split,
 t.discount_type,t.min_spend,t.nominal_discount_fraction,t.distance_code,
 WEEKDAY(t.received_date)+1 AS received_weekday,
 CASE WHEN f.user_id IS NULL THEN 0 ELSE 1 END AS has_history,
 COALESCE(f.hist_receipts,0) AS hist_receipts,
 COALESCE(f.hist_known_redemptions,0) AS hist_known_redemptions,
 COALESCE(f.hist_mature_receipts,0) AS hist_mature_receipts,
 COALESCE(f.hist_mature_redemptions_15d,0) AS hist_mature_redemptions_15d,
 f.hist_mature_redemption_rate,COALESCE(f.recent7_receipts,0) AS recent7_receipts,
 COALESCE(f.recent30_receipts,0) AS recent30_receipts,
 COALESCE(f.hist_merchant_count,0) AS hist_merchant_count,f.hist_mean_distance_code,
 f.days_since_last_receipt,f.days_since_last_known_redemption,
 t.redeemed_15d AS y
FROM o2o_analysis_20160630 t
LEFT JOIN model_user_features_v1 f ON t.user_id=f.user_id
 AND f.feature_asof=CAST(DATE_FORMAT(t.received_date,'%Y-%m-01') AS DATE)
WHERE t.received_date>='2016-03-01' AND t.received_date<='2016-06-15'
 AND DAYOFMONTH(t.received_date)<=15;

SELECT split,COUNT(*) AS records,COUNT(DISTINCT user_id) AS users,
 MIN(received_date) AS first_received,MAX(received_date) AS last_received,
 MAX(DATE_ADD(received_date,INTERVAL 15 DAY)) AS last_label_observation_day
FROM model_samples_v1 GROUP BY split ORDER BY MIN(received_date);

SELECT feature_asof,COUNT(*) AS history_users,
 SUM(last_receipt_date>=feature_asof OR last_known_redemption_date>=feature_asof) AS invalid_time_rows
FROM model_user_features_v1 GROUP BY feature_asof ORDER BY feature_asof;

-- 这里只展示训练集标签分布；验证、测试的模型效果留到Step 9。
SELECT y,COUNT(*) AS train_records FROM model_samples_v1 WHERE split='train' GROUP BY y ORDER BY y;
