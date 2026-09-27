#include <Arduino.h>
#include <SPI.h>
#include <esp_timer.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>

namespace {

constexpr uint8_t PIN_CS = D3;
constexpr uint8_t PIN_DRDY = D2;
constexpr uint8_t PIN_SCK = D8;
constexpr uint8_t PIN_MISO = D9;
constexpr uint8_t PIN_MOSI = D10;

constexpr uint32_t SPI_HZ = 5'000'000;
constexpr uint32_t SERIAL_BAUD = 921600;

constexpr uint8_t REG_DEVID_AD = 0x00;
constexpr uint8_t REG_DEVID_MST = 0x01;
constexpr uint8_t REG_PARTID = 0x02;
constexpr uint8_t REG_XDATA3 = 0x08;
constexpr uint8_t REG_FILTER = 0x28;
constexpr uint8_t REG_RANGE = 0x2C;
constexpr uint8_t REG_POWER_CTL = 0x2D;

constexpr uint8_t EXPECTED_DEVID_AD = 0xAD;
constexpr uint8_t EXPECTED_DEVID_MST = 0x1D;
constexpr uint8_t EXPECTED_PARTID = 0xED;

constexpr uint8_t FILTER_500HZ_LPF_125HZ = 0x03;
constexpr uint8_t RANGE_2G = 0x01;
constexpr float LSB_PER_G_2G = 256000.0f;

constexpr size_t SAMPLE_QUEUE_LENGTH = 256;

SPISettings adxlSpiSettings(SPI_HZ, MSBFIRST, SPI_MODE0);
QueueHandle_t sampleQueue = nullptr;
TaskHandle_t acquisitionTaskHandle = nullptr;

volatile uint32_t missedDrdy = 0;
volatile uint32_t queueDrop = 0;

struct Sample {
  int64_t timestampUs;
  uint32_t seq;
  int32_t xRaw;
  int32_t yRaw;
  int32_t zRaw;
};

uint8_t makeReadCommand(uint8_t reg) {
  return static_cast<uint8_t>((reg << 1) | 0x01);
}

uint8_t makeWriteCommand(uint8_t reg) {
  return static_cast<uint8_t>(reg << 1);
}

uint8_t readRegister(uint8_t reg) {
  SPI.beginTransaction(adxlSpiSettings);
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(makeReadCommand(reg));
  const uint8_t value = SPI.transfer(0x00);
  digitalWrite(PIN_CS, HIGH);
  SPI.endTransaction();
  return value;
}

void writeRegister(uint8_t reg, uint8_t value) {
  SPI.beginTransaction(adxlSpiSettings);
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(makeWriteCommand(reg));
  SPI.transfer(value);
  digitalWrite(PIN_CS, HIGH);
  SPI.endTransaction();
}

void readRegisters(uint8_t startReg, uint8_t* data, size_t length) {
  SPI.beginTransaction(adxlSpiSettings);
  digitalWrite(PIN_CS, LOW);
  SPI.transfer(makeReadCommand(startReg));
  for (size_t i = 0; i < length; ++i) {
    data[i] = SPI.transfer(0x00);
  }
  digitalWrite(PIN_CS, HIGH);
  SPI.endTransaction();
}

int32_t decode20Bit(const uint8_t* bytes) {
  uint32_t value =
      (static_cast<uint32_t>(bytes[0]) << 12) |
      (static_cast<uint32_t>(bytes[1]) << 4) |
      (static_cast<uint32_t>(bytes[2]) >> 4);

  if ((value & 0x80000U) != 0) {
    value |= 0xFFF00000U;
  }
  return static_cast<int32_t>(value);
}

bool readSample(Sample& sample, uint32_t seq) {
  uint8_t raw[9] = {};
  readRegisters(REG_XDATA3, raw, sizeof(raw));

  sample.timestampUs = esp_timer_get_time();
  sample.seq = seq;
  sample.xRaw = decode20Bit(&raw[0]);
  sample.yRaw = decode20Bit(&raw[3]);
  sample.zRaw = decode20Bit(&raw[6]);
  return true;
}

bool configureAdxl355() {
  // 配置寄存器必须在 standby 状态下写入。
  writeRegister(REG_POWER_CTL, 0x01);
  delay(10);

  const uint8_t devidAd = readRegister(REG_DEVID_AD);
  const uint8_t devidMst = readRegister(REG_DEVID_MST);
  const uint8_t partid = readRegister(REG_PARTID);

  Serial.printf(
      "# adxl355_ids,%02X,%02X,%02X\n",
      devidAd,
      devidMst,
      partid);

  if (devidAd != EXPECTED_DEVID_AD ||
      devidMst != EXPECTED_DEVID_MST ||
      partid != EXPECTED_PARTID) {
    Serial.println("# error,ADXL355 device id mismatch");
    return false;
  }

  // HPF 关闭；ODR=500 Hz；LPF=125 Hz。
  writeRegister(REG_FILTER, FILTER_500HZ_LPF_125HZ);

  // 保留 Range 寄存器其他可写位，仅设置 [1:0] 为 ±2 g。
  uint8_t range = readRegister(REG_RANGE);
  range = static_cast<uint8_t>((range & 0xFCU) | RANGE_2G);
  writeRegister(REG_RANGE, range);

  // Measurement mode；DRDY 保持启用。
  writeRegister(REG_POWER_CTL, 0x00);
  delay(20);

  Serial.printf(
      "# config,odr_hz=500,range_g=2,spi_hz=%lu,lsb_per_g=%.0f\n",
      static_cast<unsigned long>(SPI_HZ),
      static_cast<double>(LSB_PER_G_2G));

  return true;
}

void IRAM_ATTR onDrdyRise() {
  BaseType_t higherPriorityTaskWoken = pdFALSE;
  if (acquisitionTaskHandle != nullptr) {
    vTaskNotifyGiveFromISR(acquisitionTaskHandle, &higherPriorityTaskWoken);
  }
  if (higherPriorityTaskWoken == pdTRUE) {
    portYIELD_FROM_ISR();
  }
}

void acquisitionTask(void*) {
  uint32_t seq = 0;

  while (true) {
    const uint32_t notifications = ulTaskNotifyTake(pdTRUE, portMAX_DELAY);

    if (notifications > 1) {
      missedDrdy += notifications - 1;
    }

    Sample sample{};
    readSample(sample, seq++);

    if (xQueueSend(sampleQueue, &sample, 0) != pdPASS) {
      ++queueDrop;
    }
  }
}

void writerTask(void*) {
  Sample sample{};
  int64_t lastStatsUs = esp_timer_get_time();

  while (true) {
    if (xQueueReceive(sampleQueue, &sample, pdMS_TO_TICKS(1000)) == pdPASS) {
      Serial.printf(
          "D,%lld,%lu,%ld,%ld,%ld\n",
          static_cast<long long>(sample.timestampUs),
          static_cast<unsigned long>(sample.seq),
          static_cast<long>(sample.xRaw),
          static_cast<long>(sample.yRaw),
          static_cast<long>(sample.zRaw));
    }

    const int64_t nowUs = esp_timer_get_time();
    if (nowUs - lastStatsUs >= 5'000'000) {
      Serial.printf(
          "# stats,missed_drdy=%lu,queue_drop=%lu\n",
          static_cast<unsigned long>(missedDrdy),
          static_cast<unsigned long>(queueDrop));
      lastStatsUs = nowUs;
    }
  }
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);

