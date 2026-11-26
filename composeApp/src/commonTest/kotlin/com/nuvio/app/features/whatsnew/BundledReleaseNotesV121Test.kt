package com.nuvio.app.features.whatsnew

import com.nuvio.app.features.updater.*
import kotlin.test.*

class BundledReleaseNotesV121Test {
    @Test fun notesWorkWithoutNetworkAndDoNotDuplicateTheCurrentRelease() {
        val offline = BundledReleaseNotes.merge(null, "1.21")
        assertEquals("1.21", offline.snapshot.releases.first { it.version == "1.21" }.version)
        assertTrue(offline.snapshot.hasCompleteSinceVersion)
        assertTrue(offline.snapshot.releases.first { it.version == "1.21" }.notes.size >= 17)
        assertEquals(2, BundledReleaseNotes.merge(offline, "1.21").snapshot.releases.size)
    }

    @Test fun forkReleaseTagsAndTwoPartVersionsAreRecognized() {
        assertEquals(0, VersionUtils.parse("1.21")!!.compareTo(VersionUtils.parse("1.21.0")!!))
        val release = GitHubReleaseDto(tagName = "nuvio-enhanced-v1.21-apk", name = "Nuvio Enhanced v1.21 APK")
        assertEquals("1.21", ReleaseSelector.versionName(release))
        assertEquals(listOf(release), ReleaseSelector.eligibleReleases(listOf(release), UpdateChannel.STABLE))
    }
}
