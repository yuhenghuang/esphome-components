import esphome.config_validation as cv
from esphome.const import CONF_BUSY_PIN, CONF_DATA_RATE, CONF_RESET_PIN

from esphome.components.epaper_spi.models import EpaperModel


class UC8253(EpaperModel):
    def __init__(self, name, class_name="EPaperGDEY037Z03", **defaults):
        defaults[CONF_DATA_RATE] = "10MHz"
        super().__init__(name, class_name, **defaults)

    def option(self, name, fallback=cv.UNDEFINED) -> cv.Optional | cv.Required:
        if name in (CONF_RESET_PIN, CONF_BUSY_PIN):
            return cv.Required(name)
        return super().option(name, fallback)

    # fmt: off
    def get_init_sequence(self, config):
        return (
            (0x04,),  # Power on — UC8253 OTP handles panel config
        )


gdey037z03 = UC8253(
    "GDEY037Z03",
    width=240,
    height=416,
    minimum_update_interval="30s",
)
