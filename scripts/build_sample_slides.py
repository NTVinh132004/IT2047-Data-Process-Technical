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
STUDENT='Nguyễn Thế Vĩnh'; STUDENT_ID='26848266'
ADVISOR='……………………'  # chủ dự án tự điền
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
    prs.core_properties.author=STUDENT
    content_layout=prs.slide_layouts[5];content_layout.name='Nội dung sample'
    title_ph=content_layout.placeholders[0];title_ph.left=Inches(.6);title_ph.top=Inches(.4);title_ph.width=Inches(12.1);title_ph.height=Inches(.85)
    page_data=[];current=None
    def page(title,notes='',dark=False,section=''):
        nonlocal current
        slide=prs.slides.add_slide(content_layout)
        slide.background.fill.solid();slide.background.fill.fore_color.rgb=rgb(DARK if dark else WHITE)
        shape=slide.shapes.title;shape.text=title
        shape.text_frame.margin_left=0;shape.text_frame.margin_right=0
        for p in shape.text_frame.paragraphs:p.font.name='Arial';p.font.size=Pt(36);p.font.bold=True;p.font.color.rgb=rgb(WHITE if dark else INK)
        slide.notes_slide.notes_text_frame.text=notes+'\n\nNguồn: docs/bao-cao-do-an.md; số liệu data/reports/sample-report/metrics.json và experiments/results/. Bộ mẫu 2019, không đại diện bộ đầy đủ.'
        current={'title':title,'dark':dark,'elements':[],'notes':notes,'slide':slide}
        page_data.append(current)
        box(.6,7.06,11.5,.2,f'{STUDENT}  ·  Freddie Mac vintage 2019 (bộ mẫu)  ·  06/11/2026',10,color='A9CAC0' if dark else MUTED)
        if section:box(.6,.12,11.5,.3,section,13,color=TEAL,bold=True)
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
    def docfig(key,labels,series,title,kind='bar',percent=True):
        """Hình cho báo cáo (docs/bao-cao-do-an.md mục 6), không thêm vào slide."""
        fig,ax=plt.subplots(figsize=(11,4.8));draw_chart(ax,dict(labels=labels,series=series,title=title,kind=kind,percent=percent))
        fig.tight_layout();fig.savefig(figures/f'{key}.png',dpi=150);fig.savefig(figures/f'{key}.svg');plt.close(fig)
    def rows(items,y0=1.75,h=.95,gap=.18,left=5.3):
        """Mỗi hàng: vấn đề (ô màu) → giải pháp."""
        for i,(problem,solution) in enumerate(items):
            y=y0+i*(h+gap)
            box(.7,y,left,h,problem,17,bold=True,fill=LIGHT)
            box(.7+left+.1,y+.25,.5,.4,'→',22,color=TEAL,bold=True)
            box(.7+left+.7,y+.05,12.6-(.7+left+.7),h,solution,17,color=INK)
    def columns(items,y=1.75,h=4.6,size=16):
        """Các cột tiêu đề + nội dung."""
        w=11.9/len(items)
        for i,(head,body) in enumerate(items):
            x=.65+i*w
            box(x,y,w-.2,h,'',fill=LIGHT)
            box(x+.2,y+.15,w-.6,.5,head,22,color=TEAL,bold=True)
            box(x+.2,y+.85,w-.6,h-1.0,body,size,color=INK)
    def band(col):
        rows_=m['bands'][col];return [r['label'] for r in rows_],[r['d90_plus_count']/r['eligible_count'] for r in rows_]
    q_split=med('tn6_query','seconds',design='split');q_merged=med('tn6_query','seconds',design='merged')

    # ---------------------------------------------------------------- Mở đầu
    page('Đồ án môn Kỹ thuật xử lý dữ liệu','Giới thiệu đề tài, học viên. Nói một câu về bài toán: dữ liệu khoản vay đến theo đợt, có sửa đổi, cần giữ lịch sử và phân tích rủi ro.',True)
    box(.7,1.55,11.2,1.6,'Xây dựng Data Lakehouse kết hợp Data Vault 2.0\ntrên Apache Spark cho phân tích rủi ro tín dụng\nkhoản vay thế chấp',26,color=WHITE,bold=True)
    box(.7,3.5,11.2,1.0,'Dữ liệu: Freddie Mac Single-Family Loan-Level Dataset\nvintage 2019, bộ mẫu 50.000 khoản vay',19,color='B9D7CD')
    box(.7,4.85,11,1.4,f'Học viên: {STUDENT}  ·  MSHV: {STUDENT_ID}\nGiảng viên hướng dẫn: {ADVISOR}',22,color='E3B65C',bold=True)

    page('Lý do chọn đề tài','Ba đặc điểm của dữ liệu tín dụng làm bảng phẳng hoặc star schema ghi đè không đủ: dữ liệu đến theo đợt, bị sửa, và cần truy vết. Đó là lý do khảo sát Data Vault trên Lakehouse.',section='Mở đầu')
    columns([('Dữ liệu đến theo đợt','Freddie Mac công bố dữ liệu theo quý; mỗi khoản vay có một dòng trạng thái mỗi tháng.\n\nHệ thống phải nạp tăng dần, không nạp lại toàn bộ.'),
             ('Có lỗi và bị sửa','Dữ liệu lịch sử có thể được sửa ở lần phát hành sau; Release 47 (07/2026) đổi tên cột.\n\nGiá trị cũ vẫn phải truy vấn được.'),
             ('Cần truy vết','Kiểm toán hỏi: khoản vay ở trạng thái nào tại tháng X, theo dữ liệu của đợt nạp nào?\n\nMỗi dòng cần nguồn và thời điểm nạp.')],h=3.9)
    box(.8,5.9,11.6,.6,'Bảng ghi đè làm mất lịch sử → khảo sát Data Vault 2.0 làm lớp lưu lịch sử trên Lakehouse',19,color=TEAL,bold=True)

    page('Bài toán','Phát biểu bài toán: đầu vào, yêu cầu xử lý, đầu ra. Năm câu hỏi nghiệp vụ là tiêu chí kiểm tra đầu ra ở chương 4.',section='Mở đầu')
    diagram([('Đầu vào','2 file TXT orig/perf\n50.000 khoản vay\n1,93 triệu dòng tháng'),
             ('Xử lý','Nạp tăng dần theo kỳ\nGiữ lịch sử, chạy lại an toàn\nChặn lỗi kỹ thuật'),
             ('Đầu ra','Data Vault có lịch sử\nMart PostgreSQL\nNotebook phân tích')])
    box(.8,5.55,11.7,1.2,'Q1 quá hạn theo tháng (COVID) · Q2 điểm tín dụng, LTV, DTI · Q3 bang và bên bán · Q4 kết cục sau hoãn trả · Q5 trả trước hạn',17,color=MUTED)

    page('Mục tiêu và phạm vi','Mục tiêu đo được bằng tiêu chí nghiệm thu AC-01 đến AC-09 và cổng C0 đến C6. Phạm vi chốt ở bộ mẫu theo R-38; bộ đầy đủ và ML là hướng phát triển.',section='Mở đầu')
    columns([('Mục tiêu','• Pipeline tăng dần chạy bằng một lệnh\n• Lịch sử và truy vết đầy đủ, chạy lại không đổi số dòng\n• Trả lời 5 câu hỏi rủi ro tín dụng\n• Chứng minh thiết kế bằng 5 thực nghiệm, mỗi cấu hình 3 lần đo'),
             ('Phạm vi','• Bộ mẫu vintage 2019: 50.000 khoản vay, 29 quý (01/2019–03/2026)\n• Một máy: WSL2, RAM 12 GB, Docker\n• Ngoài phạm vi: bộ đầy đủ 8,2 GB, mô hình ML, streaming, cloud')],h=4.4,size=20)

    # ---------------------------------------------------------------- Chương 1
    page('Lakehouse, Medallion và Delta Lake','Medallion tổ chức dữ liệu theo mức hoàn thiện. Trong đồ án, Silver chứa Data Vault. Delta Lake là định dạng bảng: file Parquet cộng nhật ký giao dịch, cho phép ghi đè đúng lát và xem phiên bản cũ.',section='Chương 1 · Cơ sở lý thuyết')
    diagram([('Bronze','Dữ liệu nguồn giữ nguyên dạng chuỗi\nkèm nguồn, thời điểm nạp'),
             ('Silver','Raw Vault: lịch sử nguồn\nBusiness Vault: quy tắc nghiệp vụ'),
             ('Gold','Mô hình chiều và mart\ncho người phân tích')])
    box(.8,5.75,11.6,.9,'Delta Lake = file Parquet + nhật ký giao dịch: ACID, ghi đè đúng lát (replaceWhere), xem phiên bản cũ',18,color=TEAL)

    page('Data Vault 2.0','Bốn đối tượng chính. Điểm quan trọng: Satellite chỉ thêm dòng khi thuộc tính đổi (so hash_diff) và không bao giờ sửa hay xóa, nên giữ được mọi phiên bản.',section='Chương 1 · Cơ sở lý thuyết')
    columns([('Hub','Danh sách khóa nghiệp vụ; mỗi khóa một dòng'),
             ('Link','Quan hệ giữa các khóa; mỗi cặp một dòng'),
             ('Satellite','Thuộc tính có lịch sử; chỉ thêm khi hash_diff đổi'),
             ('PIT','Con trỏ tới phiên bản hiệu lực tại mỗi mốc')],y=1.75,h=3.6,size=18)
    box(.8,5.75,11.6,.9,'Raw Vault chỉ thêm, không sửa, không xóa; quy tắc nghiệp vụ nằm ở Business Vault để đổi luật không phải nạp lại',18,color=TEAL)

    page('Công nghệ sử dụng','Mỗi công cụ một vai trò. PySpark xử lý file và kiểm tra kỹ thuật; dbt mô hình hóa bằng SQL; Airflow điều phối mỗi tầng như một job độc lập.',section='Chương 1 · Cơ sở lý thuyết')
    columns([('PySpark','Landing, Bronze, cổng chất lượng, xuất PostgreSQL'),
             ('dbt','dbt-spark + AutomateDV: staging, Raw Vault, Business Vault, Gold bằng SQL'),
             ('Delta Lake','Lưu trữ trên đĩa; Hive Metastore, Spark Thrift Server'),
             ('Airflow','6 DAG theo tầng, bảng điều khiển, thử lại'),
             ('PostgreSQL','Mart phục vụ, notebook Jupyter')],y=1.75,h=3.6,size=17)
    box(.8,5.75,11.6,.9,'Spark 3.5.5 · Delta 3.3.2 · dbt-core 1.12 · AutomateDV 0.11.5 · Airflow 3.3 · Docker Compose',18,color=MUTED)

    # ---------------------------------------------------------------- Chương 2
    page('Bộ dữ liệu Freddie Mac','Hai file nối bằng mã khoản vay. Orig là thuộc tính lúc giải ngân, perf là trạng thái hằng tháng. Đợt sửa CORR1 là dữ liệu giả lập để kiểm chứng việc giữ lịch sử.',section='Chương 2 · Hiện trạng và dữ liệu')
    card(.7,1.7,3.7,'50.000','khoản vay (file orig)')
    card(4.8,1.7,3.7,'1.934.614','dòng khoản vay–tháng (perf)')
    card(8.9,1.7,3.7,'87 tháng','01/2019 – 03/2026')
    box(.8,3.85,11.6,1.6,'Orig: 31 trường lúc giải ngân (điểm tín dụng, LTV, DTI, bang, bên bán)\nPerf: 35 trường mỗi tháng (dư nợ, quá hạn, hoãn trả, kết thúc)\nTXT không tiêu đề, phân tách bằng |, layout Release 47',18,color=INK)
    box(.8,5.9,11.6,.6,'Đợt sửa CORR1 (giả lập): 20 khoản vay được sửa điểm tín dụng và DTI, nạp sau kỳ cuối',17,color=TEAL)

    page('Vấn đề dữ liệu → yêu cầu thiết kế','Mỗi vấn đề của dữ liệu dẫn tới một quyết định thiết kế ở chương 3. Đây là cầu nối giữa phân tích hiện trạng và thiết kế.',section='Chương 2 · Hiện trạng và dữ liệu')
    rows([('File chia theo quý khởi tạo, phân tích theo tháng báo cáo','Landing phân vùng theo tháng; mỗi kỳ nạp một quý báo cáo'),
          ('Sai số trường, mã thiếu 9999/XX, đổi tên cột','Đọc text rồi tách trường; hard rule trước Vault; schema trong conf/'),
          ('Dữ liệu bị sửa ở đợt sau','Satellite chỉ thêm phiên bản; load_date riêng cho mỗi tháng'),
          ('Nạp lại hoặc lỗi giữa chừng','Ghi đè đúng lát kỳ; bỏ qua dòng đã có; job theo tầng có thử lại')])

    # ---------------------------------------------------------------- Chương 3
    page('Kiến trúc hệ thống','Luồng dữ liệu từ TXT tới notebook. Mỗi tầng là một job Airflow riêng, đọc bảng điều khiển để biết kỳ nào sẵn sàng.',section='Chương 3 · Thiết kế hệ thống')
    diagram([('Bronze','PySpark\nchuỗi nguồn, cắt lát kỳ'),('Quality','Hard rule\nquarantine / dedup'),('Silver','dbt + AutomateDV\nRaw Vault, BV, PIT'),('Gold','Fact + 5 dimension\n3 mart'),('Serving','JDBC → PostgreSQL\nnotebook')])
    box(.8,6.0,11.5,.5,'Airflow: mỗi tầng một DAG, đọc control.layer_run; một slot Spark, một slot dbt',19,color=TEAL)

    page('Kỹ thuật nạp: TXT → landing → Bronze','Đọc TXT dạng text để giữ bằng chứng lỗi; ghi Delta phân vùng theo tháng để mỗi kỳ chỉ đọc 3 thư mục tháng. Số đo từ thực nghiệm TN7.',section='Chương 3 · Thiết kế hệ thống')
    diagram([('TXT perf',f"{mib('sample_perf_2019.txt')} MiB · 1 file\ntext + split, giữ chuỗi\n_field_count, _raw"),('Landing Delta',f"{mib('landing.sample_perf')} MiB · {storage['landing.sample_perf']['num_files']} file\nphân vùng theo tháng"),('Bronze','replaceWhere theo kỳ\nchỉ đọc 3 thư mục tháng'),('Quality','clean + quarantine\n+ dedup = Bronze')])
    box(.8,5.75,11.6,.5,f'Lát Bronze một kỳ: {sec(slice_txt)}s đọc thẳng TXT → {sec(slice_landing)}s qua landing (TN7)',20,color=TEAL,bold=True)
    box(.8,6.35,11.6,.5,f"Dòng sai số trường cài sẵn: text + split bắt {faults['text_split']['detected']}/20 · CSV mặc định 0/20",17,color=MUTED)

    page('Mô hình Raw Vault','3 Hub, 2 Link, 5 Satellite trên khoản vay và 2 satellite theo dõi hiện diện. Satellite tách theo tốc độ thay đổi: dư nợ đổi mỗi tháng, quá hạn ít đổi.',section='Chương 3 · Thiết kế hệ thống')
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
    box(.8,6.05,11.7,.7,'SHA-256 cho khóa và hash_diff · chỉ thêm khi hash_diff đổi · load_date = ngày 1 tháng sau tháng báo cáo',17,color=TEAL)

    page('Business Vault, PIT, Gold và điều phối','PIT cho phép lấy trạng thái tại một tháng bất kỳ bằng equi-join. Gold dựng lại từ Vault. Export công bố cả ba mart trong một transaction PostgreSQL.',section='Chương 3 · Thiết kế hệ thống')
    columns([('PIT','Con trỏ tới phiên bản hiệu lực tại mỗi mốc; ghost record nên mọi join là equi-join'),
             ('Business Vault','Số tháng quá hạn liên tiếp, vòng đời khoản vay, báo cáo soft rule'),
             ('Gold','Fact khoản vay × tháng, 5 dimension, 3 mart'),
             ('Airflow','6 DAG theo tầng; lease, thử lại có giới hạn')],y=1.75,h=3.8,size=17)
    box(.8,5.85,11.6,.7,'Export: JDBC vào bảng trung gian, đối soát số dòng, thay serving trong một transaction',18,color=TEAL)

    # ---------------------------------------------------------------- Chương 4
    page('Kiểm chứng hệ thống','Chín tiêu chí nghiệm thu đạt; toàn bộ 89 kiểm tra chạy lại đạt trên bản clone sạch. FR-14 là bằng chứng chính: Data Vault giữ bản cũ, bảng ghi đè thì mất.',section='Chương 4 · Thực nghiệm và đánh giá')
    card(.7,1.7,3.7,'AC-01–09','9 tiêu chí nghiệm thu đạt')
    card(4.8,1.7,3.7,'89/89','kiểm tra C0–C6 trên clone sạch')
    card(8.9,1.7,3.7,'0 lệch','dư nợ 87 tháng so với TXT')
    box(.8,3.9,11.6,1.3,'FR-14: sau đợt sửa CORR1, Satellite có phiên bản mới cho đúng 20 khoản vay, bản cũ còn nguyên; PIT trước/sau đợt sửa trả giá trị cũ/mới; bảng đối chứng ghi đè (SCD1) chỉ còn giá trị mới',18,color=INK)
    box(.8,5.6,11.6,.9,'Chạy lại một kỳ bất kỳ sinh 0 dòng mới ở Hub, Link, Satellite (AC-02)',18,color=TEAL)

    page('Thực nghiệm TN1: mở rộng quy mô','Ba tập con 25, 50, 100% khoản vay, mỗi tập 3 lần với stack mới. Ở quy mô mẫu, chi phí cố định của Spark và dbt chiếm phần lớn thời gian.',section='Chương 4 · Thực nghiệm và đánh giá')
    image(EXPERIMENTS/'tn1_scale.png',.7,1.55,11.9)
    box(.8,6.3,11.6,.5,f'Dữ liệu ×3,9 → thời gian +{100*(tn1["p100"]/tn1["p25"]-1):.0f}% · Raw Vault theo số lô (p25: 6, p100: 2) · đạt AC 9/9 lần',17,color=TEAL)

    page('Thực nghiệm TN2, TN4, TN6','Ba thực nghiệm chứng minh quyết định thiết kế Data Vault. Mỗi thực nghiệm có phép kiểm đúng: cùng số dòng hoặc cùng checksum.',section='Chương 4 · Thực nghiệm và đánh giá')
    image(EXPERIMENTS/'tn2_incremental.png',.5,1.5,6.1)
    image(EXPERIMENTS/'tn4_pit.png',6.75,1.5,6.1)
    box(.8,5.2,5.8,.9,f'TN2 · {k_last} kỳ: incremental {sec(tn2["incremental"])}s, full refresh {sec(tn2["full_refresh"])}s; cùng số dòng',16,color=MUTED)
    box(7.0,5.2,5.6,.9,f'TN4 · PIT {sec(tn4[("all_months","pit")])}s, join as-of {sec(tn4[("all_months","direct")])}s; cùng checksum',16,color=MUTED)
    box(.8,6.15,11.6,.6,f'TN6 · tách Satellite: truy vấn lịch sử quá hạn {sec(q_split)}s so với {sec(q_merged)}s; dung lượng {split_mib:.1f} so với {merged_mib:.1f} MiB (không tiết kiệm)'.replace('.',','),16,color=TEAL)

    dates=[r['reporting_date'][:7] for r in m['monthly']]
    monthly=[(name,[r[k]/r['eligible_count'] if r['eligible_count'] else None for r in m['monthly']]) for name,k in [('30–59 ngày','d30_count'),('60–89 ngày','d60_count'),('90+ ngày','d90_plus_count')]]
    page('Kết quả phân tích Q1–Q3','Q1: tỷ lệ 90+ cao nhất 3,57% ở 02/2021. Q2: nhóm điểm thấp quá hạn nhiều hơn. Q3: NJ, NV, NY cao nhất trong các bang đủ lớn. Đây là mô tả, không phải quan hệ nhân quả.',section='Chương 4 · Thực nghiệm và đánh giá')
    chart('monthly',dates,monthly,'Q1 · Tỷ lệ quá hạn theo tháng',x=.5,y=1.6,w=7.2,h=4.6)
    labels,values=band('credit_score_band');chart('credit',labels,[('90+',values)],'Q2 · 90+ theo điểm tín dụng',kind='bar',x=7.9,y=1.6,w=4.9,h=4.6)
    box(.8,6.4,11.9,.4,'Q1 đỉnh 90+ 3,57% (02/2021) · Q2 620–679: 3,49%, ≥780: 0,38% · Q3 NJ 2,52%, NV 2,04%, NY 1,91%',15,color=MUTED)
    page('Kết quả phân tích Q4–Q5','Q4: cohort 3.310 khoản vay hoãn trả COVID, 43% hồi phục, 36% trả trước, 16% vỡ nợ lần đầu. Q5: CPR đỉnh 52,8% ở 03/2021 khi lãi suất thấp.',section='Chương 4 · Thực nghiệm và đánh giá')
    chart('covid',[r['outcome'] for r in m['covid']],[('Khoản vay',[r['loan_count'] for r in m['covid']])],'Q4 · Kết cục sau hoãn trả (3.310 khoản vay)',kind='bar',percent=False,x=.5,y=1.6,w=5.8,h=4.6)
    chart('prepayment',[r['reporting_date'][:7] for r in m['prepayment']],[(k.upper(),[float(r[k]) if r[k] is not None else None for r in m['prepayment']]) for k in ['smm','cpr']],'Q5 · Trả trước hạn SMM và CPR',x=6.5,y=1.6,w=6.3,h=4.6)
    box(.8,6.35,11.7,.45,'Q4: 43,23% hồi phục · 35,98% trả trước · 15,83% vỡ nợ lần đầu · Q5: CPR đỉnh 52,80% (03/2021)',16,color=MUTED)
    # Hình cho báo cáo mục 6, không còn là trang riêng trong slide
    labels,values=band('ltv_band');docfig('ltv',labels,[('90+',values)],'LTV · tỷ lệ 90+ gộp')
    labels,values=band('dti_band');docfig('dti',labels,[('90+',values)],'DTI · tỷ lệ 90+ gộp')
    for col,key,title in [('property_state','states','Bang · 10 nhóm tỷ lệ cao'),('seller_name','sellers','Seller · OTHER là tổng hợp')]:
        top=sorted((r for r in m['bands'][col] if r['eligible_count']>=10000),key=lambda r:r['d90_plus_count']/r['eligible_count'],reverse=True)[:10]
        docfig(key,[r['label'] if len(r['label'])<=25 else r['label'][:22]+'…' for r in top],[('90+',[r['d90_plus_count']/r['eligible_count'] for r in top])],title)
    fig,axes=plt.subplots(1,2,figsize=(12,4.6))
    for ax,col,title in zip(axes,['ltv_band','dti_band'],['LTV','DTI']):
        labels,values=band(col);draw_chart(ax,dict(labels=labels,series=[('90+',values)],kind='bar',title=title,percent=True))
    fig.tight_layout();fig.savefig(figures/'ltv_dti.png',dpi=150);plt.close(fig)

    # ---------------------------------------------------------------- Chương 5
    page('Kết luận','Tóm lại kết quả, nêu thẳng hạn chế (bộ mẫu, một máy, load_date giả lập) và hướng phát triển.',section='Chương 5 · Kết luận')
    columns([('Kết quả đạt được','• Pipeline TXT → PostgreSQL chạy bằng một lệnh, giữ đủ lịch sử, chạy lại an toàn\n• 9 tiêu chí nghiệm thu, cổng C0–C6 đạt\n• 5 thực nghiệm có số đo và phép kiểm đúng\n• Trả lời đủ 5 câu hỏi rủi ro'),
             ('Hạn chế','• Bộ mẫu 50.000 khoản vay, một máy: không suy ra hiệu năng bộ đầy đủ\n• load_date là thời điểm đến giả lập\n• Đối chứng FR-14 chỉ là SCD1\n• Phân tích mô tả, không nhân quả'),
             ('Hướng phát triển','• Chạy bộ đầy đủ 2019 (hạ tầng đã có)\n• Gold incremental, gom file nhỏ\n• Mô hình PD 12 tháng trên đặc trưng PIT\n• Nhiều nguồn, triển khai trên cụm')],h=4.7,size=18)

    page('Demo và hỏi đáp','Kịch bản demo: Airflow với 6 DAG theo tầng; bảng control.layer_run; đợt sửa CORR1 và PIT trước/sau; mart PostgreSQL; notebook; thư mục experiments/results.',True)
    box(.8,1.7,11.6,1.0,'Cảm ơn thầy/cô đã lắng nghe',34,color=WHITE,bold=True)
    box(.8,3.1,11.5,2.2,'Demo: Airflow (6 DAG theo tầng) → control.layer_run → đợt sửa CORR1 và PIT trước/sau → mart PostgreSQL → notebook → experiments/results',21,color='B9D7CD')
    box(.8,5.6,11.5,.8,f'{STUDENT} · MSHV {STUDENT_ID}',20,color='E3B65C',bold=True)
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
