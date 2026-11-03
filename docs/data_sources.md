# 最终数据来源记录

## O2O优惠券
- 原始赛事入口：https://tianchi.aliyun.com/competition/entrance/231593/information
- 本次下载：公开GitHub仓库zhYao07/O2O-Coupon-Forecast的赛事数据镜像，不是官方直下。
- 文件：data/raw/o2o/ccf_offline_stage1_train.csv；1754884行、7字段；行为发生于2016年。
- 下载来源、固定树/文件指纹：o2o_download_manifest.json；原始核查：download_validation.json。
- 未识别随机发券对照，无完整订单金额、毛利、平台补贴承担和触达成本。
- 原始赛事当前条款与镜像再分发许可未完全核实，不上传原始数据或逐用户派生明细。

## Hillstrom邮件实验（独立选读附录）
- 原作者说明：https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html
- 原站下载：http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv
- 文件：data/raw/hillstrom/hillstrom.csv；64000行、12字段。
- 作者2008年公开，说明随机分为男装邮件、女装邮件、无邮件三组，跟踪两周结果。具体实验日历日期未确认。
- 下载使用作者原HTTP地址，保留SHA256，但HTTP本身不提供传输真实性保证；无标准化再分发许可确认，不上传原始文件。
- 邮件结果独立分析，不作为优惠券增量证据。

本地下载与初始核查过程保存在data_sources_initial_notes.md。
模型训练不是运营版主线，也不改变两数据集的证据边界。
