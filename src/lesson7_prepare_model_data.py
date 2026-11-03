"""独立核对MySQL建模样本、历史特征、日期窗口；验证后才允许训练。"""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import lesson5_verify_features as historical

ROOT=Path(__file__).resolve().parents[1]
EXPORT=Path('D:/MySQL_data/Uploads/coupon_lesson7_model_samples_v1.csv')
RAW=ROOT/'data/raw/o2o/ccf_offline_stage1_train.csv'
COLS=['row_id','user_id','merchant_id','coupon_id','feature_asof','received_date','split',
 'discount_type','min_spend','nominal_discount_fraction','distance_code','received_weekday','has_history',
 'hist_receipts','hist_known_redemptions','hist_mature_receipts','hist_mature_redemptions_15d',
 'hist_mature_redemption_rate','recent7_receipts','recent30_receipts','hist_merchant_count',
 'hist_mean_distance_code','days_since_last_receipt','days_since_last_known_redemption','y']
TEXT=['user_id','merchant_id','coupon_id','feature_asof','received_date','split','discount_type']
COUNTS=['hist_receipts','hist_known_redemptions','hist_mature_receipts',
        'hist_mature_redemptions_15d','recent7_receipts','recent30_receipts','hist_merchant_count']

def main():
    source=pd.read_csv(RAW,dtype=str,keep_default_na=False)
    source['row_id']=np.arange(1,len(source)+1)
    source=source[(source.Coupon_id!='null')&(source.Date_received!='null')].copy()
    source['received']=pd.to_datetime(source.Date_received,format='%Y%m%d')
    source['consumed']=pd.to_datetime(source.Date.replace('null',None),format='%Y%m%d')
    source['distance']=pd.to_numeric(source.Distance.replace('null',None))
    target=source[source.received.between('2016-03-01','2016-06-15')&source.received.dt.day.le(15)].copy()
    target['y']=(target.consumed-target.received).dt.days.between(0,15).astype(int)
    target=target.rename(columns={'User_id':'user_id','Merchant_id':'merchant_id','Coupon_id':'coupon_id'})
    target['feature_asof']=target.received.dt.strftime('%Y-%m-01')
    target['received_date']=target.received.dt.strftime('%Y-%m-%d')
    target['split']=np.select([target.received.lt('2016-05-01'),target.received.lt('2016-06-01')],
                             ['train','validation'],default='test')
    threshold=target.Discount_rate.str.contains(':',regex=False)
    target['discount_type']=np.where(threshold,'threshold','rate')
    parts=target.Discount_rate.str.split(':',expand=True)
    target['min_spend']=np.nan
    target.loc[threshold,'min_spend']=parts.loc[threshold,0].astype(float)
    target['nominal_discount_fraction']=np.nan
    target.loc[threshold,'nominal_discount_fraction']=(parts.loc[threshold,1].astype(float)/parts.loc[threshold,0].astype(float)).round(6)
    target.loc[~threshold,'nominal_discount_fraction']=(1-target.loc[~threshold,'Discount_rate'].astype(float)).round(6)
    target['distance_code']=target.distance
    target['received_weekday']=target.received.dt.weekday+1
    expected=[];audits=[]
    for asof,batch in target.groupby('feature_asof',sort=True):
        historical.ASOF=pd.Timestamp(asof)
        f=historical.build(source)
        # 和上一课相同的防泄漏验收，扩展到四个历史时点。
        masked=source[source.received<historical.ASOF].copy()
        masked.loc[masked.consumed>=historical.ASOF,'consumed']=pd.NaT
        pd.testing.assert_frame_equal(f,historical.build(masked))
        joined=batch.merge(f,on=['user_id','feature_asof'],how='left',validate='many_to_one',indicator=True)
        joined['has_history']=joined['_merge'].eq('both').astype(int)
        for c in COUNTS:joined[c]=joined[c].fillna(0)
        expected.append(joined[COLS])
        audits.append({'feature_asof':asof,'target_records':len(batch),
                       'future_information_removal_invariance':'passed'})
        print('verified historical cutoff',asof,flush=True)
    expected=pd.concat(expected,ignore_index=True).sort_values('row_id').reset_index(drop=True)
    actual=pd.read_csv(EXPORT,header=None,names=COLS,dtype={c:str for c in TEXT},na_values=[r'\N'])
    assert not actual.row_id.duplicated().any()
    actual=actual.sort_values('row_id').reset_index(drop=True)
    assert len(actual)==len(expected)
    for c in COLS:
        if c in TEXT:assert actual[c].fillna('<NULL>').equals(expected[c].fillna('<NULL>')),c
        else:
            tol=.00000051 if c in ['nominal_discount_fraction','hist_mature_redemption_rate','hist_mean_distance_code'] else 0
            good=np.isclose(actual[c],expected[c],atol=tol,rtol=0,equal_nan=True)
            if not good.all():raise AssertionError(f'{c}: {int((~good).sum())} records differ')
    assert actual.y.isin([0,1]).all()
    dates=pd.to_datetime(actual.received_date)
    assert (pd.to_datetime(actual.feature_asof)<=dates).all()
    split_summary=[]
    for name in ['train','validation','test']:
        d=actual[actual.split.eq(name)]
        split_summary.append({'split':name,'records':len(d),'users':int(d.user_id.nunique()),
          'first_received':d.received_date.min(),'last_received':d.received_date.max(),
          'last_label_observation_day':(pd.to_datetime(d.received_date).max()+pd.Timedelta(days=15)).strftime('%Y-%m-%d')})
    train_end=pd.Timestamp(split_summary[0]['last_label_observation_day'])
    valid_start=pd.Timestamp(split_summary[1]['first_received'])
    valid_end=pd.Timestamp(split_summary[1]['last_label_observation_day'])
    test_start=pd.Timestamp(split_summary[2]['first_received'])
    assert train_end<valid_start and valid_end<test_start
    assert pd.Timestamp(split_summary[2]['last_label_observation_day'])<=pd.Timestamp('2016-06-30')
    assert actual[actual.split.eq('train')].y.nunique()==2
    dest=ROOT/'data/processed/model_samples_v1.csv';dest.parent.mkdir(parents=True,exist_ok=True)
    actual.to_csv(dest,index=False)
    out=ROOT/'reports/tables'
    pd.DataFrame(split_summary).to_csv(out/'lesson7_time_split.csv',index=False,encoding='utf-8-sig')
    report={'status':'passed','all_model_records_and_fields_match_original_csv':True,
      'cutoff_checks':audits,'time_label_gap_checks':'passed','splits':split_summary,
      'raw_sha256':hashlib.sha256(RAW.read_bytes()).hexdigest(),
      'sql_export_sha256':hashlib.sha256(EXPORT.read_bytes()).hexdigest(),
      'processed_csv_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
    (out/'lesson7_data_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
