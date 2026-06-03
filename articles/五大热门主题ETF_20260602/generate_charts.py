#!/usr/bin/env python3
"""五大热门主题ETF — 跨主题横评图表"""
from PIL import Image, ImageDraw, ImageFont
import math, os
W,H=640,640;BG="#F8F9FA";GC="#DEE2E6";TD="#2D3748";TG="#718096"
COLS={"159326":"#3B82F6","513120":"#EC4899","518880":"#F59E0B","513350":"#8B5CF6","159201":"#10B981"}
try:
    ft=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",22);fa=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",13)
    fv=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",14);fc=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",11)
    ff=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",10);fl=ImageFont.truetype("/System/Library/Fonts/PingFang.ttc",13)
except: ft=fa=fv=fc=ff=fl=ImageFont.load_default()
b=os.path.dirname(__file__)or"."

def donut(ti,it,sub,on):
    im=Image.new('RGB',(W,H),BG);dr=ImageDraw.Draw(im,'RGBA')
    bb=dr.textbbox((0,0),ti,font=ft);dr.text((W//2-bb[2]//2+bb[0]//2,30),ti,font=ft,fill=TD)
    if sub:bb=dr.textbbox((0,0),sub,font=fa);dr.text((W//2-bb[2]//2+bb[0]//2,58),sub,font=fa,fill=TG)
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
        c=i%3;r=i//3;x=50+c*200;y=H-110+r*30
        dr.rectangle([x,y+4,x+14,y+18],fill=cs[i]);pct=vs[i]/tv*100
        dr.text((x+20,y),f"{ls[i]}  {vs[i]:.1f}亿 ({pct:.1f}%)",font=fc,fill=TD)
    bb=dr.textbbox((0,0),"数据来源：天天基金 2026Q1",font=ff);dr.text((W//2-bb[2]//2+bb[0]//2,H-25),"数据来源：天天基金 2026Q1",font=ff,fill=TG)
    im.save(on,quality=95);print(f"✅ {on}")

def lollipop(ti,it,un,sub,on):
    im=Image.new('RGB',(W,H),BG);dr=ImageDraw.Draw(im)
    bb=dr.textbbox((0,0),ti,font=ft);dr.text((W//2-bb[2]//2+bb[0]//2,30),ti,font=ft,fill=TD)
    if sub:bb=dr.textbbox((0,0),sub,font=fa);dr.text((W//2-bb[2]//2+bb[0]//2,58),sub,font=fa,fill=TG)
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

def hbar(ti,it,un,sub,on):
    im=Image.new('RGB',(W,H),BG);dr=ImageDraw.Draw(im)
    bb=dr.textbbox((0,0),ti,font=ft);dr.text((W//2-bb[2]//2+bb[0]//2,30),ti,font=ft,fill=TD)
    if sub:bb=dr.textbbox((0,0),sub,font=fa);dr.text((W//2-bb[2]//2+bb[0]//2,58),sub,font=fa,fill=TG)
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
    bb=dr.textbbox((0,0),"越高越好",font=ff);dr.text((W//2-bb[2]//2+bb[0]//2,cb+26),"越高越好",font=ff,fill=TG)
    im.save(on,quality=95);print(f"✅ {on}")

# Charts
donut("五大热门主题ETF规模分布",[("159326 电网",300.87,COLS["159326"]),("513120 创新药",248.48,COLS["513120"]),("518880 黄金",1138.16,COLS["518880"]),("513350 油气",10.18,COLS["513350"]),("159201 现金流",184.53,COLS["159201"])],"基金AUM（亿元，2026Q1）",os.path.join(b,"charts","section_规模占比.png"))
lollipop("五大热门主题ETF近1年回报对比",[("159326 电网",92.3,COLS["159326"]),("513120 创新药",20.7,COLS["513120"]),("518880 黄金",23.2,COLS["518880"]),("513350 油气",48.5,COLS["513350"]),("159201 现金流",25.0,COLS["159201"])],"%","2025年5月—2026年6月2日（价格口径）",os.path.join(b,"charts","section_回报对比.png"))
hbar("五大热门主题ETF日成交额对比",[("159326 电网",8.44,COLS["159326"]),("513120 创新药",27.28,COLS["513120"]),("518880 黄金",13.70,COLS["518880"]),("513350 油气",9.75,COLS["513350"]),("159201 现金流",1.79,COLS["159201"])],"亿","2026年6月2日单日成交额",os.path.join(b,"charts","section_成交额对比.png"))
print("\n✅ 3张图表生成完成")
