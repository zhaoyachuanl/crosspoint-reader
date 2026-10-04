# Read Pico support

The `readpico` PlatformIO environment targets the ESP32-S3 Read Pico with
16 MB Flash, 8 MB octal PSRAM, and a 1216 × 684 LCD-driven E0470 e-paper panel.
CrossPoint's portrait view is 684 × 1216. Native 1-bit SDMMC uses the existing
SdFat/HalStorage path; CST836U provides screen touch and three cover keys.

## Build

Initialize the FreeInk SDK submodule, then build the dedicated environment:

```sh
git submodule update --init --recursive
python -m pip install -r requirements-readpico.txt
pio run -e readpico
pio run -e readpico -t upload --upload-port <device-port>
```

The parent repository pins the Read Pico SDK implementation through its
`freeink-sdk` gitlink. Local commits must also be pushed to the SDK fork before
publishing the parent branch, so other checkouts can fetch the pinned commit.

The environment uses the existing Arduino 3.3.11 / ESP-IDF 5.5.5 toolchain.
Its font build step generates larger UI fonts from the existing licensed
sources: 15pt subtitles and 18pt body/title text, with 12pt small labels.
Read Pico's Lyra home menu uses a separate 22pt font, 80px rows and 16px gaps;
settings retain their existing font size. The larger menu has matching drawn
and touch geometry, with gaps excluded from hit testing.
Theme pixel metrics use the board's 1.5x scale. Legacy home menu dimensions
are shared with drawing so touch rows match the visuals;
FreeInkUI setting rows size themselves from the enlarged fonts.
Lyra's cover height is 339px on Read Pico, with a 355px card: thumbnail
generation, drawing, and touch share these dimensions. Other themes retain
their drawn cover dimensions rather than scaling only the container.
The user confirmed the taller Lyra card and corrected gap above Browse Files.
CJK fallbacks use a matching
SD font size, or the nearest supplied size when a pack omits one.
Board configuration lives in `platformio.readpico.ini`; personal serial ports
and tool paths belong in the ignored `platformio.local.ini`.

## Implementation and upstream updates

Hardware-specific code lives in FreeInk SDK's `ReadPicoHardware` library,
`ReadPicoProfile.h`, and `ReadPicoDriver`. The library imports only the required
official BSP, panel waveform, touch, I/O expander, power chip, and PMU sources.
Its `vendor-manifest.json` pins the demo commit and records every source hash.
The SDK library README describes source provenance and its memory budget.

CrossPoint changes are limited to the build environment, firmware board tag,
OTA repository configuration, board-scaled UI fonts/metrics, and a HAL shutdown request. The reader engines,
rendering geometry, and storage implementation remain shared with upstream.
EPUB parsing, malformed-book compatibility, and indexing error recovery belong
upstream. This hardware fork does not add book-specific handling or change
those reader paths.
For updates, first use the SDK commit selected by the new CrossPoint baseline,
then reapply the SDK hardware changes and build existing C3/S3 targets as well
as `readpico`. Do not independently advance the SDK to its latest branch tip.

The firmware carries the `readpico` board tag and uses this fork's OTA channel.
Publishing a compatible `-readpico` release asset is a separate step.

## Current validation and limits

The first firmware builds and runs on a Read Pico. The user confirmed normal
CrossPoint display, EPUB opening, screen touch, and signals from all three
cover keys. The revised mapping is Previous / Back / Next, with a fresh hold
timer on each key switch. CST836U cover contacts commit immediately, so a
release sampled after a slow screen refresh cannot remain held through the
mechanical-key debounce and trigger menu repeat. The PMU power key retains
debounce. Host tests verify single-step clicks after a 700ms polling gap,
intentional hold repeat, and power debounce during cover-key changes.
The menu-repeat fix still requires device verification.
The user confirmed the corrected home menu hit bands activate Library,
File Transfer, and Settings at their displayed positions, with settings
touch still working normally.
Host tests cover byte packing, coordinate bounds, board selection, touch/key
events, and cancellation after failed touch reads. The X4 Pro build passes.

The revised display backend combines grayscale planes into the existing
4bpp front buffer for one activation, including strip uploads. Full and Half
cleanup requests use GC16; ordinary grayscale drives all pixels with GL16,
including unchanged white pixels; Fast uses differential DU. The backend
keeps HV rails on across adjacent updates and powers down after 8 seconds
idle, matching the demo. Sleep/shutdown bypass that idle delay.
Grayscale quality across books and orientations still requires device checks.
The user confirmed faster page turns after the conversion changes. USB logs
from the same book/chapter show the following medians for cached, single-
activation text pages (7 before, 3 after; screen-touch latency uses 6 before
and 3 after). Chapter entry, uncached backward pages and cleanup turns are
excluded; these are small samples, not a general benchmark.

| Timing | Before | After |
| --- | ---: | ---: |
| Screen contact to refresh request | 728ms | 474ms |
| Screen contact to page-render completion | 1708ms | 1479ms |
| Page render total | 1487ms | 1264ms |
| Grayscale plane rendering/upload, LSB / MSB | 217 / 217ms | 95 / 105ms |
| Grayscale display call | 949ms | 974ms |

The gain is in preparation, not a shorter panel waveform. Normal GL16 drives
unchanged white pixels as the official demo requires. Upstream page layout,
font warming and backward-page cache behavior remain unchanged. The revised
8-second idle deadline applies after every refresh, including callers that
request no immediate power-off. USB logs from the final firmware confirm idle
power-off 8 seconds after the last refresh completed, including settings/home
updates through the default no-immediate-power-off path.
RTC, acceleration gestures, audio, and USB MSC are disabled.
All orientations, battery-only boot, sleep/wake, and low-battery shutdown still
require hardware validation.

Factory VCOM is read from the CW32 PMU; the backend never changes calibration.
CW32 soft sleep powers down the ESP32, so wake is a cold boot. Shutdown requests
go through CrossPoint's state-saving sleep path. GPIO41 is not configured as
an ESP32 deep-sleep wake source.

Keep a verified full ESP Flash backup before replacing the existing firmware.
That backup does not contain the independent PMU's calibration storage.
