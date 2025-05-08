
from piwigo_wrapper.banners import generate_multilang_banner

def test_generate_multilang_banner():
    html = generate_multilang_banner("Toto", "analyse-toto")
    assert "Analyse des œuvres de Toto" in html
    assert "Analysis of Toto's Work" in html
    assert "<style>" in html
    assert "📘" in html
