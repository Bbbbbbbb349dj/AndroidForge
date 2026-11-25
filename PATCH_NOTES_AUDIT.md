# Nuvio Enhanced 2 v1.1.2 — patch notes and audit status

Baseline: user's supplied Nuvio Enhanced 2 v1.1.0 source, with the prior v1.1.1 source changes retained.

## Changes in v1.1.2

### CloudStream extension settings
- Added a gear action to installed CloudStream extension cards.
- The action loads the installed extension through the existing Android DEX runtime, then invokes the extension's own `Plugin.openSettings` callback.
- Invokes the callback on Android's main thread and passes the active `Activity` context, as expected by CloudStream settings dialogs.
- Fixed Activity tracking so a later `Application` context initialization does not erase the active Activity reference.
- Rebinds the current Activity in `MainActivity.onResume()`.
- Adds diagnostic entries for settings open success/failure.
- Refuses settings execution for unverified or incompatible packages.
- On extensions that do not define `openSettings`, the UI reports that no configurable settings are exposed.

### StreamPlay and CineStream
- Their lack of configurable controls was a material compatibility gap: these plugins rely on their own settings to enable/disable internal sources and configure provider-specific options.
- The new gear action exposes each plugin's native settings callback when the installed version provides one.
- CineStream retains the existing host compatibility default that disables its optional Simkl account-sync provider because that service is not embedded in Nuvio. This is separate from CineStream's own source settings.
- This does not guarantee every StreamPlay/CineStream scraper works: upstream site availability, anti-bot responses, missing tokens, and extractor changes remain external variables.

### Previous v1.1.1 changes retained
- Batch-download planner/dialog wiring in the details screen.
- Per-provider CloudStream search timeout and diagnostic logging.
- Build workflow uploads APK artifacts rather than replacing the original release.

### Build configuration
- Version name: 1.1.2
- Android version code: 161
- Gradle distribution URL changed from the Tencent mirror to the official Gradle distribution service.

## Verification status

- Source changes and cross-source-set expect/actual declarations were inspected.
- APK compilation and Android runtime testing have NOT been completed in this environment. The Gradle wrapper could not download Gradle because DNS/network access to the configured mirror failed; Android SDK is not installed here.
- The settings feature must be compiled and tested in GitHub Actions and then tested on an Android device with StreamPlay and CineStream installed.
- A green build proves compilation, not that each third-party extension's current websites or tokens work.
