-- 第一课查看入口：只查询，可重复执行。打开后 Ctrl+Shift+Enter 执行全部。
USE coupon_growth;

-- 1. 确认环境：SELECT 是查询，VERSION() 返回服务端版本。
SELECT VERSION() AS mysql_version, DATABASE() AS current_database;

-- 2. 验收总行数。COUNT(*) 统计记录，UNION ALL 将两个结果并排放到同一张表。
SELECT 'O2O' AS dataset, COUNT(*) AS actual_rows, 1754884 AS expected_rows,
       COUNT(*) = 1754884 AS passed
FROM o2o_offline_raw
UNION ALL
SELECT 'Hillstrom', COUNT(*), 64000, COUNT(*) = 64000 FROM hillstrom_raw;

-- 3. 认识原始数据：LIMIT 只显示少量行，ORDER BY 保证展示顺序稳定。
SELECT * FROM o2o_offline_raw ORDER BY row_id LIMIT 10;
SELECT * FROM hillstrom_raw ORDER BY row_id LIMIT 10;

-- 4. 认识实验分组；仅统计人数，本课不解释效果。
SELECT segment, COUNT(*) AS users
FROM hillstrom_raw GROUP BY segment ORDER BY segment;

-- 5. 检查导入类型。raw 表为原始层，先保留字符串，下一课再转换日期和缺失值。
DESCRIBE o2o_offline_raw;
DESCRIBE hillstrom_raw;
