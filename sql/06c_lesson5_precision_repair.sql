-- 首次执行核验发现AVG整数的中间小数精度不足，修正本项目派生字段。
-- 原始表不变；主脚本已同步修正，新建画像时无需此补丁。
USE coupon_growth;
ALTER TABLE user_features_asof_20160501
MODIFY COLUMN hist_mean_distance_code DECIMAL(16,6) NULL;
UPDATE user_features_asof_20160501 f
JOIN (
 SELECT user_id,ROUND(AVG(CAST(distance_code AS DECIMAL(12,6))),6) AS mean_code
 FROM v_o2o_history_before_20160501 GROUP BY user_id
) d ON f.user_id=d.user_id
SET f.hist_mean_distance_code=d.mean_code;

SELECT user_id,hist_receipts,hist_known_redemptions,hist_mature_receipts,
 hist_mature_redemptions_15d,recent7_receipts,recent30_receipts,hist_merchant_count,
 hist_mean_distance_code,last_receipt_date,last_known_redemption_date,
 latest_mature_received_date,feature_asof,hist_mature_redemption_rate,
 days_since_last_receipt,days_since_last_known_redemption
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson5_features_20160501_v2.csv'
CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM user_features_asof_20160501 ORDER BY user_id;
