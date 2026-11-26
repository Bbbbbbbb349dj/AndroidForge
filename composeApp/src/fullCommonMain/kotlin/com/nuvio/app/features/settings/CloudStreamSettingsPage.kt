package com.nuvio.app.features.settings

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalDensity
import com.nuvio.app.core.ui.LocalNuvioScreenMetrics
import com.nuvio.app.core.ui.nuvio
import com.nuvio.app.features.cloudstream.cloudStreamBrowserViewportHeight
import com.nuvio.app.features.plugins.CloudStreamSettingsSection

private const val BrowserViewportKey = "cloudstream-browser-viewport"

internal actual fun LazyListScope.cloudStreamSettingsContent() {
    item(key = BrowserViewportKey) {
        val metrics = LocalNuvioScreenMetrics.current
        val density = LocalDensity.current
        val gap = with(density) { MaterialTheme.nuvio.spacing.listGap.roundToPx() }
        val availableHeight by remember(metrics, gap) {
            derivedStateOf {
                val layout = metrics?.listState?.layoutInfo
                val ownItem = layout?.visibleItemsInfo?.firstOrNull { it.key == BrowserViewportKey }
                if (layout == null || ownItem == null) null else {
                    val chrome = layout.visibleItemsInfo.filter { it.index < ownItem.index }
                    cloudStreamBrowserViewportHeight(
                        layout.viewportEndOffset - layout.viewportStartOffset,
                        layout.beforeContentPadding,
                        layout.afterContentPadding,
                        chrome.sumOf { it.size },
                        chrome.size * gap,
                    )
                }
            }
        }
        // Subtract the actual Settings header and insets rather than hiding the fixed footer
        // below the screen or guessing a phone-specific height. The inner list is virtualized.
        val viewportModifier = availableHeight?.let { height ->
            Modifier.height(with(density) { height.toDp() })
        } ?: Modifier.fillParentMaxHeight()
        CloudStreamSettingsSection(modifier = viewportModifier)
    }
}
