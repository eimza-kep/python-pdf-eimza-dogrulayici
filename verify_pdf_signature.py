#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python PDF E-İmza (PAdES / CAdES) Doğrulayıcı ve Bilgi Okuyucu v1.2
==================================================================
Bu betik, Türkiye 5070 Sayılı Elektronik İmza Kanunu kapsamında üretilen
PAdES ve CAdES dijital imzalı PDF belgelerini inceler; imzacının adını,
zaman damgasını, imza formatını, sertifika meta verilerini ve bütünlüğünü analiz eder.

Özellikler:
- Sıfır harici kütüphane bağımlılığı (Pure Python Standard Library)
- ETSI PAdES-BES, PAdES-LTV ve PKCS#7 Detached desteği
- PKCS#7 (.p7s) imza bloğu dışa aktarma (--extract-p7s)
- ASN.1 DER ayrıştırıcı ile sertifika CN, O, OU, ESHS sağlayıcı bilgisi tespiti
- JSON, CSV ve Markdown formatında raporlama
- Toplu dizin tarama (--dir) ve CI/CD doğrulaması (--require-signed)

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://eimza-kep.github.io/eimza-blog/)
Lisans: MIT
"""

import sys
import os
import re
import json
import csv
import argparse
import hashlib
from datetime import datetime

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def parse_pdf_date(date_str):
    """PDF Tarih formatını (D:YYYYMMDDHHmmSSOHH'mm') okunabilir tarihe çevirir."""
    if not date_str:
        return ""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", date_str)
    if m:
        year, month, day, hour, minute, sec = m.groups()
        return f"{year}-{month}-{day} {hour}:{minute}:{sec}"
    return date_str

def parse_asn1_strings_from_der(der_bytes):
    """
    Sıfır bağımlılık ile DER/PKCS#7 akışı içerisindeki PrintableString ve UTF8String
    etiketlerini tarar; sertifika sahibi (CN), kurum ve ESHS bilgilerini filtreler.
    """
    found_strings = []
    i = 0
    length_bytes = len(der_bytes)
    
    # 0x0C = UTF8String, 0x13 = PrintableString, 0x16 = IA5String
    target_tags = {0x0C, 0x13, 0x16}
    
    while i < length_bytes - 2:
        tag = der_bytes[i]
        if tag in target_tags:
            l = der_bytes[i + 1]
            content_start = i + 2
            if l > 0x80:
                num_bytes = l & 0x7F
                if content_start + num_bytes <= length_bytes:
                    l = int.from_bytes(der_bytes[content_start : content_start + num_bytes], "big")
                    content_start += num_bytes
                else:
                    i += 1
                    continue
            
            if 2 <= l <= 128 and (content_start + l) <= length_bytes:
                chunk = der_bytes[content_start : content_start + l]
                try:
                    s = chunk.decode("utf-8")
                    if any(c.isalnum() for c in s) and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", s):
                        found_strings.append(s.strip())
                except Exception:
                    try:
                        s = chunk.decode("latin-1")
                        if any(c.isalnum() for c in s) and not re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", s):
                            found_strings.append(s.strip())
                    except Exception:
                        pass
                i = content_start + l
                continue
        i += 1
        
    known_eshs = [
        "Kamu SM", "TÜBİTAK BİLGEM", "TUBITAK", "TurkTrust", "TÜRKRUST",
        "E-Tugra", "E-TUĞRA", "E-Guven", "E-GÜVEN", "EDM Bilişim", "EDM",
        "Izmir Nitelikli Elektronik Sertifika", "Yetkili Elektronik Sertifika Hizmet Sağlayıcısı"
    ]
    
    detected_eshs = []
    for s in found_strings:
        for eshs in known_eshs:
            if eshs.lower() in s.lower() and eshs not in detected_eshs:
                detected_eshs.append(eshs)

    return {
        "candidate_strings": found_strings[:15],
        "detected_eshs": detected_eshs
    }

def extract_signatures_native(pdf_path):
    """
    Sıfır bağımlılık (Zero-dependency) ile PDF ikili (binary) akışını tarayarak
    /Type /Sig nesnelerini, kriptografik bayt aralığını ve imza meta verilerini ayıklar.
    """
    with open(pdf_path, "rb") as f:
        data = f.read()

    file_size = len(data)
    sig_matches = list(re.finditer(rb"/Type\s*/Sig\b", data))
    if not sig_matches:
        return []

    signatures = []
    
    for idx, match in enumerate(sig_matches):
        start_pos = max(0, match.start() - 300)
        end_pos = min(len(data), match.end() + 4000)
        chunk = data[start_pos:end_pos].decode("latin1", errors="ignore")

        # SubFilter (PAdES / adbe.pkcs7.detached vb.)
        subfilter = ""
        sf_m = re.search(r"/SubFilter\s*/([A-Za-z0-9\._]+)", chunk)
        if sf_m:
            subfilter = sf_m.group(1)

        # İmzacı Adı (/Name)
        name = ""
        name_m = re.search(r"/Name\s*\((.*?)\)", chunk)
        if name_m:
            name = name_m.group(1)
        elif re.search(r"/Name\s*<([0-9A-Fa-f]+)>", chunk):
            hex_str = re.search(r"/Name\s*<([0-9A-Fa-f]+)>", chunk).group(1)
            try:
                name = bytes.fromhex(hex_str).decode("utf-16-be", errors="ignore")
            except Exception:
                name = hex_str

        # İmza Zamanı (/M)
        m_date = ""
        date_m = re.search(r"/M\s*\((.*?)\)", chunk)
        if date_m:
            m_date = parse_pdf_date(date_m.group(1))

        # İmza Nedeni (/Reason)
        reason = ""
        reason_m = re.search(r"/Reason\s*\((.*?)\)", chunk)
        if reason_m:
            reason = reason_m.group(1)

        # Konum (/Location)
        location = ""
        loc_m = re.search(r"/Location\s*\((.*?)\)", chunk)
        if loc_m:
            location = loc_m.group(1)

        # ByteRange
        byterange = []
        br_m = re.search(r"/ByteRange\s*\[([0-9\s]+)\]", chunk)
        signed_hash_sha256 = ""
        integrity_status = "Bilinmiyor"
        
        if br_m:
            byterange = [int(x) for x in br_m.group(1).split()]
            if len(byterange) == 4:
                o1, l1, o2, l2 = byterange
                if o1 == 0 and (o2 + l2) <= file_size:
                    signed_bytes = data[o1 : o1 + l1] + data[o2 : o2 + l2]
                    signed_hash_sha256 = hashlib.sha256(signed_bytes).hexdigest()
                    
                    if (o2 + l2) == file_size:
                        integrity_status = "TAM_KAPSAM (Belge son imzadan sonra değiştirilmemiş)"
                    else:
                        trailing = file_size - (o2 + l2)
                        integrity_status = f"REVIZYON_MEVCUT (İmzadan sonra {trailing} bayt ek veri/revizyon var)"
                else:
                    integrity_status = "GECERSIZ_ARALIK (ByteRange dosya sınırlarını aşıyor)"

        # Contents (PKCS#7 İmza verisi)
        contents_size_bytes = 0
        raw_p7s_hex = ""
        contents_m = re.search(r"/Contents\s*<([0-9A-Fa-f]+)>", chunk)
        if contents_m:
            raw_p7s_hex = contents_m.group(1)
            contents_size_bytes = len(raw_p7s_hex) // 2

        der_analysis = {"candidate_strings": [], "detected_eshs": []}
        if raw_p7s_hex:
            try:
                raw_der = bytes.fromhex(raw_p7s_hex)
                der_analysis = parse_asn1_strings_from_der(raw_der)
            except Exception:
                pass

        format_desc = "Bilinmiyor"
        if "ETSI.CAdES.detached" in subfilter:
            format_desc = "PAdES (ETSI TS 102 778 - Türkiye e-İmza Standardı)"
        elif "adbe.pkcs7.detached" in subfilter:
            format_desc = "PKCS#7 Detached (Standart Dijital İmza)"
        elif "adbe.pkcs7.sha1" in subfilter:
            format_desc = "PKCS#7 SHA1"

        signatures.append({
            "index": idx + 1,
            "signer_name": name or "İsimsiz / Sertifika İçi",
            "subfilter": subfilter,
            "format": format_desc,
            "signing_time": m_date,
            "reason": reason,
            "location": location,
            "byterange": byterange,
            "signature_size_bytes": contents_size_bytes,
            "signed_digest_sha256": signed_hash_sha256,
            "integrity": integrity_status,
            "detected_eshs": ", ".join(der_analysis["detected_eshs"]) if der_analysis["detected_eshs"] else "Belirtilmemiş",
            "cert_attributes": der_analysis["candidate_strings"][:8],
            "raw_p7s_hex": raw_p7s_hex,
            "status": "IMZALI"
        })

    return signatures

def inspect_pdf(pdf_path):
    signatures = extract_signatures_native(pdf_path)
    clean_signatures = []
    for s in signatures:
        s_copy = dict(s)
        s_copy.pop("raw_p7s_hex", None)
        clean_signatures.append(s_copy)

    return {
        "file_name": os.path.basename(pdf_path),
        "file_path": os.path.abspath(pdf_path),
        "file_size_bytes": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
        "is_signed": len(signatures) > 0,
        "signature_count": len(signatures),
        "signatures": clean_signatures,
        "_raw_signatures": signatures
    }

def export_p7s(pdf_path, output_dir=None):
    """PDF içerisindeki ham PKCS#7 (.p7s) imza ikili verilerini dosya olarak dışa aktarır."""
    r = inspect_pdf(pdf_path)
    if not r["_raw_signatures"]:
        print(f"[!] İmzalı nesne bulunamadı: {pdf_path}")
        return []
    
    out_dir = output_dir or os.path.dirname(os.path.abspath(pdf_path))
    exported_files = []
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    for sig in r["_raw_signatures"]:
        raw_hex = sig.get("raw_p7s_hex")
        if raw_hex:
            p7s_path = os.path.join(out_dir, f"{base_name}_sig_{sig['index']}.p7s")
            with open(p7s_path, "wb") as f:
                f.write(bytes.fromhex(raw_hex))
            exported_files.append(p7s_path)
            print(f"[+] PKCS#7 İmza bloğu dışa aktarıldı: {p7s_path}")

    return exported_files

