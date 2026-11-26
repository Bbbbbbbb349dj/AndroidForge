package com.lagradost.cloudstream3.ui

import androidx.annotation.DrawableRes
import androidx.annotation.StringRes

enum class WatchType(val internalId: Int, @StringRes val stringRes: Int, @DrawableRes val iconRes: Int) {
    WATCHING(0, 0, 0),
    COMPLETED(1, 0, 0),
    ONHOLD(2, 0, 0),
    DROPPED(3, 0, 0),
    PLANTOWATCH(4, 0, 0),
    NONE(5, 0, 0);

    companion object {
        fun fromInternalId(id: Int?) = entries.find { value -> value.internalId == id } ?: NONE
    }
}

enum class SyncWatchType(val internalId: Int, @StringRes val stringRes: Int, @DrawableRes val iconRes: Int) {
    NONE(-1, 0, 0),
    WATCHING(0, 0, 0),
    COMPLETED(1, 0, 0),
    ONHOLD(2, 0, 0),
    DROPPED(3, 0, 0),
    PLANTOWATCH(4, 0, 0),
    REWATCHING(5, 0, 0);

    companion object {
        fun fromInternalId(id: Int?) = entries.find { value -> value.internalId == id } ?: NONE
    }
}
