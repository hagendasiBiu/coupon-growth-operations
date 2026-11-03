-- 第三课 / 原方案 Step 4：建立统一指标口径。只查询，可重复执行。
-- 覆盖范围：质量检查通过、领取后 15 天观察窗口完整的领券记录。
-- 本文件保留原始记录口径，不直接去重相同业务字段。
USE coupon_growth;

-- COUNT(*) 数记录，COUNT(DISTINCT user_id) 数用户，两者不能混用。
-- CASE WHEN 仅保留满足条件的值；AVG 自动忽略 NULL。
-- NULLIF(分母,0) 避免除零；百分比乘 100，保留四位小数。
-- 100保留足够小数位，避免MySQL中间除法精度不足造成二次舍入。
SELECT
 COUNT(*) AS eligible_receipt_records,
 SUM(redeemed_15d) AS redeemed_records_15d,
 ROUND(100.00000000*SUM(redeemed_15d)/NULLIF(COUNT(*),0),4) AS redemption_rate_pct,
 COUNT(DISTINCT user_id) AS receiving_users,
 COUNT(DISTINCT CASE WHEN redeemed_15d=1 THEN user_id END) AS redeeming_users_15d,
 ROUND(100.00000000*COUNT(DISTINCT CASE WHEN redeemed_15d=1 THEN user_id END)
       /NULLIF(COUNT(DISTINCT user_id),0),4) AS user_redemption_rate_pct,
 ROUND(AVG(CASE WHEN redeemed_15d=1 THEN days_to_redeem END),4) AS avg_days_to_redeem,
 ROUND(COUNT(*)*1.0/NULLIF(COUNT(DISTINCT user_id),0),4) AS avg_receipts_per_user
FROM v_o2o_labeled
WHERE label_observable=1;

-- 核心定义：仅是历史行为基线，不能把核销数当作营销新增订单数。
SELECT 'redemption_rate_pct' AS metric,
       '15天核销记录数 / 可观察领券记录数 × 100%' AS definition
UNION ALL SELECT 'user_redemption_rate_pct','15天内至少核销一次的用户数 / 领券用户数 × 100%'
UNION ALL SELECT 'avg_days_to_redeem','仅对15天内核销记录计算平均核销间隔'
UNION ALL SELECT 'avg_receipts_per_user','可观察领券记录数 / 去重领券用户数';
