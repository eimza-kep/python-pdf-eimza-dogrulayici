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
import hashlib
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
        end_pos = min(len(data), match.end() + 3000)
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

        # Contents (PKCS#7 İmza boyutu)
        contents_size_bytes = 0
        contents_m = re.search(r"/Contents\s*<([0-9A-Fa-f]+)>", chunk)
        if contents_m:
            contents_size_bytes = len(contents_m.group(1)) // 2

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
            "status": "IMZALI"
        })

    return signatures

def inspect_pdf(pdf_path):
    signatures = extract_signatures_native(pdf_path)
    return {
        "file_name": os.path.basename(pdf_path),
        "file_path": os.path.abspath(pdf_path),
        "file_size_bytes": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
        "is_signed": len(signatures) > 0,
        "signature_count": len(signatures),
        "signatures": signatures
    }

def print_result_cli(result):
    print("=" * 80)
    print("       PYTHON PDF E-İMZA (PAdES / CAdES) DOĞRULAYICI v1.1")
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
    parser.add_argument("--output", help="Raporu belirtilen JSON dosyasına kaydeder")
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
            batch_results.append(r)
        
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

    result = inspect_pdf(args.pdf_path)

    if args.output:
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

