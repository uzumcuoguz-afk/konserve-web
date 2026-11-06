# -*- coding: utf-8 -*-
import os
from flask import Flask, request, render_template_string
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

SAYFA = """
<!doctype html>
<html><head><meta charset="utf-8"><title>Konserve Üretim & Stok Takip</title>
<style>
body{font-family:Arial;margin:0;padding:0;background:#f4f4f4;}header{background:#2c3e50;color:white;padding:15px 20px;}
nav{background:#34495e;padding:0;}nav a{display:inline-block;color:white;padding:12px 20px;text-decoration:none;}
nav a:hover{background:#2c3e50;}nav a.aktif{background:#2c3e50;}.icerik{padding:20px;}
table{border-collapse:collapse;width:100%;background:white;margin-bottom:20px;}th,td{border:1px solid #ddd;padding:8px;text-align:left;}
th{background:#ecf0f1;}tr:nth-child(even){background:#f9f9f9;}.yetmez{background:#ffd0d0 !important;}.yeterli{background:#d8f5d0 !important;}
.kritik{background:#ffe0b2 !important;font-weight:bold;}.maks{color:#2980b9;font-weight:bold;}.maks-sifir{color:#e74c3c;font-weight:bold;}
input,select,button{padding:6px 10px;margin:4px 0;font-size:14px;}button{background:#3498db;color:white;border:none;cursor:pointer;border-radius:4px;}
button:hover{background:#2980b9;}button.tehlike{background:#e74c3c;}button.tehlike:hover{background:#c0392b;}button.yesil{background:#27ae60;}
.kutu{background:white;padding:15px;margin-bottom:20px;border-radius:5px;}.kutu h2{margin-top:0;border-bottom:2px solid #ecf0f1;padding-bottom:8px;}
.ozet{padding:10px;margin:10px 0;border-radius:4px;font-weight:bold;}.ozet.eksik{background:#ffd0d0;color:#900;}
.ozet.tamam{background:#d8f5d0;color:#060;}.ozet.uyari{background:#ffe0b2;color:#d35400;}.grup{display:flex;gap:20px;flex-wrap:wrap;}
.miktar-input{width:110px;}.kritik-input{width:90px;}details{margin:4px 0;}summary{cursor:pointer;padding:4px;background:#ecf0f1;border-radius:4px;}
</style></head><body>
<header><h1>Konserve Üretim & Stok Takip</h1></header>
<nav>
<a href="/" class="{% if sayfa == 'uretim' %}aktif{% endif %}">Üretim Planlama</a>
<a href="/liste" class="{% if sayfa == 'liste' %}aktif{% endif %}">Üretim Listem</a>
<a href="/stok" class="{% if sayfa == 'stok' %}aktif{% endif %}">Ambalaj Stok</a>
<a href="/kimyasal" class="{% if sayfa == 'kimyasal' %}aktif{% endif %}">Kimyasal Stok</a>
<a href="/recete" class="{% if sayfa == 'recete' %}aktif{% endif %}">Reçeteler</a>
<a href="/gecmis" class="{% if sayfa == 'gecmis' %}aktif{% endif %}">Üretim Geçmişi</a>
</nav>
<div class="icerik">{{ govde|safe }}</div>
</body></html>
"""

def sb():
    return supabase

