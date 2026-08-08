# Changelog

## v1.4.0

- Introduced a unified premium visual system across the web interface.
- Added a redesigned header, navigation, status strip, panels, forms, buttons, badges, and log views.
- Rebuilt the System page with consistent module, node mode, backup, maintenance, and update controls.
- Refined the Login, Settings, and Logs pages to match the new application design.
- Added responsive layouts and mobile navigation for phones and tablets.
- Improved visual hierarchy, spacing, typography, focus states, and status feedback.
- Removed obsolete authentication, state, and service-management helpers left by earlier refactors.
- Removed unused imports while preserving all active modules, installers, systemd units, and examples.

## v1.3.9

- Fixed Dashboard reporting for GPIO and Video runtime services.
- Made reinstall preserve and start only the configured Node Mode.
- Made restored snapshots require a reboot instead of applying partial runtime changes.
- Fixed Video Player Active Low handling to use the raw electrical GPIO state.
- Made the Video service use its guaranteed runtime directory after cold boot.
- Restored secure `600` permissions for authentication data after install and update.
- Added process-safe event log rotation with a 100 KB maximum file size.
- Removed temporary backup ZIP files after download.
- Made restore remove a stale video dependency marker when it is absent from the snapshot.
- Added safe numeric validation and bounds for GPIO and TouchDesigner forms.

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
