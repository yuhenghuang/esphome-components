import importlib
import pkgutil

from esphome import core, pins
import esphome.codegen as cg
from esphome.components import display, spi
from esphome.components.display import validate_rotation
from esphome.components.mipi import flatten_sequence
import esphome.config_validation as cv
from esphome.config_validation import update_interval
from esphome.const import (
    CONF_BUSY_PIN,
    CONF_CS_PIN,
    CONF_DATA_RATE,
    CONF_DC_PIN,
    CONF_DIMENSIONS,
    CONF_FULL_UPDATE_EVERY,
    CONF_HEIGHT,
    CONF_ID,
    CONF_INIT_SEQUENCE,
    CONF_LAMBDA,
    CONF_MODEL,
    CONF_RESET_DURATION,
    CONF_RESET_PIN,
    CONF_ROTATION,
    CONF_UPDATE_INTERVAL,
    CONF_WIDTH,
)

from . import models
from esphome.components.epaper_spi.models import EpaperModel
from esphome.components.epaper_spi.display import CONF_INIT_SEQUENCE_ID

DEPENDENCIES = ["spi"]
AUTO_LOAD = ["epaper_spi", "split_buffer"]

# Import all models from our models package so they register in EpaperModel.models
for module_info in pkgutil.iter_modules(models.__path__):
    importlib.import_module(f".models.{module_info.name}", package=__package__)

epaper_spi_ns = cg.esphome_ns.namespace("epaper_spi")
EPaperBase = epaper_spi_ns.class_(
    "EPaperBase", cg.PollingComponent, spi.SPIDevice, display.Display
)

MODELS = EpaperModel.models

DIMENSION_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_WIDTH): cv.int_,
        cv.Required(CONF_HEIGHT): cv.int_,
    }
)


def model_schema(config):
    model = MODELS[config[CONF_MODEL]]
    class_name = epaper_spi_ns.class_(model.class_name, EPaperBase)
    minimum_update_interval = update_interval(
        model.get_default("minimum_update_interval", "1s")
    )
    cv_dimensions = cv.Optional if model.get_default(CONF_WIDTH) else cv.Required
    return display.FULL_DISPLAY_SCHEMA.extend(
        spi.spi_device_schema(
            cs_pin_required=False,
            default_mode="MODE0",
            default_data_rate=model.get_default(CONF_DATA_RATE, 10_000_000),
        )
    ).extend(
        {
            cv.Optional(CONF_ROTATION, default=0): validate_rotation,
            cv.Required(CONF_MODEL): cv.one_of(model.name, upper=True),
            cv.Optional(CONF_UPDATE_INTERVAL, default=cv.UNDEFINED): cv.All(
                update_interval, cv.Range(min=minimum_update_interval)
            ),
            cv.Optional(CONF_FULL_UPDATE_EVERY, default=1): cv.int_range(1, 255),
            model.option(CONF_BUSY_PIN): pins.gpio_input_pin_schema,
            model.option(CONF_CS_PIN): pins.gpio_output_pin_schema,
            model.option(CONF_DC_PIN, fallback=None): pins.gpio_output_pin_schema,
            model.option(CONF_RESET_PIN): pins.gpio_output_pin_schema,
            cv.GenerateID(): cv.declare_id(class_name),
            cv.GenerateID(CONF_INIT_SEQUENCE_ID): cv.declare_id(cg.uint8),
            cv_dimensions(CONF_DIMENSIONS): DIMENSION_SCHEMA,
            model.option(CONF_INIT_SEQUENCE, cv.UNDEFINED): cv.ensure_list(
                lambda x: x
            ),
            model.option(CONF_RESET_DURATION, cv.UNDEFINED): cv.All(
                cv.positive_time_period_milliseconds,
                cv.Range(max=core.TimePeriod(milliseconds=500)),
            ),
        }
    )


def customise_schema(config):
    config = cv.Schema(
        {
            cv.Required(CONF_MODEL): cv.one_of(*MODELS, upper=True, space="-"),
        },
        extra=cv.ALLOW_EXTRA,
    )(config)
    return model_schema(config)(config)


CONFIG_SCHEMA = customise_schema


def _final_validate(config):
    spi.final_validate_device_schema(
        "gdey037z03", require_miso=False, require_mosi=True
    )(config)
    if CONF_LAMBDA not in config and CONF_UPDATE_INTERVAL not in config:
        config[CONF_UPDATE_INTERVAL] = update_interval("1min")
    return config


FINAL_VALIDATE_SCHEMA = _final_validate


async def to_code(config):
    model = MODELS[config[CONF_MODEL]]

    init_sequence = config.get(CONF_INIT_SEQUENCE)
    if init_sequence is None:
        init_sequence = model.get_init_sequence(config)
    init_sequence = flatten_sequence(init_sequence)
    init_sequence_length = len(init_sequence)
    init_sequence_id = cg.static_const_array(
        config[CONF_INIT_SEQUENCE_ID], init_sequence
    )
    width, height = model.get_dimensions(config)
    var = cg.new_Pvariable(
        config[CONF_ID],
        model.name,
        width,
        height,
        init_sequence_id,
        init_sequence_length,
    )

    await display.register_display(var, config)
    await spi.register_spi_device(var, config, write_only=True)

    dc = await cg.gpio_pin_expression(config[CONF_DC_PIN])
    cg.add(var.set_dc_pin(dc))

    if CONF_LAMBDA in config:
        lambda_ = await cg.process_lambda(
            config[CONF_LAMBDA], [(display.DisplayRef, "it")], return_type=cg.void
        )
        cg.add(var.set_writer(lambda_))
    if reset_pin := config.get(CONF_RESET_PIN):
        reset = await cg.gpio_pin_expression(reset_pin)
        cg.add(var.set_reset_pin(reset))
    if busy_pin := config.get(CONF_BUSY_PIN):
        busy = await cg.gpio_pin_expression(busy_pin)
        cg.add(var.set_busy_pin(busy))
    cg.add(var.set_full_update_every(config[CONF_FULL_UPDATE_EVERY]))
    cg.add(var.set_update_interval(config.get(CONF_UPDATE_INTERVAL, update_interval("30s"))))
    if CONF_RESET_DURATION in config:
        cg.add(var.set_reset_duration(config[CONF_RESET_DURATION]))
