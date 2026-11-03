"""以已全字段核验的历史画像+原始5月记录，独立验证SQL分群与回看结果。"""
from pathlib import Path
import json, hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/tables'; FIGS=ROOT/'reports/figures'
UP=Path('D:/MySQL_data/Uploads')
LABELS={'00_no_history':'未观察到历史','01_sparse_history':'成熟历史不足',
 '10_active_high_response':'近期高活跃 / 历史高核销','11_active_low_response':'近期高活跃 / 历史低核销',
 '20_less_active_high_response':'近期低活跃 / 历史高核销','21_less_active_low_response':'近期低活跃 / 历史低核销'}
SUMCOLS=['segment','users','receipts','redemptions','redeeming_users','rate_pct','user_rate_pct',
         'avg_hist_receipts','avg_recent30_receipts','avg_mature_receipts','avg_hist_response_rate']
USERCOLS=['user_id','segment','has_history','hist_receipts','hist_mature_receipts',
          'hist_mature_redemption_rate','recent30_receipts','days_since_last_receipt','may_receipts','may_redemptions']
SENSCOLS=['config','users','no_history_users','sparse_history_users','active_high_response_users','changed_users']

def classify(f,min_mature=3,min_recent=2,min_rate=.10):
    return pd.Series(np.select([f.has_history.eq(0),f.hist_mature_receipts.lt(min_mature),
        f.recent30_receipts.ge(min_recent)&f.hist_mature_redemption_rate.ge(min_rate),
        f.recent30_receipts.ge(min_recent),f.hist_mature_redemption_rate.ge(min_rate)],
        list(LABELS)[:-1],default=list(LABELS)[-1]),index=f.index)

