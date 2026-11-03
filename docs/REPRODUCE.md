# 复现说明

## 无原始数据：核对汇总结果

使用Python 3.10或以上执行`python scripts/check_public_results.py`，无需安装第三方库。
此检查验证公开表的计数、随机期望与假设标记，不等同于重新计算原始数据。

## 完整重跑

本项目实际使用Python 3.13和MySQL；当时的Python包版本见`requirements-operations.txt`。
原始数据获取入口、第三方镜像与SHA256见`docs/data_sources.md`及`docs/o2o_download_manifest.json`。
仓库不再分发原始数据或逐用户记录，完整重跑需要取得相同输入并遵守原来源条款。

1. 将O2O文件放到`data/raw/o2o/ccf_offline_stage1_train.csv`，Hillstrom文件放到`data/raw/hillstrom/hillstrom.csv`。
2. 创建虚拟环境并执行`python -m pip install -r requirements-operations.txt`。
3. 按顺序运行`sql/01_import_raw_data.sql`至`sql/08_lesson7_model_samples.sql`。带b/c后缀的文件是导出或历史修复辅助，先阅读文件开头，不要无差别重复运行所有文件。
4. SQL的`LOAD DATA INFILE`和`INTO OUTFILE`路径须改为本机MySQL的`secure_file_priv`允许目录。SQL建表和导出语句并非全部幂等，建议使用独立数据库，已有结果时不要重复导入。
5. Python早期核验脚本中的`D:/MySQL_data/Uploads/`是原执行环境的导出位置；须相应改成本机目录。运行`lesson4_behavior_report.py`、`lesson5_verify_features.py`、`lesson6_segment_report.py`和`lesson7_prepare_model_data.py`生成并核验相关表。
6. 核验得到`data/processed/model_samples_v1.csv`后，执行：

```bash
python src/finalize_operations_project.py
python src/build_operations_deliverables.py
```

`model_samples_v1.csv`保留早期文件名，仅用于历史特征和标签。运营主线无模型训练步骤。
最终脚本会读取`lesson7_data_verification.json`中的指纹并校验输入；不同文件序列化或不同输入不能跳过校验冒用已有结果。
报告生成脚本也会产生本地面试/简历文字，这些属于本地辅助输出，未作为公开作品集发布。

## 字体与文件权限

图表默认优先使用Windows微软雅黑；其他平台需自行配置可用中文字体。
MySQL服务器导出目录需要写权限，`INTO OUTFILE`目标文件不能已存在。
仓库的聚合表是当时实际计算的快照；本地用户记录与数据文件始终保持Git忽略。
