/* Rakshasutra smart pole: BLE scanner + edge filter + LoRaWAN uplink.
 *
 * STATUS: reference sketch. It has NOT been compiled in CI and has NOT run on hardware.
 * The logic it calls (rs_core.c) is tested on a host computer against the Python
 * reference; the radio glue below is written from the library documentation and will
 * need bring-up on a real board.
 *
 * Target      ESP32-S3 with an SX1262 (SPI) and a 3 dBi whip routed above the shelter roof
 * Libraries   NimBLE-Arduino 2.x (built with extended advertising enabled, for Coded PHY)
 *             RadioLib 7.x (LoRaWAN, IN865)
 * Pins        set SX_* below to match the board
 *
 * A pole holds no tag keys. It cannot read, forge or verify a wearable's identity; it only
 * filters and forwards. Its own LoRaWAN keys must come from secure storage, never from
 * source code.
 */
#include <NimBLEDevice.h>
#include <RadioLib.h>

#include "rs_core.h"

// ---- board wiring (example values; change for the board in use)
#define SX_NSS 10
#define SX_DIO1 2
#define SX_RST 9
#define SX_BUSY 14

// ---- deployment settings, written per pole at installation
static const int POLE_HITS_REQUIRED = 1;        // 1 on transit tracks, 3 in dense hubs
static const double POLE_RSSI_GATE = -75.0;     // -75 dBm on tracks, -65 dBm in hubs

SX1262 radio = new Module(SX_NSS, SX_DIO1, SX_RST, SX_BUSY);
LoRaWANNode node(&radio, &IN865);

static rs_pole pole;
static SemaphoreHandle_t poleLock;              // the scan callback and loop() both touch `pole`

// Uplinks are decided under the lock and transmitted outside it: a LoRa transmission takes
// up to a third of a second and scanning must not wait for it.
struct Pending { uint8_t fport, len, confirmed; uint8_t data[222]; };
static Pending outbox[48];
static volatile int outCount = 0;

static double nowSeconds() { return millis() / 1000.0; }

static void enqueue(uint8_t fport, const uint8_t *payload, size_t len, int confirmed, void *ctx) {
  (void)ctx;
  if (outCount >= 48 || len > sizeof(outbox[0].data)) return;
  Pending &p = outbox[outCount];
  p.fport = fport; p.len = (uint8_t)len; p.confirmed = (uint8_t)confirmed;
  memcpy(p.data, payload, len);
  outCount = outCount + 1;
}

static void transmit(const Pending &p) {
  int16_t state = node.sendReceive(p.data, p.len, p.fport, p.confirmed != 0);
  if (state < RADIOLIB_ERR_NONE && p.fport == RS_FPORT_SOS) {
    node.setDatarate(3);                         // IN865 DR3 = SF9: one repeat with more link margin
    node.sendReceive(p.data, p.len, p.fport, true);
    node.setDatarate(5);                         // back to DR5 = SF7
  }
}

static void drainOutbox() {
  static Pending batch[48];
  xSemaphoreTake(poleLock, portMAX_DELAY);
  int n = outCount;
  memcpy(batch, outbox, n * sizeof(Pending));
  outCount = 0;
  xSemaphoreGive(poleLock);
  for (int i = 0; i < n; i++) transmit(batch[i]);
}

class ScanCallbacks : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice *dev) override {
    if (!dev->haveManufacturerData()) return;
    std::string md = dev->getManufacturerData();
    if (md.size() != RS_FRAME_LEN) return;       // hardware-cheap first filter; Company_ID is checked in the core
    xSemaphoreTake(poleLock, portMAX_DELAY);
    rs_pole_on_adv(&pole, (const uint8_t *)md.data(), md.size(), dev->getRSSI(), nowSeconds(), enqueue, nullptr);
    xSemaphoreGive(poleLock);
  }
};

void setup() {
  Serial.begin(115200);
  poleLock = xSemaphoreCreateMutex();
  rs_pole_init(&pole, POLE_HITS_REQUIRED, POLE_RSSI_GATE);

  int16_t state = radio.begin();
  if (state != RADIOLIB_ERR_NONE) { Serial.printf("radio.begin failed: %d\n", state); }
  // Keys: read joinEUI, devEUI, nwkKey and appKey from encrypted NVS here and call
  // node.beginOTAA(joinEUI, devEUI, nwkKey, appKey); then node.activateOTAA().
  // They are deliberately not in this file.

  NimBLEDevice::init("");
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(new ScanCallbacks(), true);   // true: report every advertisement, not only new devices
  scan->setActiveScan(false);                          // passive: a pole never transmits to a wearable while scanning
  scan->setPhy(NimBLEScan::Phy::SCAN_CODED);
  scan->setInterval(160);
  scan->setWindow(160);                                // continuous scan
  scan->start(0, false);
}

void loop() {
  static uint32_t lastFlush = 0, lastBeat = 0;
  static uint32_t jitter = 200 + esp_random() % 1300;  // 200 to 1500 ms, so poles do not transmit together
  uint32_t ms = millis();

  if (ms - lastFlush >= 15000 + jitter) {
    lastFlush = ms;
    jitter = 200 + esp_random() % 1300;
    xSemaphoreTake(poleLock, portMAX_DELAY);
    rs_pole_flush(&pole, nowSeconds(), enqueue, nullptr);
    xSemaphoreGive(poleLock);
  }
  if (ms - lastBeat >= 60000) {
    lastBeat = ms;
    xSemaphoreTake(poleLock, portMAX_DELAY);
    rs_pole_heartbeat(&pole, enqueue, nullptr);
    xSemaphoreGive(poleLock);
  }
  drainOutbox();                                       // an SOS queued by the scan callback leaves here within 10 ms
  delay(10);
}