def main():
    f=pd.read_csv(OUT/'lesson5_user_features_20160501.csv',dtype={'user_id':str})
    raw=pd.read_csv(ROOT/'data/raw/o2o/ccf_offline_stage1_train.csv',dtype=str,keep_default_na=False)
    may=raw[(raw.Coupon_id!='null') & raw.Date_received.between('20160501','20160531')].copy()
    rec=pd.to_datetime(may.Date_received,format='%Y%m%d')
    con=pd.to_datetime(may.Date.replace('null',None),format='%Y%m%d')
    may['y']=(con-rec).dt.days.between(0,15).astype(int)
    u=may.groupby('User_id').agg(may_receipts=('y','size'),may_redemptions=('y','sum')).rename_axis('user_id').reset_index()
    u=u.merge(f,on='user_id',how='left',validate='one_to_one',indicator=True)
    u['has_history']=u['_merge'].eq('both').astype(int)
    for c in ['hist_receipts','hist_mature_receipts','recent30_receipts']:u[c]=u[c].fillna(0)
    u['segment']=classify(u)
    actual=pd.read_csv(UP/'coupon_lesson6_users.csv',header=None,names=USERCOLS,dtype={'user_id':str},na_values=[r'\N'])
    assert not actual.user_id.duplicated().any()
    a=actual.sort_values('user_id').reset_index(drop=True)
    e=u[USERCOLS].sort_values('user_id').reset_index(drop=True)
    for c in USERCOLS:
        if c in ['user_id','segment']:assert a[c].equals(e[c]),c
        else:assert np.allclose(a[c],e[c],equal_nan=True,rtol=0,atol=1e-9),c
    expected=u.groupby('segment').agg(users=('user_id','size'),receipts=('may_receipts','sum'),
        redemptions=('may_redemptions','sum'),redeeming_users=('may_redemptions',lambda x:int(x.gt(0).sum())),
        avg_hist_receipts=('hist_receipts','mean'),avg_recent30_receipts=('recent30_receipts','mean'),
        avg_mature_receipts=('hist_mature_receipts','mean'),avg_hist_response_rate=('hist_mature_redemption_rate','mean')).reset_index()
    expected['rate_pct']=100*expected.redemptions/expected.receipts
    expected['user_rate_pct']=100*expected.redeeming_users/expected.users
    summary=pd.read_csv(UP/'coupon_lesson6_summary.csv',header=None,names=SUMCOLS,na_values=[r'\N'])
    expected=expected.sort_values('segment').reset_index(drop=True)
    summary=summary.sort_values('segment').reset_index(drop=True)
    assert summary.segment.equals(expected.segment)
    for c in SUMCOLS[1:]:
        tol=.000051 if c in ['rate_pct','user_rate_pct'] else (.00000051 if c.startswith('avg_') else 0)
        assert np.allclose(summary[c],expected[c],atol=tol,rtol=0,equal_nan=True),c
    assert summary.users.sum()==148439 and summary.receipts.sum()==215348 and summary.redemptions.sum()==21580
    configs={'baseline':(3,2,.10),'min_mature_5':(5,2,.10),'min_recent_3':(3,3,.10),'min_rate_20pct':(3,2,.20)}
    sens=[]
    for key,(n,r,p) in configs.items():
        segment=classify(u,n,r,p)
        sens.append([key,len(u),int(segment.eq('00_no_history').sum()),int(segment.eq('01_sparse_history').sum()),
                     int(segment.eq('10_active_high_response').sum()),int(segment.ne(u.segment).sum())])
    se=pd.DataFrame(sens,columns=SENSCOLS).sort_values('config').reset_index(drop=True)
    sa=pd.read_csv(UP/'coupon_lesson6_sensitivity.csv',header=None,names=SENSCOLS).sort_values('config').reset_index(drop=True)
    pd.testing.assert_frame_equal(sa,se,check_dtype=False)
    summary['user_share_pct']=summary.users/summary.users.sum()*100
    summary.to_csv(OUT/'lesson6_segment_summary.csv',index=False,encoding='utf-8-sig')
    actual.to_csv(OUT/'lesson6_segmented_users.csv',index=False,encoding='utf-8-sig')
    sa.to_csv(OUT/'lesson6_rule_sensitivity.csv',index=False,encoding='utf-8-sig')
    history=f.assign(has_history=1)
    history['segment']=classify(history)
    history.groupby('segment').size().rename('history_users').to_csv(OUT/'lesson6_history_population.csv',encoding='utf-8-sig')

    font=Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font));plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
    colors=['#9aa5ad','#bec7cd','#16847d','#316b93','#598d86','#748d9b']
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(16,7),gridspec_kw={'width_ratios':[1,1.15]})
    y=np.arange(len(summary));labs=[LABELS[x] for x in summary.segment]
    ax1.barh(y,summary.user_share_pct,color=colors);ax1.set_yticks(y,labs);ax1.invert_yaxis()
    ax1.set_xlim(0,max(summary.user_share_pct)*1.38);ax1.set_xlabel('5月实际领券用户占比（%）')
    ax1.set_title('分群规模｜每人仅归一组',loc='left',fontweight='bold')
    for i,row in enumerate(summary.itertuples()):ax1.text(row.user_share_pct+.5,i,f'{row.users:,}人 / {row.user_share_pct:.2f}%',va='center',fontsize=9)
    ax2.barh(y,summary.rate_pct,color=colors);ax2.set_yticks(y,['']*len(y));ax2.invert_yaxis()
    ax2.set_xlim(0,max(summary.rate_pct)*1.42);ax2.set_xlabel('5月领券后15天记录核销率（%）')
    ax2.set_title('结果回看｜5月结果未参与规则制定',loc='left',fontweight='bold')
    overall=21580/215348*100;ax2.axvline(overall,ls='--',color='#ac5b42',lw=1,label=f'5月总体 {overall:.2f}%')
    for i,row in enumerate(summary.itertuples()):ax2.text(row.rate_pct+.4,i,f'{row.rate_pct:.2f}%（{row.redemptions:,}/{row.receipts:,}）',va='center',fontsize=9)
    ax2.legend(frameon=False,loc='lower right',fontsize=9)
    for ax in [ax1,ax2]:ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    fig.suptitle('用户分群｜05-01冻结历史画像，5月离线回看',x=.03,ha='left',fontsize=19,fontweight='bold')
    fig.text(.03,.02,'规则：成熟历史≥3条；近30天领券≥2条为高活跃；历史成熟核销率≥10%为高核销。\n'
        '仅描述5月实际领券样本，不能预知未来领券名单；群体差异不是因果增量，“高核销”不等于高补贴价值。',fontsize=10,color='#555555')
    fig.tight_layout(rect=[.01,.09,.99,.94]);fig.savefig(FIGS/'lesson6_segmentation_dashboard.png',dpi=170);plt.close(fig)
    report={'asof':'2016-05-01','may_users':148439,'may_receipts':215348,'may_redemptions':21580,
        'all_user_assignments_and_outcomes_match':True,'all_summary_fields_match':True,
        'all_sensitivity_configs_match':True,'rule_version':'v1','status':'passed',
        'feature_csv_sha256':hashlib.sha256((OUT/'lesson5_user_features_20160501.csv').read_bytes()).hexdigest(),
        'sql_summary_sha256':hashlib.sha256((UP/'coupon_lesson6_summary.csv').read_bytes()).hexdigest(),
        'scope':'May observed receipt users only; rules fixed from pre-May features; response association not causal uplift.'}
    (OUT/'lesson6_verification.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(summary.to_string(index=False));print(sa.to_string(index=False));print(json.dumps(report))

if __name__=='__main__':main()
