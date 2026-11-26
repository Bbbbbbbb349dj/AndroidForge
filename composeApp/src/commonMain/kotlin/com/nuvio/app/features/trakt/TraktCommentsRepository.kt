package com.nuvio.app.features.trakt

import co.touchlab.kermit.Logger
import com.nuvio.app.core.format.extractReleaseYearForDisplay
import com.nuvio.app.features.addons.httpGetTextWithHeaders
import com.nuvio.app.features.addons.httpRequestRaw
import com.nuvio.app.features.details.MetaDetails
import com.nuvio.app.features.tmdb.TmdbPublicReviewDto
import com.nuvio.app.features.tmdb.TmdbService
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import nuvio.composeapp.generated.resources.Res
import nuvio.composeapp.generated.resources.details_comments_trakt_load_failed_with_code
import nuvio.composeapp.generated.resources.trakt_user_fallback
import org.jetbrains.compose.resources.getString
import kotlin.math.abs
import kotlin.math.roundToInt

private const val COMMENTS_SORT = "likes"
private const val COMMENTS_LIMIT = 50
private const val COMMENTS_CACHE_TTL_MS = 10 * 60_000L
private val INLINE_SPOILER_REGEX = Regex("(?is)\\[spoiler\\].*?\\[/spoiler\\]")
private val INLINE_SPOILER_TAG_REGEX = Regex("\\[/?spoiler\\]", RegexOption.IGNORE_CASE)

private val commentsJson = Json { ignoreUnknownKeys = true }

/**
 * Public reviews & comments aggregator.
 *
 * Source policy & attribution:
 * - Uses public, unauthenticated Trakt API v2 comment/review endpoints (`trakt-api-key`)
 *   and official TMDB API v3 `/reviews` endpoints — NO user login required.
 * - IMDb and Letterboxd prohibit unauthenticated HTML scraping in their Terms of Service;
 *   we intentionally avoid brittle/non-compliant scrapers and instead attribute every review
 *   with its official source (`Trakt` or `TMDB`), author handle, and canonical `sourceUrl`.
 */
object TraktCommentsRepository {
    private val log = Logger.withTag("PublicReviews")

    private data class TimedCache(
        val pages: Map<Int, List<TraktCommentReview>>,
        val pageCount: Int,
        val itemCount: Int,
        val updatedAtMs: Long,
    )

    private val cacheMutex = Mutex()
    private val cache = mutableMapOf<String, TimedCache>()

