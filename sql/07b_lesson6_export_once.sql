-- 一次性导出，已导出后不要重跑。本课日常入口是07主脚本。
USE coupon_growth;
SELECT segment,users,receipts,redemptions,redeeming_users,rate_pct,user_rate_pct,
 avg_hist_receipts,avg_recent30_receipts,avg_mature_receipts,avg_hist_response_rate
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson6_summary.csv'
CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n'
FROM lesson6_segment_summary ORDER BY segment;

SELECT user_id,segment,has_history,hist_receipts,hist_mature_receipts,hist_mature_redemption_rate,
 recent30_receipts,days_since_last_receipt,may_receipts,may_redemptions
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson6_users.csv'
CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n'
FROM may_user_segments_20160501 ORDER BY user_id;

SELECT config,users,no_history_users,sparse_history_users,active_high_response_users,changed_users
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson6_sensitivity.csv'
CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n'
FROM lesson6_rule_sensitivity ORDER BY config;
