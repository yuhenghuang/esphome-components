#pragma once

#include "esphome/components/epaper_spi/epaper_spi.h"

namespace esphome::epaper_spi {

/**
 * Driver for GDEY037Z03 BWR e-ink display with UC8253 controller.
 *
 * The UC8253 uses factory OTP for panel configuration (resolution, LUTs),
 * so the init sequence consists of only a power-on command.
 *
 * BUSY pin polarity: LOW = busy, HIGH = idle (inverted vs ESPHome default).
 * Configure with inverted: true on busy_pin in YAML.
 */
class EPaperGDEY037Z03 : public EPaperBase {
 public:
  EPaperGDEY037Z03(const char *name, uint16_t width, uint16_t height,
                   const uint8_t *init_sequence, size_t init_sequence_length)
      : EPaperBase(name, width, height, init_sequence, init_sequence_length, DISPLAY_TYPE_COLOR) {
    this->buffer_length_ = BW_BUFFER_SIZE * 2;  // two color planes for BWR
  }

  void fill(Color color) override;
  void clear() override;

 protected:
  bool initialise(bool partial) override;
  void draw_pixel_at(int x, int y, Color color) override;

  bool transfer_data() override;
  void refresh_screen(bool partial) override;
  void power_on() override;    // no-op: power-on happens in init sequence
  void power_off() override;
  void deep_sleep() override;

 private:
  static constexpr size_t BW_BUFFER_SIZE = 12480;  // 240 * 416 / 8
  bool send_red_{false};  // false = sending BW (DTM1), true = sending RW (DTM2)
};

}  // namespace esphome::epaper_spi
