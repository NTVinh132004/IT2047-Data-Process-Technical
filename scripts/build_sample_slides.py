"""PowerPoint editable và bản PDF/HTML đọc được từ cùng metrics sample, không đọc raw loan ID."""
import base64
import hashlib
import json
import math
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.util import Inches, Pt

from experiments.charts import load as load_experiment, measured, stats
from experiments.run import RESULTS as EXPERIMENTS

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/reports/sample-report'
DARK='143D35'; INK='163C33'; TEAL='087F73'; GOLD='C58B24'; MUTED='536A63'; WHITE='FFFFFF'; LIGHT='F1F7F4'
COLORS=[TEAL,GOLD,'BB5954','739C6B','69788F','A37DA2']
matplotlib.rcdefaults()  # experiments.charts đặt rcParams toàn cục (nền, grid); slide dùng mặc định riêng
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False})


def rgb(s):return RGBColor.from_string(s)
def num(n):return f'{n:,}'.replace(',','.')
def pct(n,d):return f'{100*n/d:.2f}%'.replace('.',',')


def main():
    m=json.loads((OUT/'metrics.json').read_text())
    if not m['passed']:raise RuntimeError('Sample chưa đối soát đạt')
    figures=OUT/'figures'; figures.mkdir(exist_ok=True)
    def med(name,field,**where):
        rows=[r for r in measured(load_experiment(name)) if all(r[k]==v for k,v in where.items())]
        return stats([float(r[field]) for r in rows])[0]
    def sec(v):return f'{v:.2f}'.replace('.',',') if v<10 else f'{v:,.0f}'.replace(',','.')
    storage={r['table']:r for r in load_experiment('tn7_storage')}
    faults={r['method']:r for r in load_experiment('tn7_reader_faults')}
    tn1={x:med('tn1_scale','end_to_end_s',subset=x) for x in ('p25','p50','p100')}
    k_last=max(int(r['periods_loaded']) for r in load_experiment('tn2_incremental'))
    tn2={m:med('tn2_incremental','wall_s',method=m,periods_loaded=str(k_last)) for m in ('incremental','full_refresh')}
    tn4={(sc,m):med('tn4_pit','seconds',scenario=sc,method=m) for sc in ('all_months','one_month') for m in ('pit','direct')}
    tn6=load_experiment('tn6_storage')
    split_mib=sum(int(r['size_bytes']) for r in tn6 if r['design']=='split')/2**20
    merged_mib=sum(int(r['size_bytes']) for r in tn6 if r['design']=='merged')/2**20
    slices=measured(load_experiment('tn7_bronze_slice'))
    slice_txt=stats([float(r['seconds']) for r in slices if r['method']=='txt_direct'])[0]
    slice_landing=stats([float(r['seconds']) for r in slices if r['method']=='landing'])[0]
    def mib(t):return f"{int(storage[t]['size_bytes'])/2**20:.1f}".replace('.',',')
    preview=OUT/'slide-preview';preview.mkdir(exist_ok=True)
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    prs.core_properties.title='Lakehouse và Data Vault 2.0 — Freddie Mac sample 2019'
    prs.core_properties.subject='Kỹ thuật xử lý dữ liệu, thực nghiệm C5 và phân tích mô tả trên sample (R-38)'
    prs.core_properties.author='Dự án mortgage-datavault'
    content_layout=prs.slide_layouts[5];content_layout.name='Nội dung sample'
    title_ph=content_layout.placeholders[0];title_ph.left=Inches(.6);title_ph.top=Inches(.4);title_ph.width=Inches(12.1);title_ph.height=Inches(.85)
    page_data=[];current=None
    def page(title,notes='',dark=False):
        nonlocal current
        slide=prs.slides.add_slide(content_layout)
        slide.background.fill.solid();slide.background.fill.fore_color.rgb=rgb(DARK if dark else WHITE)
        shape=slide.shapes.title;shape.text=title
        shape.text_frame.margin_left=0;shape.text_frame.margin_right=0
        for p in shape.text_frame.paragraphs:p.font.name='Arial';p.font.size=Pt(36);p.font.bold=True;p.font.color.rgb=rgb(WHITE if dark else INK)
        slide.notes_slide.notes_text_frame.text=notes+'\nNguồn số liệu: data/reports/sample-report/metrics.json; sample 2019. Không đại diện bộ đầy đủ.\nC0–C4: hồ sơ 30/10/2026; đối soát sample 31/10/2026; thực nghiệm C5: experiments/results/ (R-38).'
        current={'title':title,'dark':dark,'elements':[],'notes':notes,'slide':slide}
        page_data.append(current)
        box(.6,7.06,11.5,.2,'Freddie Mac sample 2019  ·  05/11/2026  ·  Kết quả trong phạm vi sample',10,color='A9CAC0' if dark else MUTED)
        box(12.15,7.02,.5,.25,f'{len(page_data):02d}',12,color='A9CAC0' if dark else MUTED)
        return slide
    def box(x,y,w,h,text,size=20,color=INK,bold=False,fill=None):
        slide=current['slide']
        sh=slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x),Inches(y),Inches(w),Inches(h)) if fill else slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
        sh.name=f'S{len(page_data):02d}_text_{len(current["elements"])}'
        if fill:sh.fill.solid();sh.fill.fore_color.rgb=rgb(fill);sh.line.fill.background()
        tf=sh.text_frame;tf.clear();tf.margin_left=Inches(.15 if fill else 0);tf.margin_right=Inches(.15 if fill else 0);tf.margin_top=Inches(.12 if fill else 0);tf.word_wrap=True
        wrapped='\n'.join(textwrap.fill(line,width=max(15,int((w-.3 if fill else w)*72/(size*.53))),break_long_words=False) for line in str(text).split('\n'))
        for i,line in enumerate(wrapped.split('\n')):
            p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line;p.font.name='Arial';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=rgb(color);p.space_after=Pt(3)
        current['elements'].append(dict(type='text',x=x,y=y,w=w,h=h,text=wrapped,size=size,color=color,bold=bold,fill=fill))
    def card(x,y,w,value,label):
        box(x,y,w,1.65,'',fill=LIGHT)
        box(x+.2,y+.2,w-.4,.65,value,36,color=TEAL,bold=True)
        box(x+.2,y+1.0,w-.4,.5,label,17,color=MUTED)
    def chart(key,labels,series,title,kind='line',x=.7,y=1.65,w=8.2,h=4.75,percent=True,doc=True):
        data=CategoryChartData();data.categories=labels
        for name,values in series:data.add_series(name,values)
        typ=XL_CHART_TYPE.LINE if kind=='line' else XL_CHART_TYPE.BAR_CLUSTERED
        obj=current['slide'].shapes.add_chart(typ,Inches(x),Inches(y),Inches(w),Inches(h),data).chart
        obj.has_legend=len(series)>1
        if obj.has_legend:
            obj.legend.position=XL_LEGEND_POSITION.BOTTOM
            obj.legend.font.size=Pt(12)
        obj.has_title=False;obj.chart_style=10
        obj.value_axis.tick_labels.font.size=Pt(12);obj.category_axis.tick_labels.font.size=Pt(12)
        obj.value_axis.tick_labels.number_format='0.0%' if percent else '#,##0'
        if kind=='line':
            obj.category_axis.tick_label_spacing=max(1,len(labels)//8)
        for idx,s in enumerate(obj.series):
            s.format.line.color.rgb=rgb(COLORS[idx%len(COLORS)])
            if kind!='line':s.format.fill.solid();s.format.fill.fore_color.rgb=rgb(COLORS[idx%len(COLORS)])
        spec=dict(type='chart',key=key,labels=labels,series=series,title=title,kind=kind,x=x,y=y,w=w,h=h,percent=percent)
        current['elements'].append(spec)
        if doc:
            fig,ax=plt.subplots(figsize=(11,4.8));draw_chart(ax,spec);fig.tight_layout();fig.savefig(figures/f'{key}.png',dpi=150);fig.savefig(figures/f'{key}.svg');plt.close(fig)
    def image(path,x,y,w):
        import matplotlib.image as mpimg
        h=w*mpimg.imread(path).shape[0]/mpimg.imread(path).shape[1]
        current['slide'].shapes.add_picture(str(path),Inches(x),Inches(y),width=Inches(w))
        current['elements'].append(dict(type='image',path=str(path),x=x,y=y,w=w,h=h))
    def commentary(head,body):
        box(9.25,1.8,3.25,.9,head,26,color=TEAL,bold=True)
        box(9.25,2.95,3.2,3.4,body,18,color=MUTED)
    def diagram(labels):
        count=len(labels);w=11.9/count
        for i,(title,detail) in enumerate(labels):
            x=.65+i*w
            box(x,2.25,w-.18,1.3,title,20,bold=True,fill=LIGHT)
            box(x,3.9,w-.2,1.6,detail,17,color=MUTED)
            if i<count-1:box(x+w-.29,2.62,.35,.4,'→',20,color=TEAL)
    def draw_chart(ax,spec):
        labels=spec['labels'];series=spec['series'];xs=list(range(len(labels)))
        if spec['kind']=='line':
            for idx,(name,values) in enumerate(series):ax.plot(xs,[float('nan') if v is None else v for v in values],label=name,color='#'+COLORS[idx],linewidth=2)
            ticks=list(range(0,len(labels),max(1,len(labels)//7)));ax.set_xticks(ticks,[labels[i] for i in ticks],rotation=25,ha='right')
        else:
            width=.75/len(series)
            for idx,(name,values) in enumerate(series):ax.barh([i+idx*width for i in xs],values,height=width,label=name,color='#'+COLORS[idx])
            ax.set_yticks([i+(len(series)-1)*width/2 for i in xs],labels);ax.invert_yaxis()
        if spec['percent']:
            from matplotlib.ticker import PercentFormatter
            (ax.yaxis if spec['kind']=='line' else ax.xaxis).set_major_formatter(PercentFormatter(1))
        ax.grid(axis='y' if spec['kind']=='line' else 'x',alpha=.15)
        if len(series)>1:ax.legend(loc='best',fontsize=10)
        ax.set_title(spec['title'],loc='left',fontsize=15,pad=14,color='#'+INK)
    page('Lakehouse + Data Vault 2.0','Phạm vi: implementation sample, không phải nghiệm thu hiệu năng full.',True)
    box(.7,1.7,11.8,1.25,'Truy vết lịch sử và phân tích rủi ro tín dụng',32,color=WHITE,bold=True)
    box(.7,3.4,10.7,1.3,'Freddie Mac sample vintage 2019\nĐồ án cao học · Kỹ thuật xử lý dữ liệu',24,color='B9D7CD')
    box(.7,5.5,10.7,.7,'TXT → Delta Lake → Data Vault → PostgreSQL → Notebook',22,color='E3B65C')
    page('Kết quả chính trên sample','C1 end_to_end_seconds; C4 ac05/ac08; đối soát hiện tại metrics source_files/monthly.')
    card(.7,1.7,3.7,'50.000','khoản vay trong nguồn')
    card(4.8,1.7,3.7,'1.934.614','quan sát khoản vay–tháng')
    card(8.9,1.7,3.7,'87 tháng','01/2019–03/2026')
    box(.8,4.0,11.5,.9,'Đã có: 29 quý + CORR1; 6 tầng SUCCESS; 8 biểu đồ',26,bold=True)
    box(.8,5.35,11.5,.9,f'5 thực nghiệm C5 × 3 lần đo: pipeline {sec(tn1["p25"])}s → {sec(tn1["p100"])}s khi dữ liệu tăng 3,9 lần',22,color=MUTED)
    page('Bài toán cần giữ lịch sử','FR-14, R-17, R-36. SCD1 chỉ là đối chứng cụ thể; không phủ nhận SCD2.')
    diagram([('Nguồn đến theo kỳ','Khoản vay có nhiều quan sát tháng'),('Có sửa dữ liệu','Giá trị cũ cần còn truy vấn được'),('Raw Vault','Giữ phiên bản và nguồn giao'),('Mart / notebook','Trả lời câu hỏi rủi ro')])
    box(.8,6.0,11.7,.5,'Đối chứng là SCD1, không phải mọi phương án star schema',19,color=TEAL)
    page('Dữ liệu và đợt sửa tách riêng','metrics source_files/tables; C3 ac09. 50.020 Bronze orig bao gồm 20 correction, không phải 50.020 dòng TXT.')
    card(.7,1.7,3.7,'50.000','dòng orig TXT')
    card(4.8,1.7,3.7,'20 dòng','CORR1 giả lập, thêm sau kỳ cuối')
    card(8.9,1.7,3.7,'50.020','dòng Bronze orig sau CORR1')
    box(.8,4.1,11.5,.8,'Perf và fact không tăng thêm tháng vì sửa orig',25,bold=True)
    box(.8,5.35,11.5,.8,'SHA-256 nguồn và phiên bản Delta được lưu cùng metrics',20,color=MUTED)
    page('Kiến trúc chạy trên một máy','PRD R-25/R-33/R-36. Delta local, không MinIO/Metabase. PostgreSQL chỉ serving/control/metastore/Airflow.')
    diagram([('Bronze','PySpark\nChuỗi nguồn, cắt lát kỳ'),('Quality','Hard rule\nQuarantine / dedup'),('Silver','dbt + automate-dv\nRaw Vault + BV / PIT'),('Gold','Fact + 5 dimension\n3 mart'),('Serving','JDBC → PostgreSQL\nNotebook / Jupyter')])
    box(.8,6.0,11.5,.5,'Airflow: mỗi tầng một DAG, đọc control.layer_run; pool 1 slot Spark, 1 slot dbt',20,color=TEAL)
    page('TXT → landing → Bronze: đọc một lần','TN7 (R-28, R-27, SP-06/07): experiments/results/tn7_*.csv; trung vị 3 lần đo, lake thực nghiệm p100.')
    diagram([('TXT perf',f"{mib('sample_perf_2019.txt')} MiB · 1 file\ntext + split, giữ chuỗi\n_field_count, _raw"),('Landing Delta',f"{mib('landing.sample_perf')} MiB · {storage['landing.sample_perf']['num_files']} file\nphân vùng theo tháng"),('Bronze','replaceWhere theo kỳ\nchỉ đọc 3 thư mục tháng'),('Quality','clean + quarantine\n+ dedup = Bronze')])
    box(.8,5.75,11.6,.5,f'Lát Bronze một kỳ: {sec(slice_txt)}s đọc thẳng TXT → {sec(slice_landing)}s qua landing',21,color=TEAL,bold=True)
    box(.8,6.35,11.6,.5,f"Sai số trường cài sẵn: text + split bắt {faults['text_split']['detected']}/20 · CSV mặc định 0/20 · CSV FAILFAST dừng cả lần đọc",17,color=MUTED)
    page('Raw Vault gồm Hub, Link, Satellite','Model raw_vault: 3 hub, 2 link, 5 satellite thuộc tính và 2 record-tracking satellites.')
    for x1,y1,x2,y2 in [(2.1,2.5,3.9,3.15),(6.65,2.5,3.9,3.15),(10.9,2.5,9.4,3.15),(6.65,2.5,9.4,3.15),(6.65,2.5,6.65,4.45)]:
        line=current['slide'].shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2))
        line.line.color.rgb=rgb(TEAL);line.line.width=Pt(1.5)
        current['elements'].append(dict(type='line',x=x1,y=y1,w=x2-x1,h=y2-y1))
    box(.7,1.7,2.8,.8,'Hub Seller',21,bold=True,fill=LIGHT)
    box(5.25,1.7,2.8,.8,'Hub Loan',21,bold=True,fill=LIGHT)
    box(9.5,1.7,2.8,.8,'Hub Servicer',21,bold=True,fill=LIGHT)
    box(2.3,3.15,3.25,.8,'Link Loan–Seller',20,bold=True,fill=LIGHT)
    box(7.75,3.15,3.25,.8,'Link Loan–Servicer',20,bold=True,fill=LIGHT)
    box(4.25,4.45,4.8,1.35,'5 Satellite của Loan\nOrigination · Property · Balance\nDelinquency · Termination',18,bold=True,fill=LIGHT)
    box(.8,6.1,11.7,.6,'Tracking: xts_loan và xts_loan_servicer · Hash SHA-256 cố định · insert-only',18,color=TEAL)
    page('Kỳ điều phối khác tháng nghiệp vụ','DEV-03, R-01. load_date là thời điểm đến giả lập, không phải thời gian insert thật.')
    diagram([('2019Q1','Một kỳ yêu cầu qua Airflow'),('201901','reporting_period\nTháng báo cáo'),('2019-02-01','load_date giả lập\nNgày đầu tháng sau'),('Control','started_at / finished_at\nThời gian chạy thật')])
    box(.8,6.0,11.5,.5,'Không dùng chung một load_date cho cả quý',22,color=TEAL,bold=True)
    page('Hard rule trước, soft rule sau Raw Vault','R-35. Sample thực tế không có quarantine; fixture giả kiểm khả năng bắt lỗi.')
    diagram([('Giữ nguyên','Bronze và Raw giữ mã thiếu thô'),('Chặn kỹ thuật','Số trường, khóa, kiểu, trùng xung đột'),('Báo cáo nghiệp vụ','BV quality_violation\nKhông loại khỏi Raw')])
    box(.8,6.0,11.5,.6,'Bronze = clean + quarantine + dedup; sample hiện khớp',21,color=TEAL)
    page('Kiểm chứng MVP và chạy lại an toàn','C0–C4 tại snapshot C4: 69 tests, không phải 69 lần đo. Baseline C1 là một lần.')
    card(.7,1.7,3.7,'69/69','kiểm tra tại mốc C4')
    card(4.8,1.7,3.7,'0 lệch','87 tháng ở cổng C4')
    card(8.9,1.7,3.7,'17m 36,6s','một baseline nạp đầu sample')
    box(.8,4.0,11.5,1.0,'C2/C3/C4: chạy lại giữ số dòng; C4 thử rollback và chặn export khi Gold lỗi',23,bold=True)
    box(.8,5.6,11.5,.75,'Đối soát mới: TXT → mart PostgreSQL về số dòng/dư nợ; Gold bằng mart về số dòng',18,color=MUTED)
    page('FR-14: sửa dữ liệu vẫn giữ bản cũ','C3 ac09: 20/20 đúng. Sat origination có 50.021 dòng gồm một ghost; baseline SCD1 50.000.')
    diagram([('Đợt gốc','50.000 khoản vay\nSatellite giữ phiên bản đầu'),('CORR1','20 khoản vay được sửa\nload_date mới'),('Satellite','Thêm 20 phiên bản\nBản cũ còn nguyên'),('SCD1 đối chứng','50.000 dòng\nChỉ còn giá trị mới')])
    box(.8,6.0,11.5,.5,'Không suy ra Data Vault luôn tốt hơn mô hình chiều có lịch sử',19,color=TEAL)
    page('TN1 · Quy mô và chi phí cố định','tn1_scale.csv: mỗi lần đo dựng stack và lake mới; AC-01/05/06 đạt mọi lần chạy.')
    image(EXPERIMENTS/'tn1_scale.png',.7,1.55,11.9)
    box(.8,6.3,11.6,.5,f'Dữ liệu ×3,9 → thời gian +{100*(tn1["p100"]/tn1["p25"]-1):.0f}% · ingest không đổi · Raw Vault theo số lô (p25: 6 lô, p100: 2 lô) · AC đạt 9/9 lần',17,color=TEAL)
    page('TN2 · Incremental và TN4 · PIT','tn2_incremental.csv: số dòng incremental = full refresh ở mọi mốc. tn4_pit.csv: checksum PIT = join trực tiếp.')
    image(EXPERIMENTS/'tn2_incremental.png',.5,1.6,6.1)
    image(EXPERIMENTS/'tn4_pit.png',6.75,1.6,6.1)
    box(.8,5.4,5.8,1.1,f'{k_last} kỳ: incremental {sec(tn2["incremental"])}s, full refresh {sec(tn2["full_refresh"])}s; cùng số dòng',17,color=MUTED)
    box(7.0,5.4,5.6,1.1,f'Mọi tháng: PIT {sec(tn4[("all_months","pit")])}s, join as-of {sec(tn4[("all_months","direct")])}s; cùng checksum',17,color=MUTED)
    page('TN6 · Tách Satellite theo tốc độ đổi','tn6_storage.csv, tn6_query.csv. Parquet nén cột nên Satellite gộp không lớn hơn tổng ba Satellite tách.')
    image(EXPERIMENTS/'tn6_split.png',.7,1.55,11.9)
    q_split=med('tn6_query','seconds',design='split');q_merged=med('tn6_query','seconds',design='merged')
    box(.8,6.3,11.6,.5,f'Lợi ở truy vấn lịch sử quá hạn ({sec(q_split)}s so với {sec(q_merged)}s), không ở dung lượng ({split_mib:.1f} so với {merged_mib:.1f} MiB)'.replace('.',','),18,color=TEAL)
    dates=[r['reporting_date'][:7] for r in m['monthly']]
    monthly=[(name,[r[k]/r['eligible_count'] if r['eligible_count'] else None for r in m['monthly']]) for name,k in [('30–59 ngày','d30_count'),('60–89 ngày','d60_count'),('90+ ngày','d90_plus_count')]]
    page('Q1 · Quá hạn tăng trong giai đoạn COVID','metrics monthly; max 90+ Feb2021 1073/30067; March2026 134/14246. Không nhân quả.')
    chart('monthly',dates,monthly,'Tỷ lệ trên khoản vay hoạt động có trạng thái hợp lệ')
    commentary('Đỉnh 90+: 3,57%','02/2021: 1.073 / 30.067\n03/2026: 0,94%\n\nDanh mục và quy mô thay đổi theo thời gian; không suy ra tác động chính sách')
    def band(col):
        rows=m['bands'][col];return [r['label'] for r in rows],[r['d90_plus_count']/r['eligible_count'] for r in rows]
    page('Q2 · Điểm tín dụng, LTV, DTI và quá hạn 90+','metrics bands credit/ltv/dti. Mẫu số là quan sát khoản vay–tháng hợp lệ, không phải khoản vay duy nhất; không nhân quả.')
    labels,values=band('credit_score_band');chart('credit',labels,[('90+',values)],'Điểm tín dụng',kind='bar',x=.5,y=1.7,w=4.2,h=4.5)
    labels,values=band('ltv_band');chart('ltv',labels,[('90+',values)],'LTV',kind='bar',x=4.75,y=1.7,w=4.1,h=4.5)
    labels,values=band('dti_band');chart('dti',labels,[('90+',values)],'DTI',kind='bar',x=8.9,y=1.7,w=4.1,h=4.5)
    box(.8,6.35,11.7,.4,'Tỷ lệ 90+ gộp toàn thời gian · 620–679: 3,49%, ≥780: 0,38% · nhóm <620 chỉ 1.744 quan sát',16,color=MUTED)
    # Hình gộp cho tài liệu, giữ hai biểu đồ native riêng trong PowerPoint.
    fig,axes=plt.subplots(1,2,figsize=(12,4.6))
    for ax,col,title in zip(axes,['ltv_band','dti_band'],['LTV','DTI']):
        labels,values=band(col);draw_chart(ax,dict(labels=labels,series=[('90+',values)],kind='bar',title=title,percent=True))
    fig.tight_layout();fig.savefig(figures/'ltv_dti.png',dpi=150);plt.close(fig)
    page('Q3 · So sánh bang và bên bán','metrics bands property_state/seller_name. Chỉ hiển thị nhóm >=10000 quan sát; OTHER là tổng hợp.')
    for x,col,key,title in [(.7,'property_state','states','Bang · 10 nhóm tỷ lệ cao'),(7,'seller_name','sellers','Seller · OTHER là tổng hợp')]:
        rows=sorted((r for r in m['bands'][col] if r['eligible_count']>=10000),key=lambda r:r['d90_plus_count']/r['eligible_count'],reverse=True)[:10]
        labels=[r['label'] if len(r['label'])<=25 else r['label'][:22]+'…' for r in rows]
        chart(key,labels,[('90+',[r['d90_plus_count']/r['eligible_count'] for r in rows])],title,kind='bar',x=x,y=1.65,w=5.65,h=4.8)
    box(.8,6.4,11.7,.4,'Ngưỡng trình bày: ≥10.000 quan sát hợp lệ gộp toàn thời gian; không phải kiểm định',16,color=MUTED)
    page('Q4 · Kết cục cohort hoãn trả COVID','metrics covid; tổng3310. R-36 window12thángsauFlast; hồi cứu không dùng như dự báo tại thời điểm F.')
    chart('covid',[r['outcome'] for r in m['covid']],[('Khoản vay',[r['loan_count'] for r in m['covid']])],'3.310 khoản vay · kết cục hồi cứu',kind='bar',percent=False)
    commentary('43,23% hồi phục','35,98% trả trước\n15,83% vỡ nợ lần đầu\n1,21% UNKNOWN\n\nKhông đo tác động nhân quả của chương trình hoãn trả')
    page('Q5 · Trả trước hạn SMM và CPR','metrics prepayment. CPR annualized, không phải xác suất dự báo; early Feb2019 lowdenominator8.341m30loans.')
    chart('prepayment',[r['reporting_date'][:7] for r in m['prepayment']],[(k.upper(),[float(r[k]) if r[k] is not None else None for r in m['prepayment']]) for k in ['smm','cpr']],'SMM và CPR · giữ cả giai đoạn đầu vintage')
    commentary('03/2021: CPR 52,80%','Trong giai đoạn từ 2020\n\n02/2019 có mẫu số rất nhỏ (30 khoản vay tháng trước), nên CPR nhạy\n\nKhông đồng nhất trả trước với tái cấp vốn')
    page('Kết luận, giới hạn và demo','Nguồn: docs/bao-cao-do-an.md, PRD 1.9, R-33/R-36/R-38; C1–C5 JSON. AutomateDV loading https://automate-dv.readthedocs.io/en/latest/best_practises/loading/ ; PostgreSQL transactions https://www.postgresql.org/docs/16/tutorial-transactions.html',True)
    box(.8,1.6,11.6,1.3,'Luồng TXT → Delta → Data Vault → PostgreSQL giữ lịch sử, chạy lại an toàn và đo được từng tầng',27,color=WHITE,bold=True)
    box(.8,3.2,11.5,1.6,'Giới hạn: một vintage, một nguồn, bộ mẫu 50.000 khoản vay, một máy; load_date giả lập; đối chứng FR-14 chỉ là SCD1; không suy rộng hiệu năng lên bộ đầy đủ',19,color='B9D7CD')
    box(.8,5.0,11.5,1.2,'Demo: Airflow / control.layer_run → CORR1 và PIT trước/sau → mart PostgreSQL → notebook → experiments/results',19,color='E3B65C')
    pptx=OUT/'bao-cao-sample.pptx';prs.save(pptx)
    # PDF và preview được render từ mô tả bố cục chung, không giả làm bản chuyển đổi Office.
    with PdfPages(OUT/'bao-cao-sample.pdf') as pdf:
        for idx,spec in enumerate(page_data,1):
            fig=plt.figure(figsize=(13.333,7.5),facecolor='#'+(DARK if spec['dark'] else WHITE))
            title=fig.text(.6/13.333,1-.57/7.5,spec['title'],fontsize=36,fontweight='bold',va='top',color='#'+(WHITE if spec['dark'] else INK))
            for el in spec['elements']:
                x,y,w,h=[el[k] for k in ('x','y','w','h')]
                if el['type']=='image':
                    import matplotlib.image as mpimg
                    ax=fig.add_axes([x/13.333,1-(y+h)/7.5,w/13.333,h/7.5]);ax.imshow(mpimg.imread(el['path']));ax.axis('off')
                elif el['type']=='chart':
                    pad=1.5 if el['kind']=='bar' and max(map(len,el['labels']))>12 else .8
                    ax=fig.add_axes([(x+pad)/13.333,1-(y+h-.4)/7.5,(w-pad-.15)/13.333,(h-.8)/7.5]);draw_chart(ax,el);ax.tick_params(labelsize=11)
                elif el['type']=='line':
                    from matplotlib.lines import Line2D
                    fig.lines.append(Line2D([x/13.333,(x+w)/13.333],[1-y/7.5,1-(y+h)/7.5],transform=fig.transFigure,color='#'+TEAL,linewidth=1.5,zorder=-.5))
                else:
                    if el['fill']:fig.patches.append(FancyBboxPatch((x/13.333,1-(y+h)/7.5),w/13.333,h/7.5,boxstyle='round,pad=0.004',transform=fig.transFigure,facecolor='#'+el['fill'],edgecolor='none',zorder=-1))
                    if el['text']:fig.text((x+(.15 if el['fill'] else 0))/13.333,1-(y+(.12 if el['fill'] else 0))/7.5,el['text'],va='top',fontsize=el['size'],fontweight='bold' if el['bold'] else 'normal',color='#'+el['color'],linespacing=1.2)
            pdf.savefig(fig);fig.savefig(preview/f'slide-{idx:02d}.png',dpi=85);plt.close(fig)
    slides=[]
    for idx in range(1,len(page_data)+1):
        data=base64.b64encode((preview/f'slide-{idx:02d}.png').read_bytes()).decode()
        slides.append(f'<section><img alt="Slide {idx}" src="data:image/png;base64,{data}"></section>')
    html='''<!doctype html><html lang="vi"><meta charset="utf-8"><title>Báo cáo sample 2019</title><style>body{margin:0;background:#102D27}section{display:none;height:100vh;align-items:center;justify-content:center}section.on{display:flex}img{max-width:100%;max-height:100vh;object-fit:contain}nav{position:fixed;bottom:8px;right:12px;color:white;font:14px Arial;background:#143D35;padding:7px;border-radius:7px}</style>'''+''.join(slides)+'''<nav>← →: chuyển slide · F: toàn màn hình · <span id="page"></span></nav><script>let i=0,s=[...document.querySelectorAll('section')];function show(){s.forEach((e,j)=>e.classList.toggle('on',i===j));document.getElementById('page').textContent=(i+1)+' / '+s.length}document.onkeydown=e=>{if(e.key==='ArrowRight'||e.key===' '){i=Math.min(i+1,s.length-1);show()}if(e.key==='ArrowLeft'){i=Math.max(0,i-1);show()}if(e.key.toLowerCase()==='f')document.documentElement.requestFullscreen()};show()</script></html>'''
    (OUT/'bao-cao-sample.html').write_text(html)
    # Nội dung và speaker notes dùng cho kiểm đọc, không ghi đối tượng slide vào JSON.
    outline=[{'slide':i+1,'title':s['title'],'notes':s['notes'],'texts':[e['text'] for e in s['elements'] if e['type']=='text']} for i,s in enumerate(page_data)]
    (OUT/'slide-outline.json').write_text(json.dumps(outline,ensure_ascii=False,indent=2))
    manifest={'slides':len(page_data),'metrics_sha256':hashlib.sha256((OUT/'metrics.json').read_bytes()).hexdigest(),'pdf_render':'Cùng mô tả bố cục/nội dung; không phải LibreOffice/PowerPoint export','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [pptx,OUT/'bao-cao-sample.pdf',OUT/'bao-cao-sample.html']}}
    manifest['native_charts']=sum(sh.has_chart for slide in prs.slides for sh in slide.shapes)
    (OUT/'build-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps(manifest,ensure_ascii=False))


if __name__=='__main__':main()
