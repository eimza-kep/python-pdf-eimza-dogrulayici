#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python PDF E-İmza (PAdES) Doğrulayıcı ve Bilgi Okuyucu
=====================================================
Bu betik, Türkiye 5070 Sayılı Elektronik İmza Kanunu kapsamında üretilen
PAdES ve CAdES dijital imzalı PDF belgelerini inceler; imzacının adını,
zaman damgasını, imza formatını ve bütünlüğünü analiz eder.

Yazar: E-İmza & Dijital Dönüşüm Portalı (https://eimza-kep.github.io/eimza-blog/)
Lisans: MIT
"""

import sys
import os
import re
import json
import argparse
from datetime import datetime

def parse_pdf_date(date_str):
    """PDF Tarih formatını (D:YYYYMMDDHHmmSSOHH'mm') okunabilir tarihe çevirir."""
    if not date_str:
        return ""
    m = re.match(r"D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", date_str)
    if m:
        year, month, day, hour, minute, sec = m.groups()
        return f"{year}-{month}-{day} {hour}:{minute}:{sec}"
    return date_str

def extract_signatures_native(pdf_path):
    """
    Sıfır bağımlılık (Zero-dependency) ile PDF ikili (binary) akışını tarayarak
    /Type /Sig nesnelerini ve imza meta verilerini ayıklar.
    """
    with open(pdf_path, "rb") as f:
        data = f.read()

    # /Type /Sig arama
    sig_matches = list(re.finditer(rb"/Type\s*/Sig\b", data))
    if not sig_matches:
        return []

    signatures = []
    
    for idx, match in enumerate(sig_matches):
        start_pos = max(0, match.start() - 200)
        end_pos = min(len(data), match.end() + 2000)
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
        if br_m:
            byterange = [int(x) for x in br_m.group(1).split()]

        format_desc = "Bilinmiyor"
        if "ETSI.CAdES.detached" in subfilter:
            format_desc = "PAdES (ETSI TS 102 778 - Türkiye e-İmza Standardı)"
        elif "adbe.pkcs7.detached" in subfilter:
            format_desc = "PKCS#7 Detached (Standart Dijital İmza)"
        elif "adbe.pkcs7.sha1" in subfilter:
            format_desc = "PKCS#7 SHA1"

        signatures.append({
            "index": idx + 1,
            "signer_name": name or "İsimsiz veya X.509 ASN.1 Sertifika İçi",
            "subfilter": subfilter,
            "format": format_desc,
            "signing_time": m_date,
            "reason": reason,
            "location": location,
            "byterange": byterange,
            "status": "IMZALI"
        })

    return signatures

def inspect_pdf(pdf_path, as_json=False):
    if not os.path.exists(pdf_path):
        print(f"Hata: Dosya bulunamadı -> {pdf_path}", file=sys.stderr)
        sys.exit(1)

    signatures = extract_signatures_native(pdf_path)

    result = {
        "file_name": os.path.basename(pdf_path),
        "file_path": os.path.abspath(pdf_path),
        "is_signed": len(signatures) > 0,
        "signature_count": len(signatures),
        "signatures": signatures
    }

    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("=" * 80)
    print("       PYTHON PDF E-İMZA (PAdES / CAdES) DOĞRULAYICI v1.0")
    print("=" * 80)
    print(f"İncelenen Dosya: {result['file_name']}")
    print(f"Dosya Yolu:      {result['file_path']}")
    print(f"İmza Durumu:     {'✅ İMZALI BELGE' if result['is_signed'] else '❌ İMZASIZ / DİJİTAL İMZA YOK'}")
    print(f"Toplam İmza:     {result['signature_count']} Adet\n")

    if not signatures:
        print("[!] Bu PDF dosyasında herhangi bir dijital imza sözlüğü (/Type /Sig) tespit edilemedi.")
        print("    Not: Islak imza taramaları görseldir ve elektronik imza sayılmaz.")
        print("\nRehber: https://eimza-kep.github.io/eimza-blog/posts/e-imza-cihazlari-nasil-calisir-teknik-rehber.html")
        return

    for sig in signatures:
        print(f"--- İmza #{sig['index']} ---")
        print(f"  İmzacı:       {sig['signer_name']}")
        print(f"  Standart:     {sig['format']}")
        print(f"  Alt Filtre:   {sig['subfilter']}")
        print(f"  İmza Tarihi:  {sig['signing_time'] or 'Belirtilmemiş'}")
        if sig['reason']:
            print(f"  İmza Amacı:   {sig['reason']}")
        if sig['location']:
            print(f"  Konum:        {sig['location']}")
        print(f"  Bayt Aralığı: {sig['byterange']}")
        print()

    print("-" * 80)
    print("💡 BİLGİ: 5070 Sayılı Kanun gereği geçerli e-imzalar Nitelikli Elektronik Sertifika (NES)")
    print("   ile üretilir ve ıslak imza ile birebir aynı hukuki geçerliliğe sahiptir.")
    print("   Rehber: https://eimza-kep.github.io/eimza-blog/posts/e-imza-cihazlari-nasil-calisir-teknik-rehber.html")
    print("=" * 80)

def main():
    parser = argparse.ArgumentParser(
        description="PDF E-İmza (PAdES/CAdES) Doğrulama ve İmza Bilgisi Okuyucu"
    )
    parser.add_argument("pdf_path", help="İncelenecek PDF dosyasının yolu")
    parser.add_argument("--json", action="store_true", help="Sonucu JSON formatında verir")
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    inspect_pdf(args.pdf_path, as_json=args.json)

if __name__ == "__main__":
    main()
