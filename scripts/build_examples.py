#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright (c) 2026 RivanXU.
# Required Notice: selfcollege-waba by RivanXU.
"""Build the original university oscillator example, with desktop PDF previews."""
from __future__ import annotations
import copy
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image as PILImage
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from render_study_pdfs import MathFormula, SafeMarkup, publish_outputs
from inline_math import inline_math_paragraph

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'examples'
CONTENT_FILE = ROOT / 'examples/demo-content.json'
SLIDE_W, SLIDE_H = 720, 540
INK = colors.HexColor('#263746')
NAVY = colors.HexColor('#17334D')
TEAL = colors.HexColor('#117E82')
MUTED = colors.HexColor('#607485')
LINE = colors.HexColor('#D9E3EA')
for name, filename in [('SourceSans','LiberationSans-Regular.ttf'),('SourceBold','LiberationSans-Bold.ttf'),('SourceCN','NotoSansSC-Regular.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(ROOT/'assets/fonts'/filename)))
pdfmetrics.registerFont(TTFont('StudyCN', str(ROOT/'assets/fonts/NotoSansSC-Regular.ttf')))


def text(c, value, x, top, width, cn=False, size=18, bold=False):
    face = 'SourceCN' if cn else ('SourceBold' if bold else 'SourceSans')
    style = ParagraphStyle('slide',fontName=face,fontSize=size,leading=size*1.35,
                           textColor=INK,wordWrap='CJK' if cn else None)
    p = inline_math_paragraph(value, style, MathFormula, SafeMarkup)
    _, h = p.wrap(width, 1000)
    if top-h < 22:
        raise ValueError('Slide text reaches its footer; reorganize the content.')
    p.drawOn(c,x,top-h)
    return top-h


def equation(c, latex, x, top, width=648, size=21):
    f=MathFormula(latex,size)
    if f.width>width:
        raise ValueError('Slide formula is too wide; split it without shrinking.')
    f.drawOn(c,x,top-f.height)
    return top-f.height


def response_chart(c, cn, x=80,y=105,width=590,height=137):
    gamma=.2; omega=math.sqrt(4-gamma*gamma)
    A=.1; B=gamma*A/omega; R=math.hypot(A,B)
    def point(t,v): return (x+t/10*width,y+(v+.12)/.24*height)
    c.setLineWidth(.55); c.setStrokeColor(LINE)
    for t in [0,2,4,6,8,10]:
        xx,_=point(t,0); c.line(xx,y,xx,y+height)
        text(c,str(t),xx-7,y-7,30,cn,13)
    for v in [-.1,0,.1]:
        _,yy=point(0,v); c.line(x,yy,x+width,yy)
        text(c,f'{v:g}',x-43,yy+7,38,cn,13)
    for envelope in [-1,1,0]:
        path=c.beginPath()
        for i in range(401):
            t=i/40; decay=math.exp(-gamma*t)
            v=envelope*R*decay if envelope else decay*(A*math.cos(omega*t)+B*math.sin(omega*t))
            xx,yy=point(t,v)
            if i==0: path.moveTo(xx,yy)
            else: path.lineTo(xx,yy)
        c.setStrokeColor(MUTED if envelope else TEAL)
        c.setDash(4,3) if envelope else c.setDash()
        c.setLineWidth(.9 if envelope else 1.8); c.drawPath(path)
    c.setDash()
    text(c,r'时间 \(t\)（s）' if cn else r'Time \(t\) (s)',x+width/2-45,y-32,160,cn,14)
    text(c,r'位移 \(x\)（m）' if cn else r'Displacement \(x\) (m)',x,y+height+23,250,cn,14)
    c.setStrokeColor(TEAL); c.setLineWidth(1.8); c.line(x+290,y+height+14,x+314,y+height+14)
    text(c,'位移' if cn else 'Displacement',x+320,y+height+24,140,cn,14)
    c.setStrokeColor(MUTED); c.setDash(4,3); c.line(x+435,y+height+14,x+459,y+height+14);c.setDash()
    text(c,'包络线' if cn else 'Envelopes',x+465,y+height+24,115,cn,14)


def build_slides(kind):
    cn=kind=='target'; path=OUT/('translated-slides.pdf' if cn else 'source-slides.pdf')
    c=canvas.Canvas(str(path),pagesize=(SLIDE_W,SLIDE_H),invariant=1)
    titles=['力与自由运动','振动为何衰减','初值确定运动'] if cn else ['Forces and free motion','Why oscillations decay','Initial data choose the motion']
    for i in range(3):
        c.setFillColor(colors.white);c.rect(0,0,720,540,fill=1,stroke=0)
        c.setFillColor(NAVY);c.rect(0,535,720,5,fill=1,stroke=0)
        text(c,'阻尼振动 / 原创演示' if cn else 'DAMPED OSCILLATOR / ORIGINAL DEMO',36,513,648,cn,11)
        text(c,titles[i],36,482,648,cn,25,True)
        c.setStrokeColor(LINE);c.line(36,439,684,439)
        if i==0:
            text(c,r'\(x(t)\) 为相对平衡位置的位移。' if cn else r'Measure \(x(t)\) from the equilibrium position.',36,420,648,cn)
            text(c,'弹簧力' if cn else 'Spring force',36,366,300,cn,16)
            text(c,'阻尼力' if cn else 'Damping force',385,366,299,cn,16)
            equation(c,r'F_s=-kx',36,337,300)
            equation(c,r'F_d=-bx^{\prime}',385,337,299)
            text(c,'牛顿第二定律把两种力串联起来。' if cn else 'Newton\'s second law connects both forces.',36,279,648,cn)
            equation(c,r'mx^{\prime\prime}=-bx^{\prime}-kx',36,245)
            equation(c,r'mx^{\prime\prime}+bx^{\prime}+kx=0',36,197)
            text(c,r'\(m>0\)、\(k>0\)、\(b>0\)；系数恒定，无外部驱动力。' if cn else r'\(m>0\), \(k>0\), \(b>0\); constant coefficients; no driving force.',36,137,648,cn,17)
            text(c,'接下来：什么函数同时满足惯性、阻尼和回复作用？' if cn else 'Next: which function satisfies inertia, damping and restoring force?',36,87,648,cn,17)
        elif i==1:
            text(c,'试取指数函数，把微分关系变为代数关系。' if cn else 'Try an exponential to turn differentiation into algebra.',36,420,648,cn)
            equation(c,r'x(t)=C e^{\lambda t}',36,383)
            equation(c,r'm\lambda^2+b\lambda+k=0',36,337)
            equation(c,r'\gamma=\frac{b}{2m},\qquad\omega_0=\sqrt{\frac{k}{m}}',36,292)
            text(c,r'欠阻尼条件：\(0<\gamma<\omega_0\)。' if cn else r'Underdamped condition: \(0<\gamma<\omega_0\).',36,222,648,cn,18)
            equation(c,r'\lambda=-\gamma\pm i\omega_{\mathrm{d}},\qquad\omega_{\mathrm{d}}=\sqrt{\omega_0^2-\gamma^2}',36,182)
            text(c,'实部决定衰减；虚部决定振动。' if cn else 'Real part: decay. Imaginary part: oscillation.',36,117,648,cn)
            text(c,'接下来：初始位移和速度如何选出具体运动？' if cn else 'Next: how do initial displacement and velocity select the motion?',36,67,648,cn,17)
        else:
            equation(c,r'x(t)=e^{-\gamma t}[A\cos(\omega_{\mathrm{d}}t)+B\sin(\omega_{\mathrm{d}}t)]',36,416)
            equation(c,r'A=x_0,\qquad B=\frac{v_0+\gamma x_0}{\omega_{\mathrm{d}}}',36,368)
            text(c,r'示例：\(m=1\) kg，\(b=0.4\) kg/s，\(k=4\) N/m，\(x_0=0.1\) m，\(v_0=0\)。' if cn else r'Example: \(m=1\) kg, \(b=0.4\) kg/s, \(k=4\) N/m, \(x_0=0.1\) m, \(v_0=0\).',36,299,648,cn,15)
            response_chart(c,cn)
            text(c,r'包络线为 \(\pm R e^{-\gamma t}\)，\(R=\sqrt{A^2+B^2}\)；位移仍会振荡。' if cn else r'Envelopes: \(\pm R e^{-\gamma t}\), \(R=\sqrt{A^2+B^2}\). Displacement still oscillates.',36,48,648,cn,14)
        c.setFont('SourceCN' if cn else 'SourceSans',9);c.setFillColor(MUTED);c.drawRightString(684,15,f'{i+1:02d} / 03');c.showPage()
    c.save();return path


def content():
    return json.loads(CONTENT_FILE.read_text())


def build_spec(portable=True):
    source='examples/source-slides.pdf' if portable else str(OUT/'source-slides.pdf')
    target='examples/translated-slides.pdf' if portable else str(OUT/'translated-slides.pdf')
    data=content()
    guide=copy.deepcopy(data['guide'])
    for page in guide:
        for block in page['blocks']:
            if block.get('type')=='source_crop':block['source_pdf']=source
    spec={'course_code':'OSCILLATOR','course_name':'From forces to motion','lecture':'Original university example','file_stem':'oscillator-demo','source_pdf':source,'translated_pdf':target,'bilingual_mode':'paired_pdf','bilingual_layout':{'page_width':1190.551,'page_height':900,'annotation_height':230},'labels':{'guide_header':'SELFCOLLEGE WABA / ORIGINAL DEMO','bilingual_header':'SELFCOLLEGE WABA / ORIGINAL DEMO','guide_name':'study-guide','bilingual_name':'slide-companion','source_heading':'Original slide / English','translation_heading':'Translated slide / Chinese'},'guide':guide,'bilingual':data['bilingual']}
    path=OUT/'demo-spec.json';path.write_text(json.dumps(spec,indent=2,ensure_ascii=False)+'\n');return path


def run_renderer(spec, where):
    subprocess.run([sys.executable,str(ROOT/'scripts/render_study_pdfs.py'),'--spec',str(spec),'--output-dir',str(where)],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)


def build_guide():
    spec_path=build_spec(False);spec=json.loads(spec_path.read_text());spec.pop('bilingual')
    p=OUT/'.guide-input.json';p.write_text(json.dumps(spec))
    where=OUT/'.guide-stage';run_renderer(p,where)
    guide=OUT/'beginner-study-guide.pdf';shutil.copyfile(where/'oscillator-demo_study-guide.pdf',guide)
    shutil.rmtree(where);p.unlink();return guide


def normalize_public_pdf_metadata(path):
    reader=PdfReader(path);writer=PdfWriter();writer.append(reader)
    writer.add_metadata({'/Title':'selfcollege-waba / '+path.stem,'/Author':'selfcollege-waba','/Subject':'Original university teaching example','/Creator':'selfcollege-waba','/Producer':'selfcollege-waba','/CreationDate':'D:20000101000000Z','/ModDate':'D:20000101000000Z'})
    if '/Metadata' in writer._root_object:del writer._root_object['/Metadata']
    with path.open('wb') as f:writer.write(f)


def make_previews(paths, temporary):
    renderer=shutil.which('pdftoppm')
    if not renderer:
        bundled=Path(sys.base_prefix).parent/'bin/override/pdftoppm'
        if bundled.exists():renderer=str(bundled)
    if not renderer:raise RuntimeError('Install Poppler and put pdftoppm on PATH.')
    targets={}
    for path in paths:
        prefix=temporary/path.stem
        subprocess.run([renderer,'-r','180','-png',str(path),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        targets[path.stem]=sorted(temporary.glob(path.stem+'-*.png'))
    previews=OUT/'previews';previews.mkdir(exist_ok=True)
    for pdf,page,name,dpi in [(OUT/'slide-companion.pdf',3,'comparison.png',216),(OUT/'beginner-study-guide.pdf',5,'explanation.png',288),(OUT/'beginner-study-guide.pdf',8,'practice.png',288)]:
        prefix=temporary/('preview-'+Path(name).stem)
        subprocess.run([renderer,'-f',str(page),'-l',str(page),'-singlefile','-r',str(dpi),'-png',str(pdf),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        PILImage.open(prefix.with_suffix('.png')).convert('RGB').save(previews/name)
    return targets


def main():
    global OUT
    destination=OUT
    with tempfile.TemporaryDirectory(prefix='.selfcollege-demo-',dir=ROOT.parent) as temp_name:
        temp=Path(temp_name);OUT=temp/'examples';OUT.mkdir()
        try:
            source=build_slides('source');target=build_slides('target');guide=build_guide()
            spec=build_spec(False);data=json.loads(spec.read_text());data.pop('guide');spec.write_text(json.dumps(data))
            run_renderer(spec,temp/'paired')
            companion=OUT/'slide-companion.pdf';shutil.copyfile(temp/'paired/oscillator-demo_slide-companion.pdf',companion)
            paths=[source,target,companion,guide]
            for p in paths:normalize_public_pdf_metadata(p)
            previews=make_previews(paths,temp)
            qa=ROOT/'tmp/example-qa';qa.mkdir(parents=True,exist_ok=True)
            for p in temp.glob('*.png'):shutil.copyfile(p,qa/p.name)
            report={'authorship':'Original university oscillator model, slides, practice and chart; no private course content','language_pair':['English','Simplified Chinese'],'slide_layout':'Corresponding text boxes, equations and plotted data at equal panel scale','pdf_pages':{p.name:len(PdfReader(p).pages) for p in paths},'rendered_pages':sum(len(v) for v in previews.values()),'homework':'Complete original four-part question on page8; all answers on pages8-10','formula_rendering':'Vector mathematical glyphs and fraction bars; peer fraction operands retain size, scripts retain hierarchy','visual_review_status':'pending for regenerated outputs','visual_review_required':True,'preview_export':{'comparison_dpi':216,'guide_dpi':288,'qa_dpi':180,'source':'Directly rendered actual desktop PDF pages; no bitmap enlargement'},'reading_baseline':'Computer PDF reading; no device-specific artifacts'}
            (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n');build_spec(True)
            publications=[{'path':str(destination/p.relative_to(OUT)),'stage':str(p)} for p in sorted(OUT.rglob('*')) if p.is_file()]
            for item in publications:Path(item['path']).parent.mkdir(parents=True,exist_ok=True)
            publish_outputs(publications,[],temp)
        finally:OUT=destination
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