  const uint32_t waitStart = millis();
  while (!Serial && (millis() - waitStart < 3000)) {
    delay(10);
  }

  Serial.println();
  Serial.println("# washguard_acquisition,version=0.1.0");

  pinMode(PIN_CS, OUTPUT);
  digitalWrite(PIN_CS, HIGH);
  pinMode(PIN_DRDY, INPUT);

  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI, PIN_CS);

  if (!configureAdxl355()) {
    Serial.println("# fatal,ADXL355 init failed");
    while (true) {
      delay(1000);
    }
  }

  sampleQueue = xQueueCreate(SAMPLE_QUEUE_LENGTH, sizeof(Sample));
  if (sampleQueue == nullptr) {
    Serial.println("# fatal,sample queue allocation failed");
    while (true) {
      delay(1000);
    }
  }

  xTaskCreatePinnedToCore(
      acquisitionTask,
      "wg_acquire",
      4096,
      nullptr,
      4,
      &acquisitionTaskHandle,
      1);

  xTaskCreatePinnedToCore(
      writerTask,
      "wg_writer",
      4096,
      nullptr,
      2,
      nullptr,
      0);

  attachInterrupt(digitalPinToInterrupt(PIN_DRDY), onDrdyRise, RISING);

  Serial.println("# ready");
  Serial.println("# wire_format,D,timestamp_us,seq,x_raw,y_raw,z_raw");
}

void loop() {
  delay(1000);
}
