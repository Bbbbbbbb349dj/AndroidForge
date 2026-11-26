package com.lagradost.cloudstream3.syncproviders.providers

import com.lagradost.cloudstream3.syncproviders.SubtitleAPI
import com.lagradost.cloudstream3.syncproviders.SyncAPI
import com.lagradost.cloudstream3.syncproviders.SyncIdName

class MALApi : SyncAPI() {
    override val name: String = "MAL"
    override val idPrefix: String = "mal"
    override val mainUrl: String = "https://myanimelist.net"
    override val syncIdName: SyncIdName = SyncIdName.MyAnimeList
    override val hasOAuth2: Boolean = true
}

class AniListApi : SyncAPI() {
    override val name: String = "AniList"
    override val idPrefix: String = "anilist"
    override val mainUrl: String = "https://anilist.co"
    override val syncIdName: SyncIdName = SyncIdName.Anilist
    override val hasOAuth2: Boolean = true

    data class CoverImage(
        @com.fasterxml.jackson.annotation.JsonProperty("extraLarge") val extraLarge: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("large") val large: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("medium") val medium: String? = null,
    )

    data class Title(
        @com.fasterxml.jackson.annotation.JsonProperty("romaji") val romaji: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("english") val english: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("native") val native: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("userPreferred") val userPreferred: String? = null,
    )

    data class SeasonNextAiringEpisode(
        @com.fasterxml.jackson.annotation.JsonProperty("episode") val episode: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("timeUntilAiring") val timeUntilAiring: Int? = null,
    )

    data class LikePageInfo(
        @com.fasterxml.jackson.annotation.JsonProperty("total") val total: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("currentPage") val currentPage: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("lastPage") val lastPage: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("perPage") val perPage: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("hasNextPage") val hasNextPage: Boolean? = null,
    )

    data class MediaCoverImage(
        @com.fasterxml.jackson.annotation.JsonProperty("extraLarge") val extraLarge: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("large") val large: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("medium") val medium: String? = null,
    )

    data class MediaTitle(
        @com.fasterxml.jackson.annotation.JsonProperty("romaji") val romaji: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("english") val english: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("native") val native: String? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("userPreferred") val userPreferred: String? = null,
    )

    data class RecommendedMedia(
        @com.fasterxml.jackson.annotation.JsonProperty("id") val id: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("idMal") val idMal: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("title") val title: MediaTitle? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("coverImage") val coverImage: MediaCoverImage? = null,
    )

    data class Recommendation(
        @com.fasterxml.jackson.annotation.JsonProperty("rating") val rating: Int? = null,
        @com.fasterxml.jackson.annotation.JsonProperty("mediaRecommendation") val mediaRecommendation: RecommendedMedia? = null,
    )

    data class RecommendationEdge(
        @com.fasterxml.jackson.annotation.JsonProperty("node") val node: Recommendation? = null,
    )

    data class RecommendationConnection(
        @com.fasterxml.jackson.annotation.JsonProperty("edges") val edges: List<RecommendationEdge> = emptyList(),
        @com.fasterxml.jackson.annotation.JsonProperty("nodes") val nodes: List<Recommendation> = emptyList(),
    )
}

class KitsuApi : SyncAPI() {
    override val name: String = "Kitsu"
    override val idPrefix: String = "kitsu"
    override val mainUrl: String = "https://kitsu.app"
    override val syncIdName: SyncIdName = SyncIdName.Kitsu
    override val hasInApp: Boolean = true
}

class SimklApi : SyncAPI() {
    override val name: String = "Simkl"
    override val idPrefix: String = "simkl"
    override val mainUrl: String = "https://simkl.com"
    override val syncIdName: SyncIdName = SyncIdName.Simkl
    override val hasOAuth2: Boolean = true
    override val hasPin: Boolean = true
}

class LocalList : SyncAPI() {
    override val name: String = "Local"
    override val idPrefix: String = "local"
    override val requiresLogin: Boolean = false
    override val syncIdName: SyncIdName = SyncIdName.LocalList
}

class OpenSubtitlesApi : SubtitleAPI() {
    override val name: String = "OpenSubtitles"
    override val idPrefix: String = "opensubtitles"
    override val hasInApp: Boolean = true
}

class Addic7ed : SubtitleAPI() {
    override val name: String = "Addic7ed"
    override val idPrefix: String = "addic7ed"
    override val requiresLogin: Boolean = false
}

class SubDlApi : SubtitleAPI() {
    override val name: String = "SubDL"
    override val idPrefix: String = "subdl"
    override val requiresLogin: Boolean = false
}

class SubSourceApi : SubtitleAPI() {
    override val name: String = "SubSource"
    override val idPrefix: String = "subsource"
    override val requiresLogin: Boolean = false
}
