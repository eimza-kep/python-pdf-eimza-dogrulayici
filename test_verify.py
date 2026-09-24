# -*- coding: utf-8 -*-
"""Unit tests for Python PDF E-Signature Validator"""
import os
import unittest
from verify_pdf_signature import parse_pdf_date, inspect_pdf

class TestPDFSignatureVerifier(unittest.TestCase):
    def test_parse_pdf_date(self):
        pdf_date = "D:20260924153000+03'00'"
        formatted = parse_pdf_date(pdf_date)
        self.assertEqual(formatted, "2026-09-24 15:30:00")

    def test_unsigned_pdf(self):
        test_file = os.path.join(os.path.dirname(__file__), "temp_unsigned.pdf")
        try:
            # Create a simple valid unsigned PDF
            with open(test_file, "wb") as f:
                f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000056 00000 n \n0000000111 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n164\n%%EOF")
            
            res = inspect_pdf(test_file)
            self.assertFalse(res["is_signed"])
            self.assertEqual(res["signature_count"], 0)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_simulated_signed_pdf(self):
        test_file = os.path.join(os.path.dirname(__file__), "temp_signed.pdf")
        try:
            # Create a PDF with /Type /Sig structure
            dummy_sig_pdf = (
                b"%PDF-1.7\n"
                b"4 0 obj\n"
                b"<< /Type /Sig /Filter /Adobe.PPKLite /SubFilter /ETSI.CAdES.detached "
                b"/Name (Av. Hakan Yilmaz) /M (D:20260924140000) "
                b"/ByteRange [0 100 200 50] /Contents <00112233> >>\n"
                b"endobj\n"
                b"%%EOF"
            )
            with open(test_file, "wb") as f:
                f.write(dummy_sig_pdf)

            res = inspect_pdf(test_file)
            self.assertTrue(res["is_signed"])
            self.assertEqual(res["signature_count"], 1)
            sig = res["signatures"][0]
            self.assertEqual(sig["signer_name"], "Av. Hakan Yilmaz")
            self.assertEqual(sig["subfilter"], "ETSI.CAdES.detached")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

if __name__ == "__main__":
    unittest.main()
