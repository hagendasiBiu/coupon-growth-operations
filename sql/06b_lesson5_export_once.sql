-- 一次性导出用于独立核验，不覆盖已有文件。文件中没有5月核销结果。
USE coupon_growth;
SELECT user_id,hist_receipts,hist_known_redemptions,hist_mature_receipts,
 hist_mature_redemptions_15d,recent7_receipts,recent30_receipts,hist_merchant_count,
 hist_mean_distance_code,last_receipt_date,last_known_redemption_date,
 latest_mature_received_date,feature_asof,hist_mature_redemption_rate,
 days_since_last_receipt,days_since_last_known_redemption
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson5_features_20160501_v2.csv'
CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM user_features_asof_20160501 ORDER BY user_id;

SELECT has_history,COUNT(*) AS may_receipts,COUNT(DISTINCT user_id) AS may_users
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson5_coverage_20160501.csv'
CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' LINES TERMINATED BY '\n'
FROM v_may_receipt_features GROUP BY has_history ORDER BY has_history;