    suspend fun getCommentsPage(
        meta: MetaDetails,
        page: Int = 1,
        forceRefresh: Boolean = false,
    ): TraktCommentsPage {
        val type = resolveCommentsType(meta) ?: return TraktCommentsPage(emptyList(), page, 0, 0)
        val cacheKey = "${type.apiValue}|${meta.id.trim()}|${meta.name.trim().lowercase()}"

        if (forceRefresh) {
            cacheMutex.withLock { cache.remove(cacheKey) }
        } else {
            cacheMutex.withLock {
                val cached = cache[cacheKey]
                if (
                    cached != null &&
                    currentTimeMillis() - cached.updatedAtMs <= COMMENTS_CACHE_TTL_MS &&
                    cached.pages.containsKey(page)
                ) {
                    return TraktCommentsPage(
                        items = cached.pages.getValue(page),
                        currentPage = page,
                        pageCount = cached.pageCount,
                        itemCount = cached.itemCount,
                    )
                }
            }
        }

        val resolvedIds = resolvePublicReviewIds(meta, type)
        if (resolvedIds.traktTarget == null && resolvedIds.tmdbId == null) {
            return TraktCommentsPage(emptyList(), page, 0, 0)
        }

        return coroutineScope {
            val traktDeferred = async {
                resolvedIds.traktTarget?.let { target ->
                    runCatching { fetchTraktPublicPage(target, page) }
                        .onFailure { err -> log.w(err) { "Trakt public comments fetch failed for ${target.pathId}" } }
                        .getOrNull()
                }
            }
            val tmdbDeferred = async {
                resolvedIds.tmdbId?.let { tmdbId ->
                    runCatching { fetchTmdbPublicPage(tmdbId, meta.type, page) }
                        .onFailure { err -> log.w(err) { "TMDB public reviews fetch failed for tmdbId=$tmdbId" } }
                        .getOrNull()
                }
            }

            val traktPage = traktDeferred.await()
            val tmdbPage = tmdbDeferred.await()

            val merged = mergePublicReviewLists(
                traktItems = traktPage?.items.orEmpty(),
                tmdbItems = tmdbPage?.items.orEmpty(),
            )
            val totalPages = maxOf(traktPage?.pageCount ?: 0, tmdbPage?.pageCount ?: 0)
                .let { if (it == 0 && merged.isNotEmpty()) page else it }
            val totalItems = (traktPage?.itemCount ?: 0) + (tmdbPage?.itemCount ?: 0)

            cacheMutex.withLock {
                val cached = cache[cacheKey]
                cache[cacheKey] = TimedCache(
                    pages = (cached?.pages.orEmpty()) + (page to merged),
                    pageCount = totalPages,
                    itemCount = totalItems.coerceAtLeast(merged.size),
                    updatedAtMs = currentTimeMillis(),
                )
            }

            TraktCommentsPage(
                items = merged,
                currentPage = page,
                pageCount = totalPages,
                itemCount = totalItems.coerceAtLeast(merged.size),
            )
        }
    }

    fun clearCache() {
        cache.clear()
    }

    private suspend fun fetchTraktPublicPage(
        target: ResolvedCommentsTarget,
        page: Int,
    ): TraktCommentsPage {
        val headers = TraktAuthRepository.publicOrAuthorizedHeaders()
        val endpoint = when (target.type) {
            TraktCommentsType.MOVIE -> "movies"
            TraktCommentsType.SHOW -> "shows"
        }
        val url = "https://api.trakt.tv/$endpoint/${target.pathId}/comments/$COMMENTS_SORT?page=$page&limit=$COMMENTS_LIMIT"
        val response = httpRequestRaw(
            method = "GET",
            url = url,
            headers = headers,
            body = "",
        )
        if (response.status == 404) {
            return TraktCommentsPage(emptyList(), page, 0, 0)
        }
        if (response.status !in 200..299) {
            throw IllegalStateException(
                getString(Res.string.details_comments_trakt_load_failed_with_code, response.status),
            )
        }
        val dtos = commentsJson.decodeFromString<List<TraktCommentDto>>(response.body)
        val pageCount = response.headers["X-Pagination-Page-Count"]?.toIntOrNull()
            ?: response.headers["x-pagination-page-count"]?.toIntOrNull()
            ?: page
        val itemCount = response.headers["X-Pagination-Item-Count"]?.toIntOrNull()
            ?: response.headers["x-pagination-item-count"]?.toIntOrNull()
            ?: dtos.size
        val selected = filterDisplayableComments(dtos).map(::toTraktReviewModel)
        return TraktCommentsPage(
            items = selected,
            currentPage = page,
            pageCount = pageCount,
            itemCount = itemCount,
        )
    }

    private suspend fun fetchTmdbPublicPage(
        tmdbId: String,
        mediaType: String,
        page: Int,
    ): TraktCommentsPage {
        val response = TmdbService.fetchPublicReviews(
            tmdbId = tmdbId,
            mediaType = mediaType,
            page = page,
        ) ?: return TraktCommentsPage(emptyList(), page, 0, 0)
        val mapped = response.results
            .filter { !it.content.isNullOrBlank() }
            .map(::toTmdbReviewModel)
        return TraktCommentsPage(
            items = mapped,
            currentPage = response.page,
            pageCount = response.totalPages,
            itemCount = response.totalResults,
        )
    }

