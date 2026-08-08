# Changelog

## v1.3.8

- Added optional second sensor for Video Player.
- Added Active threshold and Idle threshold.
- Kept Active lock as independent playback protection.
- Fixed Video Player GPIO/VLC runtime permissions.
- Fixed Video Player restart to respect Node Mode.
- Fixed GPIO restart to respect Node Mode.
- Fixed generic service restart to respect Node Mode.
- Added validation for Video Player GPIO and threshold settings.
- Added protection against duplicate GPIO use for Sensor 1 and Sensor 2.
- Changed HDMI CEC boot default to disabled.
- Improved Dashboard and Diagnostics runtime service reporting.
- Preserved runtime configuration files during reinstall/update.
- Expanded Backup/Restore to include system runtime configuration.

## v1.3.7

- Added paired_sequence mode for legacy Arduino-style UDP installations.
- Fixed version alignment between VERSION, README and module manifests.
- Includes video-node service fixes and GPIO diagnostics live update fixes.


## v1.1.0

### Added

- Basic session authentication
- Login page
- Logout action
- Password change page
- Default password warning
- Password hash storage in `auth.json`

## v1.0.0

Initial public release.

### Added

- Web dashboard
- Input manager
- Advanced input settings
- GPIO service
- UDP sender
- Press/release UDP engine
- Single input mode
- Sequence input mode
- Live GPIO status via SSE
- Diagnostics page
- Logs page
- System page
- Backup and restore
- GPIO hot reload
- Runtime state tracking
