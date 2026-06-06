#!/usr/bin/env python3
"""消费vs消费电子ETF 图表生成"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import os

FONT_PATH = '/System/Library/Fonts/PingFang.ttc'
fm.fontManager.addfont(FONT_PATH)
prop = fm.FontProperties(fname=FONT_PATH)
FONT_NAME = prop.get_name()
plt.rcParams['font.family'] = FONT_NAME
plt.rcParams['font.size'] = 11

OUT = os.path.join(os.path.dirname(__file__), 'charts')
os.makedirs(OUT, exist_ok=True)

C_RED = '#E74C3C'; C_RED2 = '#F1948A'; C_RED3 = '#F5B7B1'; C_RED4 = '#FADBD8'
C_BLUE = '#2980B9'; C_BLUE2 = '#5DADE2'; C_BLUE3 = '#85C1E9'; C_BLUE4 = '#D6EAF8'
C_GRAY = '#E8E8E8'; BG = '#F8F9FA'

# ====== 1) 环形图-规模双列 ======
def chart1():
    names1 = ['汇添富\n110亿','富国\n34亿','易方达\n19亿','景顺\n14亿','景顺\n14亿','招商\n7亿','华宝\n7亿','其他\n20只']
    vals1 = [110.1,34.3,18.7,13.8,13.7,7.1,7.1,38.2]
    colors1 = [C_RED,C_RED2,C_RED3,C_RED4,'#FDEDEC','#F9EBEA','#F5EEF8',C_GRAY]
    names2 = ['华夏\n55亿','易方达\n29亿','富国\n16亿','平安\n4亿','招商\n3亿','其他\n2只']
    vals2 = [55.1,28.8,16.3,3.6,3.1,2.1]
    colors2 = [C_BLUE,C_BLUE2,C_BLUE3,C_BLUE4,'#EAF2F8',C_GRAY]

    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,6),facecolor=BG)
    ax1.pie(vals1,labels=names1,colors=colors1,textprops={'fontsize':9,'weight':'bold'})
    ax1.set_title('消费ETF 规模结构',fontsize=14,weight='bold',color='#2D3748',pad=18)
    ax2.pie(vals2,labels=names2,colors=colors2,textprops={'fontsize':9,'weight':'bold'})
    ax2.set_title('消费电子ETF 规模结构',fontsize=14,weight='bold',color='#2D3748',pad=18)
    fig.text(0.25,0.02,f'共34只 总{sum(vals1):.0f}亿',ha='center',fontsize=10,color='#718096')
    fig.text(0.75,0.02,f'共7只 总{sum(vals2):.0f}亿',ha='center',fontsize=10,color='#718096')
    plt.tight_layout(rect=[0,0.05,1,1])
    plt.savefig(f'{OUT}/section_01_scale_donut.png',dpi=150,facecolor=BG)
    plt.close()

# ====== 2) 棒棒糖-1年收益 ======
def chart2():
    names = ['汇添富\n消费ETF','富国\n消费50','广发\n可选消费','华夏\n消费电子','易方达\n消费电子','富国\n消费电子']
    vals = [-14.32,-8.09,6.24,91.28,107.94,105.03]
    colors = [C_RED,C_RED2,C_RED3,C_BLUE,C_BLUE2,C_BLUE3]
    fig,ax=plt.subplots(figsize=(10,6),facecolor=BG)
    ax.set_facecolor(BG)
    for i,(v,c) in enumerate(zip(vals,colors)):
        ax.plot([0,v],[i,i],color=c,lw=4,solid_capstyle='round',zorder=2)
        ax.scatter(v,i,s=200,color=c,zorder=3,edgecolors='white',lw=2)
        xo=5 if v>=0 else -5
        ax.annotate(f'{v:+.2f}%',(v,i),textcoords='offset points',xytext=(xo*4,0),ha='left' if v>=0 else 'right',va='center',fontsize=12,weight='bold',color='#2D3748')
    ax.set_yticks(range(len(names))); ax.set_yticklabels(names,fontsize=10)
    ax.axvline(0,color='#CBD5E0',lw=1,zorder=1)
    ax.set_xlim(-30,135)
    ax.set_title('近1年收益对比',fontsize=16,weight='bold',color='#2D3748',pad=15)
    ax.grid(axis='x',color='#E2E8F0',lw=0.5)
    for s in ax.spines.values(): s.set_visible(False)
    plt.tight_layout()
    plt.savefig(f'{OUT}/section_02_return_lollipop.png',dpi=150,facecolor=BG)
    plt.close()

# ====== 3) 横向柱状-风险三连 ======
def chart3():
    names = ['汇添富\n消费','富国\n消费50','广发\n可选消费','华夏\n消费电子','易方达\n消费电子','富国\n消费电子']
    colors = [C_RED,C_RED2,C_RED3,C_BLUE,C_BLUE2,C_BLUE3]
    sharpe=[-1.08,-0.75,0.36,2.19,2.38,2.29]
    mdd=[-21.35,-14.22,-12.63,-18.03,-18.19,-18.12]
    vol=[15.1,12.89,14.01,31.1,32.3,32.94]
    fig,axes=plt.subplots(1,3,figsize=(14,5),facecolor=BG)
    for ax in axes: ax.set_facecolor(BG)
    # sharpe
    bars=axes[0].barh(range(6),sharpe,height=0.6,color=colors)
    for v,b in zip(sharpe,bars):
        axes[0].text(v+0.05 if v>=0 else v-0.5,b.get_y()+b.get_height()/2,f'{v:.2f}',va='center',fontsize=10,weight='bold')
    axes[0].set_yticks(range(6)); axes[0].set_yticklabels(names,fontsize=9)
    axes[0].set_title('夏普比率',fontsize=13,weight='bold'); axes[0].axvline(0,color='#CBD5E0',lw=1)
    for s in axes[0].spines.values(): s.set_visible(False)
    # mdd
    bars=axes[1].barh(range(6),mdd,height=0.6,color=colors)
    for v,b in zip(mdd,bars): axes[1].text(v-0.4,b.get_y()+b.get_height()/2,f'{v:.1f}%',va='center',fontsize=10,weight='bold',ha='right')
    axes[1].set_yticks(range(6)); axes[1].set_yticklabels([])
    axes[1].set_title('最大回撤',fontsize=13,weight='bold')
    for s in axes[1].spines.values(): s.set_visible(False)
    # vol
    bars=axes[2].barh(range(6),vol,height=0.6,color=colors)
    for v,b in zip(vol,bars): axes[2].text(v+0.3,b.get_y()+b.get_height()/2,f'{v:.1f}%',va='center',fontsize=10,weight='bold')
    axes[2].set_yticks(range(6)); axes[2].set_yticklabels([])
    axes[2].set_title('年化波动率',fontsize=13,weight='bold')
    for s in axes[2].spines.values(): s.set_visible(False)
    plt.tight_layout(pad=3)
    plt.savefig(f'{OUT}/section_03_risk_hbar.png',dpi=150,facecolor=BG)
    plt.close()

# ====== 4) 持仓饼图双列 ======
def chart4():
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(12,6),facecolor=BG)
    cats1=['白酒\n茅台+五粮液 21%','乳业\n伊利 10%','猪肉\n牧原+温氏 15%','其他\n消费品']
    vals1=[21,10,15,54]; colors1=[C_RED,C_RED2,C_RED3,C_RED4]
    ax1.pie(vals1,labels=cats1,colors=colors1,textprops={'fontsize':10,'weight':'bold'},startangle=90)
    ax1.set_title('消费ETF (汇添富 159928)\n传统消费品：白酒+乳业+猪肉',fontsize=13,weight='bold',color='#2D3748',pad=15)
    cats2=['连接器\n立讯+东山 14%','半导体\n兆易+寒武纪+中芯 20%','面板\n京东方+TCL 11%','其他\n电子制造']
    vals2=[14,20,11,55]; colors2=[C_BLUE,C_BLUE2,C_BLUE3,C_BLUE4]
    ax2.pie(vals2,labels=cats2,colors=colors2,textprops={'fontsize':10,'weight':'bold'},startangle=90)
    ax2.set_title('消费电子ETF (华夏 159732)\n半导体+电子制造：芯片主导',fontsize=13,weight='bold',color='#2D3748',pad=15)
    plt.tight_layout(pad=3)
    plt.savefig(f'{OUT}/section_04_holdings_pie.png',dpi=150,facecolor=BG)
    plt.close()

if __name__=='__main__':
    chart1(); chart2(); chart3(); chart4()
    print('All charts generated OK')