    private suspend fun resolvePublicReviewIds(
        meta: MetaDetails,
        type: TraktCommentsType,
    ): ResolvedPublicReviewIds {
        var imdbId = resolveDirectPathId(meta)
        var tmdbId = resolveTmdbCandidate(meta)?.toString()

        val initialImdbId = imdbId
        if (tmdbId == null && initialImdbId != null) {
            tmdbId = runCatching { TmdbService.ensureTmdbId(initialImdbId, meta.type) }.getOrNull()
        }

        if (imdbId == null && tmdbId == null && meta.name.isNotBlank()) {
            val year = meta.releaseInfo?.let(::extractReleaseYearForDisplay)
            val searched = runCatching {
                TmdbService.ensureTmdbIdBySearch(
                    title = meta.name,
                    mediaType = meta.type,
                    year = year,
                )
            }.getOrNull()
            if (searched != null) {
                tmdbId = searched.first
                imdbId = searched.second
            }
        }

        val traktTarget = when {
            !imdbId.isNullOrBlank() -> ResolvedCommentsTarget(type, imdbId)
            tmdbId?.toIntOrNull() != null -> resolveViaTraktSearch(type, tmdbId.toInt())
            else -> null
        }

        return ResolvedPublicReviewIds(
            traktTarget = traktTarget,
            tmdbId = tmdbId,
        )
    }

    private fun resolveCommentsType(meta: MetaDetails): TraktCommentsType? =
        when (meta.type.trim().lowercase()) {
            "movie", "film" -> TraktCommentsType.MOVIE
            "series", "show", "tv", "anime" -> TraktCommentsType.SHOW
            else -> null
        }

    private fun resolveDirectPathId(meta: MetaDetails): String? {
        val id = meta.id.trim()
        if (id.startsWith("tt", ignoreCase = true) && id.length >= 7) return id.substringBefore(':')
        for (part in id.split(':')) {
            val trimmed = part.trim()
            if (trimmed.startsWith("tt", ignoreCase = true) && trimmed.length >= 7) return trimmed
        }
        return null
    }

    private fun resolveTmdbCandidate(meta: MetaDetails): Int? {
        val id = meta.id.trim()
        for (part in id.split(':')) {
            val trimmed = part.trim()
            if (!trimmed.startsWith("tt", ignoreCase = true) && trimmed.isNotEmpty() && trimmed.all(Char::isDigit)) {
                return trimmed.toIntOrNull()
            }
        }
        return null
    }

    private suspend fun resolveViaTraktSearch(
        type: TraktCommentsType,
        tmdbId: Int,
    ): ResolvedCommentsTarget? {
        val headers = TraktAuthRepository.publicOrAuthorizedHeaders()
        val url = "https://api.trakt.tv/search/tmdb/$tmdbId?type=${type.apiValue}"
        return try {
            val responseText = httpGetTextWithHeaders(url, headers)
            val results = commentsJson.decodeFromString<List<TraktCommentsSearchResultDto>>(responseText)
            val matched = results.firstOrNull {
                it.type.equals(type.apiValue, ignoreCase = true)
            }
            val ids = when (type) {
                TraktCommentsType.MOVIE -> matched?.movie?.ids
                TraktCommentsType.SHOW -> matched?.show?.ids
            }
            val pathId = ids?.bestPathId() ?: return null
            ResolvedCommentsTarget(type, pathId)
        } catch (e: Exception) {
            log.w(e) { "TMDB→Trakt lookup failed for tmdbId=$tmdbId" }
            null
        }
    }
}

private data class ResolvedCommentsTarget(
    val type: TraktCommentsType,
    val pathId: String,
)

private data class ResolvedPublicReviewIds(
    val traktTarget: ResolvedCommentsTarget?,
    val tmdbId: String?,
)

private fun TraktCommentsIdsDto.bestPathId(): String? =
    when {
        !imdb.isNullOrBlank() -> imdb
        trakt != null -> trakt.toString()
        !slug.isNullOrBlank() -> slug
        else -> null
    }

