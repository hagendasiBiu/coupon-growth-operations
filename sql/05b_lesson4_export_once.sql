-- 助手一次性导出结果给图表脚本使用；MySQL 不覆盖既有文件。
-- 不作为日常学习入口。已导出后再次执行会提示文件已存在。
USE coupon_growth;
SELECT dimension,bucket,receipts,redemptions,rate_pct
INTO OUTFILE 'D:/MySQL_data/Uploads/coupon_lesson4_summary_20261026.csv'
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
FROM lesson4_behavior_summary ORDER BY dimension,bucket;
