-- 第五课 / Step 6：固定2016-05-01零点的历史画像，只使用此前可知的信息。
USE coupon_growth;

-- 全期快照包含未来消费日期，因此必须先屏蔽05-01及之后的消费。
-- 没有行为日志的到达时间，只能按事件日期模拟“当时可知”，此限制在报告中披露。
CREATE OR REPLACE VIEW v_o2o_history_before_20160501 AS
SELECT row_id,user_id,merchant_id,received_date,distance_code,
 CASE WHEN days_to_redeem>=0
       AND DATE_ADD(received_date,INTERVAL days_to_redeem DAY)<'2016-05-01'
      THEN DATE_ADD(received_date,INTERVAL days_to_redeem DAY) END AS known_consumed_date,
 CASE WHEN DATE_ADD(received_date,INTERVAL 15 DAY)<'2016-05-01'
      THEN 1 ELSE 0 END AS is_mature_receipt
FROM o2o_analysis_20160630
WHERE received_date<'2016-05-01';

-- user_id为主键，保证每位用户仅一行，也保证下一步连接不会放大领券记录。
-- 固定快照，已存在时不重新写入；更改历史口径后需建立新版本，不复用旧结果。
CREATE TABLE IF NOT EXISTS user_features_asof_20160501
(user_id VARCHAR(32) NOT NULL PRIMARY KEY)
AS
SELECT a.*,DATE('2016-05-01') AS feature_asof,
 ROUND(1.00000000*hist_mature_redemptions_15d/NULLIF(hist_mature_receipts,0),6)
   AS hist_mature_redemption_rate,
 DATEDIFF('2016-05-01',last_receipt_date) AS days_since_last_receipt,
 DATEDIFF('2016-05-01',last_known_redemption_date) AS days_since_last_known_redemption
FROM (
 SELECT user_id,COUNT(*) AS hist_receipts,
  COUNT(known_consumed_date) AS hist_known_redemptions,
  SUM(is_mature_receipt) AS hist_mature_receipts,
  SUM(CASE WHEN is_mature_receipt=1
                 AND DATEDIFF(known_consumed_date,received_date) BETWEEN 0 AND 15
           THEN 1 ELSE 0 END) AS hist_mature_redemptions_15d,
  SUM(CASE WHEN received_date>='2016-04-24' THEN 1 ELSE 0 END) AS recent7_receipts,
  SUM(CASE WHEN received_date>='2016-04-01' THEN 1 ELSE 0 END) AS recent30_receipts,
  COUNT(DISTINCT merchant_id) AS hist_merchant_count,
  ROUND(AVG(CAST(distance_code AS DECIMAL(12,6))),6) AS hist_mean_distance_code,
  MAX(received_date) AS last_receipt_date,
  MAX(known_consumed_date) AS last_known_redemption_date,
  MAX(CASE WHEN is_mature_receipt=1 THEN received_date END) AS latest_mature_received_date
 FROM v_o2o_history_before_20160501 WHERE user_id IS NOT NULL GROUP BY user_id
) a;

-- 5月领券记录用于离线回看，画像冻结在05-01；5月新出现的用户用has_history标记。
-- 5月用户名单是离线分析样本，不宣称05-01已预知谁将领券。
-- 本课不做预测；target_redeemed_15d是未来结果，后续绝不能放入模型X。
CREATE OR REPLACE VIEW v_may_receipt_features AS
SELECT t.row_id AS target_row_id,t.user_id,t.merchant_id,t.coupon_id,
 t.received_date AS target_received_date,t.discount_type,t.min_spend,
 t.nominal_discount_fraction,t.distance_code,
 DATE('2016-05-01') AS feature_asof,
 CASE WHEN f.user_id IS NULL THEN 0 ELSE 1 END AS has_history,
 COALESCE(f.hist_receipts,0) AS hist_receipts,
 COALESCE(f.hist_known_redemptions,0) AS hist_known_redemptions,
 COALESCE(f.hist_mature_receipts,0) AS hist_mature_receipts,
 COALESCE(f.hist_mature_redemptions_15d,0) AS hist_mature_redemptions_15d,
 f.hist_mature_redemption_rate,
 COALESCE(f.recent7_receipts,0) AS recent7_receipts,
 COALESCE(f.recent30_receipts,0) AS recent30_receipts,
 COALESCE(f.hist_merchant_count,0) AS hist_merchant_count,
 f.hist_mean_distance_code,f.days_since_last_receipt,
 f.days_since_last_known_redemption,
 t.redeemed_15d AS target_redeemed_15d
FROM o2o_analysis_20160630 t LEFT JOIN user_features_asof_20160501 f ON t.user_id=f.user_id
WHERE t.received_date>='2016-05-01' AND t.received_date<'2016-06-01';

-- 历史日期、计数和成熟核销率的验收。
SELECT COUNT(*) AS history_users,SUM(hist_receipts) AS history_receipts,
 SUM(hist_known_redemptions) AS known_redemptions,
 SUM(hist_mature_receipts) AS mature_receipts,
 SUM(hist_mature_redemptions_15d) AS mature_redemptions_15d,
 MAX(last_receipt_date) AS latest_receipt,
 MAX(last_known_redemption_date) AS latest_known_redemption,
 MAX(latest_mature_received_date) AS latest_mature_receipt,
 SUM(hist_mature_receipts=0) AS users_without_mature_receipts,
 SUM(last_receipt_date>='2016-05-01'
     OR last_known_redemption_date>='2016-05-01'
     OR hist_mature_redemptions_15d>hist_mature_receipts
     OR recent7_receipts>recent30_receipts
     OR recent30_receipts>hist_receipts) AS invalid_feature_rows
FROM user_features_asof_20160501;

SELECT has_history,COUNT(*) AS may_receipts,COUNT(DISTINCT user_id) AS may_users
FROM v_may_receipt_features GROUP BY has_history ORDER BY has_history;

SELECT * FROM user_features_asof_20160501 ORDER BY user_id LIMIT 15;
