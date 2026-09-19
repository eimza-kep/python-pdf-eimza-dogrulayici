# Python PDF E-İmza (PAdES / CAdES) Doğrulayıcı 📜🔏

[![Lisans: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
[![Standart: PAdES](https://img.shields.io/badge/Standart-ETSI%20PAdES-orange.svg)](https://etsi.org)
[![Bağımlılık: Yok](https://img.shields.io/badge/Dependencies-Zero--Dependency-success.svg)](https://github.com)
[![Blog](https://img.shields.io/badge/Rehber-E--%C4%B0mza%20Blog-22c55e.svg)](https://eimza-kep.github.io/eimza-blog/)

Türkiye'de **5070 Sayılı Elektronik İmza Kanunu** kapsamında üretilen; kamu kurumları (GİB, EKAP, UYAP, KEP, Web Tapu, Noterler) ve özel sektör tarafından imzalanmış PDF belgelerinin **elektronik imza geçerliliğini, imzacının adını, imza tarihini ve standart formatını (PAdES / CAdES)** inceleyen hafif ve açık kaynaklı Python aracıdır.

---

## ✨ Öne Çıkan Özellikler

* ⚡ **Sıfır Harici Bağımlılık (Zero-Dependency):** Herhangi bir ağır C kütüphanesine veya harici modüle ihtiyaç duymadan saf Python ile PDF binary akışını tarar.
* 👤 **İmzacı ve Meta Veri Çıkarımı:** İmzacı Adı (`/Name`), İmza Zamanı (`/M`), İmza Nedeni (`/Reason`), Konum (`/Location`) ve Bayt Aralığını (`/ByteRange`) ayrıştırır.
* 🇹🇷 **Türkiye Standartlarıyla Uyumlu:** `ETSI.CAdES.detached` (PAdES) ve `adbe.pkcs7.detached` formatlarını destekler.
* 🤖 **JSON Çıkış Desteği:** REST API'lerinize, backend servislerinize ve Django/FastAPI/Flask projelerinize doğrudan entegre edilebilir.

---

## 🚀 Hızlı Başlangıç

### 1. Komut Satırından Çalıştırma
```bash
python verify_pdf_signature.py sozlesme_imzali.pdf
```

**Örnek Çıktı:**
```text
================================================================================
       PYTHON PDF E-İMZA (PAdES / CAdES) DOĞRULAYICI v1.0
================================================================================
İncelenen Dosya: sozlesme_imzali.pdf
Dosya Yolu:      C:\Evraklar\sozlesme_imzali.pdf
İmza Durumu:     ✅ İMZALI BELGE
Toplam İmza:     1 Adet

--- İmza #1 ---
  İmzacı:       AHMET YILMAZ
  Standart:     PAdES (ETSI TS 102 778 - Türkiye e-İmza Standardı)
  Alt Filtre:   ETSI.CAdES.detached
  İmza Tarihi:  2026-09-18 14:32:10
  İmza Amacı:   Belgeyi Onaylıyorum
  Bayt Aralığı: [0, 84210, 102400, 15320]
```

### 2. JSON Formatında Çıktı Alma
Otomasyon sistemleri ve API pipeline'ları için:
```bash
python verify_pdf_signature.py sozlesme_imzali.pdf --json
```

```json
{
  "file_name": "sozlesme_imzali.pdf",
  "is_signed": true,
  "signature_count": 1,
  "signatures": [
    {
      "index": 1,
      "signer_name": "AHMET YILMAZ",
      "format": "PAdES (ETSI TS 102 778 - Türkiye e-İmza Standardı)",
      "subfilter": "ETSI.CAdES.detached",
      "signing_time": "2026-09-18 14:32:10",
      "status": "IMZALI"
    }
  ]
}
```

---

## 🐍 Python Projelerinde Kütüphane Olarak Kullanım

Kendi Python projenizde doğrudan fonksiyon olarak çağırabilirsiniz:

```python
from verify_pdf_signature import extract_signatures_native

signatures = extract_signatures_native("ihale_teklifi.pdf")

if signatures:
    print(f"Belge imzalı! İmzacı: {signatures[0]['signer_name']}")
else:
    print("Belgede dijital imza bulunamadı!")
```

---

## 📚 İlgili Teknik Rehberler

* 📄 [E-İmza Cihazları (USB Token) Nasıl Çalışır? Çipin İçindeki Teknik Dünya](https://eimza-kep.github.io/eimza-blog/posts/e-imza-cihazlari-nasil-calisir-teknik-rehber.html)
* 📄 [EKAP İhalesine e-İmza ile Teklif Nasıl Verilir? Hatalar ve Çözümleri](https://eimza-kep.github.io/eimza-blog/posts/ekap-e-imza-ile-ihale-teklif-verme.html)
* 📄 [Web Tapu Üzerinden E-İmza ile Satış ve İpotek Başvurusu Rehberi](https://eimza-kep.github.io/eimza-blog/posts/web-tapu-e-imza-ile-basvuru-rehberi.html)
* 📄 [Dijital Kimliğin Evrimi: Kil Tabletlerden E-İmza ve YubiKey'lere](https://eimza-kep.github.io/eimza-blog/posts/e-imza-ve-dijital-guvenlik-tarihi-yubikey-2fa.html)

---

## ⚖️ Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Ticari ve kişisel projelerde serbestçe kullanılabilir.