@app.route("/", methods=["GET", "POST"])
def uretim():
    c = sb()
    urunler = c.table("urun").select("id, ad").order("ad").execute().data
    sonuc = None
    plan = []
    girilen = {}

    if request.method == "POST":
        for u in urunler:
            uid = u["id"]
            deger = request.form.get(f"miktar_{uid}", "").strip()
            girilen[uid] = deger
            if deger:
                try:
                    m = float(deger.replace(",", "."))
                    if m > 0:
                        plan.append((uid, u["ad"], m))
                except:
                    pass

        if request.form.get("hesapla") and plan:
            amb_gerekli = {}
            kim_gerekli = {}
            for uid, ad, m in plan:
                rec = c.table("recete").select("malzeme_id, miktar").eq("urun_id", uid).execute().data
                for r in rec:
                    mid = r["malzeme_id"]
                    amb_gerekli[mid] = amb_gerekli.get(mid, 0) + r["miktar"] * m
                krec = c.table("kimyasal_recete").select("kimyasal_id, miktar").eq("urun_id", uid).execute().data
                for r in krec:
                    kid = r["kimyasal_id"]
                    kim_gerekli[kid] = kim_gerekli.get(kid, 0) + r["miktar"] * m

            amb_satirlar = []
            amb_eksik = False
            for mid, miktar in amb_gerekli.items():
                row = c.table("malzeme").select("ad, stok, kritik").eq("id", mid).execute().data[0]
                ad, stok, kritik = row["ad"], row["stok"], row["kritik"]
                if stok < miktar:
                    durum = f"YETMEZ ({miktar-stok:g} eksik)"
                    sinif = "yetmez"
                    amb_eksik = True
                else:
                    durum = f"YETERLİ ({stok-miktar:g} kalır)"
                    sinif = "yeterli"
                amb_satirlar.append((ad, miktar, stok, durum, sinif))
            amb_satirlar.sort(key=lambda s: 0 if "YETMEZ" in s[3] else 1)

            kim_satirlar = []
            kim_eksik = False
            for kid, miktar in kim_gerekli.items():
                row = c.table("kimyasal").select("ad, birim, stok").eq("id", kid).execute().data[0]
                ad, birim, stok = row["ad"], row["birim"], row["stok"]
                if stok < miktar:
                    durum = f"YETMEZ ({miktar-stok:g} {birim} eksik)"
                    sinif = "yetmez"
                    kim_eksik = True
                else:
                    durum = f"YETERLİ ({stok-miktar:g} {birim} kalır)"
                    sinif = "yeterli"
                kim_satirlar.append((f"{ad} ({birim})", miktar, stok, durum, sinif))
            kim_satirlar.sort(key=lambda s: 0 if "YETMEZ" in s[3] else 1)

            kritik_uyari = []
            for mid, miktar in amb_gerekli.items():
                row = c.table("malzeme").select("ad, stok, kritik").eq("id", mid).execute().data[0]
                ad, stok, kritik = row["ad"], row["stok"], row["kritik"]
                if kritik and kritik > 0 and (stok - miktar) < kritik:
                    kritik_uyari.append(f"{ad}: üretim sonrası {stok-miktar:g} kalır, kritik seviye {kritik:g}")

            sonuc = {"amb": amb_satirlar, "kim": kim_satirlar,
                     "amb_eksik": amb_eksik, "kim_eksik": kim_eksik,
                     "kritik_uyari": kritik_uyari}

        elif request.form.get("onayla") and plan:
            amb_gerekli = {}
            kim_gerekli = {}
            for uid, ad, m in plan:
                for r in c.table("recete").select("malzeme_id, miktar").eq("urun_id", uid).execute().data:
                    mid = r["malzeme_id"]
                    amb_gerekli[mid] = amb_gerekli.get(mid, 0) + r["miktar"] * m
                for r in c.table("kimyasal_recete").select("kimyasal_id, miktar").eq("urun_id", uid).execute().data:
                    kid = r["kimyasal_id"]
                    kim_gerekli[kid] = kim_gerekli.get(kid, 0) + r["miktar"] * m

            eksik = False
            for mid, miktar in amb_gerekli.items():
                stok = c.table("malzeme").select("stok").eq("id", mid).execute().data[0]["stok"]
                if stok < miktar:
                    eksik = True
                    break
            if not eksik:
                for kid, miktar in kim_gerekli.items():
                    stok = c.table("kimyasal").select("stok").eq("id", kid).execute().data[0]["stok"]
                    if stok < miktar:
                        eksik = True
                        break

            if not eksik:
                tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
                for uid, ad, m in plan:
                    gecmis_res = c.table("uretim_gecmis").insert({
                        "tarih": tarih, "urun_id": uid, "urun_ad": ad, "miktar": m
                    }).execute()
                    gid = gecmis_res.data[0]["id"]
                    for r in c.table("recete").select("malzeme_id, miktar").eq("urun_id", uid).execute().data:
                        ad_m = c.table("malzeme").select("ad").eq("id", r["malzeme_id"]).execute().data[0]["ad"]
                        c.table("uretim_detay").insert({
                            "gecmis_id": gid, "tip": "ambalaj",
                            "malzeme_ad": ad_m, "miktar": r["miktar"] * m
                        }).execute()
                    for r in c.table("kimyasal_recete").select("kimyasal_id, miktar").eq("urun_id", uid).execute().data:
                        ad_k = c.table("kimyasal").select("ad").eq("id", r["kimyasal_id"]).execute().data[0]["ad"]
                        c.table("uretim_detay").insert({
                            "gecmis_id": gid, "tip": "kimyasal",
                            "malzeme_ad": ad_k, "miktar": r["miktar"] * m
                        }).execute()

                for mid, miktar in amb_gerekli.items():
                    mevcut = c.table("malzeme").select("stok").eq("id", mid).execute().data[0]["stok"]
                    c.table("malzeme").update({"stok": mevcut - miktar}).eq("id", mid).execute()
                for kid, miktar in kim_gerekli.items():
                    mevcut = c.table("kimyasal").select("stok").eq("id", kid).execute().data[0]["stok"]
                    c.table("kimyasal").update({"stok": mevcut - miktar}).eq("id", kid).execute()

                sonuc = {"mesaj": "✓ Üretim kaydedildi. Stoklar güncellendi."}
                girilen = {}

    # Maks. üretim hesapla
    max_uret = {}
    for u in urunler:
        uid = u["id"]
        limitler = []
        for r in c.table("recete").select("malzeme_id, miktar").eq("urun_id", uid).execute().data:
            if r["miktar"] > 0:
                stok = c.table("malzeme").select("stok").eq("id", r["malzeme_id"]).execute().data[0]["stok"]
                limitler.append(int(stok // r["miktar"]))
        for r in c.table("kimyasal_recete").select("kimyasal_id, miktar").eq("urun_id", uid).execute().data:
            if r["miktar"] > 0:
                stok = c.table("kimyasal").select("stok").eq("id", r["kimyasal_id"]).execute().data[0]["stok"]
                limitler.append(int(stok // r["miktar"]))
        max_uret[uid] = min(limitler) if limitler else None

    govde = '<div class="kutu"><h2>Üretim Planlama (Anlık)</h2><form method="post"><table><tr><th>Ürün</th><th>Miktar</th><th>Maks. Üretim</th></tr>'
    for u in urunler:
        uid = u["id"]
        ad = u["ad"]
        v = girilen.get(uid, "")
        mx = max_uret.get(uid)
        if mx is None:
            mx_str = '<span class="maks-sifir">Reçete yok</span>'
        elif mx == 0:
            mx_str = '<span class="maks-sifir">Yetersiz</span>'
        else:
            mx_str = f'<span class="maks">{mx:,} adet</span>'.replace(",", ".")
        govde += f'<tr><td>{ad}</td><td><input type="number" name="miktar_{uid}" min="0" step="1" style="width:120px" value="{v}"></td><td>{mx_str}</td></tr>'
    govde += '</table><br><button type="submit" name="hesapla" value="1">PLANI HESAPLA</button> <button type="submit" name="onayla" value="1" class="tehlike">ÜRETİMİ ONAYLA (stoktan düş)</button></form></div>'

    if sonuc and "amb" in sonuc:
        govde += '<div class="grup"><div class="kutu"><h3>Ambalaj Malzemeleri</h3>'
        govde += f'<div class="ozet {"eksik" if sonuc["amb_eksik"] else "tamam"}">{"Ambalajda eksik var!" if sonuc["amb_eksik"] else "Ambalaj yeterli."}</div>'
        govde += '<table><tr><th>Malzeme</th><th>Gerekli</th><th>Stok</th><th>Durum</th></tr>'
        for ad, miktar, stok, durum, sinif in sonuc["amb"]:
            govde += f'<tr class="{sinif}"><td>{ad}</td><td>{miktar:g}</td><td>{stok:g}</td><td>{durum}</td></tr>'
        govde += '</table></div><div class="kutu"><h3>Kimyasallar</h3>'
        if not sonuc["kim"]:
            govde += '<div class="ozet eksik">Kimyasal reçetesi tanımlı değil.</div>'
        else:
            govde += f'<div class="ozet {"eksik" if sonuc["kim_eksik"] else "tamam"}">{"Kimyasalda eksik var!" if sonuc["kim_eksik"] else "Kimyasallar yeterli."}</div>'
            govde += '<table><tr><th>Kimyasal</th><th>Gerekli</th><th>Stok</th><th>Durum</th></tr>'
            for ad, miktar, stok, durum, sinif in sonuc["kim"]:
                govde += f'<tr class="{sinif}"><td>{ad}</td><td>{miktar:g}</td><td>{stok:g}</td><td>{durum}</td></tr>'
            govde += '</table>'
        govde += '</div></div>'
        if sonuc["kritik_uyari"]:
            govde += '<div class="kutu"><h3>⚠ Kritik Seviye Uyarıları</h3><div class="ozet uyari">'
            for u in sonuc["kritik_uyari"]:
                govde += f"• {u}<br>"
            govde += '</div></div>'
    elif sonuc and "mesaj" in sonuc:
        govde += f'<div class="ozet tamam">{sonuc["mesaj"]}</div>'

    return render_template_string(SAYFA, sayfa="uretim", govde=govde)


@app.route("/liste", methods=["GET", "POST"])
def liste():
    c = sb()
    if request.method == "POST" and request.form.get("kaydet_liste"):
        baslik = request.form.get("baslik", "İsimsiz Liste")
        tarih = datetime.now().strftime("%d.%m.%Y %H:%M")
        res = c.table("uretim_listesi").insert({"baslik": baslik, "tarih": tarih}).execute()
        lid = res.data[0]["id"]
        for key, val in request.form.items():
            if key.startswith("miktar_") and val.strip():
                try:
                    m = float(val.replace(",", "."))
                    if m > 0:
                        uid = int(key.replace("miktar_", ""))
                        ad = c.table("urun").select("ad").eq("id", uid).execute().data[0]["ad"]
                        c.table("uretim_listesi_detay").insert({
                            "liste_id": lid, "urun_ad": ad, "miktar": m
                        }).execute()
                except:
                    pass
        return render_template_string(SAYFA, sayfa="liste",
            govde=f'<div class="kutu"><h2>Başarılı</h2><div class="ozet tamam">"{baslik}" listesi kaydedildi.</div><a href="/liste">Geri Dön</a></div>')

    if request.method == "POST" and request.form.get("sil_liste"):
        lid = request.form.get("liste_id")
        c.table("uretim_listesi_detay").delete().eq("liste_id", lid).execute()
        c.table("uretim_listesi").delete().eq("id", lid).execute()

    urunler = c.table("urun").select("id, ad").order("ad").execute().data
    listeler = c.table("uretim_listesi").select("id, baslik, tarih").order("id", desc=True).execute().data

    govde = '<div class="grup"><div class="kutu" style="min-width: 400px;"><h2>Yeni Üretim Listesi Oluştur</h2><form method="post"><input type="hidden" name="kaydet_liste" value="1"><label>Liste Başlığı: </label><input type="text" name="baslik" required placeholder="Örn: Ekim 1. Hafta" style="width: 200px;"><br><br><table><tr><th>Ürün</th><th>Miktar</th></tr>'
    for u in urunler:
        govde += f'<tr><td>{u["ad"]}</td><td><input type="number" name="miktar_{u["id"]}" min="0" step="1" style="width:100px"></td></tr>'
    govde += '</table><br><button type="submit" class="yesil">LİSTEYİ KAYDET</button></form></div>'
    govde += '<div class="kutu" style="min-width: 400px;"><h2>Kayıtlı Listeler</h2>'
    if listeler:
        for li in listeler:
            lid = li["id"]
            detaylar = c.table("uretim_listesi_detay").select("urun_ad, miktar").eq("liste_id", lid).execute().data
            govde += f'<details><summary><b>{li["baslik"]}</b> ({li["tarih"]})</summary><table><tr><th>Ürün</th><th>Miktar</th></tr>'
            for d in detaylar:
                govde += f'<tr><td>{d["urun_ad"]}</td><td>{d["miktar"]:g}</td></tr>'
            govde += f'</table><form method="post" onsubmit="return confirm(\'Silinsin mi?\')"><input type="hidden" name="liste_id" value="{lid}"><button type="submit" name="sil_liste" value="1" class="tehlike">Sil</button></form></details><br>'
    else:
        govde += '<div class="ozet uyari">Kayıtlı liste yok.</div>'
    govde += '</div></div>'
    return render_template_string(SAYFA, sayfa="liste", govde=govde)


@app.route("/stok", methods=["GET", "POST"])
def stok():
    c = sb()
    if request.method == "POST":
        for m in c.table("malzeme").select("id").execute().data:
            mid = m["id"]
            yeni = request.form.get(f"stok_{mid}", "").strip()
            kritik = request.form.get(f"kritik_{mid}", "").strip()
            if yeni:
                try:
                    c.table("malzeme").update({"stok": float(yeni.replace(",", "."))}).eq("id", mid).execute()
                except:
                    pass
            if kritik != "":
                try:
                    c.table("malzeme").update({"kritik": float(kritik.replace(",", "."))}).eq("id", mid).execute()
                except:
                    pass

    malzemeler = c.table("malzeme").select("id, ad, stok, kritik").order("ad").execute().data
    govde = '<div class="kutu"><h2>Ambalaj Stok Durumu</h2><div class="ozet uyari">Turuncu satırlar = kritik seviyenin altında.</div><form method="post"><table><tr><th>Malzeme</th><th>Stok</th><th>Kritik Seviye</th><th>Durum</th></tr>'
    for m in malzemeler:
        mid, ad, s, k = m["id"], m["ad"], m["stok"], m["kritik"] or 0
        sinif = "kritik" if (k > 0 and s < k) else ""
        durum = "⚠ KRİTİK" if (k > 0 and s < k) else "OK"
        govde += f'<tr class="{sinif}"><td>{ad}</td><td><input type="number" name="stok_{mid}" step="any" class="miktar-input" value="{s:g}"></td><td><input type="number" name="kritik_{mid}" step="any" class="kritik-input" value="{k:g}"></td><td>{durum}</td></tr>'
    govde += '</table><br><button type="submit" class="yesil">STOKLARI KAYDET</button></form></div>'
    return render_template_string(SAYFA, sayfa="stok", govde=govde)


@app.route("/kimyasal", methods=["GET", "POST"])
def kimyasal():
    c = sb()
    if request.method == "POST":
        for k in c.table("kimyasal").select("id").execute().data:
            kid = k["id"]
            yeni = request.form.get(f"stok_{kid}", "").strip()
            kritik = request.form.get(f"kritik_{kid}", "").strip()
            if yeni:
                try:
                    c.table("kimyasal").update({"stok": float(yeni.replace(",", "."))}).eq("id", kid).execute()
                except:
                    pass
            if kritik != "":
                try:
                    c.table("kimyasal").update({"kritik": float(kritik.replace(",", "."))}).eq("id", kid).execute()
                except:
                    pass

    kim = c.table("kimyasal").select("id, ad, birim, stok, kritik").order("ad").execute().data
    govde = '<div class="kutu"><h2>Kimyasal Stok Durumu</h2><div class="ozet uyari">Turuncu satırlar = kritik seviyenin altında.</div><form method="post"><table><tr><th>Kimyasal</th><th>Birim</th><th>Stok</th><th>Kritik Seviye</th><th>Durum</th></tr>'
    for k in kim:
        kid, ad, birim, s, krt = k["id"], k["ad"], k["birim"], k["stok"], k["kritik"] or 0
        sinif = "kritik" if (krt > 0 and s < krt) else ""
        durum = "⚠ KRİTİK" if (krt > 0 and s < krt) else "OK"
        govde += f'<tr class="{sinif}"><td>{ad}</td><td>{birim}</td><td><input type="number" name="stok_{kid}" step="any" class="miktar-input" value="{s:g}"></td><td><input type="number" name="kritik_{kid}" step="any" class="kritik-input" value="{krt:g}"></td><td>{durum}</td></tr>'
    govde += '</table><br><button type="submit" class="yesil">STOKLARI KAYDET</button></form></div>'
    return render_template_string(SAYFA, sayfa="kimyasal", govde=govde)


@app.route("/recete", methods=["GET", "POST"])
def recete():
    c = sb()
    urunler = c.table("urun").select("id, ad").order("ad").execute().data
    secili_uid = request.args.get("uid", type=int) or (urunler[0]["id"] if urunler else None)

    if request.method == "POST":
        secili_uid = request.form.get("uid", type=int)
        if secili_uid and request.form.get("kaydet"):
            for m in c.table("malzeme").select("id").execute().data:
                mid = m["id"]
                deger = request.form.get(f"amb_{mid}", "").strip()
                if deger:
                    try:
                        mik = float(deger.replace(",", "."))
                        if mik > 0:
                            c.table("recete").upsert({
                                "urun_id": secili_uid, "malzeme_id": mid, "miktar": mik
                            }).execute()
                        else:
                            c.table("recete").delete().eq("urun_id", secili_uid).eq("malzeme_id", mid).execute()
                    except:
                        pass
                else:
                    c.table("recete").delete().eq("urun_id", secili_uid).eq("malzeme_id", mid).execute()

            for k in c.table("kimyasal").select("id").execute().data:
                kid = k["id"]
                deger = request.form.get(f"kim_{kid}", "").strip()
                if deger:
                    try:
                        mik = float(deger.replace(",", "."))
                        if mik > 0:
                            c.table("kimyasal_recete").upsert({
                                "urun_id": secili_uid, "kimyasal_id": kid, "miktar": mik
                            }).execute()
                        else:
                            c.table("kimyasal_recete").delete().eq("urun_id", secili_uid).eq("kimyasal_id", kid).execute()
                    except:
                        pass
                else:
                    c.table("kimyasal_recete").delete().eq("urun_id", secili_uid).eq("kimyasal_id", kid).execute()

    govde = '<div class="kutu"><h2>Reçete Düzenleme</h2><form method="get"><label>Ürün seç: </label><select name="uid" onchange="this.form.submit()">'
    for u in urunler:
        sel = "selected" if u["id"] == secili_uid else ""
        govde += f'<option value="{u["id"]}" {sel}>{u["ad"]}</option>'
    govde += '</select></form>'
    
    if secili_uid:
        amb_mevcut = {r["malzeme_id"]: r["miktar"] for r in c.table("recete").select("malzeme_id, miktar").eq("urun_id", secili_uid).execute().data}
        kim_mevcut = {r["kimyasal_id"]: r["miktar"] for r in c.table("kimyasal_recete").select("kimyasal_id, miktar").eq("urun_id", secili_uid).execute().data}
        
        govde += '<form method="post"><input type="hidden" name="uid" value="' + str(secili_uid) + '"><h3>Ambalaj Reçetesi (1 adet ürün için)</h3><table><tr><th>Malzeme</th><th>Miktar</th></tr>'
        for m in c.table("malzeme").select("id, ad").order("ad").execute().data:
            mid, ad = m["id"], m["ad"]
            deger = amb_mevcut.get(mid, "")
            ds = f"{deger:g}" if deger != "" else ""
            govde += f'<tr><td>{ad}</td><td><input type="number" name="amb_{mid}" step="any" class="miktar-input" value="{ds}" placeholder="kullanılmıyor"></td></tr>'
        
        govde += '</table><h3>Kimyasal Reçetesi (1 adet ürün için)</h3><table><tr><th>Kimyasal</th><th>Miktar</th></tr>'
        for k in c.table("kimyasal").select("id, ad, birim").order("ad").execute().data:
            kid, ad, birim = k["id"], k["ad"], k["birim"]
            deger = kim_mevcut.get(kid, "")
            ds = f"{deger:g}" if deger != "" else ""
            govde += f'<tr><td>{ad} ({birim})</td><td><input type="number" name="kim_{kid}" step="any" class="miktar-input" value="{ds}" placeholder="kullanılmıyor"></td></tr>'
        
        govde += '</table><br><button type="submit" name="kaydet" value="1" class="yesil">REÇETEYİ KAYDET</button></form>'
    govde += '</div>'
    return render_template_string(SAYFA, sayfa="recete", govde=govde)


@app.route("/gecmis", methods=["GET", "POST"])
def gecmis():
    c = sb()
    if request.method == "POST" and request.form.get("temizle"):
        c.table("uretim_detay").delete().neq("id", 0).execute()
        c.table("uretim_gecmis").delete().neq("id", 0).execute()
        return render_template_string(SAYFA, sayfa="gecmis", govde='<div class="kutu"><h2>Geçmiş</h2><div class="ozet tamam">Temizlendi.</div><a href="/gecmis">Geri</a></div>')

    kayitlar = c.table("uretim_gecmis").select("id, tarih, urun_ad, miktar").order("id", desc=True).execute().data
    govde = f'<div class="kutu"><h2>Üretim Geçmişi</h2><p>Toplam {len(kayitlar)} kayıt</p>'
    if kayitlar:
        govde += '<form method="post" onsubmit="return confirm(\'Tümü silinecek. Emin misiniz?\')"><button type="submit" name="temizle" value="1" class="tehlike">TÜM GEÇMİŞİ TEMİZLE</button></form><br>'
        govde += '<table><tr><th>Tarih</th><th>Ürün</th><th>Miktar</th><th>Detay</th></tr>'
        for k in kayitlar:
            kid, tarih, urun_ad, miktar = k["id"], k["tarih"], k["urun_ad"], k["miktar"]
            detaylar = c.table("uretim_detay").select("tip, malzeme_ad, miktar").eq("gecmis_id", kid).execute().data
            detay_html = "<details><summary>Göster</summary><ul>"
            for d in detaylar:
                detay_html += f"<li>[{d['tip']}] {d['malzeme_ad']}: {d['miktar']:g}</li>"
            detay_html += "</ul></details>"
            govde += f'<tr><td>{tarih}</td><td>{urun_ad}</td><td>{miktar:g}</td><td>{detay_html}</td></tr>'
        govde += '</table>'
    else:
        govde += '<div class="ozet uyari">Henüz üretim kaydı yok.</div>'
    govde += '</div>'
    return render_template_string(SAYFA, sayfa="gecmis", govde=govde)

if __name__ == "__main__":
    app.run(debug=True)