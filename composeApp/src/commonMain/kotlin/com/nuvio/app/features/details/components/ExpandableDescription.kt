package com.nuvio.app.features.details.components

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.details_show_less
import nuvio.composeapp.generated.resources.details_show_more
import org.jetbrains.compose.resources.stringResource

@Composable
internal fun ExpandableDescription(
    text: String,
    collapsedMaxLines: Int,
    modifier: Modifier = Modifier,
    style: TextStyle = MaterialTheme.typography.bodyMedium,
    color: Color = MaterialTheme.colorScheme.onSurface,
) {
    var expanded by rememberSaveable(text) { mutableStateOf(false) }
    var canExpand by remember(text) { mutableStateOf(false) }
    val showMoreLabel = stringResource(Res.string.details_show_more)
    val showLessLabel = stringResource(Res.string.details_show_less)

    Column(
        modifier = modifier
            .fillMaxWidth()
            .animateContentSize()
            .clickable(
                enabled = canExpand || expanded,
                role = Role.Button,
            ) { expanded = !expanded },
    ) {
        Text(
            text = text,
            style = style,
            color = color,
            maxLines = if (expanded) Int.MAX_VALUE else collapsedMaxLines,
            overflow = if (expanded) TextOverflow.Clip else TextOverflow.Ellipsis,
            onTextLayout = { result ->
                if (!expanded && result.hasVisualOverflow) {
                    canExpand = true
                }
            },
        )
        if (canExpand || expanded) {
            Spacer(modifier = Modifier.height(6.dp))
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(999.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f))
                    .border(
                        1.dp,
                        MaterialTheme.colorScheme.outline.copy(alpha = 0.45f),
                        RoundedCornerShape(999.dp),
                    )
                    .clickable(role = Role.Button) { expanded = !expanded }
                    .semantics {
                        contentDescription = if (expanded) showLessLabel else showMoreLabel
                    }
                    .padding(horizontal = 10.dp, vertical = 4.dp),
            ) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        text = if (expanded) showLessLabel else "⋯ $showMoreLabel",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }
        }
    }
}
