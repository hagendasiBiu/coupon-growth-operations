-- 第六课 / Step 7：历史特征分群，5月结果只作回看，不参与分组。
USE coupon_growth;

-- 阈值：成熟领券至少3条；近30天领券至少2条；历史成熟核销率至少10%。
-- 这是业务启发式规则，不是调参得到的最优策略，也不等于用户真实增量价值。
CREATE OR REPLACE VIEW v_may_segmented_receipts AS
SELECT m.*,
 CASE WHEN has_history=0 THEN '00_no_history'
      WHEN hist_mature_receipts<3 THEN '01_sparse_history'
      WHEN recent30_receipts>=2 AND hist_mature_redemption_rate>=0.10 THEN '10_active_high_response'
      WHEN recent30_receipts>=2 THEN '11_active_low_response'
      WHEN hist_mature_redemption_rate>=0.10 THEN '20_less_active_high_response'
      ELSE '21_less_active_low_response' END AS segment
FROM v_may_receipt_features m;

-- 对每个用户汇总，避免一人多条领券记录导致画像平均值被重复加权。
-- MAX取同一冻结画像的常量；5月核销数独立保存，用于事后回看。
CREATE TABLE IF NOT EXISTS may_user_segments_20160501
(user_id VARCHAR(32) NOT NULL PRIMARY KEY)
AS SELECT user_id,segment,MAX(has_history) AS has_history,
 MAX(hist_receipts) AS hist_receipts,MAX(hist_mature_receipts) AS hist_mature_receipts,
 MAX(hist_mature_redemption_rate) AS hist_mature_redemption_rate,
 MAX(recent30_receipts) AS recent30_receipts,
 MAX(days_since_last_receipt) AS days_since_last_receipt,
 COUNT(*) AS may_receipts,SUM(target_redeemed_15d) AS may_redemptions
FROM v_may_segmented_receipts GROUP BY user_id,segment;

CREATE TABLE IF NOT EXISTS lesson6_segment_summary AS
SELECT segment,COUNT(*) AS users,SUM(may_receipts) AS receipts,
 SUM(may_redemptions) AS redemptions,
 SUM(may_redemptions>0) AS redeeming_users,
 ROUND(100.00000000*SUM(may_redemptions)/SUM(may_receipts),4) AS rate_pct,
 ROUND(100.00000000*SUM(may_redemptions>0)/COUNT(*),4) AS user_rate_pct,
 ROUND(AVG(CAST(hist_receipts AS DECIMAL(16,6))),6) AS avg_hist_receipts,
 ROUND(AVG(CAST(recent30_receipts AS DECIMAL(16,6))),6) AS avg_recent30_receipts,
 ROUND(AVG(CAST(hist_mature_receipts AS DECIMAL(16,6))),6) AS avg_mature_receipts,
 ROUND(AVG(hist_mature_redemption_rate),6) AS avg_hist_response_rate
FROM may_user_segments_20160501 GROUP BY segment;

-- 只用历史字段检查阈值敏感性，不根据5月核销表现选择配置。
CREATE TABLE IF NOT EXISTS lesson6_rule_sensitivity AS
SELECT c.config,COUNT(*) AS users,
 SUM(u.has_history=0) AS no_history_users,
 SUM(u.has_history=1 AND u.hist_mature_receipts<c.min_mature) AS sparse_history_users,
 SUM(u.has_history=1 AND u.hist_mature_receipts>=c.min_mature
     AND u.recent30_receipts>=c.min_recent AND u.hist_mature_redemption_rate>=c.min_rate)
     AS active_high_response_users,
 SUM(u.segment<>CASE
      WHEN u.has_history=0 THEN '00_no_history'
      WHEN u.hist_mature_receipts<c.min_mature THEN '01_sparse_history'
      WHEN u.recent30_receipts>=c.min_recent AND u.hist_mature_redemption_rate>=c.min_rate THEN '10_active_high_response'
      WHEN u.recent30_receipts>=c.min_recent THEN '11_active_low_response'
      WHEN u.hist_mature_redemption_rate>=c.min_rate THEN '20_less_active_high_response'
      ELSE '21_less_active_low_response' END) AS changed_users
FROM may_user_segments_20160501 u
CROSS JOIN (
 SELECT 'baseline' AS config,3 AS min_mature,2 AS min_recent,0.10 AS min_rate
 UNION ALL SELECT 'min_mature_5',5,2,0.10
 UNION ALL SELECT 'min_recent_3',3,3,0.10
 UNION ALL SELECT 'min_rate_20pct',3,2,0.20
) c GROUP BY c.config;

-- 验收：用户互斥、记录不放大；分组总核销数与5月整体一致。
SELECT SUM(users) AS users,SUM(receipts) AS may_receipts,SUM(redemptions) AS may_redemptions,
 SUM(users)=148439 AND SUM(receipts)=215348 AND SUM(redemptions)=21580 AS passed
FROM lesson6_segment_summary;

SELECT * FROM lesson6_segment_summary ORDER BY segment;
SELECT * FROM lesson6_rule_sensitivity ORDER BY config;

-- 与本次5月回看人群区分：全部历史画像的群体数量，未使用5月是否领券筛选。
SELECT CASE WHEN hist_mature_receipts<3 THEN '01_sparse_history'
 WHEN recent30_receipts>=2 AND hist_mature_redemption_rate>=0.10 THEN '10_active_high_response'
 WHEN recent30_receipts>=2 THEN '11_active_low_response'
 WHEN hist_mature_redemption_rate>=0.10 THEN '20_less_active_high_response'
 ELSE '21_less_active_low_response' END AS segment,COUNT(*) AS history_users
FROM user_features_asof_20160501 GROUP BY segment ORDER BY segment;
