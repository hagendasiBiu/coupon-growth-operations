"""从原始CSV独立构建05-01画像，逐用户核对SQL；验证删除未来信息后画像不变。"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ASOF=pd.Timestamp('2016-05-01')
RAW=ROOT/'data/raw/o2o/ccf_offline_stage1_train.csv'
SQL_EXPORT=Path('D:/MySQL_data/Uploads/coupon_lesson5_features_20160501_v2.csv')
COVERAGE=Path('D:/MySQL_data/Uploads/coupon_lesson5_coverage_20160501.csv')
OUT=ROOT/'reports/tables'
COLS=['user_id','hist_receipts','hist_known_redemptions','hist_mature_receipts',
      'hist_mature_redemptions_15d','recent7_receipts','recent30_receipts','hist_merchant_count',
      'hist_mean_distance_code','last_receipt_date','last_known_redemption_date',
      'latest_mature_received_date','feature_asof','hist_mature_redemption_rate',
      'days_since_last_receipt','days_since_last_known_redemption']
DATES=['last_receipt_date','last_known_redemption_date','latest_mature_received_date','feature_asof']
FLOATS=['hist_mean_distance_code','hist_mature_redemption_rate']

def build(source):
    h=source[source.received<ASOF].copy()
    h['known']=h.consumed.where(h.consumed<ASOF)
    h['known_flag']=h.known.notna().astype(int)
    h['mature']=(h.received+pd.Timedelta(days=15)<ASOF).astype(int)
    h['mature_y']=(h.mature.eq(1) & (h.known-h.received).dt.days.between(0,15)).astype(int)
    h['recent7']=(h.received>=ASOF-pd.Timedelta(days=7)).astype(int)
    h['recent30']=(h.received>=ASOF-pd.Timedelta(days=30)).astype(int)
    h['mature_date']=h.received.where(h.mature.eq(1))
    f=h.groupby('User_id',sort=True).agg(
        hist_receipts=('received','size'),hist_known_redemptions=('known_flag','sum'),
        hist_mature_receipts=('mature','sum'),hist_mature_redemptions_15d=('mature_y','sum'),
        recent7_receipts=('recent7','sum'),recent30_receipts=('recent30','sum'),
        hist_merchant_count=('Merchant_id','nunique'),hist_mean_distance_code=('distance','mean'),
        last_receipt_date=('received','max'),last_known_redemption_date=('known','max'),
        latest_mature_received_date=('mature_date','max')).rename_axis('user_id').reset_index()
    f['hist_mean_distance_code']=f.hist_mean_distance_code.round(6)
    f['feature_asof']=ASOF
    f['hist_mature_redemption_rate']=(f.hist_mature_redemptions_15d/f.hist_mature_receipts.replace(0,np.nan)).round(6)
    f['days_since_last_receipt']=(ASOF-f.last_receipt_date).dt.days
    f['days_since_last_known_redemption']=(ASOF-f.last_known_redemption_date).dt.days
    for c in DATES:f[c]=f[c].dt.strftime('%Y-%m-%d')
    return f[COLS]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    source=pd.read_csv(RAW,dtype=str,keep_default_na=False)
    source=source[(source.Coupon_id!='null') & (source.Date_received!='null')].copy()
    source['received']=pd.to_datetime(source.Date_received,format='%Y%m%d')
    source['consumed']=pd.to_datetime(source.Date.replace('null',None),format='%Y%m%d')
    source['distance']=pd.to_numeric(source.Distance.replace('null',None))
    expected=build(source)
    # 防泄漏检查：删除未来领取，屏蔽未来消费；所有历史画像必须完全不变。
    masked=source[source.received<ASOF].copy()
    masked.loc[masked.consumed>=ASOF,'consumed']=pd.NaT
    pd.testing.assert_frame_equal(expected,build(masked))
    actual=pd.read_csv(SQL_EXPORT,header=None,names=COLS,dtype={'user_id':str},na_values=[r'\N'])
    assert not actual.user_id.duplicated().any()
    actual=actual.sort_values('user_id').reset_index(drop=True)
    expected=expected.sort_values('user_id').reset_index(drop=True)
    assert actual.user_id.equals(expected.user_id),'用户集合不同'
    for c in COLS:
        if c in DATES or c=='user_id':
            assert actual[c].fillna('<NULL>').equals(expected[c].fillna('<NULL>')),c
        else:
            tolerance=.00000051 if c in FLOATS else 0
            good=np.isclose(actual[c],expected[c],atol=tolerance,rtol=0,equal_nan=True)
            if not good.all():
                raise AssertionError(f'{c}: {int((~good).sum())}个用户不匹配')
    assert (actual.hist_mature_redemptions_15d<=actual.hist_mature_receipts).all()
    assert (actual.recent7_receipts<=actual.recent30_receipts).all()
    assert (actual.recent30_receipts<=actual.hist_receipts).all()
    assert actual.loc[actual.hist_mature_receipts.eq(0),'hist_mature_redemption_rate'].isna().all()
    may=source[(source.received>=ASOF)&(source.received<pd.Timestamp('2016-06-01'))].copy()
    may['has_history']=may.User_id.isin(set(expected.user_id)).astype(int)
    expected_cov=may.groupby('has_history').agg(may_receipts=('User_id','size'),may_users=('User_id','nunique')).reset_index()
    actual_cov=pd.read_csv(COVERAGE,header=None,names=['has_history','may_receipts','may_users'])
    pd.testing.assert_frame_equal(actual_cov,expected_cov,check_dtype=False)
    assert actual_cov.may_receipts.sum()==215348
    actual.to_csv(OUT/'lesson5_user_features_20160501.csv',index=False,encoding='utf-8-sig')
    actual_cov.to_csv(OUT/'lesson5_may_coverage.csv',index=False,encoding='utf-8-sig')
    actual.head(20).to_csv(OUT/'lesson5_feature_examples.csv',index=False,encoding='utf-8-sig')
    report={'asof':'2016-05-01','history_users':len(actual),
       'history_receipts':int(actual.hist_receipts.sum()),
       'known_redemptions':int(actual.hist_known_redemptions.sum()),
       'mature_receipts':int(actual.hist_mature_receipts.sum()),
       'mature_redemptions_15d':int(actual.hist_mature_redemptions_15d.sum()),
       'users_without_mature_receipts':int(actual.hist_mature_receipts.eq(0).sum()),
       'latest_history_receipt':actual.last_receipt_date.max(),
       'latest_known_redemption':actual.last_known_redemption_date.dropna().max(),
       'latest_mature_receipt':actual.latest_mature_received_date.dropna().max(),
       'may_coverage':actual_cov.to_dict('records'),
       'all_users_all_fields_match_original_csv':True,
       'future_information_removal_invariance':'passed',
       'raw_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),
       'sql_export_sha256':hashlib.sha256(SQL_EXPORT.read_bytes()).hexdigest(),
       'limitation':'事件日期模拟可知信息，无法验证日志延迟；固定05-01画像用于5月样本，不是逐日更新画像。',
       'status':'passed'}
    (OUT/'lesson5_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
