# 原始字段字典（第一课）

2026-10-26：根据实际下载 CSV 表头核验，数据库原始层全部保留文本。

## O2O：o2o_offline_raw
| 字段 | 含义 | 使用注意 |
|---|---|---|
| row_id | 本地自动生成的记录号 | 不是原始用户 ID |
| User_id | 用户 ID | 同一用户可有多条记录 |
| Merchant_id | 商家 ID | 类别标识 |
| Coupon_id | 优惠券 ID | 文本 null 需清洗，不是随机对照标识 |
| Discount_rate | 折扣或满减表达式 | 面额不等于平台实际承担成本 |
| Distance | 距离编码 | 单位及边界待天池原说明核对 |
| Date_received | 领取日期文本 | 不等于发券日期 |
| Date | 消费日期文本 | 需区分有券核销和无券消费 |

## Hillstrom：hillstrom_raw
| 字段 | 含义 | 时序 |
|---|---|---|
| row_id | 本地行标识 | 不是 O2O 用户标识 |
| recency | 距上次购买月数 | 干预前 |
| history_segment | 历史消费分档 | 干预前 |
| history | 历史消费金额 | 干预前 |
| mens / womens | 历史购买男装/女装标志 | 干预前 |
| zip_code | 城乡区域类别 | 干预前；实际数据有 Surburban 拼写 |
| newbie | 新客户标志 | 干预前 |
| channel | 历史购买渠道 | 干预前 |
| segment | 随机邮件实验分组 | 处理分配 |
| visit | 后续访问标志 | 干预后，仅作结果 |
| conversion | 后续购买标志 | 干预后，仅作结果 |
| spend | 后续消费金额 | 干预后收入，非利润 |

随机实验及字段语义依据作者原始说明：https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html
O2O 具体缺失组合和日期范围在下一课审计，不预设缺失代表真实未购买。
