#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOTOR DE SEÑALES v3.0 — CUARTEL GENERAL
========================================
100% DINAMICO: precio, RSI 1H/4H, MACD, Stoch, ADX, Order Blocks, Niveles
calculados en tiempo real con cascada de fuentes (BingX → Binance → Yahoo).
"""
import os, sys, time, requests, math, json
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import sys as _sys, os as _os
_bam_path = _os.path.dirname(_os.path.abspath(__file__))
if _bam_path not in _sys.path:
    _sys.path.insert(0, _bam_path)
from conector_exchanges import BINGX_KEY

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "X-BX-APIKEY": BINGX_KEY if BINGX_KEY else ""
}


ACTIVOS = [
    {"sym":"BTC",  "bingx":"BTC-USDT",           "binance":"BTCUSDT", "yahoo":None,    "tipo":"CRIPTO",  "exchange":"Binance Cross Margin 5X"},
    {"sym":"ETH",  "bingx":"ETH-USDT",            "binance":"ETHUSDT", "yahoo":None,    "tipo":"CRIPTO",  "exchange":"BingX Perpetuos"},
    {"sym":"SOL",  "bingx":"SOL-USDT",            "binance":"SOLUSDT", "yahoo":None,    "tipo":"CRIPTO",  "exchange":"BingX Perpetuos"},
    {"sym":"AVGO", "bingx":"NCSKAVGO2USD-USDT",   "binance":None,      "yahoo":"AVGO",  "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"NVDA", "bingx":"NCSKNVDA2USD-USDT",   "binance":None,      "yahoo":"NVDA",  "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"TSLA", "bingx":"NCSKTSLA2USD-USDT",   "binance":None,      "yahoo":"TSLA",  "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"MSFT", "bingx":"NCSKMSFT2USD-USDT",   "binance":None,      "yahoo":"MSFT",  "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"META", "bingx":"NCSKMETA2USD-USDT",   "binance":None,      "yahoo":"META",  "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"AMD",  "bingx":"NCSKAMD2USD-USDT",    "binance":None,      "yahoo":"AMD",   "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"AMZN", "bingx":"NCSKAMZN2USD-USDT",   "binance":None,      "yahoo":"AMZN",  "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"AAPL", "bingx":"NCSKAAPL2USD-USDT",   "binance":None,      "yahoo":"AAPL",  "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"GOOGL","bingx":"NCSKGOOGL2USD-USDT",  "binance":None,      "yahoo":"GOOGL", "tipo":"ACCION",  "exchange":"BingX Perpetuos"},
    {"sym":"QQQ",  "bingx":"NCSKQQQ2USD-USDT",    "binance":None,      "yahoo":"QQQ",   "tipo":"ETF",     "exchange":"BingX Perpetuos"},
]

def get_price(act):
    try:
        r = requests.get("https://open-api.bingx.com/openApi/swap/v2/quote/price",
                         params={"symbol":act["bingx"]},headers=HEADERS,timeout=5)
        d = r.json()
        if d.get("code")==0:
            p = float(d["data"]["price"])
            if p > 0: return p
    except: pass
    if act.get("binance"):
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price",
                             params={"symbol":act["binance"]},headers=HEADERS,timeout=5)
            if r.status_code==200:
                p = float(r.json()["price"])
                if p > 0: return p
        except: pass
    if act.get("yahoo"):
        try:
            u = f"https://query1.finance.yahoo.com/v8/finance/chart/{act['yahoo']}?interval=1d&range=1d"
            r = requests.get(u,headers=HEADERS,timeout=5)
            if r.status_code==200:
                res = r.json().get("chart",{}).get("result",[])
                if res:
                    p = float(res[0].get("meta",{}).get("regularMarketPrice",0))
                    if p > 0: return p
        except: pass
    return 0.0

def get_klines(act, limit=200):
    # BingX klines v3
    try:
        r = requests.get("https://open-api.bingx.com/openApi/swap/v3/quote/klines",
                         params={"symbol":act["bingx"],"interval":"1h","limit":limit},
                         headers=HEADERS,timeout=8)
        d = r.json()
        if d.get("code")==0 and d.get("data"):
            df = pd.DataFrame(d["data"])
            for c in ["open","high","low","close","volume"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c],errors="coerce")
            df.rename(columns={"volume":"vol","time":"ot"},inplace=True)
            if "vol" not in df.columns: df["vol"] = 1000.0
            df = df.dropna(subset=["close"]).sort_values("ot").reset_index(drop=True)
            if len(df) >= 20: return df
    except: pass
    if act.get("binance"):
        try:
            r = requests.get("https://data-api.binance.vision/api/v3/klines",
                             params={"symbol":act["binance"],"interval":"1h","limit":limit},
                             headers=HEADERS,timeout=8)
            if r.status_code==200:
                df = pd.DataFrame(r.json(),columns=["ot","open","high","low","close","vol",
                                                      "ct","qv","tr","tb","tq","ig"])
                for c in ["open","high","low","close","vol"]:
                    df[c] = df[c].astype(float)
                return df.sort_values("ot").reset_index(drop=True)
        except: pass
    return pd.DataFrame()

def rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p,min_periods=1).mean()
    l = (-d.clip(upper=0)).rolling(p,min_periods=1).mean()
    return round(float((100-(100/(1+g/(l+1e-9)))).iloc[-1]),1)

def macd_estado(s):
    h = (s.ewm(span=12,adjust=False).mean()-s.ewm(span=26,adjust=False).mean())
    h -= h.ewm(span=9,adjust=False).mean()
    c,p = float(h.iloc[-1]), float(h.iloc[-2]) if len(h)>1 else float(h.iloc[-1])
    if c>=0: return "VERDE_CLARO" if c>=p else "VERDE_OSCURO"
    return "ROJO_CLARO" if c>p else "ROJO_OSCURO"

def stoch(df,k=14,sm=3):
    lmin = df["low"].rolling(k,min_periods=1).min()
    hmax = df["high"].rolling(k,min_periods=1).max()
    return round(float(((100*(df["close"]-lmin)/(hmax-lmin+1e-9)).rolling(sm,min_periods=1).mean()).iloc[-1]),1)

def adx(df,p=14):
    h,l,c = df["high"],df["low"],df["close"]
    tr  = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    dmp = (h-h.shift()).clip(lower=0)
    dmn = (l.shift()-l).clip(lower=0)
    atr_ = tr.rolling(p,min_periods=1).mean()
    pdi  = 100*dmp.rolling(p,min_periods=1).mean()/(atr_+1e-9)
    ndi  = 100*dmn.rolling(p,min_periods=1).mean()/(atr_+1e-9)
    dx   = 100*(pdi-ndi).abs()/(pdi+ndi+1e-9)
    return round(float(dx.rolling(p,min_periods=1).mean().iloc[-1]),1)

def order_block(df,px):
    if len(df)<10:
        return {"label":f"OB Est. ${px*0.972:,.2f}–${px*0.985:,.2f}","ob_low":px*0.972,"ob_high":px*0.985}
    op = df["open"].values; cl = df["close"].values
    lo = df["low"].values;  hi = df["high"].values
    for i in range(len(df)-3,5,-1):
        if cl[i]<op[i] and cl[i+1]>cl[i] and cl[i+2]>cl[i+1]:
            if lo[i]<px:
                return {"label":f"1H Bullish OB ${lo[i]:,.2f}–${op[i]:,.2f}","ob_low":lo[i],"ob_high":op[i]}
    sop = float(df["low"].tail(48).min())
    return {"label":f"1H Soporte ${sop:,.2f}","ob_low":sop,"ob_high":sop*1.01}

def niveles(df,px,rsi1h,macd_e,stk,adxv):
    if df.empty or px<=0:
        return _fb(px)
    n = len(df)
    sop7 = float(df["low"].tail(min(168,n)).min())
    res7 = float(df["high"].tail(min(168,n)).max())
    sop3 = float(df["low"].tail(min(72,n)).min())
    res3 = float(df["high"].tail(min(72,n)).max())
    h,l,c = df["high"],df["low"],df["close"]
    tr   = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    atr_ = float(tr.rolling(14,min_periods=1).mean().iloc[-1])
    ema55v = float(c.ewm(span=55,adjust=False).mean().iloc[-1])
    ema10v = float(c.ewm(span=10,adjust=False).mean().iloc[-1])

    # Entradas calculadas desde niveles reales
    le  = max(sop3*1.002, ema55v*0.998)
    lsl = sop7*0.995
    lr  = le - lsl
    lt1 = le + lr
    lt2 = le + lr*2.618
    se  = min(res3*0.998, ema55v*1.025)
    ssl = res7*1.005
    sr  = ssl - se
    st1 = se - sr
    st2 = se - sr*2.618

    # Score real
    sc = 40
    if rsi1h<=30: sc+=35
    elif rsi1h<=45: sc+=25
    elif rsi1h>=70: sc-=20
    elif rsi1h>=60: sc-=10
    if macd_e in("ROJO_CLARO","VERDE_CLARO"): sc+=20
    elif macd_e=="VERDE_OSCURO": sc+=10
    elif macd_e=="ROJO_OSCURO": sc-=15
    if stk<=20: sc+=20
    elif stk>=80: sc-=20
    if adxv>=25: sc+=10
    dist = (px-sop7)/sop7*100
    if dist<=2: sc+=15
    elif dist<=5: sc+=8
    sc = max(0,min(100,sc))

    if sc>=70: rec="🟢 LONG (Alta Confluencia)"
    elif sc>=55: rec="🟡 ESPERA (Confirmar)"
    elif sc<=30: rec="🔴 SHORT (Sobrecompra)"
    else: rec="⚪ NEUTRO"

    razon = f"RSI {rsi1h} | Stoch {stk} | ADX {adxv} | {macd_e}"

    return {"sop_7d":round(sop7,4),"res_7d":round(res7,4),"ema55":round(ema55v,4),
            "ema10":round(ema10v,4),"atr":round(atr_,4),
            "long_trigger":round(le,4),"long_sl":round(lsl,4),
            "long_tp1":round(lt1,4),"long_tp2":round(lt2,4),
            "short_trigger":round(se,4),"short_sl":round(ssl,4),
            "short_tp1":round(st1,4),"short_tp2":round(st2,4),
            "score":sc,"recom":rec,"razon":razon,"dist_sop_pct":round(dist,2)}

def _fb(px):
    px = px or 1
    return {"sop_7d":round(px*.96,4),"res_7d":round(px*1.05,4),
            "ema55":round(px*.985,4),"ema10":round(px*.998,4),"atr":round(px*.015,4),
            "long_trigger":round(px*.985,4),"long_sl":round(px*.96,4),
            "long_tp1":round(px*1.015,4),"long_tp2":round(px*1.05,4),
            "short_trigger":round(px*1.02,4),"short_sl":round(px*1.05,4),
            "short_tp1":round(px*.99,4),"short_tp2":round(px*.96,4),
            "score":50,"recom":"⚪ NEUTRO (sin datos)","razon":"Sin velas","dist_sop_pct":0.0}

def analizar_activo(act):
    sym = act["sym"]
    t0  = time.time()
    px  = get_price(act)
    df  = get_klines(act)
    if not df.empty and len(df)>=20 and px>0:
        rsi1 = rsi(df["close"],14)
        me   = macd_estado(df["close"])
        stk  = stoch(df)
        adxv = adx(df)
        ob   = order_block(df,px)
        niv  = niveles(df,px,rsi1,me,stk,adxv)
        if "ot" in df.columns:
            df["dt"] = pd.to_datetime(df["ot"].astype(float),unit="ms",utc=True)
        else:
            df["dt"] = pd.date_range(end=pd.Timestamp.utcnow(),periods=len(df),freq="1h")
        df4  = df.set_index("dt").resample("4h").agg({"close":"last"}).dropna()
        rsi4 = rsi(df4["close"],14) if len(df4)>=14 else rsi1
    else:
        rsi1=50.0;rsi4=50.0;me="NEUTRO";stk=50.0;adxv=0.0
        ob={"label":"Sin datos","ob_low":px*.97,"ob_high":px*.985}
        niv=_fb(px)
    return {"sym":sym,"tipo":act["tipo"],"exchange":act["exchange"],
            "precio":round(px,4) if px>0 else 0.0,
            "rsi_1h":rsi1,"rsi_4h":rsi4,"macd_estado":me,"stoch_k":stk,"adx":adxv,
            "ob_dom":ob["label"],"ob_low":ob["ob_low"],"ob_high":ob["ob_high"],
            **niv,"elapsed_s":round(time.time()-t0,2),"ts":int(time.time()),"datos_ok":px>0}

def run_motor_v3(activos=None,max_workers=6):
    tgts = activos or ACTIVOS
    res  = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(analizar_activo,a):a for a in tgts}
        for f in futs:
            try: res.append(f.result(timeout=25))
            except Exception as e:
                a=futs[f]
                res.append({**_fb(0),"sym":a["sym"],"tipo":a["tipo"],
                            "exchange":a["exchange"],"precio":0.0,"error":str(e)})
    res.sort(key=lambda x:x.get("score",0),reverse=True)
    return res

if __name__=="__main__":
    print("\n🚀 MOTOR v3.0 — TEST COMPLETO\n"+"="*70)
    t0  = time.time()
    res = run_motor_v3()
    print(f"\n{'SYM':<7}{'PRECIO':>12}{'RSI1H':>7}{'RSI4H':>7}{'STOCH':>7}{'ADX':>6}{'MACD':>14}{'SCORE':>7}")
    print("─"*75)
    for r in res:
        px = f"${r['precio']:>10,.2f}" if r['precio']>0 else "     N/A    "
        print(f"{r['sym']:<7}{px}{r.get('rsi_1h',0):>7.1f}{r.get('rsi_4h',0):>7.1f}"
              f"{r.get('stoch_k',0):>7.1f}{r.get('adx',0):>6.1f}"
              f"{r.get('macd_estado','?'):>14}{r.get('score',0):>7}  {r.get('recom','')}")
    print(f"\n{'SYM':<7}{'LONG ENTRY':>13}{'  LONG SL':>12}{'  LONG TP1':>12}{'  LONG TP2':>14}")
    print("─"*65)
    for r in res:
        print(f"{r['sym']:<7}${r.get('long_trigger',0):>11,.2f}  ${r.get('long_sl',0):>10,.2f}"
              f"  ${r.get('long_tp1',0):>10,.2f}  ${r.get('long_tp2',0):>12,.2f}")
    print(f"\n⏱️  {round(time.time()-t0,1)}s total | {len(res)} activos paralelos")
    out = "/tmp/senales_v3.json"
    with open(out,"w") as f: json.dump(res,f,indent=2,default=str)
    print(f"✅ Señales guardadas en {out}")
