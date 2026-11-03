"""后台完成运营版项目：规则名单回看、预算敏感性、独立邮件实验附录及可阅读报告。"""
from pathlib import Path
import json,hashlib,math,html,base64
import numpy as np
import pandas as pd
from scipy.stats import norm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'reports'; TABLES=REPORTS/'tables'; FIGS=REPORTS/'figures'
PLAN_PATH=ROOT/'docs/operations_final_plan.json'
LABELS={'00_no_history':'未观察到历史','01_sparse_history':'成熟历史不足',
 '10_active_high_response':'高活跃/高历史核销','11_active_low_response':'高活跃/低历史核销',
 '20_less_active_high_response':'低活跃/高历史核销','21_less_active_low_response':'低活跃/低历史核销'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pct(x):return f'{x:.2f}%'
def mdtable(df):
    d=df.copy().fillna('—')
    return '| '+' | '.join(map(str,d.columns))+' |\n|'+ '|'.join(['---']*len(d.columns))+'|\n'+ '\n'.join('| '+' | '.join(map(str,row))+' |' for row in d.itertuples(index=False,name=None))

def classify(d):
    return np.select([d.has_history.eq(0),d.hist_mature_receipts.lt(3),
      d.recent30_receipts.ge(2)&d.hist_mature_redemption_rate.ge(.10),
      d.recent30_receipts.ge(2),d.hist_mature_redemption_rate.ge(.10)],
      list(LABELS)[:-1],default=list(LABELS)[-1])

def choose_policy(candidate,plan):
    # 显式只读历史特征和匿名ID；函数完全不接收核销标签。
    cols=['user_id','segment','hist_mature_redemption_rate','recent30_receipts','days_since_last_receipt']
    x=candidate[cols].copy()
    x['priority']=x.segment.map({s:i for i,s in enumerate(plan['priority'])})
    x['tie']=x.user_id.map(lambda u:hashlib.sha256((str(u)+'|42').encode()).hexdigest())
    x=x.sort_values(['priority','hist_mature_redemption_rate','recent30_receipts','days_since_last_receipt','tie'],
                    ascending=[True,False,False,True,True],na_position='last')
    cap=plan['capacity']; selected=[]
    groups=[(~x.segment.isin(['00_no_history','01_sparse_history']),.70),
            (x.segment.eq('01_sparse_history'),.15),(x.segment.eq('00_no_history'),.15)]
    for mask,share in groups:selected.extend(x.loc[mask].head(round(cap*share)).user_id.tolist())
    selected.extend(x.loc[~x.user_id.isin(selected)].head(cap-len(selected)).user_id.tolist())
    assert len(selected)==len(set(selected))==cap
    return selected

def email_appendix():
    p=ROOT/'data/raw/hillstrom/hillstrom.csv';d=pd.read_csv(p)
    assert len(d)==64000 and set(d.segment)=={'Mens E-Mail','Womens E-Mail','No E-Mail'}
    assert d.conversion.isin([0,1]).all() and (d.spend>=0).all()
    summary=d.groupby('segment').agg(users=('conversion','size'),purchases=('conversion','sum'),
             purchase_rate=('conversion','mean'),spend_per_user=('spend','mean')).reset_index()
    summary.to_csv(TABLES/'final_email_groups.csv',index=False,encoding='utf-8-sig')
    control=d[d.segment.eq('No E-Mail')];p0=control.conversion.mean();n0=len(control)
    rng=np.random.default_rng(20261026);B=1000;boot={}
    for group,frame in d.groupby('segment'):
        values=frame.spend.to_numpy();means=[]
        for _ in range(B//50):means.extend(values[rng.integers(0,len(values),(50,len(values)))].mean(axis=1))
        boot[group]=np.array(means)
    effects=[];balance=[]
    for group in ['Mens E-Mail','Womens E-Mail']:
        t=d[d.segment.eq(group)];p1=t.conversion.mean();n1=len(t)
        delta=p1-p0;se=math.sqrt(p1*(1-p1)/n1+p0*(1-p0)/n0)
        pooled=(t.conversion.sum()+control.conversion.sum())/(n1+n0)
        z=delta/math.sqrt(pooled*(1-pooled)*(1/n1+1/n0))
        spend_delta=t.spend.mean()-control.spend.mean()
        ci=np.quantile(boot[group]-boot['No E-Mail'],[.025,.975])
        effects.append({'treatment':group,'control':'No E-Mail','purchase_ate_pp':100*delta,
          'purchase_ci95_low_pp':100*(delta-1.96*se),'purchase_ci95_high_pp':100*(delta+1.96*se),
          'purchase_p_value':2*norm.sf(abs(z)),'spend_ate_usd_per_user':spend_delta,
          'spend_bootstrap_ci95_low':float(ci[0]),'spend_bootstrap_ci95_high':float(ci[1]),
          'status':'primary' if group=='Mens E-Mail' else 'secondary_exploratory'})
        cov=d[['recency','history','mens','womens','newbie']].join(pd.get_dummies(d[['channel','zip_code']],dtype=float))
        for c in cov:
            a=cov.loc[t.index,c].astype(float);b=cov.loc[control.index,c].astype(float)
            sd=math.sqrt((a.var(ddof=1)+b.var(ddof=1))/2)
            balance.append({'treatment':group,'feature':c,'smd':(a.mean()-b.mean())/sd if sd>0 else 0})
    e=pd.DataFrame(effects);e.to_csv(TABLES/'final_email_effects.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(balance).to_csv(TABLES/'final_email_balance.csv',index=False,encoding='utf-8-sig')
    return summary,e,max(abs(b['smd']) for b in balance),sha(p)

def plot_outputs(groups,policy_count,random_expected,random_range,cap,scenarios):
    font=Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
    fig,axes=plt.subplots(1,2,figsize=(14,6))
    ax=axes[0];vals=[random_expected,policy_count]
    bars=ax.bar(['随机名单期望','固定规则名单'],vals,color=['#91a6b3','#19877e'],width=.55)
    ax.errorbar(0,random_expected,yerr=[[random_expected-random_range[0]],[random_range[1]-random_expected]],
                color='#42586b',capsize=6,fmt='none')
    for b,v in zip(bars,vals):ax.text(b.get_x()+b.get_width()/2,v+25,f'{v:,.1f}',ha='center',fontweight='bold')
    ax.set_ylim(0,max(vals)*1.25);ax.set_ylabel('已观测首条券核销覆盖数')
    ax.set_title(f'6月历史样本回看｜各选{cap:,}人',loc='left',fontweight='bold')
    ax=axes[1];g=groups.sort_values('segment');y=np.arange(len(g))
    ax.barh(y,g.selected_users,color='#19877e');ax.set_yticks(y,[LABELS[x] for x in g.segment]);ax.invert_yaxis()
    ax.set_xlabel('规则名单人数');ax.set_title('名单分配｜保留信息不足人群探索',loc='left',fontweight='bold')
    ax.set_xlim(0,max(g.selected_users)*1.25)
    for i,n in enumerate(g.selected_users):ax.text(n+20,i,f'{n:,}',va='center')
    fig.suptitle('运营规则名单回看｜实际核销数据，非实际投放实验',x=.03,ha='left',fontsize=17,fontweight='bold')
    fig.text(.03,.02,'候选：6月1—15日实际领券用户，每人首条券；历史冻结06-01。误差线为200次随机抽样的95%分位区间。\n'
             '覆盖差异是离线样本筛选结果，不是营销新增购买；规则在读取本次回看结果前固定。',fontsize=9,color='#555555')
    fig.tight_layout(rect=[.01,.11,.99,.93]);fig.savefig(FIGS/'final_policy_replay.png',dpi=170);plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,5))
    for name,g in scenarios.groupby('policy'):
        g=g[(g.contact_cost.eq(.2))&(g.coupon_cost.eq(5))&(g.contribution_per_incremental_order.eq(30))]
        ax.plot(g.incremental_share*100,g.simulated_roi*100,marker='o',label=name)
    ax.axhline(0,color='#a95543',ls='--');ax.set_xlabel('假设：已观测核销中真正由营销新增的比例（%）')
    ax.set_ylabel('模拟增量ROI（%）');ax.set_title('假设情景：增量比例未知，不能报告真实ROI',loc='left',fontweight='bold')
    ax.legend(frameon=False);ax.grid(alpha=.15)
    fig.text(.06,.02,'假设触达成本0.2元/人、核销补贴5元/次、每笔增量订单贡献利润30元；未由O2O识别真实增量。',fontsize=9,color='#555555')
    fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(FIGS/'final_roi_scenarios.png',dpi=170);plt.close(fig)

def main():
    plan=json.loads(PLAN_PATH.read_text(encoding='utf-8'));data_path=ROOT/'data/processed/model_samples_v1.csv'
    verification=json.loads((TABLES/'lesson7_data_verification.json').read_text(encoding='utf-8'))
    assert verification['status']=='passed' and sha(data_path)==verification['processed_csv_sha256']
    d=pd.read_csv(data_path,dtype={'user_id':str,'merchant_id':str,'coupon_id':str})
    june=d[d.split.eq('test')].copy();assert len(june)==90965
    candidate=june.sort_values(['received_date','row_id']).drop_duplicates('user_id').copy()
    assert len(candidate)==76257 and candidate.user_id.is_unique
    assert candidate.feature_asof.eq('2016-06-01').all()
    candidate['segment']=classify(candidate)
    selected=choose_policy(candidate,plan)
    altered=candidate.copy();altered['y']=1-altered.y
    assert selected==choose_policy(altered,plan),'名单不得依赖目标核销标签'
    picked=candidate[candidate.user_id.isin(selected)].copy();cap=plan['capacity']
    population_success=int(candidate.y.sum());observed=int(picked.y.sum())
    random_expected=cap*population_success/len(candidate)
    rng=np.random.default_rng(42);ys=candidate.y.to_numpy();draws=[]
    for seed in range(plan['random_comparison']['draws']):draws.append(int(ys[rng.choice(len(ys),cap,replace=False)].sum()))
    qlo,qhi=np.quantile(draws,[.025,.975]);ratio=observed/random_expected-1
    random_stats={'candidate_users':len(candidate),'population_first_coupon_redemptions':population_success,
       'capacity':cap,'policy_observed_redemptions':observed,'random_expected_redemptions':random_expected,
       'policy_observed_rate':observed/cap,'random_expected_rate':population_success/len(candidate),
       'coverage_difference':observed-random_expected,'relative_coverage_difference':ratio,
       'random_draws':200,'random_draw_mean':float(np.mean(draws)),
       'random_draw_p025':float(qlo),'random_draw_p975':float(qhi),
       'label_flip_selection_invariance':'passed',
       'causal_claim':False,'new_campaign_effect_identified':False}
    (TABLES/'final_policy_replay.json').write_text(json.dumps(random_stats,indent=2),encoding='utf-8')
    groups=candidate.groupby('segment').agg(candidate_users=('user_id','size')).reset_index()
    gs=picked.groupby('segment').agg(selected_users=('user_id','size'),observed_redemptions=('y','sum')).reset_index()
    groups=groups.merge(gs,on='segment',how='left').fillna(0)
    for c in ['selected_users','observed_redemptions']:groups[c]=groups[c].astype(int)
    assert groups.selected_users.sum()==cap and groups.observed_redemptions.sum()==observed
    groups.to_csv(TABLES/'final_policy_allocation.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame({'random_draw':np.arange(1,201),'observed_redemptions':draws}).to_csv(TABLES/'final_random_replays.csv',index=False)
    (ROOT/'outputs/predictions').mkdir(parents=True,exist_ok=True)
    picked[['user_id','row_id','segment','y']].to_csv(ROOT/'outputs/predictions/final_rule_list_replay.csv',index=False)
    scenarios=[]
    for name,redeemed in [('随机名单期望',random_expected),('固定规则名单',observed)]:
      for contact in [.1,.2,.5]:
       for coupon in [3,5,8]:
        for contribution in [20,30,40]:
         for theta in plan['incremental_share_scenarios']:
          cost=cap*contact+redeemed*coupon;profit=theta*redeemed*contribution
          scenarios.append({'policy':name,'selected_users':cap,'observed_redemptions_or_expected_coverage':redeemed,
            'contact_cost':contact,'coupon_cost':coupon,'contribution_per_incremental_order':contribution,
            'incremental_share':theta,'assumed_marketing_cost':cost,'assumed_incremental_contribution':profit,
            'simulated_incremental_net_profit':profit-cost,'simulated_roi':(profit-cost)/cost,
            'break_even_incremental_share':cost/(redeemed*contribution),'result_type':'assumption_scenario_not_real_business_roi'})
    scenarios=pd.DataFrame(scenarios);scenarios.to_csv(TABLES/'final_budget_scenarios.csv',index=False,encoding='utf-8-sig')
    email_groups,email_effects,max_smd,email_hash=email_appendix()
    plot_outputs(groups,observed,random_expected,(qlo,qhi),cap,scenarios)
    # 所有事实和参数集中写入可追溯清单，文案生成另一步完成。
    result={'policy':random_stats,'allocation':groups.to_dict('records'),
      'roi_base':scenarios[scenarios.contact_cost.eq(.2)&scenarios.coupon_cost.eq(5)&scenarios.contribution_per_incremental_order.eq(30)].to_dict('records'),
      'budget_scenario_rows':len(scenarios),'email_groups':email_groups.to_dict('records'),
      'email_effects':email_effects.to_dict('records'),'max_email_covariate_smd':max_smd,
      'plan_sha256':sha(PLAN_PATH),'source_data_sha256':sha(data_path),'hillstrom_sha256':email_hash,
      'status':'passed','gui_used':False,'mysql_mcp_used':False}
    (TABLES/'final_operations_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
