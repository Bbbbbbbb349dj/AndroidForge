package com.nuvio.app.features.settings

import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.ui.Modifier
import com.nuvio.app.features.plugins.CloudStreamSettingsSection

internal actual fun LazyListScope.cloudStreamSettingsContent() {
    item {
        // A bounded viewport lets the repository browser recycle hundreds of extension rows.
        CloudStreamSettingsSection(modifier = Modifier.fillParentMaxHeight())
    }
}
