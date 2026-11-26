package com.lagradost.cloudstream3.ui.settings

import android.content.Context
import android.content.res.Configuration
import android.content.res.Resources

object Globals {
    var beneneCount = 0

    const val PHONE: Int = 0b00001
    const val TV: Int = 0b00010
    const val EMULATOR: Int = 0b00100
    private var layoutId: Int = PHONE

    fun Context.updateTv() {
        val uiMode = resources?.configuration?.uiMode ?: 0
        layoutId = if ((uiMode and Configuration.UI_MODE_TYPE_MASK) == Configuration.UI_MODE_TYPE_TELEVISION) {
            TV
        } else {
            PHONE
        }
    }

    fun isLandscape(): Boolean =
        isLayout(TV or EMULATOR) ||
            Resources.getSystem().configuration.orientation == Configuration.ORIENTATION_LANDSCAPE

    fun isLayout(flags: Int): Boolean = (layoutId and flags) != 0
}
