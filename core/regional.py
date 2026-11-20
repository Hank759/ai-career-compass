"""Regional wages and BEA price-level proxies with conservative geography matching."""
import json,re
from functools import lru_cache
from pathlib import Path
import pandas as pd
from core import data_access as d

@lru_cache(maxsize=1)
def prices():
    return pd.DataFrame(json.loads((Path(__file__).resolve().parents[1]/'data/reference/regional_prices.json').read_text(encoding='utf-8')))

def normalized_name(name):
    return re.sub(r'\s+',' ',str(name).replace(' (Metropolitan Statistical Area)','').strip()).casefold()

def adjust(frame,scope):
    ref=prices();ref=ref[ref.scope==scope].copy()
    if ref.area.duplicated().any():raise ValueError('Ambiguous BEA geography code')
    out=frame.merge(ref[['area','bea_name','rpp','year','source']],on='area',how='left',validate='many_to_one',suffixes=('','_rpp'))
    matched=out.area_title.map(normalized_name)==out.bea_name.map(normalized_name)
    for column in ['rpp','year_rpp','source']:
        if column in out:out.loc[~matched,column]=None
    out['price_match']=matched & out.rpp.notna()
    out['price_adjusted_wage']=out.a_median.div(out.rpp/100)
    return out

def wage_catalog(scope,area):
    table,path=d.TABLES[scope]
    return d.frame(f'''SELECT r.OCC_CODE AS code,r.OCC_TITLE AS occupation,b.a_median AS median_wage,b.tot_emp AS employment,
        b.area,r.AREA_TITLE AS area_title,b.year
        FROM "{table}" r JOIN sources s ON s.table_name=?
        JOIN bls_observations b ON b.source_id=s.id AND b.source_row=r._src_row
        WHERE b.area=? AND b.o_group='detailed' AND b.naics='000000' AND b.own_code='1235' ''',(table,area))

def recommendation_inputs(profile):
    from core import planning as p
    region=profile.get('preferred_region') or {}
    scope=region.get('scope','National')
    if scope=='National':return p.wage_catalog(),{'scope':'National','basis':'Nominal USD','wage_year':2025}
    rows=wage_catalog(scope,region['area'])
    if rows.code.duplicated().any():raise ValueError('Ambiguous regional occupational records')
    rows=adjust(rows.rename(columns={'median_wage':'a_median'}),scope).rename(columns={'a_median':'nominal_median_wage'})
    basis=region.get('wage_basis','Nominal USD')
    rows['median_wage']=rows.price_adjusted_wage if basis=='Price-adjusted proxy' else rows.nominal_median_wage
    return rows,{'scope':scope,'area':region['area'],'area_title':rows.area_title.iloc[0] if not rows.empty else region['area'],
        'basis':basis,'wage_year':2025,'rpp_year':2024,'matched_price_rows':int(rows.price_match.sum()),'occupation_rows':len(rows)}

def explanation():
    return ('Price-adjusted proxy = May 2025 median annual wage / (2024 BEA all-items RPP / 100). '
        'RPP uses U.S. = 100. This mixes reference years and approximates relative purchasing power; it is not a 2025 cost-of-living estimate, '
        'inflation adjustment, disposable income or a household budget. Taxes, individual housing costs and relocation costs are excluded. '
        'Both area code and normalized area name must match. Unmatched codes or names remain missing; unchanged boundaries are not independently verified.')

def comparison_panel(frame,scope):
    import streamlit as st
    rows=adjust(frame,scope)
    st.subheader('Compare purchasing-power proxies')
    st.caption(explanation())
    st.caption(f'{int(rows.price_match.sum())} of {len(rows)} published area records match the bundled 2024 price reference. Unmatched areas and unpublished wages remain blank.')
    basis=st.segmented_control('Regional wage comparison',['Nominal USD','Price-adjusted proxy'],default='Nominal USD',key='regional_wage_basis') or 'Nominal USD'
    measure='a_median' if basis=='Nominal USD' else 'price_adjusted_wage'
    chart=rows[['area_title',measure]].dropna().sort_values(measure,ascending=False).head(10)
    if not chart.empty:st.bar_chart(chart,x='area_title',y=measure,horizontal=True,x_label=basis,y_label='Area',alt='Ten highest available area wage values using the selected nominal or purchasing-power proxy measure')
    st.dataframe(rows[['area_title','a_median','rpp','price_adjusted_wage','price_match','source']].rename(columns={'area_title':'Area','a_median':'2025 median wage (USD)','rpp':'2024 RPP (US=100)','price_adjusted_wage':'Price-adjusted wage proxy','price_match':'Matched geography','source':'Price source'}),hide_index=True,alt='Nominal wages, regional prices, adjusted proxies and geography matches')
    st.download_button('Download regional price comparison',rows.to_csv(index=False).encode('utf-8-sig'),'regional_price_comparison.csv','text/csv',key='download_regional_prices')
    st.markdown('[BEA regional price parities and methodology](https://www.bea.gov/data/prices-inflation/regional-price-parities-state-and-metro-area)')
