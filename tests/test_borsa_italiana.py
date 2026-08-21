"""Tests de l'extracteur Borsa Italiana.

Ce module est le seul du projet a lire une page HTML plutot qu'une API. Le
risque n'y est pas la panne — une page qui disparait leve une erreur toute
seule — mais la lecture qui glisse d'un champ et renvoie un autre nombre,
plausible et faux. Ces tests portent donc surtout sur ce cas.
"""
import datetime as dt

import pytest

from veille_financiere.models import SourceError
from veille_financiere.sources.borsa_italiana import BorsaItalianaSource

SPEC = {"series_id": "equity.ftsemib", "native_id": "FTSEMIB",
        "expect_title": "FTSE MIB", "unit": "points", "frequency": "daily"}


def page(cours="52.665,82", variation="+0,09", veille="52.618,20",
         titre="FTSE MIB", horodatage="20/08/26"):
    """Reproduit la structure reelle de la page, y compris les nombres
    voisins qui pourraient etre pris pour le cours."""
    return f"""
    <html><body>
    <h1 class="t-text"><a href="/dettaglio.html">{titre}</a></h1>
    <div class="summary-value">
      <span class="t-text -black-warm-60 -formatPrice"><strong> {cours} </strong></span>
      <span class="t-text -size-lg -cbalanced -percPrice"><strong> {variation}% </strong></span>
    </div>
    <span class="t-text -block -size-xs">Data - Ora Ultimo Valore:
      <strong> {horodatage} - 17.40.00 </strong></span>
    <table><tbody>
      <tr><td>Max Oggi</td><td>52.887,11</td></tr>
      <tr><td>Min Oggi</td><td>52.546,75</td></tr>
      <tr><td>Chiusura precedente</td><td>{veille}</td></tr>
      <tr><td>Max Anno Prima</td><td>44.944,54</td></tr>
      <tr><td>Min Anno Prima</td><td>32.730,57</td></tr>
      <tr><td>Primo Valore</td><td>52.669,67</td></tr>
    </tbody></table>
    </body></html>
    """ + "x" * 5000        # la page reelle depasse largement le seuil de taille


class PageFetcher:
    def __init__(self, contenu):
        self.contenu = contenu

    def fetch(self, url, params=None, headers=None, **kwargs):
        return self.contenu


def collecte(contenu, spec=None):
    return BorsaItalianaSource(PageFetcher(contenu))._fetch_series(spec or SPEC)


# --------------------------------------------------------------- cas nominal
def test_lit_le_cours_et_sa_date():
    obs = collecte(page())
    assert len(obs) == 1
    assert obs[0].value == pytest.approx(52665.82)
    assert obs[0].date == dt.date(2026, 8, 20)


def test_conserve_le_detail_du_calcul():
    """La cloture precedente et la variation restent consultables : c'est ce
    qui permet de refaire le controle a posteriori."""
    meta = collecte(page())[0].meta
    assert meta["cloture_precedente"] == pytest.approx(52618.20)
    assert meta["variation_pct"] == pytest.approx(0.09)


def test_convertit_la_notation_italienne():
    obs = collecte(page(cours="9.001,50", veille="9.000,00", variation="+0,02"))
    assert obs[0].value == pytest.approx(9001.50)


# ------------------------------------------------- le controle d'arithmetique
def test_refuse_un_cours_qui_ne_colle_pas_a_la_variation_affichee():
    """Le cas qui justifie tout le dispositif : l'extraction glisse et
    ramene le plus haut de l'annee precedente au lieu du cours du jour. Le
    nombre est plausible, la page ne proteste pas — seule l'arithmetique le
    trahit."""
    with pytest.raises(SourceError, match="incoherente"):
        collecte(page(cours="44.944,54"))


def test_refuse_une_cloture_precedente_glissee():
    with pytest.raises(SourceError, match="incoherente"):
        collecte(page(veille="44.944,54"))


def test_accepte_l_arrondi_au_centieme():
    """La page arrondit sa variation : le recalcul ne tombe jamais juste au
    chiffre pres, et refuser pour autant rendrait la source inutilisable."""
    obs = collecte(page(cours="52.665,82", veille="52.618,20", variation="+0,09"))
    assert obs[0].value == pytest.approx(52665.82)


def test_refuse_une_cloture_precedente_nulle():
    with pytest.raises(SourceError):
        collecte(page(veille="0,00"))


# ------------------------------------------------- structure de page modifiee
def test_refuse_une_page_qui_ne_parle_pas_du_bon_indice():
    with pytest.raises(SourceError, match="ne mentionne pas"):
        collecte(page(titre="FTSE Italia Mid Cap"))


def test_refuse_une_page_amputee_du_cours():
    ampute = page().replace("-formatPrice", "-autreClasse")
    with pytest.raises(SourceError, match="cours introuvable"):
        collecte(ampute)


def test_refuse_une_page_sans_cloture_precedente():
    ampute = page().replace("Chiusura precedente", "Autre libelle")
    with pytest.raises(SourceError, match="cloture precedente introuvable"):
        collecte(ampute)


def test_refuse_une_page_sans_horodatage():
    ampute = page().replace("Ultimo Valore:", "Autre chose:")
    with pytest.raises(SourceError, match="horodatage introuvable"):
        collecte(ampute)


def test_refuse_une_reponse_tronquee():
    """Une page d'erreur ou une redirection est bien plus courte."""
    with pytest.raises(SourceError, match="trop courte"):
        collecte("<html><body>Servizio non disponibile</body></html>")


def test_refuse_une_reponse_qui_n_est_pas_du_texte():
    with pytest.raises(SourceError, match="trop courte"):
        collecte({"erreur": "json inattendu"})
