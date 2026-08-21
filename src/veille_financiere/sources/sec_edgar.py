"""SEC EDGAR - fondamentaux XBRL des societes cotees aux Etats-Unis.

La SEC impose un User-Agent nominatif; sans contact declare on s'abstient
plutot que de risquer un blocage cote SEC.
"""
from __future__ import annotations

from typing import Any

from ..models import Observation, SourceError
from .base import Source, parse_period

BASE = "https://data.sec.gov/api/xbrl/companyconcept"


class SecEdgarSource(Source):
    name = "sec_edgar"

    def __init__(self, fetcher, contact: str = "") -> None:
        super().__init__(fetcher)
        self.contact = contact.strip()

    def _headers(self) -> dict[str, str]:
        who = self.contact or "veille-financiere contact-non-declare"
        return {"User-Agent": f"veille-financiere {who}",
                "Accept-Encoding": "gzip, deflate"}

    def _fetch_series(self, spec: dict[str, Any]) -> list[Observation]:
        """Collecte un concept, en essayant ses synonymes s'il en a.

        La taxonomie US-GAAP evolue et les societes ne migrent pas au meme
        rythme : le chiffre d'affaires se lit sous
        ``RevenueFromContractWithCustomerExcludingAssessedTax`` chez Apple,
        Microsoft, Amazon et Tesla, mais sous ``Revenues`` chez NVIDIA,
        Alphabet et JPMorgan, ou le premier concept est vide ou perime. On
        retient donc le premier synonyme qui renvoie effectivement des
        donnees, plutot que d'imposer un nom unique a tout le monde.
        """
        noms = spec["native_id"]
        if isinstance(noms, str):
            noms = [noms]

        erreurs: list[str] = []
        candidats: list[tuple[Any, str, list[Observation]]] = []
        for nom in noms:
            try:
                obs = self._concept(spec, nom)
            except Exception as exc:  # noqa: BLE001 - on passe au synonyme
                erreurs.append(f"{nom}: {str(exc)[:80]}")
                continue
            if obs:
                candidats.append((max(o.date for o in obs), nom, obs))
            else:
                erreurs.append(f"{nom}: aucune observation")

        if not candidats:
            raise SourceError(" | ".join(erreurs)[:250])

        # On retient le synonyme le plus a jour, et non le premier qui repond.
        # Une balise abandonnee continue de servir son historique : chez
        # JPMorgan, le concept moderne de chiffre d'affaires s'arrete en 2014
        # alors que l'ancien est tenu a jour. Prendre le premier venu aurait
        # fige la serie douze ans en arriere sans que rien ne le signale.
        candidats.sort(key=lambda c: c[0], reverse=True)
        base = candidats[0][2]
        for _, _, autre in candidats[1:]:
            base = self._completer(base, autre)
        base.sort(key=lambda o: o.date, reverse=True)
        return base

    @staticmethod
    def _completer(base: list[Observation],
                   appoint: list[Observation]) -> list[Observation]:
        """Comble les trous d'une serie avec une balise voisine, si elles
        disent la meme chose la ou elles se recoupent.

        Une societe peut alterner entre deux balises au fil des annees : chez
        Alphabet, ``Revenues`` couvre les trimestres recents mais saute trois
        ans que l'autre balise renseigne. Les recoller donne un historique
        continu — a condition de verifier d'abord qu'il s'agit bien de la
        meme grandeur, sinon on fabriquerait une rupture invisible au point
        de raccord.

        La verification porte sur les dates communes : sans recoupement, on
        ne peut rien affirmer et l'on s'abstient.
        """
        par_date = {o.date: o for o in base}
        communes = [d for d in (o.date for o in appoint) if d in par_date]
        if not communes:
            return base

        valeurs_appoint = {o.date: o.value for o in appoint}
        for jour in communes:
            a, b = par_date[jour].value, valeurs_appoint[jour]
            denominateur = max(abs(a), abs(b), 1.0)
            if abs(a - b) / denominateur > 0.01:
                return base   # grandeurs differentes : pas de raccord

        base = list(base)
        for obs in appoint:
            if obs.date not in par_date:
                base.append(obs)
        return base

    def _concept(self, spec: dict[str, Any], nom: str) -> list[Observation]:
        cik = str(spec["cik"]).zfill(10)
        taxonomy = spec.get("taxonomy", "us-gaap")
        payload = self.fetcher.fetch(
            f"{BASE}/CIK{cik}/{taxonomy}/{nom}.json",
            headers=self._headers(),
        )
        unit_key = spec.get("xbrl_unit", "USD")
        rows = (payload.get("units") or {}).get(unit_key)
        if not rows:
            available = list((payload.get("units") or {}).keys())
            raise SourceError(
                f"{nom}: unite {unit_key} absente (dispo: {available[:4]})")

        # Deux natures de concepts cohabitent dans XBRL:
        #  - les concepts de stock (Assets, StockholdersEquity) sont dates a
        #    un instant et n'ont pas de champ "start";
        #  - les concepts de flux (NetIncomeLoss, Revenues) couvrent une
        #    duree, et la meme balise apparait aussi bien dans un 10-Q
        #    (3 mois) que dans un 10-K (12 mois).
        # Melanger les deux dans une seule serie produirait des variations
        # absurdes: on filtre donc les flux sur la duree demandee.
        want_days = spec.get("duration_days")
        best: dict[str, dict] = {}
        for row in rows:
            end = row.get("end")
            if end is None or row.get("val") is None:
                continue
            start = row.get("start")
            if start is not None:
                span = (parse_period(end) - parse_period(start)).days
                if want_days is not None and abs(span - want_days) > 20:
                    continue
            # A periode egale, on retient la publication la plus recente
            # (les chiffres sont revises d'un depot a l'autre).
            key = f"{row.get('start', '')}:{end}"
            prev = best.get(key)
            if prev is None or (row.get("filed", "") > prev.get("filed", "")):
                best[key] = row

        out: list[Observation] = []
        for row in best.values():
            out.append(
                self._obs(
                    spec, parse_period(row["end"]), float(row["val"]),
                    form=row.get("form", ""), fy=row.get("fy"),
                    fp=row.get("fp", ""), filed=row.get("filed", ""),
                )
            )

        if want_days is not None:
            out += self._quatriemes_trimestres(spec, rows, want_days,
                                               {o.date for o in out})

        out.sort(key=lambda o: o.date, reverse=True)
        return out[: spec.get("limit", 24)]

    def _quatriemes_trimestres(self, spec: dict[str, Any], rows: list[dict],
                               want_days: int,
                               deja_vues: set) -> list[Observation]:
        """Reconstitue le dernier trimestre d'un exercice, absent de XBRL.

        Les societes ne deposent pas de 10-Q pour leur quatrieme trimestre :
        celui-ci n'apparait que fondu dans le cumul annuel du 10-K. La serie
        saute donc un point par exercice, et la variation d'un trimestre au
        suivant enjambe un trou — chez NVIDIA, cela faisait passer le
        resultat net de 31,9 a 58,3 milliards d'un coup, alors que le
        trimestre manquant valait 43,0.

        On le retrouve par difference : exercice complet moins cumul des
        trois premiers trimestres, a condition que les deux couvrent la meme
        date de depart et que le cumul s'arrete bien un trimestre plus tot.
        """
        annuels: dict[tuple[str, str], float] = {}
        cumuls: dict[tuple[str, str], float] = {}
        for row in rows:
            start, end, val = row.get("start"), row.get("end"), row.get("val")
            if not start or not end or val is None:
                continue
            span = (parse_period(end) - parse_period(start)).days
            if abs(span - want_days * 4) <= 30:
                annuels[(start, end)] = float(val)
            elif abs(span - want_days * 3) <= 25:
                cumuls[(start, end)] = float(val)

        deduits: list[Observation] = []
        for (debut, fin_exercice), total in annuels.items():
            # Le cumul de reference part du meme jour que l'exercice.
            candidats = [(f, v) for (d, f), v in cumuls.items() if d == debut]
            if not candidats:
                continue
            fin_cumul, partiel = max(candidats)
            ecart = (parse_period(fin_exercice) - parse_period(fin_cumul)).days
            if not (want_days - 25 <= ecart <= want_days + 25):
                continue
            date_obs = parse_period(fin_exercice)
            if date_obs in deja_vues:
                continue
            deduits.append(self._obs(spec, date_obs, total - partiel,
                                     derive=True, base_annuelle=total,
                                     base_cumul=partiel))
            deja_vues.add(date_obs)
        return deduits
