package com.lagradost.cloudstream3.subtitles

import com.lagradost.cloudstream3.TvType

object AbstractSubtitleEntities {
    data class SubtitleEntity(
        var idPrefix: String,
        var name: String,
        var lang: String,
        var data: String,
        var type: TvType = TvType.Movie,
        var source: String = idPrefix,
        var epNumber: Int? = null,
        var seasonNumber: Int? = null,
        var year: Int? = null,
        var isHearingImpaired: Boolean = false,
    )

    data class SubtitleSearch(
        var query: String,
        var imdbId: String? = null,
        var tmdbId: Int? = null,
        var malId: Int? = null,
        var aniListId: Int? = null,
        var lang: String? = null,
        var epNumber: Int? = null,
        var seasonNumber: Int? = null,
        var year: Int? = null,
    )
}

class SubtitleResource {
    val subtitles: MutableList<String> = mutableListOf()

    fun addUrl(url: String?) {
        if (!url.isNullOrBlank()) {
            subtitles += url
        }
    }
}
