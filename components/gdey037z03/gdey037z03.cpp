#include "gdey037z03.h"

#include "esphome/core/application.h"
#include "esphome/core/log.h"

namespace esphome::epaper_spi {

static const char *const TAG = "epaper_spi.gdey037z03";

void EPaperGDEY037Z03::clear() {
  this->fill(COLOR_ON);
}

bool EPaperGDEY037Z03::initialise(bool partial) {
  delay(10);  // Vendor requires 10ms after RST HIGH before power-on
  return EPaperBase::initialise(partial);
}

void EPaperGDEY037Z03::fill(Color color) {
  if (this->get_clipping().is_set()) {
    EPaperBase::fill(color);
    return;
  }

  bool is_red = (color.red > 128) && (color.green < 128) && (color.blue < 128);
  bool is_light = (static_cast<int>(color.r) + color.g + color.b) >= 382;

  uint8_t bw_byte, rw_byte;
  if (is_red) {
    bw_byte = 0x00;
    rw_byte = 0xFF;  // ~RW=0 → NEW=0 → OLD=0,NEW=0 → Red
  } else if (is_light) {
    bw_byte = 0xFF;
    rw_byte = 0x00;  // ~RW=1 → NEW=1 → OLD=1,NEW=1 → White
  } else {
    bw_byte = 0x00;
    rw_byte = 0x00;  // ~RW=1 → NEW=1 → OLD=0,NEW=1 → Black
  }

  this->buffer_.fill(bw_byte);
  // Overwrite the RW plane (second half of buffer)
  for (size_t i = BW_BUFFER_SIZE; i < BW_BUFFER_SIZE * 2; i++) {
    this->buffer_[i] = rw_byte;
  }

  this->x_high_ = this->width_;
  this->y_high_ = this->height_;
  this->x_low_ = 0;
  this->y_low_ = 0;
}

void HOT EPaperGDEY037Z03::draw_pixel_at(int x, int y, Color color) {
  if (!this->rotate_coordinates_(x, y))
    return;

  bool is_red = (color.red > 128) && (color.green < 128) && (color.blue < 128);
  bool is_light = (static_cast<int>(color.r) + color.g + color.b) >= 382;

  uint8_t bw_bit, rw_bit;
  if (is_red) {
    bw_bit = 0;
    rw_bit = 1;  // ~RW=0 → NEW=0 → OLD=0,NEW=0 → Red
  } else if (is_light) {
    bw_bit = 1;
    rw_bit = 0;  // ~RW=1 → NEW=1 → OLD=1,NEW=1 → White
  } else {
    bw_bit = 0;
    rw_bit = 0;  // ~RW=1 → NEW=1 → OLD=0,NEW=1 → Black
  }

  const size_t bw_byte_pos = y * this->row_width_ + x / 8;
  const size_t rw_byte_pos = BW_BUFFER_SIZE + bw_byte_pos;
  const uint8_t mask = 0x80 >> (x % 8);

  if (bw_bit) {
    this->buffer_[bw_byte_pos] |= mask;
  } else {
    this->buffer_[bw_byte_pos] &= ~mask;
  }

  if (rw_bit) {
    this->buffer_[rw_byte_pos] |= mask;
  } else {
    this->buffer_[rw_byte_pos] &= ~mask;
  }
}

void EPaperGDEY037Z03::power_on() {
  // No-op: power-on (0x04) is handled in the init sequence during INITIALISE state
}

void EPaperGDEY037Z03::power_off() {
  ESP_LOGV(TAG, "Power off");
  this->command(0x02);  // POF
}

void EPaperGDEY037Z03::deep_sleep() {
  ESP_LOGV(TAG, "Deep sleep");
  delay(100);  // Vendor requires >=100ms delay after POF before DSLP
  this->cmd_data(0x07, {0xA5});  // DSLP
}

void EPaperGDEY037Z03::refresh_screen(bool partial) {
  ESP_LOGV(TAG, "Refresh screen");
  this->command(0x12);  // DRF
  this->next_delay_ = 1;  // Vendor requires >=200us delay after DRF
}

bool HOT EPaperGDEY037Z03::transfer_data() {
  const size_t total_bytes = BW_BUFFER_SIZE;
  const auto start_time = millis();

  if (this->current_data_index_ == 0) {
    // Start of a phase — send the appropriate command
    this->command(this->send_red_ ? 0x13 : 0x10);  // DTM2 or DTM1
  }

  size_t buf_idx = 0;
  uint8_t bytes_to_send[MAX_TRANSFER_SIZE];

  this->start_data_();
  while (this->current_data_index_ != total_bytes) {
    if (this->send_red_) {
      // RW plane — send inverted
      bytes_to_send[buf_idx++] = ~this->buffer_[BW_BUFFER_SIZE + this->current_data_index_];
    } else {
      // BW plane — send raw
      bytes_to_send[buf_idx++] = this->buffer_[this->current_data_index_];
    }
    this->current_data_index_++;

    if (buf_idx == sizeof bytes_to_send) {
      this->write_array(bytes_to_send, buf_idx);
      buf_idx = 0;
      if (millis() - start_time > MAX_TRANSFER_TIME) {
        this->disable();
        return false;
      }
    }
  }

  if (buf_idx != 0) {
    this->write_array(bytes_to_send, buf_idx);
  }
  this->disable();

  this->current_data_index_ = 0;

  if (this->send_red_) {
    // Both phases complete
    this->send_red_ = false;
    return true;
  } else {
    // BW phase done, continue to RW phase
    this->send_red_ = true;
    return false;
  }
}

}  // namespace esphome::epaper_spi