def generate_markdown_report(result):
    md = f"# PDF E-İmza Doğrulama Raporu: {result['file_name']}\n\n"
    md += f"- **Dosya:** `{result['file_name']}`\n"
    md += f"- **Tam Yol:** `{result['file_path']}`\n"
    md += f"- **Boyut:** {result['file_size_bytes']:,} bayt\n"
    md += f"- **İmza Durumu:** {'✅ İmzalı Belge' if result['is_signed'] else '❌ İmzasız'}\n"
    md += f"- **İmza Sayısı:** {result['signature_count']}\n\n"
    
    if not result['signatures']:
        md += "> ⚠️ Bu belgede dijital elektronik imza sözlüğü (`/Type /Sig`) tespit edilemedi.\n"
        return md

    md += "| # | İmzacı | Format / Standart | Tarih | ESHS Sağlayıcı | Bütünlük |\n"
    md += "|---|---|---|---|---|---|\n"
    for s in result['signatures']:
        md += f"| {s['index']} | **{s['signer_name']}** | {s['subfilter']} | {s['signing_time'] or '-'} | {s['detected_eshs']} | {s['integrity']} |\n"

    md += "\n## İmza Detayları\n"
    for s in result['signatures']:
        md += f"### İmza #{s['index']} - {s['signer_name']}\n"
        md += f"- **Standart:** {s['format']}\n"
        md += f"- **İmzalanan SHA-256 Özeti:** `{s['signed_digest_sha256']}`\n"
        md += f"- **İmza Boyutu:** {s['signature_size_bytes']} bayt\n"
        if s.get("cert_attributes"):
            md += f"- **Sertifika Nitelikleri:** {', '.join(s['cert_attributes'])}\n"
        md += "\n"

    return md

