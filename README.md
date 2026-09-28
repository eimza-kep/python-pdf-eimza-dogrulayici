# Python PDF E-İmza (PAdES / CAdES) Doğrulayıcı 📜🔏

[![Python CI](https://github.com/eimza-kep/python-pdf-eimza-dogrulayici/actions/workflows/ci.yml/badge.svg)](https://github.com/eimza-kep/python-pdf-eimza-dogrulayici/actions)
[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Standart: PAdES](https://img.shields.io/badge/Standart-ETSI%20PAdES-orange.svg)](https://etsi.org)
[![Bağımlılık: Yok](https://img.shields.io/badge/Dependencies-Zero--Dependency-success.svg)](https://github.com)
[![Blog](https://img.shields.io/badge/Rehber-E--%C4%B0mza%20Blog-22c55e.svg)](https://eimza-kep.github.io/eimza-blog/)

Türkiye'de **5070 Sayılı Elektronik İmza Kanunu** kapsamında üretilen; kamu kurumları (GİB, EKAP, UYAP, KEP, Web Tapu, Noterler) ve özel sektör tarafından imzalanmış PDF belgelerinin **elektronik imza geçerliliğini, imzacının adını, imza tarihini, ESHS sağlayıcısını ve standart formatını (PAdES / CAdES)** inceleyen hafif ve açık kaynaklı Python aracıdır.

---

## ✨ Öne Çıkan Özellikler

* ⚡ **Sıfır Harici Bağımlılık (Zero-Dependency):** Herhangi bir ağır C kütüphanesine veya harici modüle ihtiyaç duymadan saf Python standart kütüphanesiyle çalışır.
* 👤 **İmzacı ve Meta Veri Çıkarımı:** İmzacı Adı (`/Name`), İmza Zamanı (`/M`), İmza Nedeni (`/Reason`), Konum (`/Location`) ve Bayt Aralığını (`/ByteRange`) ayrıştırır.
* 🔍 **ASN.1 DER Ayrıştırma:** PKCS#7 imza gövdesini tarayarak Kamu SM, TÜRKTRUST, E-Tuğra, E-Güven vb. ESHS sağlayıcılarını tespit eder.
* 📦 **PKCS#7 (.p7s) Dışa Aktarma:** PDF içindeki ham dijital imza bloğunu `--extract-p7s` ile ayıklayıp harici denetim araçlarına sunabilir.
* 📊 **Çoklu Raporlama:** Terminal, JSON, CSV ve Markdown formatlarında rapor üretir.
* 🇹🇷 **Türkiye Standartlarıyla Uyumlu:** `ETSI.CAdES.detached` (PAdES) ve `adbe.pkcs7.detached` formatlarını destekler.
* 🤖 **CI/CD Entegrasyonu:** `--require-signed` bayrağı ile imzasız dokümanlarda derleme/dağıtım durdurma kontrolü sunar.

---

## 🚀 Hızlı Başlangıç

### 1. Komut Satırından Çalıştırma
```bash
python verify_pdf_signature.py sozlesme_imzali.pdf
```

**Örnek Çıktı:**
```text
================================================================================
       PYTHON PDF E-İMZA (PAdES / CAdES) DOĞRULAYICI v1.2
================================================================================
İncelenen Dosya: sozlesme_imzali.pdf
Dosya Yolu:      C:\Evraklar\sozlesme_imzali.pdf
İmza Durumu:     ✅ İMZALI BELGE
Toplam İmza:     1 Adet

--- İmza #1 ---
  İmzacı:         AHMET YILMAZ
  Standart:       PAdES (ETSI TS 102 778 - Türkiye e-İmza Standardı)
  Alt Filtre:     ETSI.CAdES.detached
  İmza Tarihi:    2026-09-18 14:32:10
  ESHS Sağlayıcı: Kamu SM
  İmza Amacı:     Belgeyi Onaylıyorum
  İmza Boyutu:    8192 bayt
  İmzalanan Özet: SHA-256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
  Bütünlük:       TAM_KAPSAM (Belge son imzadan sonra değiştirilmemiş)
```

### 2. Markdown ve CSV Raporu Alma
```bash
# Markdown raporu oluşturma
python verify_pdf_signature.py sozlesme_imzali.pdf --markdown

# Klasördeki tüm belgeleri CSV olarak dışa aktarma
python verify_pdf_signature.py --dir ./evraklar/ --csv rapor.csv
```

### 3. Ham PKCS#7 (.p7s) İmza Bloğunu Çıkarma
```bash
python verify_pdf_signature.py sozlesme_imzali.pdf --extract-p7s
```

### 4. JSON Formatında Çıktı Alma
Otomasyon sistemleri ve API pipeline'ları için:
```bash
python verify_pdf_signature.py sozlesme_imzali.pdf --json
```

### 5. Klasördeki Tüm PDF'leri Toplu İnceleme (Batch Scan)
```bash
# Klasör tarama ve imzasız belge varsa çıkış kodu 1 döndürme
python verify_pdf_signature.py --dir ./evraklar/ --require-signed
```

---

## 🐍 Python Projelerinde Kütüphane Olarak Kullanım

Kendi Python projenizde doğrudan fonksiyon olarak çağırabilirsiniz:

```python
from verify_pdf_signature import inspect_pdf, extract_signatures_native

# Detaylı denetim raporu
result = inspect_pdf("ihale_teklifi.pdf")

if result["is_signed"]:
    print(f"Belge imzalı! Toplam imza sayısı: {result['signature_count']}")
    for sig in result["signatures"]:
        print(f"-> İmzacı: {sig['signer_name']} | Tarih: {sig['signing_time']} | ESHS: {sig['detected_eshs']}")
else:
    print("Belgede geçerli dijital imza tespit edilemedi!")
```

---

## 🔗 E-Dönüşüm Açık Kaynak Ekosistemi

Bu araç [eimza-kep](https://github.com/eimza-kep) organizasyonunun açık kaynak e-dönüşüm araçları ekosisteminin bir parçasıdır:

* 🇹🇷 **[awesome-turkiye-e-donusum](https://github.com/eimza-kep/awesome-turkiye-e-donusum):** Türkiye E-Dönüşüm kütüphane, mevzuat ve araçlar listesi.
* 🔓 **[eimza-pin-bloke-asistani](https://github.com/eimza-kep/eimza-pin-bloke-asistani):** USB token PIN bloke çözüm rehberi ve PUK kurtarma terminali.
* 🩺 **[akilli-kart-surucu-teshis](https://github.com/eimza-kep/akilli-kart-surucu-teshis):** Windows 10/11 akıllı kart sürücüsü ve AKİS servis tanı asistanı.
* ⏱️ **[mali-muhur-eimza-suresi-kontrol](https://github.com/eimza-kep/mali-muhur-eimza-suresi-kontrol):** Sertifika bitiş tarihi hesaplama ve bildirim aracı.
* 🧾 **[e-fatura-xml-goruntuleyici](https://github.com/eimza-kep/e-fatura-xml-goruntuleyici):** GİB UBL-TR e-Fatura ve e-Arşiv XML görüntüleyici.
* 📝 **[udf2md](https://github.com/eimza-kep/udf2md):** UYAP UDF dosyalarını Markdown'a dönüştüren CLI aracı.

---

## 📚 İlgili Teknik Rehberler
* 📄 [PDF Dokümanlara Ücretsiz ve Güvenli E-İmza Atma Rehberi](https://eimzabilgi.site/yazilar/ucretsiz-e-imza-atma-yontemleri.html)
* 📄 [Özel Anahtar (Private Key) Neden Akıllı Kartın İçinden Kopyalanamaz?](https://kimlikguvenlik.site/yazilar/ozel-anahtar-private-key-neden-kopyalanamaz.html)
* 📄 [Zaman Damgası (Timestamp) Nedir ve Belgelerde Neden Zorunludur?](https://kimlikguvenlik.site/yazilar/zaman-damgasi-timestamp-nedir-neden-zorunlu.html)
* 📄 [Elektronik İmza Nedir? Islak İmza Yerine Hangi Alanlarda Kullanılır?](https://eimzabilgi.site/yazilar/5070-sayili-kanun-eimza-hukuki-gecerlilik.html)

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Ticari ve kişisel projelerde serbestçe kullanılabilir.