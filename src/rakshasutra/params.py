"""Every number the models use, with where it comes from.

Status codes:
  PAPER      stated in White Paper WP-01 as a design value; not yet measured
  STANDARD   fixed by a published standard or specification
  DATASHEET  taken from a component datasheet; to be re-checked against the exact part
  DEFINED    an encoding or layout this repository had to fix because the paper leaves it open
  ASSUMED    no source; chosen so a calculation can run, and flagged wherever it is used

`data/params.csv` is written from this table by `experiments/write_params.py`; a test
keeps the two in step.
"""
from __future__ import annotations

# (key, value, unit, status, source or note)
TABLE = [
    # --- trek and deployment
    ("trek_km", 22.5, "km", "PAPER", "WP-01 Sec. III-A, total of the six zones"),
    ("poles_total", 255, "poles", "PAPER", "WP-01 Sec. III-A"),
    ("poles_fiber", 60, "poles", "PAPER", "WP-01 Sec. V-D; zones 3 and 5 on the fibre LAN"),
    ("gateways", 6, "gateways", "PAPER", "WP-01 Sec. III-B"),
    ("altitude_min_m", 762.0, "m", "PAPER", "WP-01 Sec. III-A (2,500 ft)"),
    ("altitude_max_m", 2017.0, "m", "PAPER", "WP-01 Sec. III-A (6,619 ft)"),
    ("zone4_himkoti_km", 3.5, "km", "ASSUMED", "split of the 6.5 km of zone 4 between its two parallel branches"),
    ("zone4_sanjichhat_km", 3.0, "km", "ASSUMED", "split of the 6.5 km of zone 4 between its two parallel branches"),
    # --- BLE link
    ("ble_tx_dbm", 8.0, "dBm", "PAPER", "WP-01 Eq. 2; note the nRF52811 named in the paper is specified to +4 dBm"),
    ("ble_tx_dbm_1m_above", 4.0, "dBm", "PAPER", "WP-01 Table III, first row"),
    ("ble_pl0_db", 40.2, "dB", "PAPER", "WP-01 Eq. 2, path loss at 1 m"),
    ("ble_exponent", 2.15, "", "PAPER", "WP-01 Eq. 2, under the steel roof; not measured"),
    ("ble_sigma_db", 4.2, "dB", "PAPER", "WP-01 Eq. 2, log-normal shadowing"),
    ("ble_body_db", 14.0, "dB", "PAPER", "WP-01 Table III, heavy crowd"),
    ("ble_antenna_gain_db", 0.0, "dB", "ASSUMED", "sum of wearable and pole antenna gains; the paper gives none"),
    ("ble_sens_1m_dbm", -96.0, "dBm", "PAPER", "WP-01 Table III"),
    ("ble_sens_coded_dbm", -103.0, "dBm", "PAPER", "WP-01 Eq. 2, Coded PHY S=8 on ESP32-S3"),
    ("gi_loss_ble_db", 24.1, "dB", "PAPER", "WP-01 Sec. III-B, roof penetration at 2.44 GHz; not measured"),
    ("gi_loss_lora_db", 18.4, "dB", "PAPER", "WP-01 Sec. III-B, roof penetration at 866 MHz; not measured"),
    ("pdr_target", 0.98, "", "PAPER", "WP-01 Table III, 'reliable range' means at least 98% delivery"),
    # --- LoRa link
    ("lora_tx_dbm", 14.0, "dBm", "PAPER", "WP-01 Sec. III-B"),
    ("lora_coax_db", 0.9, "dB", "PAPER", "WP-01 Sec. III-B, 1 m of RG-316"),
    ("lora_gw_gain_dbi", 5.8, "dBi", "PAPER", "WP-01 Sec. III-B"),
    ("lora_sens_sf7_dbm", -126.5, "dBm", "PAPER", "WP-01 Sec. III-B, SX1302"),
    ("lora_sens_sf9_dbm", -131.5, "dBm", "PAPER", "WP-01 Sec. III-B, SX1302"),
    ("lora_freq_mhz", 866.0, "MHz", "STANDARD", "centre of IN865, LoRa Alliance RP002-1.0.4"),
    ("lora_body_internal_db", 3.0, "dB", "PAPER", "WP-01 Table III, internal antenna under the roof"),
    ("ridge_loss_db", 20.0, "dB", "ASSUMED", "one knife-edge ridge between pole and gateway"),
    # --- LoRaWAN capacity
    ("lora_channels", 8, "channels", "PAPER", "WP-01 Sec. V-A"),
    ("lora_mac_overhead", 13, "bytes", "STANDARD", "LoRaWAN MHDR, FHDR, FPort and MIC"),
    ("lora_max_app_bytes", 222, "bytes", "STANDARD", "IN865 DR5, repeater-compatible; RP002-1.0.4"),
    ("cell_poles", 60, "poles", "PAPER", "WP-01 Sec. VI-B"),
    ("pass_seconds", 55.0, "s", "PAPER", "WP-01 Sec. VI-B, mean time between poles"),
    ("raw_ping_seconds", 2.0, "s", "PAPER", "WP-01 Table IV, row 1"),
    ("raw_ping_bytes", 7, "bytes", "ASSUMED", "6-byte MAC and 1-byte RSSI per forwarded ping"),
    ("arrival_tuple_bytes", 8, "bytes", "PAPER", "WP-01 Algorithm 2, line 12"),
    ("departure_bytes", 4, "bytes", "PAPER", "WP-01 Algorithm 2, line 17"),
    ("chunk_tags", 25, "tags", "PAPER", "WP-01 Algorithm 2, line 16"),
    ("departure_ids_per_frame", 50, "ids", "PAPER", "WP-01 Algorithm 2, line 17"),
    ("flush_seconds", 15.0, "s", "PAPER", "WP-01 Algorithm 2"),
    ("heartbeat_seconds", 60.0, "s", "PAPER", "WP-01 Algorithm 2"),
    ("depart_timeout_s", 90.0, "s", "PAPER", "WP-01 Algorithm 2, line 15"),
    ("rssi_gate_track_dbm", -75.0, "dBm", "PAPER", "WP-01 Algorithm 2, line 8"),
    ("rssi_gate_hub_dbm", -65.0, "dBm", "PAPER", "WP-01 Algorithm 2, line 8"),
    ("sos_per_minute", 10, "frames", "PAPER", "WP-01 Algorithm 2, line 3"),
    # --- timing and kinematics
    ("adv_interval_s", 0.8, "s", "PAPER", "WP-01 Sec. IV-C"),
    ("adv_interval_sos_s", 0.2, "s", "PAPER", "WP-01 Sec. IV-C"),
    ("slot_seconds", 900, "s", "PAPER", "WP-01 Sec. IV-C"),
    ("walk_mps", 1.25, "m/s", "PAPER", "WP-01 Sec. V-C"),
    ("ev_mps", 5.56, "m/s", "PAPER", "WP-01 Sec. V-C (20 km/h)"),
    ("core_zone_m", 25.0, "m", "PAPER", "WP-01 Sec. V-C, length of track a pole reports as 'here'"),
    ("class_a_batch_s", 15.0, "s", "PAPER", "WP-01 Sec. V-C"),
    ("class_a_confirm_s", 90.0, "s", "PAPER", "WP-01 Sec. V-C"),
    ("class_a_downlink_s", 60.0, "s", "PAPER", "WP-01 Sec. V-C"),
    ("class_a_gatt_s", 8.0, "s", "PAPER", "WP-01 Sec. V-C"),
    ("tether_scan_period_s", 5.0, "s", "PAPER", "WP-01 Sec. V-C, Layer 1"),
    ("tether_scan_window_s", 0.005, "s", "PAPER", "WP-01 Sec. V-C, Layer 1"),
    ("tether_misses", 4, "scans", "PAPER", "WP-01 Sec. V-C, Layer 1"),
    ("adv_delay_max_s", 0.010, "s", "STANDARD", "Bluetooth Core 5.1, random advDelay of 0 to 10 ms"),
    ("separation_alert_m", 200.0, "m", "PAPER", "WP-01 Sec. V-C, Layer 2"),
    ("suspect_speed_mps", 8.0, "m/s", "ASSUMED", "above the 5.56 m/s of an electric vehicle; faster sightings are flagged"),
    ("suspect_min_m", 300.0, "m", "ASSUMED", "shorter hops are within radio range of two poles and are not flagged"),
    ("class_c_downlink_s", 1.0, "s", "ASSUMED", "server decision, network server and one Class C downlink"),
    ("lorawan_retry_s", 3.0, "s", "ASSUMED", "wait before a confirmed uplink is repeated (RX2 window plus back-off)"),
    ("backhaul_s", 0.3, "s", "ASSUMED", "gateway to control-room alarm"),
    # --- wearable power
    ("battery_mah", 620.0, "mAh", "PAPER", "WP-01 Table V, CR2450"),
    ("battery_cold_derate", 0.30, "", "PAPER", "WP-01 Sec. VI-C, capacity lost at -5 C"),
    ("battery_r_warm_ohm", 15.0, "ohm", "PAPER", "WP-01 Sec. VI-C"),
    ("battery_r_cold_ohm", 42.0, "ohm", "PAPER", "WP-01 Sec. VI-C"),
    ("battery_v_cold", 2.95, "V", "PAPER", "WP-01 Sec. VI-C, open-circuit voltage at -5 C"),
    ("brownout_v", 1.70, "V", "PAPER", "WP-01 Sec. VI-C, nRF52811 minimum supply"),
    ("i_sleep_ua", 1.80, "uA", "PAPER", "WP-01 Table V"),
    ("i_tx_ma", 14.20, "mA", "PAPER", "WP-01 Table V"),
    ("t_tx_ms", 1.25, "ms", "PAPER", "WP-01 Table V; matches a 1M PHY event on three channels, not Coded PHY"),
    ("i_rx_ma", 4.60, "mA", "PAPER", "WP-01 Table V"),
    ("t_scan_ms", 5.00, "ms", "PAPER", "WP-01 Table V"),
    ("scan_period_ms", 4000.0, "ms", "PAPER", "WP-01 Table V"),
    ("i_cmac_ma", 3.80, "mA", "PAPER", "WP-01 Table V"),
    ("t_cmac_ms", 0.45, "ms", "PAPER", "WP-01 Table V"),
    ("i_rack_ua", 0.60, "uA", "PAPER", "WP-01 Table V"),
    ("active_hours", 14.0, "h/day", "PAPER", "WP-01 Sec. VI-C"),
    ("i_pulse_ma", 32.0, "mA", "PAPER", "WP-01 Sec. VI-C, buzzer and LED"),
    ("holdup_uf", 100.0, "uF", "PAPER", "WP-01 Sec. VI-C"),
    ("pulse_on_ms", 100.0, "ms", "PAPER", "WP-01 Sec. VI-C"),
    ("pulse_off_ms", 400.0, "ms", "PAPER", "WP-01 Sec. VI-C"),
    # --- identity and filters
    ("company_id", 0xFF5A, "", "PAPER", "WP-01 Table II, laboratory identifier"),
    ("bloom_bits", 512, "bits", "PAPER", "WP-01 Algorithm 2"),
    ("bloom_probes", 3, "", "PAPER", "WP-01 Algorithm 2, lines 20-22"),
    ("active_table", 1024, "entries", "PAPER", "WP-01 Algorithm 2"),
    ("window_slots", 3, "slots", "PAPER", "WP-01 Sec. IV-D"),
    ("arbitration_s", 15.0, "s", "PAPER", "WP-01 Algorithm 1, line 12"),
    ("crystal_ppm", 20.0, "ppm", "PAPER", "WP-01 Sec. IV-D"),
    ("truncation", "leading bytes", "", "DEFINED", "Trunc keeps the first bytes of the CMAC, as in RFC 4493"),
    ("counter_encoding", "little-endian", "", "DEFINED", "the counter enters every CMAC input as it appears on air"),
    ("wake_token_layout", "id4|cmd1|tag3", "", "DEFINED", "the paper fixes 8 bytes and 24 bits of tag only"),
    ("sos_uplink_layout", "frame15|rssi1", "", "DEFINED", "one RSSI byte is appended so the server can pick the nearest pole"),
    ("bloom_hashes", "CRC-16/CCITT-FALSE, FNV-1a 32", "", "DEFINED", "the paper names CRC16 and FNV1a without variants"),
]

P = {key: value for key, value, _unit, _status, _source in TABLE}
STATUS = {key: status for key, _value, _unit, status, _source in TABLE}