internal fun mergePublicReviewLists(
    traktItems: List<TraktCommentReview>,
    tmdbItems: List<TraktCommentReview>,
): List<TraktCommentReview> {
    val result = mutableListOf<TraktCommentReview>()
    val seenFingerprints = mutableSetOf<String>()
    val maxSize = maxOf(traktItems.size, tmdbItems.size)
    for (index in 0 until maxSize) {
        if (index < tmdbItems.size) {
            val item = tmdbItems[index]
            val fp = "${item.authorDisplayName.lowercase()}|${item.comment.take(80).lowercase()}"
            if (seenFingerprints.add(fp)) result += item
        }
        if (index < traktItems.size) {
            val item = traktItems[index]
            val fp = "${item.authorDisplayName.lowercase()}|${item.comment.take(80).lowercase()}"
            if (seenFingerprints.add(fp)) result += item
        }
    }
    return result
}

private fun filterDisplayableComments(comments: List<TraktCommentDto>): List<TraktCommentDto> =
    comments.filter { !it.comment.isNullOrBlank() }

private fun containsInlineSpoilers(comment: String?): Boolean {
    if (comment.isNullOrBlank()) return false
    return INLINE_SPOILER_REGEX.containsMatchIn(comment)
}

private fun stripInlineSpoilerMarkup(comment: String?): String {
    if (comment.isNullOrBlank()) return ""
    return comment
        .replace(INLINE_SPOILER_TAG_REGEX, "")
        .replace(Regex("\\s+"), " ")
        .trim()
}

private fun toTraktReviewModel(dto: TraktCommentDto): TraktCommentReview {
    val authorDisplayName = dto.user?.name
        ?.takeIf { it.isNotBlank() }
        ?: dto.user?.username?.takeIf { it.isNotBlank() }
        ?: runBlocking { getString(Res.string.trakt_user_fallback) }

    return TraktCommentReview(
        id = dto.id,
        authorDisplayName = authorDisplayName,
        authorUsername = dto.user?.username?.takeIf { it.isNotBlank() },
        comment = stripInlineSpoilerMarkup(dto.comment),
        spoiler = dto.spoiler == true,
        containsInlineSpoilers = containsInlineSpoilers(dto.comment),
        review = dto.review == true,
        likes = dto.likes ?: 0,
        rating = dto.userStats?.rating,
        createdAt = dto.createdAt,
        updatedAt = dto.updatedAt,
        sourceName = "Trakt",
        sourceUrl = if (dto.id > 0) "https://trakt.tv/comments/${dto.id}" else null,
    )
}

private fun toTmdbReviewModel(dto: TmdbPublicReviewDto): TraktCommentReview {
    val username = dto.authorDetails?.username?.takeIf { it.isNotBlank() }
    val displayName = dto.authorDetails?.name?.takeIf { it.isNotBlank() }
        ?: dto.author?.takeIf { it.isNotBlank() }
        ?: username
        ?: "TMDB Reviewer"
    val cleanContent = dto.content.orEmpty()
        .replace(Regex("<[^>]+>"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()
    val syntheticId = -abs(dto.id.hashCode().coerceAtLeast(1)).toLong()

    return TraktCommentReview(
        id = syntheticId,
        authorDisplayName = displayName,
        authorUsername = username,
        comment = cleanContent,
        spoiler = false,
        containsInlineSpoilers = false,
        review = true,
        likes = 0,
        rating = dto.authorDetails?.rating?.takeIf { it > 0.0 }?.roundToInt(),
        createdAt = dto.createdAt,
        updatedAt = dto.updatedAt,
        sourceName = "TMDB",
        sourceUrl = dto.url?.takeIf { it.isNotBlank() }
            ?: dto.id.takeIf { it.isNotBlank() }?.let { "https://www.themoviedb.org/review/$it" },
    )
}

private fun currentTimeMillis(): Long = TraktPlatformClock.nowEpochMs()