def print_result_cli(result):
    print("=" * 80)
    print("       PYTHON PDF E-İMZA (PAdES / CAdES) DOĞRULAYICI v1.2")
    print("=" * 80)
    print(f"İncelenen Dosya: {result['file_name']}")
    print(f"Dosya Yolu:      {result['file_path']}")
    print(f"İmza Durumu:     {'✅ İMZALI BELGE' if result['is_signed'] else '❌ İMZASIZ / DİJİTAL İMZA YOK'}")
    print(f"Toplam İmza:     {result['signature_count']} Adet\n")

    if not result['signatures']:
        print("[!] Bu PDF dosyasında herhangi bir dijital imza sözlüğü (/Type /Sig) tespit edilemedi.")
        print("    Not: Islak imza taramaları görseldir ve elektronik imza sayılmaz.")
        print("\nRehber: https://eimza-kep.github.io/eimza-blog/posts/pdf-dokumanlara-e-imza-atma-ucretsiz-rehber.html")
        return

    for sig in result['signatures']:
        print(f"--- İmza #{sig['index']} ---")
        print(f"  İmzacı:         {sig['signer_name']}")
        print(f"  Standart:       {sig['format']}")
        print(f"  Alt Filtre:     {sig['subfilter']}")
        print(f"  İmza Tarihi:    {sig['signing_time'] or 'Belirtilmemiş'}")
        if sig.get('detected_eshs') and sig['detected_eshs'] != "Belirtilmemiş":
            print(f"  ESHS Sağlayıcı: {sig['detected_eshs']}")
        if sig['reason']:
            print(f"  İmza Amacı:     {sig['reason']}")
        if sig['location']:
            print(f"  Konum:          {sig['location']}")
        print(f"  İmza Boyutu:    {sig['signature_size_bytes']} bayt")
        if sig['signed_digest_sha256']:
            print(f"  İmzalanan Özet: SHA-256:{sig['signed_digest_sha256']}")
        print(f"  Bütünlük:       {sig['integrity']}")
        print()

    print("-" * 80)
    print("💡 BİLGİ: 5070 Sayılı Kanun gereği geçerli e-imzalar Nitelikli Elektronik Sertifika (NES)")
    print("   ile üretilir ve ıslak imza ile birebir aynı hukuki geçerliliğe sahiptir.")
    print("   Rehber: https://eimza-kep.github.io/eimza-blog/posts/pdf-dokumanlara-e-imza-atma-ucretsiz-rehber.html")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description="PDF E-İmza (PAdES/CAdES) Doğrulama ve İmza Bilgisi Okuyucu"
    )
    parser.add_argument("pdf_path", nargs="?", default=None, help="İncelenecek PDF dosyasının yolu")
    parser.add_argument("--dir", help="Belirtilen dizindeki tüm PDF dosyalarını toplu inceleme")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON formatında verir")
    parser.add_argument("--markdown", action="store_true", help="Sonucu Markdown formatında verir")
    parser.add_argument("--csv", help="Toplu veya tekli tarama sonucunu belirtilen CSV dosyasına yazar")
    parser.add_argument("--output", help="Raporu belirtilen JSON/Markdown dosyasına kaydeder")
    parser.add_argument("--extract-p7s", action="store_true", help="PDF içindeki ham PKCS#7 (.p7s) imza dosyalarını dışa aktarır")
    parser.add_argument("--require-signed", action="store_true", help="İmzasız belge tespit edilirse 1 çıkış kodu üretir")
    
    args = parser.parse_args()

    if not args.pdf_path and not args.dir:
        parser.print_help()
        sys.exit(0)

    if args.dir:
        if not os.path.isdir(args.dir):
            print(f"Hata: Dizin bulunamadı -> {args.dir}", file=sys.stderr)
            sys.exit(1)
        pdf_files = [os.path.join(args.dir, f) for f in os.listdir(args.dir) if f.lower().endswith(".pdf")]
        batch_results = []
        any_unsigned = False
        for p in sorted(pdf_files):
            r = inspect_pdf(p)
            if not r["is_signed"]:
                any_unsigned = True
            r.pop("_raw_signatures", None)
            batch_results.append(r)
        
        if args.csv:
            with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Dosya", "Imzali_Mi", "Imza_Sayisi", "Ilk_Imzaci", "Format", "Tarih", "ESHS"])
                for b in batch_results:
                    first_sig = b["signatures"][0] if b["signatures"] else {}
                    writer.writerow([
                        b["file_name"],
                        "EVET" if b["is_signed"] else "HAYIR",
                        b["signature_count"],
                        first_sig.get("signer_name", "-"),
                        first_sig.get("subfilter", "-"),
                        first_sig.get("signing_time", "-"),
                        first_sig.get("detected_eshs", "-")
                    ])
            print(f"[OK] CSV raporu kaydedildi: {args.csv}")

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(batch_results, f, ensure_ascii=False, indent=2)
            print(f"[OK] Toplu rapor kaydedildi: {args.output}")
        elif args.json:
            print(json.dumps(batch_results, ensure_ascii=False, indent=2))
        else:
            print(f"Toplam {len(batch_results)} adet PDF tarandı:")
            for r in batch_results:
                icon = "✅" if r["is_signed"] else "❌"
                print(f"  {icon} {r['file_name']} (İmza Sayısı: {r['signature_count']})")
        
        if args.require_signed and any_unsigned:
            sys.exit(1)
        return

    if not os.path.exists(args.pdf_path):
        print(f"Hata: Dosya bulunamadı -> {args.pdf_path}", file=sys.stderr)
        sys.exit(1)

    if args.extract_p7s:
        export_p7s(args.pdf_path)

    result = inspect_pdf(args.pdf_path)
    raw_sigs = result.pop("_raw_signatures", None)

    if args.csv:
        with open(args.csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Dosya", "Imzali_Mi", "Imza_Sayisi", "Imza_No", "Imzaci", "Format", "Tarih", "ESHS", "Butunluk"])
            if result["signatures"]:
                for s in result["signatures"]:
                    writer.writerow([
                        result["file_name"],
                        "EVET",
                        result["signature_count"],
                        s["index"],
                        s["signer_name"],
                        s["subfilter"],
                        s["signing_time"],
                        s["detected_eshs"],
                        s["integrity"]
                    ])
            else:
                writer.writerow([result["file_name"], "HAYIR", 0, "-", "-", "-", "-", "-", "-"])
        print(f"[OK] CSV raporu kaydedildi: {args.csv}")

    if args.markdown:
        md = generate_markdown_report(result)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"[OK] Markdown raporu kaydedildi: {args.output}")
        else:
            print(md)
    elif args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[OK] Rapor kaydedildi: {args.output}")
    elif args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_result_cli(result)

    if args.require_signed and not result["is_signed"]:
        sys.exit(1)

if __name__ == "__main__":
    main()
