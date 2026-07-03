# Hardware notes

Recommended basic wiring for a clean digital input:

```text
GPIO pin ---- switch/button ---- GND
```

Use internal pull-up enabled in the input configuration.

For noisy or analog-like sensors, add proper signal conditioning. Options:

- external pull-up or pull-down resistor
- RC filter
- comparator module
- ADC module
- replacing the sensor with a dry-contact switch

Raspberry Pi GPIO pins are digital inputs. They are not analog inputs.
