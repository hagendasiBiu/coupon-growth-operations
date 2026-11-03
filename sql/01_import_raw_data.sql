-- 第一课：原始数据入库。已执行成功后不要重复运行此文件。
-- 原始字段先保留为文本，null 字符串及日期转换留到下一课。
CREATE DATABASE IF NOT EXISTS coupon_growth CHARACTER SET utf8mb4;
USE coupon_growth;

-- 不使用 IF NOT EXISTS：已有表时明确报错，防止误以为可以重复导入。
CREATE TABLE o2o_offline_raw (
    row_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    User_id VARCHAR(32), Merchant_id VARCHAR(32), Coupon_id VARCHAR(32),
    Discount_rate VARCHAR(32), Distance VARCHAR(32),
    Date_received VARCHAR(16), `Date` VARCHAR(16)
) ENGINE=InnoDB;

LOAD DATA INFILE 'D:/MySQL_data/Uploads/coupon_project_o2o_85ed49fd.csv'
INTO TABLE o2o_offline_raw
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\r\n'
IGNORE 1 LINES
(User_id, Merchant_id, Coupon_id, Discount_rate, Distance, Date_received, `Date`);
SHOW WARNINGS;

CREATE TABLE hillstrom_raw (
    row_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    recency VARCHAR(32), history_segment VARCHAR(64), `history` VARCHAR(32),
    mens VARCHAR(8), womens VARCHAR(8), zip_code VARCHAR(32), newbie VARCHAR(8),
    channel VARCHAR(32), segment VARCHAR(32), visit VARCHAR(8),
    conversion VARCHAR(8), spend VARCHAR(32)
) ENGINE=InnoDB;

LOAD DATA INFILE 'D:/MySQL_data/Uploads/coupon_project_hillstrom_0e589332.csv'
INTO TABLE hillstrom_raw
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY ''
LINES TERMINATED BY '\r\n'
IGNORE 1 LINES
(recency, history_segment, `history`, mens, womens, zip_code, newbie,
 channel, segment, visit, conversion, spend);
SHOW WARNINGS;

SELECT 'o2o_offline_raw' AS dataset, COUNT(*) AS actual_rows, 1754884 AS expected_rows
FROM o2o_offline_raw
UNION ALL
SELECT 'hillstrom_raw', COUNT(*), 64000 FROM hillstrom_raw;
