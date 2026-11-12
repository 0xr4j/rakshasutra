/* Rakshasutra browser kernel: the same formulas as the Python reference, in plain JavaScript.
 * tests/test_demo_parity.py runs this file under Node and compares it with Python. */
(function (root) {
  "use strict";
  const SBOX = (function () {                      // AES S-box, generated rather than typed
    const s = new Uint8Array(256); let p = 1, q = 1;
    do {
      p = p ^ ((p << 1) & 0xff) ^ (p & 0x80 ? 0x1b : 0);
      q ^= q << 1; q ^= q << 2; q ^= q << 4; q &= 0xff; if (q & 0x80) q ^= 0x09;
      const x = q ^ ((q << 1) | (q >> 7)) ^ ((q << 2) | (q >> 6)) ^ ((q << 3) | (q >> 5)) ^ ((q << 4) | (q >> 4));
      s[p] = (x ^ 0x63) & 0xff;
    } while (p !== 1);
    s[0] = 0x63; return s;
  })();
  const RCON = [1, 2, 4, 8, 16, 32, 64, 128, 0x1b, 0x36];
  const xt = (a) => ((a << 1) ^ (a & 0x80 ? 0x1b : 0)) & 0xff;

  function aesEncrypt(key, block) {
    const rk = new Uint8Array(176); rk.set(key);
    for (let i = 16; i < 176; i += 4) {
      let w = [rk[i - 4], rk[i - 3], rk[i - 2], rk[i - 1]];
      if (i % 16 === 0) w = [SBOX[w[1]] ^ RCON[i / 16 - 1], SBOX[w[2]], SBOX[w[3]], SBOX[w[0]]];
      for (let c = 0; c < 4; c++) rk[i + c] = rk[i - 16 + c] ^ w[c];
    }
    let s = Uint8Array.from(block, (b, i) => b ^ rk[i]);
    for (let r = 1; r <= 10; r++) {
      const t = new Uint8Array(16);
      for (let c = 0; c < 4; c++) for (let i = 0; i < 4; i++) t[4 * c + i] = SBOX[s[(4 * (c + i) + i) % 16]];
      if (r !== 10) {
        for (let c = 0; c < 4; c++) {
          const [a0, a1, a2, a3] = [t[4 * c], t[4 * c + 1], t[4 * c + 2], t[4 * c + 3]];
          s[4 * c] = xt(a0) ^ xt(a1) ^ a1 ^ a2 ^ a3; s[4 * c + 1] = a0 ^ xt(a1) ^ xt(a2) ^ a2 ^ a3;
          s[4 * c + 2] = a0 ^ a1 ^ xt(a2) ^ xt(a3) ^ a3; s[4 * c + 3] = xt(a0) ^ a0 ^ a1 ^ a2 ^ xt(a3);
        }
      } else s = t;
      for (let i = 0; i < 16; i++) s[i] ^= rk[16 * r + i];
    }
    return s;
  }
  function dbl(b) {
    const o = new Uint8Array(16);
    for (let i = 0; i < 16; i++) o[i] = ((b[i] << 1) | (i < 15 ? b[i + 1] >> 7 : 0)) & 0xff;
    if (b[0] & 0x80) o[15] ^= 0x87;
    return o;
  }
  function aesCmac(key, msg) {
    const k1 = dbl(aesEncrypt(key, new Uint8Array(16))), k2 = dbl(k1);
    const n = Math.max(1, Math.ceil(msg.length / 16)), complete = msg.length > 0 && msg.length % 16 === 0;
    const last = new Uint8Array(16), rem = msg.length - (n - 1) * 16;
    last.set(msg.slice((n - 1) * 16));
    if (!complete) last[rem] = 0x80;
    let x = new Uint8Array(16);
    for (let i = 0; i < n - 1; i++) x = aesEncrypt(key, x.map((b, j) => b ^ msg[16 * i + j]));
    return aesEncrypt(key, x.map((b, j) => b ^ last[j] ^ (complete ? k1[j] : k2[j])));
  }
  const hex = (b) => Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  const unhex = (s) => Uint8Array.from((s.match(/../g) || []).map((x) => parseInt(x, 16)));

  function rollingId(key, c) { return aesCmac(key, [1, c & 0xff, (c >> 8) & 0xff]).slice(0, 4); }
  function macAddress(key, c) { const m = aesCmac(key, [2, c & 0xff, (c >> 8) & 0xff]).slice(0, 6); m[0] |= 0xc0; return m; }
  function buildFrame(key, c, flags, batteryCode, role) {
    const f = new Uint8Array(15);
    f[0] = 0x5a; f[1] = 0xff; f[2] = 4 | ((role & 1) << 4); f[3] = c & 0xff; f[4] = (c >> 8) & 0xff;
    f.set(rollingId(key, c), 5); f[9] = flags & 0xff; f[10] = batteryCode & 0xff;
    f.set(aesCmac(key, f.slice(2, 11)).slice(0, 4), 11);
    return f;
  }

  function timeOnAir(appBytes, sf) {                // seconds; SF7..SF10, 125 kHz, coding rate 4/5
    sf = sf || 7;
    const n = Math.max(Math.ceil((8 * (appBytes + 13) - 4 * sf + 44) / (4 * sf)) * 5, 0);
    return (Math.pow(2, sf) / 125000) * (8 + 4.25 + 8 + n);
  }
  function poisson(mean) {
    const pmf = []; let p = Math.exp(-mean), total = 0, k = 0;
    while (total < 1 - 1e-12 || k <= mean) {
      pmf.push(p); total += p; k += 1; p *= mean / k;
      if (k > mean + 60 * Math.sqrt(mean + 1) + 60) break;
    }
    return pmf;
  }
  function split(count, per, unit) {
    const out = []; for (let i = 0; i < Math.floor(count / per); i++) out.push(per * unit);
    if (count % per) out.push((count % per) * unit); return out;
  }
  function periodic(name, poles, period, mean, sizes) {
    let frames = 0, air = 0;
    poisson(mean).forEach((p, k) => sizes(k).forEach((b) => { frames += p; air += p * timeOnAir(b); }));
    return { name, frames: (poles / period) * frames, air: (poles / period) * air };
  }
  /* Load and loss of one gateway cell; mirrors rakshasutra.capacity.cell_load. */
  function cellLoad(arch, tags, poles, departures, passS, channels) {
    poles = poles || 60; passS = passS || 55; channels = channels || 8;
    const present = tags / poles, arrivals = (tags * 15) / (passS * poles), streams = [];
    const rawBeat = () => periodic("heartbeat", poles, 60, present, (k) => split(k, 55, 4));
    if (arch === "raw") streams.push({ name: "arrivals", frames: tags / 2, air: (tags / 2) * timeOnAir(7) });
    else if (arch === "single") {
      streams.push({ name: "arrivals", frames: tags / passS, air: (tags / passS) * timeOnAir(8) }); streams.push(rawBeat());
    } else if (arch === "batch") {
      streams.push(periodic("arrivals", poles, 15, arrivals, (k) => split(k, 27, 8))); streams.push(rawBeat());
    } else {
      streams.push(periodic("arrivals", poles, 15, arrivals, (k) => split(k, 25, 8)));
      if (departures !== false) streams.push(periodic("departures", poles, 15, arrivals, (k) => split(k, 50, 4)));
      const rate = (poles * (1 - Math.exp(-present))) / 60;
      streams.push({ name: "heartbeat", frames: rate, air: rate * timeOnAir(64) });
    }
    const load = streams.reduce((a, s) => a + s.air, 0) / channels;
    return { load, loss: 1 - Math.exp(-2 * load), streams };
  }
  function bloomFpr(tags) { return Math.pow(1 - Math.exp((-3 * tags) / 512), 3); }

  function advEventMs(phy) {
    if (phy === "1m") return (3 * (1 + 4 + 2 + 6 + 17 + 3) * 8) / 1000;
    const pkt = (n) => (376 + (n * 8 + 27) * 8) / 1000;
    return 3 * pkt(9) + pkt(29);
  }
  function batteryMonths(phy, cold, activeHours, advIntervalS) {
    activeHours = activeHours === undefined ? 14 : activeHours; advIntervalS = advIntervalS || 0.8;
    const tx = phy === "table" ? 1.25 : advEventMs(phy);
    const ua = 1.8 + (14.2 * 1000 * tx) / (advIntervalS * 1000) + (4.6 * 1000 * 5) / 4000 + (3.8 * 1000 * 0.45) / 900000;
    const daily = activeHours * ua + (24 - activeHours) * 0.6;
    return { ua, months: ((620 * (cold ? 0.7 : 1) * 1000) / daily) / (365.25 / 12) };
  }
  function invNorm98() { return 2.0537489106318225; }
  function bleRange(sensDbm, txDbm, roofDb, bodyDb) {
    const budget = txDbm - 40.2 - bodyDb - roofDb - sensDbm - invNorm98() * 4.2;
    return Math.pow(10, budget / 21.5);
  }
  function pulseVmin(capUf, pulseMa, onMs, offMs) {
    const r = 42, v0 = 2.95, full = (pulseMa / 1000) * r, c = capUf * 1e-6;
    if (c <= 0) return v0 - full;
    const a = Math.exp(-(onMs / 1000) / (r * c)), b = Math.exp(-(offMs / 1000) / (r * c));
    return v0 - (full * (1 - a)) / (1 - a * b);
  }
  const api = { aesCmac, buildFrame, rollingId, macAddress, timeOnAir, cellLoad, bloomFpr, advEventMs, batteryMonths,
    bleRange, pulseVmin, hex, unhex };
  if (typeof module !== "undefined" && module.exports) module.exports = api; else root.RS = api;
})(typeof window !== "undefined" ? window : globalThis);
