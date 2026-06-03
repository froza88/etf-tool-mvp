#!/usr/bin/env python3
"""AI主题ETF五强对比 — 多样图表+封面"""
from PIL import Image, ImageDraw, ImageFont
import math, os

W,H = 640,640; BG="#F8F9FA"; GC="#DEE2E6"; TD="#2D3748"; TG="#718096"
COLS={"159819":"#3B82F6","515050":"#EC4899","562500":"#F59E0B","159363":"#8B5CF6","588760":"#10B981"}
try:
    ft=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",22); fa=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",13)
    fv=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",14); fc=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",11)
    ff=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",10); fl=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",13)
except: ft=fa=fv=fc=ff=fl=ImageFont.load_default()
b=os.path.dirname(__file__)or"."

# ===== DONUT =====
def donut(ti,it,sub,on):
    im=Image.new('RGB',(W,H),BG);dr=ImageDraw.Draw(im,'RGBA')
    bb=dr.textbbox((0,0),ti,font=ft);dr.text((W//2-bb[2]//2+bb[0]//2,30),ti,font=ft,fill=TD)
    if sub:
        bb=dr.textbbox((0,0),sub,font=fa);dr.text((W//2-bb[2]//2+bb[0]//2,58),sub,font=fa,fill=TG)
    vs=[x[1]for x in it];cs=[x[2]for x in it];ls=[x[0]for x in it];tv=sum(vs)
    cx,cy=W//2,340;or_=140;ir=75;sa=-90
    for i in range(len(it)):
        sw=vs[i]/tv*360
        dr.pieslice([cx-or_,cy-or_,cx+or_,cy+or_],int(sa),int(sa+sw),fill=cs[i],outline='white')
        sa+=sw
    dr.ellipse([cx-ir,cy-ir,cx+ir,cy+ir],fill=BG)
    bb=dr.textbbox((0,0),f"{tv:.0f}亿",font=ft);dr.text((cx-bb[2]//2+bb[0]//2,cy-12),f"{tv:.0f}亿",font=ft,fill=TD)
    bb=dr.textbbox((0,0),"总规模",font=fa);dr.text((cx-bb[2]//2+bb[0]//2,cy+12),"总规模",font=fa,fill=TG)
    for i in range(len(it)):
        c=i%3;r=i//3;x=60+c*190;y=H-110+r*30
        dr.rectangle([x,y+4,x+14,y+18],fill=cs[i]);pct=vs[i]/tv*100
        dr.text((x+20,y),f"{ls[i]}  {vs[i]:.1f}亿 ({pct:.1f}%)",font=fc,fill=TD)
    bb=dr.textbbox((0,0),"数据来源：天天基金 2026Q1",font=ff);dr.text((W//2-bb[2]//2+bb[0]//2,H-25),"数据来源：天天基金 2026Q1",font=ff,fill=TG)
    im.save(on,quality=95);print(f"✅ {on}")

# ===== LOLLIPOP =====
def lollipop(ti,it,un,sub,on):
    im=Image.new('RGB',(W,H),BG);dr=ImageDraw.Draw(im)
    bb=dr.textbbox((0,0),ti,font=ft);dr.text((W//2-bb[2]//2+bb[0]//2,30),ti,font=ft,fill=TD)
    if sub:
        bb=dr.textbbox((0,0),sub,font=fa);dr.text((W//2-bb[2]//2+bb[0]//2,58),sub,font=fa,fill=TG)
    vs=[x[1]for x in it];cs=[x[2]for x in it];ls=[x[0]for x in it]
    mv=max(vs);mn=min(vs)
    tmn=math.floor(mn/10)*10;tmx=math.ceil(mv/10)*10+10
    cl,cr,ct,cb=100,W-35,80,H-130;cw=cr-cl;ch=cb-ct;tr=tmx-tmn
    for tk in range(tmn,tmx+10,10):
        y=cb-((tk-tmn)/tr)*ch if tr else cb
        dr.line([(cl,y),(cr,y)],fill=GC,width=1)
        bb=dr.textbbox((0,0),f"{tk}{un}",font=fa);dr.text((cl-bb[2]+bb[0]-8,y-bb[3]//2+bb[1]//2),f"{tk}{un}",font=fa,fill=TG)
    n=len(it);gap=(cw-40)/(n-1)if n>1 else 0
    for i,(lb,va,co) in enumerate(zip(ls,vs,cs)):
        x=cl+20+i*gap;bh=((va-tmn)/tr)*ch if tr else 0;yt=cb-bh
        dr.line([(x,cb-1),(x,yt)],fill=co,width=3)
        r=10;dr.ellipse([x-r,yt-r,x+r,yt+r],fill=co,outline='white',width=2)
        bb=dr.textbbox((0,0),f"{va:.1f}{un}",font=fv);dr.text((x-bb[2]//2+bb[0]//2,yt-r-bb[3]+bb[1]-4),f"{va:.1f}{un}",font=fv,fill=TD)
        bb=dr.textbbox((0,0),lb,font=fc);dr.text((x-bb[2]//2+bb[0]//2,cb+10),lb,font=fc,fill=TD)
    bb=dr.textbbox((0,0),"越高越好",font=ff);dr.text((W//2-bb[2]//2+bb[0]//2,H-25),"越高越好",font=ff,fill=TG)
    im.save(on,quality=95);print(f"✅ {on}")

# ===== HBAR =====
def hbar(ti,it,un,sub,on):
    im=Image.new('RGB',(W,H),BG);dr=ImageDraw.Draw(im)
    bb=dr.textbbox((0,0),ti,font=ft);dr.text((W//2-bb[2]//2+bb[0]//2,30),ti,font=ft,fill=TD)
    if sub:
        bb=dr.textbbox((0,0),sub,font=fa);dr.text((W//2-bb[2]//2+bb[0]//2,58),sub,font=fa,fill=TG)
    vs=[x[1]for x in it];cs=[x[2]for x in it];ls=[x[0]for x in it];mv=max(vs)
    cl,cr,ct,cb=130,W-35,90,H-55;n=len(it);bh=min(56,(cb-ct-(n-1)*14)/n);gp=14
    tmx=math.ceil(mv/5)*5+5
    for tk in range(0,int(tmx)+5,5):
        x=cl+(tk/tmx)*(cr-cl);dr.line([(x,ct),(x,cb)],fill=GC,width=1)
        dr.text((x,cb+4),f"{tk}{un}",font=fc,fill=TG,anchor='mt')
    for i,(lb,va,co) in enumerate(zip(ls,vs,cs)):
        y=ct+i*(bh+gp);bw=(va/tmx)*(cr-cl)
        dr.rounded_rectangle([cl,y,cl+bw,y+bh],radius=6,fill=co)
        bb=dr.textbbox((0,0),f"{va:.2f}{un}",font=fv);dr.text((cl+bw+10,y+bh//2-bb[3]//2+bb[1]//2),f"{va:.2f}{un}",font=fv,fill=TD)
        bb=dr.textbbox((0,0),lb,font=fl);dr.text((cl-10,y+bh//2-bb[3]//2+bb[1]//2),lb,font=fl,fill=TD,anchor='ra')
    bb=dr.textbbox((0,0),"越高越好（流动性更强）",font=ff);dr.text((W//2-bb[2]//2+bb[0]//2,cb+26),"越高越好（流动性更强）",font=ff,fill=TG)
    im.save(on,quality=95);print(f"✅ {on}")

# ===== FEE =====
def fee_chart(ti,sub,on):
    FW,FH=640,480;im=Image.new('RGB',(FW,FH),BG);dr=ImageDraw.Draw(im,'RGBA')
    try:
        fbig=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",48);fsub=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",14)
        fb=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",15);fnote=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",11)
        f28=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",28);f56=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",56)
    except: fbig=fsub=fb=fnote=f28=f56=ImageFont.load_default()
    
    bb=dr.textbbox((0,0),ti,font=ft);dr.text((FW//2-bb[2]//2+bb[0]//2,30),ti,font=ft,fill=TD)
    if sub:
        bb=dr.textbbox((0,0),sub,font=fsub);dr.text((FW//2-bb[2]//2+bb[0]//2,58),sub,font=fsub,fill=TG)
    
    # Split layout: left = 159819 (0.20%), right = others (0.60%)
    mid = FW//2
    
    # Left card - winner
    dr.rounded_rectangle([40,85,mid-15,260],radius=14,fill='#EFF6FF',outline='#BFDBFE',width=2)
    dr.text((mid//2+5,110),'🏆 最低费率',font=fsub,fill='#3B82F6',anchor='mt')
    dr.text((mid//2+5,150),'0.20%',font=f56,fill='#3B82F6',anchor='mt')
    dr.text((mid//2+5,200),'年总费率',font=fsub,fill='#64748B',anchor='mt')
    dr.text((mid//2+5,230),'159819 易方达',font=fb,fill='#1E3A5F',anchor='mt')
    dr.text((mid//2+5,250),'管理0.15% + 托管0.05%',font=fnote,fill='#94A3B8',anchor='mt')
    
    # Right card - others
    dr.rounded_rectangle([mid+15,85,FW-40,260],radius=14,fill='#F8FAFC',outline='#E2E8F0',width=1)
    dr.text((mid+(FW-40-mid)//2+8,110),'其他四只',font=fsub,fill='#64748B',anchor='mt')
    dr.text((mid+(FW-40-mid)//2+8,150),'0.60%',font=f28,fill='#94A3B8',anchor='mt')
    dr.text((mid+(FW-40-mid)//2+8,200),'年总费率',font=fsub,fill='#94A3B8',anchor='mt')
    others=['515050 华夏通信','562500 华夏机器人','159363 华宝','588760 广发']
    for j,nm in enumerate(others):
        dr.text((mid+(FW-40-mid)//2+8,226+j*16),nm,font=fnote,fill='#94A3B8',anchor='mt')
    
    # 3x indicator between the two
    dr.ellipse([mid-22,155,mid+22,199],fill='#FEF2F2',outline='#FECACA',width=2)
    dr.text((mid,177),'3x',font=fb,fill='#E74C3C',anchor='mm')
    
    # Bottom cost comparison
    dr.line([(40,290),(FW-40,290)],fill='#E2E8F0',width=1)
    dr.text((FW//2,315),'持有10万元/年的实际成本',font=fb,fill=TD,anchor='mt')
    
    # Two cost cards at bottom
    bcw=(FW-120)//2
    dr.rounded_rectangle([40,340,40+bcw,420],radius=10,fill='#EFF6FF',outline='#BFDBFE',width=1)
    dr.text((40+bcw//2,365),'200元',font=fbig,fill='#3B82F6',anchor='mt')
    dr.text((40+bcw//2,398),'159819 易方达',font=fsub,fill='#64748B',anchor='mt')
    
    dr.rounded_rectangle([FW-40-bcw,340,FW-40,420],radius=10,fill='#F8FAFC',outline='#E2E8F0',width=1)
    dr.text((FW-40-bcw//2,365),'600元',font=f28,fill='#94A3B8',anchor='mt')
    dr.text((FW-40-bcw//2,398),'其他四只',font=fsub,fill='#94A3B8',anchor='mt')
    
    dr.text((FW-150,FH-22),'不推荐 · 只给数据',font=fnote,fill='#CBD5E1')
    im.save(on,quality=95);print(f"✅ {on}")

# Generate charts
donut("AI主题ETF规模分布",[("159819 易方达",221.41,COLS["159819"]),("515050 华夏通信",78.02,COLS["515050"]),("562500 华夏机器人",209.52,COLS["562500"]),("159363 华宝",55.64,COLS["159363"]),("588760 广发",22.32,COLS["588760"])],"基金资产净值（亿元，2026Q1）",os.path.join(b,"charts","section_规模占比.png"))
lollipop("AI主题ETF近1年回报对比",[("159819 易方达",103.2,COLS["159819"]),("515050 华夏通信",228.7,COLS["515050"]),("562500 华夏机器人",24.5,COLS["562500"]),("159363 华宝",188.2,COLS["159363"]),("588760 广发",50.5,COLS["588760"])],"%","2025年5月—2026年6月1日区间涨跌幅（价格口径）",os.path.join(b,"charts","section_回报对比.png"))
hbar("AI主题ETF日成交额对比",[("159819 易方达",8.57,COLS["159819"]),("515050 华夏通信",13.30,COLS["515050"]),("562500 华夏机器人",9.03,COLS["562500"]),("159363 华宝",11.65,COLS["159363"]),("588760 广发",3.30,COLS["588760"])],"亿","2026年6月1日单日成交额",os.path.join(b,"charts","section_成交额对比.png"))
fee_chart("AI主题ETF费率对比","总费率（管理费+托管费）",os.path.join(b,"charts","section_费率对比.png"))
print("\n✅ 4张图表生成完成")
