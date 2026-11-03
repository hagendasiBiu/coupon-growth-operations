"""核对 MySQL 导出与原始CSV，生成行为分析图表；不连接数据库或更改原始数据。"""
from pathlib import Path
import hashlib
import json
import shutil
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/o2o/ccf_offline_stage1_train.csv'
EXPORT = Path('D:/MySQL_data/Uploads/coupon_lesson4_summary_20261026.csv')
TABLES = ROOT / 'reports/tables'
FIGS = ROOT / 'reports/figures'
TABLES.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)

def main():
    actual = pd.read_csv(EXPORT, header=None,
                         names=['dimension', 'bucket', 'receipts', 'redemptions', 'rate_pct'],
                         dtype={'dimension': str, 'bucket': str})
    assert not actual.duplicated(['dimension', 'bucket']).any()
    # 独立从原CSV计算，不用导出结果反推“预期值”。
    df = pd.read_csv(RAW, dtype=str, keep_default_na=False)
    df = df[(df.Coupon_id != 'null') & (df.Date_received != 'null')].copy()
    rec = pd.to_datetime(df.Date_received, format='%Y%m%d', errors='raise')
    df = df[rec + pd.Timedelta(days=15) <= pd.Timestamp('2016-06-30')].copy()
    rec = pd.to_datetime(df.Date_received, format='%Y%m%d')
    consumed = pd.to_datetime(df.Date.replace('null', None), format='%Y%m%d')
    df['y'] = (consumed - rec).dt.days.between(0, 15).astype(int)
    threshold = df.Discount_rate.str.contains(':', regex=False)
    parts = df.Discount_rate.str.split(':', expand=True)
    discount = pd.Series(index=df.index, dtype=float)
    discount.loc[threshold] = (parts.loc[threshold, 1].astype(float)
                              / parts.loc[threshold, 0].astype(float)).round(6)
    # 对齐MySQL DECIMAL的六位精度，避免Python的1-0.7变成0.30000000000000004而跨分组边界。
    discount.loc[~threshold] = (1 - df.loc[~threshold, 'Discount_rate'].astype(float)).round(6)
    df['discount_type'] = np.where(threshold, 'threshold', 'rate')
    df['discount_band'] = pd.cut(discount, [-np.inf,.1,.2,.3,.5,np.inf],
        labels=['01_0_to_10pct','02_10_to_20pct','03_20_to_30pct','04_30_to_50pct','05_over_50pct']).astype(str)
    distance = pd.to_numeric(df.Distance.replace('null', None))
    df['distance_band'] = np.select([distance.isna(), distance.eq(0), distance.eq(1),
        distance.le(3), distance.le(5)], ['07_unknown','01_code_0','02_code_1','03_code_2_3','04_code_4_5'],
        default='05_code_6_10')
    df['month'] = rec.dt.strftime('%Y-%m')
    df['weekday'] = (rec.dt.weekday + 1).astype(str)
    df['merchant'] = df.Merchant_id
    expected = []
    for dim in ['discount_type','discount_band','distance_band','month','weekday','merchant']:
        g = df.groupby(dim, observed=True)['y'].agg(receipts='size', redemptions='sum').reset_index()
        g = g.rename(columns={dim:'bucket'}); g['dimension'] = dim
        expected.append(g)
    expected = pd.concat(expected, ignore_index=True)
    check = actual.merge(expected, on=['dimension','bucket'], how='outer', suffixes=('_sql','_file'), indicator=True)
    assert check['_merge'].eq('both').all(), '分组键不匹配'
    for col in ['receipts','redemptions']:
        mismatches=check[~check[f'{col}_sql'].eq(check[f'{col}_file'])]
        if len(mismatches):
            print(mismatches.to_string(index=False))
        assert check[f'{col}_sql'].eq(check[f'{col}_file']).all(), f'{col}不匹配'
    assert np.allclose(actual.rate_pct, actual.redemptions/actual.receipts*100, atol=.000051, rtol=0)
    for dim,g in actual.groupby('dimension'):
        assert g.receipts.sum()==1053282 and g.redemptions.sum()==64395, dim
    actual.to_csv(TABLES/'lesson4_behavior_summary.csv',index=False,encoding='utf-8-sig')
    for dim,g in actual.groupby('dimension'):
        g.to_csv(TABLES/f'lesson4_{dim}.csv',index=False,encoding='utf-8-sig')
    actual[(actual.dimension=='merchant') & (actual.receipts>=1000)].sort_values(
        ['rate_pct','receipts','bucket'],ascending=[False,False,True]).head(10).to_csv(
        TABLES/'lesson4_merchant_top10.csv',index=False,encoding='utf-8-sig')

    font = Path('C:/Windows/Fonts/msyh.ttc')
    if font.exists():
        from matplotlib import font_manager
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = FontProperties(fname=str(font)).get_name()
    plt.rcParams.update({'axes.unicode_minus':False,'font.size':10,
                         'axes.spines.top':False,'axes.spines.right':False})
    names={
        'discount_band':('名义优惠比例与核销率',{'01_0_to_10pct':'≤10%','02_10_to_20pct':'(10%,20%]',
          '03_20_to_30pct':'(20%,30%]','04_30_to_50pct':'(30%,50%]','05_over_50pct':'>50%'}),
        'distance_band':('距离编码与核销率',{'01_code_0':'0','02_code_1':'1','03_code_2_3':'2–3',
          '04_code_4_5':'4–5','05_code_6_10':'6–10','07_unknown':'未知'}),
        'month':('领取月份与核销率',{}),
        'weekday':('领取星期与核销率',dict(zip(list('1234567'),['一','二','三','四','五','六','日'])))}
    baseline=64395/1053282*100
    def panel(ax,dim):
        g=actual[actual.dimension==dim].sort_values('bucket')
        title,labels=names[dim]
        xs=np.arange(len(g)); bars=ax.bar(xs,g.rate_pct,
            color=['#178680' if n>=1000 else '#929d9d' for n in g.receipts],width=.65)
        ax.axhline(baseline,color='#ac5b42',ls='--',lw=1,label=f'总体 {baseline:.2f}%')
        ax.set_xticks(xs,[labels.get(x,x) for x in g.bucket])
        ax.set_title(title,loc='left',fontweight='bold',pad=14)
        ax.set_ylabel('15天记录核销率（%）')
        ax.set_ylim(0,max(float(g.rate_pct.max()),baseline)*1.32)
        for bar,row in zip(bars,g.itertuples()):
            ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.12,
                    f'{row.rate_pct:.2f}%\nn={row.receipts:,}',ha='center',va='bottom',fontsize=8,
                    bbox={'facecolor':'white','edgecolor':'none','pad':.3,'alpha':.94})
        ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
        ax.legend(frameon=False,fontsize=8,loc='upper right')
    fig,axes=plt.subplots(2,2,figsize=(15,10))
    for ax,dim in zip(axes.flat,names):panel(ax,dim)
    fig.suptitle('优惠券使用行为｜历史数据分组对比',fontsize=20,fontweight='bold',x=.06,ha='left')
    fig.text(.06,.02,'来源：MySQL实际汇总，已独立核对原始CSV；n为领券记录数，保留字段相同记录。\n'
             '描述性关联，不代表因果增量；灰柱n<1,000，谨慎解读。满减按门槛计算名义优惠比例；6月仅含1—15日领取记录。',fontsize=10,color='#555555')
    fig.tight_layout(rect=[.02,.08,.99,.94]);fig.savefig(FIGS/'lesson4_behavior_dashboard.png',dpi=170);plt.close(fig)
    for dim in names:
        fig,ax=plt.subplots(figsize=(9,5));panel(ax,dim)
        fig.tight_layout();fig.savefig(FIGS/f'lesson4_{dim}.png',dpi=170);plt.close(fig)
    report={'raw_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),
            'sql_export_sha256':hashlib.sha256(EXPORT.read_bytes()).hexdigest(),
            'group_rows':len(actual),'dimensions':6,'all_group_counts_match_original_csv':True,
            'each_dimension_receipts':1053282,'each_dimension_redemptions':64395,
            'sql_script':'sql/05_lesson4_behavior.sql','status':'passed'}
    (TABLES/'lesson4_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
    print(actual[actual.dimension!='merchant'].to_string(index=False))

if __name__=='__main__':
    main()
