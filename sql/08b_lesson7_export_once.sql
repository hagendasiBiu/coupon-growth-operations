-- 一次性导出，包含模型标签；不得把标签、ID和审计日期放入X。
USE coupon_growth;
SELECT row_id,user_id,merchant_id,coupon_id,feature_asof,received_date,split,
 discount_type,min_spend,nominal_discount_fraction,distance_code,received_weekday,has_history,
 hist_receipts,hist_known_redemptions,hist_mature_receipts,hist_mature_redemptions_15d,
 hist_mature_redemption_rate,recent7_receipts,recent30_receipts,hist_merchant_count,
 hist_mean_distance_code,days_since_last_receipt,days_since_last_known_redemption,y
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson7_model_samples_v1.csv'
CHARACTER SET utf8mb4 FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' LINES TERMINATED BY '\n'
FROM model_samples_v1 ORDER BY received_date,row_id;
