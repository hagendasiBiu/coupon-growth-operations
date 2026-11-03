"""用已运行的结果生成运营版报告、简历及面试材料，不操作GUI或数据库。"""
from pathlib import Path
import json,html,base64,math
import pandas as pd
from scipy.stats import norm

ROOT=Path(__file__).resolve().parents[1];R=ROOT/'reports';T=R/'tables'

def table(d):
    d=d.fillna('—')
    return '| '+' | '.join(map(str,d.columns))+' |\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join('| '+' | '.join(map(str,row))+' |' for row in d.itertuples(index=False,name=None))
def write(p,s):p.write_text(s.strip()+'\n',encoding='utf-8')
def image_data(path):return 'data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()

def main():
    result=json.loads((T/'final_operations_verification.json').read_text(encoding='utf-8'));p=result['policy']
    assert result['status']=='passed'
    seg=pd.read_csv(T/'lesson6_segment_summary.csv')
    labels={'00_no_history':'未观察到历史','01_sparse_history':'成熟历史不足',
      '10_active_high_response':'近期高活跃/历史高核销','11_active_low_response':'近期高活跃/历史低核销',
      '20_less_active_high_response':'近期低活跃/历史高核销','21_less_active_low_response':'近期低活跃/历史低核销'}
    sg=seg[['segment','users','receipts','rate_pct']].copy();sg['segment']=sg.segment.map(labels)
    sg['rate_pct']=sg.rate_pct.map(lambda v:f'{v:.2f}%');sg.columns=['5月分群','用户数','领券记录','15天记录核销率']
    roi=pd.DataFrame(result['roi_base']);roi=roi[roi.policy.eq('固定规则名单')]
    rt=roi[['incremental_share','assumed_marketing_cost','simulated_incremental_net_profit','simulated_roi']].copy()
    rt['incremental_share']=rt.incremental_share.map(lambda x:f'{x:.0%}')
    rt['assumed_marketing_cost']=rt.assumed_marketing_cost.map(lambda x:f'{x:,.0f}元')
    rt['simulated_incremental_net_profit']=rt.simulated_incremental_net_profit.map(lambda x:f'{x:,.0f}元')
    rt['simulated_roi']=rt.simulated_roi.map(lambda x:f'{x:.2%}')
    rt.columns=['假设新增比例','假设营销成本','模拟增量净收益','模拟ROI']
    rate_policy=p['policy_observed_rate']*100;rate_random=p['random_expected_rate']*100;gain=p['relative_coverage_difference']*100
    report=f'''
# 优惠券运营分析与用户分层策略
个人项目｜公开历史数据｜策略运营 / 增长运营方向｜最终运营版

## 1. 业务问题与结论
问题：优惠券资源有限时，应该先研究哪些人群、怎样分配重点和探索名额，以及如何验证是否真正值得投入？

基于1754884条O2O历史行为，建立15天记录和用户核销口径，形成39.27万历史用户画像及六类人群。
在5月实际领券用户中，89.67%没有足够的成熟历史信息，因此不宜只围绕少量高响应用户制定策略。
运营方案采用70%历史充分人群名额、30%信息不足人群探索，保留低信息用户的观察机会。

6月历史回看中，从76257位实际领券用户中各选10000人，规则名单覆盖{p['policy_observed_redemptions']}次已观测首券核销，随机名单理论期望{p['random_expected_redemptions']:.1f}次。
这是同名额下的离线筛选覆盖差异，不是新营销活动带来的新增订单或增量ROI。

## 2. 数据与指标
- O2O原始行为1754884条；可评价15天领券记录1053282条，核销64395条，记录核销率6.11%。
- 去重领券用户510698人，至少核销一次40075人，用户核销率7.85%。记录与用户口径分开。
- 相同字段额外记录37893条；缺乏独立领券流水号，当前保留，不能把它们直接视为误重复。
- 使用历史公开赛事数据，行为发生于2016年；本次下载为第三方赛事数据镜像，并非2026年平台业务。
- 原始数据和逐用户明细不作为公开项目附件再分发，来源/指纹见docs/data_sources.md等记录。

## 3. 从分析到运营人群
距离编码0和6—10组的15天记录核销率分别为11.57%与1.41%，是值得进一步研究的响应差异，未证明因果关系。
名义优惠比例(20%,30%]组核销率9.32%，(30%,50%]组7.60%；优惠比例并非简单越大越好，不能忽略门槛和人群构成。

画像只使用每个历史时点之前的行为。先单列无历史与成熟历史不足者，再对成熟领券≥3条者，按近30天领券≥2条、历史成熟核销率≥10%形成四象限。

{table(sg)}

高活跃/高历史核销组仅938人，5月记录核销率26.61%；不能把它与整体10.02%的差异表述为投放后的提升。
阈值敏感性检查显示，成熟记录门槛从3条改为5条，高活跃高核销组由938变成495人；规则有不确定性，不是唯一正确名单。

## 4. 可执行策略与次月回看
**名额规则**：每10000个名额，7000给历史充分人群、1500给成熟历史不足者、1500给未观察到历史者。
历史充分人群按“高活跃高核销 → 低活跃高核销 → 高活跃低核销 → 低活跃低核销”优先级排序。
组内按历史成熟核销率、近期领券、距上次领券天数排序，同分用固定哈希打散；不读取本次核销标签。

**回看方法**：6月1—15日实际领券用户，每人取该期间首条券，历史冻结06-01；不是05-01或06-01就预知未来领券名单。
观察首条券15天核销，保持一人一条结果，避免多次领券用户重复计数。规则在读取本次回看结果前固定，6月数据此前已做描述性EDA，因此不称为完全盲态验证。

| 对比方式 | 名单人数 | 已观测首券核销覆盖 | 覆盖比例 |
|---|---:|---:|---:|
| 随机名单理论期望 | 10000 | {p['random_expected_redemptions']:.1f} | {rate_random:.2f}% |
| 固定规则名单实际回看 | 10000 | {p['policy_observed_redemptions']} | {rate_policy:.2f}% |

相对随机期望的离线覆盖差异为{gain:.2f}%，约多覆盖539次已发生的首券核销。
200次无放回随机抽样平均覆盖{p['random_draw_mean']:.2f}次，95%抽样分位约{p['random_draw_p025']:.0f}—{p['random_draw_p975']:.0f}次；这是名单抽样波动，不是因果效果置信区间。
改写核销标签后名单不变，检查通过。当前所有指标都是已有领券样本中的回看，不是未发券用户上的发券实验。

## 5. 资源与成本：用假设表，不能编造真实ROI
比较约束是相同10000个名额，不是相同总补贴预算：更多核销也可能带来更多补贴支出。
数据没有订单毛利、实际补贴承担、触达成本及未投放对照。因此不能给出真实增量ROI。

情景假设：触达0.2元/人，核销补贴5元/次，每笔营销新增订单贡献利润30元。
额外假设θ为已观测核销中真正由营销新增的比例；θ未知，仅设0%、10%、30%、50%、100%供敏感性分析。
这些并未证明新策略实施后还会发生同样的核销，作用是说明预算判断需要什么条件。

{table(rt)}

基准假设下，规则名单营销成本7635元，θ至少约22.58%才保本；这是保本条件测算，不是识别出的真实新增比例。
共输出270组触达成本、补贴成本、贡献利润和增量比例组合，均标记为假设场景。

## 6. 验证与落地建议
优先用用户级分层A/B实验验证净贡献，而不是直接把高核销人群加大补贴。
真实上线需补齐可触达用户全集、发券/送达日志、订单与退款、实际补贴和毛利字段；实验分组先于触达，用户不得跨组。
按信息充分性和历史核销分层随机分配当前策略/规则策略，保持相同预算约束；主要指标为观察窗口内每名入组用户净贡献利润，辅以购买率、核销率和补贴成本。
方案未上线执行，详见A_B测试方案.md；不要在简历上写“已完成平台A/B测试”。

## 7. 项目完成范围与证据
已完成：清洗、指标体系、行为分析、历史画像、六类分群、规则名单次月回看、成本敏感性、实验方案、报告和简历。
模型训练保留为附加探索，不作为运营版必做项，也不写模型性能或真实业务ROI提升。
Hillstrom邮件随机实验单独做平均增量分析作为选读附录，不训练复杂Uplift模型，不把它的结果移植到优惠券业务。
本轮没有操控电脑界面、没有连接MySQL MCP；使用此前实际执行并独立核验的MySQL结果与本地原始数据。
完整证据见tables/final_operations_verification.json，后台复现见src/finalize_operations_project.py。
'''
    write(R/'运营版_最终报告.md',report)
    # 简历使用简洁且范围明确的描述，避免误读成真实投放增长。
    cv=f'''
# 简历可直接使用

**优惠券运营分析与用户分层策略｜个人项目**
工具：MySQL、Python（Pandas、可视化）｜数据：公开O2O历史营销数据

- **业务分析：** 基于175万条优惠券相关行为数据，使用SQL建立15天核销指标，从折扣、距离、时间及商家等六个维度拆解差异，形成用户分层依据。
- **用户策略：** 构建39.27万用户历史画像，对次月14.84万领券用户划分六类人群；识别信息不足群体占89.67%，设计70%重点名额与30%探索名额的分配方案。
- **策略回看：** 在后续月份7.63万名实际领券用户中进行1万名额离线回看，规则名单覆盖1127次首券核销，随机名单理论期望588次；补充成本敏感性测算与分层A/B验证方案。

## 更短版本（简历空间不足时）
- 使用SQL分析175万条公开O2O历史行为，构建39.27万用户画像和六类分群，设计兼顾历史响应与信息不足人群探索的名额分配策略。
- 在后续6月7.63万领券用户样本中进行1万名额离线回看，规则名单覆盖1127次已观测首券核销，随机名单期望588次，并提出成本敏感性分析及A/B验证方案。

## 数字怎么解释
1127和588是在同一历史样本、同样10000个名额下的观察覆盖与理论期望，离线覆盖相对差异{gain:.2f}%。
**不是新增订单、真实投放提升或因果增量。简历正文优先用1127与588的直接对比，面试时再解释计算。**
70%/30%是设计参数，不是算法证明的最优比例；270组费用表是基于假设的测算，不是真实费用或真实ROI。
这是个人公开数据项目，不能写成某平台真实任职或实际运营业绩；不必写AUC、复杂模型、Uplift或“ROI提升X%”。

代码由AI协助生成与执行，投递前应理解指标口径、规则和结果来源，能在面试中解释与复现。
'''
    write(R/'简历可直接使用.md',cv);write(R/'resume_bullets.md',cv)
    z=norm.ppf(.975)+norm.ppf(.8);n=math.ceil(2*z*z*.08*.92/(.01**2))
    ab=f'''
# 用户级分层A/B验证方案（未实施）

目的：验证规则资源分配能否改善每名入组用户的增量净贡献，区分“本来就会核销”和“因为营销才购买”。

1. 实验对象必须从真实业务可触达用户全集确定，不能事后只挑已领券用户。本项目没有该全集，上线需补齐。
2. 在触达前，按信息充分性、历史响应和必要的业务区域分层，用户级随机分配对照组（现有策略）与实验组（规则策略）。固定用户分组，不跨组重复触达。
3. 若以同总预算比较，应分别约束触达费与实际补贴支出；不能仅相同人数就宣称相同营销预算。
4. 主指标：15天每名入组用户贡献利润减实际营销成本，按所有入组用户统计（ITT），未购买者仍在分母。
5. 辅指标：购买率、核销率、每订单补贴、每核销成本；护栏：退款、投诉/退订、复购和补贴超支。
6. 每位用户观察满15天后再读数，退款等延迟结果增加7天回补，不在结果有利时提前停止。
7. 净利润样本量需要先导数据的方差、目标提升和预算，本项目不能直接给出可信的利润样本量。
8. 仅作样本量练习：如果规划基线购买率8%、希望检测绝对提升1个百分点、双侧5%显著性与80%功效，常用近似每组约{n:,}人。8%是规划假设，不是本项目证明的真实业务基线；利润指标仍需另算样本量。
9. 预先固定主要比较、指标、样本量与结束规则，报告效应及区间，不只挑P值或表现最好的人群。

本文件是设计方案，未发券、未触达用户、未在平台启动实验。不得写成“完成真实A/B测试并提升转化”。
'''
    write(R/'A_B测试方案.md',ab)
    eg=pd.DataFrame(result['email_groups']);eg['purchase_rate']=eg.purchase_rate.map(lambda x:f'{x:.4%}');eg['spend_per_user']=eg.spend_per_user.map(lambda x:f'${x:.4f}')
    eg=eg.rename(columns={'segment':'实验组','users':'人数','purchases':'购买人数','purchase_rate':'购买率','spend_per_user':'人均收入'})
    em=result['email_effects'][0]
    appendix=f'''
# 独立邮件随机实验附录（选读，不是优惠券结果）

来源：Kevin Hillstrom作者2008年公开的邮件营销实验，64000位客户随机分为男装邮件、女装邮件、无邮件三组，观察后续两周。
作者说明：https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html

{table(eg)}

预先沿用男装邮件vs无邮件作为主要比较：购买率差{em['purchase_ate_pp']:.4f}个百分点，近似95%区间[{em['purchase_ci95_low_pp']:.4f}, {em['purchase_ci95_high_pp']:.4f}]个百分点。
人均收入差${em['spend_ate_usd_per_user']:.4f}，1000次非参数bootstrap的95%区间[${em['spend_bootstrap_ci95_low']:.4f}, ${em['spend_bootstrap_ci95_high']:.4f}]。
干预前字段最大绝对标准化均值差为{result['max_email_covariate_smd']:.4f}。平衡结果本身不证明随机化，随机分配机制来自原作者说明。

女装比较为探索性附录，两个处理组各自的95%区间不是同时置信区间，不借此挑选最优人群。
真实成本与毛利缺失，因此不能计算真实邮件ROI。这里是邮件实验的平均增量，不是O2O优惠券增量；两套用户没有合并。
运营版简历主线不需要写这一附录，更不需要训练个体Uplift模型。
'''
    write(R/'独立邮件实验附录.md',appendix)
    interview=f'''
# 面试讲解：把项目讲成运营分析

## 60秒版本
我做的是一个公开数据的优惠券运营分析项目，核心问题是资源有限时怎么划分人群、分配重点和探索名额。
我先用SQL清洗175万条行为并建立15天核销指标，再用历史时点之前的数据构建39.27万用户画像。
在次月领券用户中，我发现信息不足人群占89.67%，所以没有只选高响应人群，而是保留30%探索名额。
随后在后续月份7.63万名领券用户中做1万名额离线回看，规则名单覆盖1127次已发生的首券核销，随机名单期望588次。
这个结果说明规则有历史响应识别价值，但不等于营销新增订单，所以我补充了成本敏感性和用户级A/B方案，准备验证真实增量利润。

## 常见追问
**为什么运营要训练模型？** 不必。这个项目的运营主线用SQL、规则分群和情景分析就能说明问题。早期训练模型属于附加探索，不作为主要成果。

**1127 vs 588是不是增长91.66%？** 是同一历史样本中名单覆盖的相对差异，不是业务增长。我们不知道没发券会怎样，也未实际执行新营销。

**为什么不直接把补贴都给高核销用户？** 他们可能本来就会买，高响应不等于高增量；同时大量用户历史不足，全部排除会损失探索机会。

**70%/30%为什么这样定？** 是可解释的首版资源规则，非最优值。重点是明确探索与利用的取舍，后续应通过预算约束实验评估不同配比，而不是根据一次回看选最高结果。

**6.11%、10.02%、11.27%有什么区别？** 6.11%是全期完整15天领券记录核销率；10.02%是5月全部领券记录核销率；11.27%是6月筛选10000人后每人首条券的观察覆盖比例。人群、月份、分析单位不同，不能直接串成增长曲线。

**为什么你的随机名单不是整数588？** 588.0116是无放回随机抽10000人的理论期望，等于10000×4484/76257。200次抽样平均587.38，用来校验随机波动，主比较用理论期望。

**怎么防数据泄漏？** 按事件日期截断历史，未来消费不计已知核销；成熟15天核销率只看当时窗口完整的记录；删除未来信息后画像不变，并逐字段对照原始CSV。

**为什么不写真实ROI？** 数据缺实际毛利、补贴承担和未投放对照；我只用透明假设计算保本条件，真实增量需要实验和真实财务字段。

**你做过真实平台投放吗？** 本项目没有。它是个人公开数据项目，代码有AI协助，我需要理解并能复现分析，不把个人项目说成真实任职业绩。

## 面试前只需掌握
指标分母、历史/未来边界、六类用户、70/30策略、1127与588的回看口径，以及为什么需要A/B验证增量。
不必背模型参数或复杂算法。
'''
    write(R/'面试讲解.md',interview)
    # 独立、无外部依赖的HTML，便于用户直接打开阅读。
    esc=html.escape
    body=f'''<header><div class="eyebrow">个人项目 · 公开历史数据 · 运营分析版</div><h1>优惠券运营分析<br>与用户分层策略</h1><p>从业务问题到人群策略、名额分配和验证方案。无需把模型训练作为主线。</p></header>
    <nav><a href="#findings">业务发现</a><a href="#segments">人群分层</a><a href="#policy">名单回看</a><a href="#budget">成本假设</a><a href="#validate">验证与简历</a></nav>
    <div class="cards"><div><b>175万</b><span>历史行为记录</span></div><div><b>39.27万</b><span>历史用户画像</span></div><div><b>1,127 / 588</b><span>规则覆盖 / 随机期望</span></div><div><b>30%</b><span>信息不足人群探索名额</span></div></div>
    <section id="findings"><h2>01 先找到可研究的问题</h2><p>完整15天领券记录核销率为6.11%。距离、折扣与时间存在差异，但差异不能直接解释为营销新增购买。</p><img alt="优惠券六维分析中的四个维度" src="{image_data(R/'figures/lesson4_behavior_dashboard.png')}"></section>
    <section id="segments"><h2>02 分层首先处理信息不足</h2><p>5月实际领券用户中，89.67%没有足够成熟历史。高响应小人群值得研究，但信息不足不等于低价值。</p>{sg.to_html(index=False,border=0,escape=True)}<p class="note">分群只用历史字段，5月结果只作回看；高核销不是高补贴价值。</p></section>
    <section id="policy"><h2>03 同名额下，规则能覆盖多少已观测核销？</h2><p>6月76,257名实际领券用户，每人取首条券。规则预留7,000个历史充分人群名额、1,500个历史不足名额和1,500个无历史名额。</p><img alt="规则名单历史回看" src="{image_data(R/'figures/final_policy_replay.png')}"><div class="callout">规则名单覆盖1,127次；随机名单理论期望588次。离线覆盖相对差异91.66%，<strong>不是实际投放增长</strong>。</div><p class="note">候选是事后可见的实际领券样本；比较约束是相同人数，而非相同总补贴成本。</p></section>
    <section id="budget"><h2>04 费用缺失时，只做透明假设</h2><p>假设触达0.2元/人、核销补贴5元/次、每笔营销新增订单贡献利润30元。真正由营销新增的比例未知。</p>{rt.to_html(index=False,border=0,escape=True)}<p class="note">上表全部为模拟。基准假设下，新增比例约22.58%才保本，不能将这个比例写成真实效果。</p><details><summary>查看敏感性图</summary><img alt="假设ROI敏感性" src="{image_data(R/'figures/final_roi_scenarios.png')}"></details></section>
    <section id="validate"><h2>05 用实验验证，用准确口径写简历</h2><p>下一步真实业务需补齐触达全集、发券/订单/退款和毛利字段，做用户级分层A/B；比较每名入组用户净贡献，保持总预算一致。方案已完成，尚未执行真实投放。</p><h3>简历建议</h3><ul><li>SQL分析175万条历史行为，构建39.27万用户画像及六类分群。</li><li>设计70%重点与30%探索名额；在7.63万领券用户中做1万名额离线回看，覆盖1127次首券核销，随机期望588次。</li><li>补充成本敏感性及A/B验证方案，不宣称真实ROI或新增订单。</li></ul><p>详细成稿见同目录《简历可直接使用.md》《面试讲解.md》。</p></section>
    <footer>已在后台完成，不操作电脑界面、不连接MySQL MCP。数据指纹及结果核验记录见tables/final_operations_verification.json。模型文件仅保留为附加探索。</footer>'''
    css='''*{box-sizing:border-box}body{margin:0;background:#f3f6f8;color:#1c3040;font:16px/1.8 "Microsoft YaHei",sans-serif}main{max-width:1120px;margin:auto;padding:40px 26px}header{background:#183747;color:white;padding:48px;border-radius:14px}header h1{font-size:40px;line-height:1.35;margin:16px 0}header p{color:#d5e4ea}.eyebrow{letter-spacing:2px;font-size:13px;color:#b6d9da}nav{display:flex;gap:22px;flex-wrap:wrap;padding:24px 0}nav a{color:#177e78;text-decoration:none}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.cards div{background:white;padding:22px;border-radius:10px}.cards b{display:block;color:#177e78;font-size:27px}.cards span{font-size:13px;color:#596d7a}section{background:white;padding:30px;margin-top:24px;border-radius:12px}h2{font-size:24px}img{width:100%;height:auto;margin:12px 0}table{width:100%;border-collapse:collapse;font-size:14px;overflow:auto;display:block}th,td{padding:10px 13px;text-align:left;border-bottom:1px solid #e4ecef;white-space:nowrap}th{background:#edf5f5}.note,footer{font-size:13px;color:#617786}.callout{border-left:4px solid #17847e;background:#eef7f5;padding:18px}summary{cursor:pointer;color:#177e78}footer{padding:28px 0} @media(max-width:700px){main{padding:14px}.cards{grid-template-columns:repeat(2,1fr)}header,section{padding:22px}header h1{font-size:29px}} @media print{body{background:white}nav{display:none}section{break-inside:avoid}main{padding:0}}'''
    html_doc=f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>优惠券运营分析与用户分层策略</title><style>{css}</style></head><body><main>{body}</main></body></html>'
    write(R/'运营版_最终报告.html',html_doc)
    write(ROOT/'先看这里_运营版成果.md','''# 项目已经按运营分析版收尾

先打开 reports/运营版_最终报告.html，看业务结论和图表。
简历直接看 reports/简历可直接使用.md；面试准备看 reports/面试讲解.md。

本版主线：业务指标 → 用户分层 → 规则名单 → 次月历史回看 → 成本敏感性 → A/B验证方案。
不需要继续模型训练、模型评估或复杂Uplift建模。已训练模型保留作附加材料，非简历重点。

全部结果在后台完成；没有操作电脑界面，也无需连接MySQL MCP。
1127 vs 588是已观测首券核销的离线覆盖对比，不是实际营销增长。费用和ROI均为假设情景。
''')
    print(json.dumps({'deliverables':'completed','sample_size_planning_per_arm':n,'html_bytes':(R/'运营版_最终报告.html').stat().st_size},ensure_ascii=False))

if __name__=='__main__':main()
