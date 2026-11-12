"""Radio link budgets under the steel rain shelters (white paper, Section III-B and Table III).

Everything here is the paper's propagation model evaluated as written. None of the
inputs has been measured on the trek yet; see `params.py` for the status of each.
"""
from __future__ import annotations

import math
from statistics import NormalDist

from .params import P

_N = NormalDist()


def ble_rx_dbm(distance_m: float, tx_dbm: float | None = None, roof_loss_db: float = 0.0,
               body_db: float | None = None) -> float:
    """Eq. 2 without the random shadowing term: median received power at the pole."""
    tx = P["ble_tx_dbm"] if tx_dbm is None else tx_dbm
    body = P["ble_body_db"] if body_db is None else body_db
    return (tx + P["ble_antenna_gain_db"] - P["ble_pl0_db"]
            - 10 * P["ble_exponent"] * math.log10(max(distance_m, 1e-3)) - body - roof_loss_db)


def ble_margin_db(distance_m: float, sensitivity_dbm: float | None = None, **kw) -> float:
    sens = P["ble_sens_coded_dbm"] if sensitivity_dbm is None else sensitivity_dbm
    return ble_rx_dbm(distance_m, **kw) - sens


def delivery_probability(margin_db: float, sigma_db: float | None = None) -> float:
    """Chance one frame clears the receiver sensitivity under log-normal shadowing."""
    sigma = P["ble_sigma_db"] if sigma_db is None else sigma_db
    return _N.cdf(margin_db / sigma)


def ble_reliable_range_m(sensitivity_dbm: float | None = None, tx_dbm: float | None = None,
                         roof_loss_db: float = 0.0, body_db: float | None = None,
                         pdr: float | None = None) -> float:
    """Largest distance at which a single frame is delivered with probability `pdr`."""
    sens = P["ble_sens_coded_dbm"] if sensitivity_dbm is None else sensitivity_dbm
    tx = P["ble_tx_dbm"] if tx_dbm is None else tx_dbm
    body = P["ble_body_db"] if body_db is None else body_db
    fade = _N.inv_cdf(P["pdr_target"] if pdr is None else pdr) * P["ble_sigma_db"]
    budget = tx + P["ble_antenna_gain_db"] - P["ble_pl0_db"] - body - roof_loss_db - sens - fade
    return 10 ** (budget / (10 * P["ble_exponent"]))


def lora_mapl_db(sensitivity_dbm: float | None = None, roof_loss_db: float = 0.0,
                 coax_db: float | None = None, extra_db: float = 0.0) -> float:
    """Maximum allowable path loss from pole to gateway (the paper's 145.4 dB)."""
    sens = P["lora_sens_sf7_dbm"] if sensitivity_dbm is None else sensitivity_dbm
    coax = P["lora_coax_db"] if coax_db is None else coax_db
    return P["lora_tx_dbm"] - coax + P["lora_gw_gain_dbi"] - sens - roof_loss_db - extra_db


def free_space_db(distance_km: float, freq_mhz: float | None = None) -> float:
    f = P["lora_freq_mhz"] if freq_mhz is None else freq_mhz
    return 32.45 + 20 * math.log10(f) + 20 * math.log10(distance_km)


def lora_margin_db(distance_km: float, ridges: int = 1, **kw) -> float:
    """Margin left after free-space loss and `ridges` knife-edge ridges (each an ASSUMED 20 dB)."""
    return lora_mapl_db(**kw) - free_space_db(distance_km) - ridges * P["ridge_loss_db"]


def table() -> list[dict]:
    """The five scenarios of the white paper's Table III, recomputed from Eq. 2."""
    s1m, sc = P["ble_sens_1m_dbm"], P["ble_sens_coded_dbm"]
    rows = [
        dict(link="Wearable to pole, pole above the roof", phy="BLE 1M", tx_dbm=P["ble_tx_dbm_1m_above"],
             roof_db=P["gi_loss_ble_db"], sens_dbm=s1m,
             range_m=ble_reliable_range_m(s1m, P["ble_tx_dbm_1m_above"], P["gi_loss_ble_db"])),
        dict(link="Wearable to pole, pole under the roof", phy="BLE 1M", tx_dbm=P["ble_tx_dbm"],
             roof_db=0.0, sens_dbm=s1m, range_m=ble_reliable_range_m(s1m)),
        dict(link="Wearable to pole, pole under the roof", phy="BLE Coded S=8", tx_dbm=P["ble_tx_dbm"],
             roof_db=0.0, sens_dbm=sc, range_m=ble_reliable_range_m(sc)),
    ]
    for label, roof, coax, body in (("Pole to gateway, antenna under the roof", P["gi_loss_lora_db"], 0.0,
                                     P["lora_body_internal_db"]),
                                    ("Pole to gateway, whip above the roof", 0.0, P["lora_coax_db"], 0.0)):
        kw = dict(roof_loss_db=roof, coax_db=coax, extra_db=body)
        rows.append(dict(link=label, phy="LoRa SF7", tx_dbm=P["lora_tx_dbm"], roof_db=roof,
                         sens_dbm=P["lora_sens_sf7_dbm"], mapl_db=lora_mapl_db(**kw),
                         margin_4km_db=lora_margin_db(4.0, **kw), margin_8km_db=lora_margin_db(8.0, **kw)))
    return rows
