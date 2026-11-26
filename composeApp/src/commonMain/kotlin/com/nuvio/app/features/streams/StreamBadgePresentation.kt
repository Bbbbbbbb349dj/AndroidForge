package com.nuvio.app.features.streams

import kotlinx.atomicfu.locks.SynchronizedObject
import kotlinx.atomicfu.locks.synchronized

object StreamBadgePresentation {
    private val filterCacheLock = SynchronizedObject()
    private var cachedRules: StreamBadgeRules? = null
    private var cachedFilters: List<CompiledStreamBadgeFilter> = emptyList()

    fun apply(groups: List<AddonStreamGroup>, rules: StreamBadgeRules): List<AddonStreamGroup> {
        val filters = compiledFilters(rules)
        if (filters.isEmpty()) return groups
        return groups.map { group ->
            group.copy(
                streams = group.streams.map { stream ->
                    val matchedBadges = StreamBadgeMatcher.matchedBadges(stream, filters)
                    if (matchedBadges.isEmpty()) {
                        stream
                    } else {
                        stream.copy(badges = mergeBadges(stream.badges, matchedBadges))
                    }
                },
            )
        }
    }

    fun applyToStreams(streams: List<StreamItem>, rules: StreamBadgeRules): List<StreamItem> {
        if (streams.isEmpty()) return streams
        val filters = compiledFilters(rules)
        if (filters.isEmpty()) return streams
        return streams.map { stream ->
            val matchedBadges = StreamBadgeMatcher.matchedBadges(stream, filters)
            if (matchedBadges.isEmpty()) stream else stream.copy(badges = mergeBadges(stream.badges, matchedBadges))
        }
    }

    /**
     * Detects the audio-variant label ("SUB", "DUB" or "DUAL") for a stream from its badge
     * names, title, description and filename. Nuvio Enhanced: drives the stream/batch variant
     * pills and keeps SUB/DUB downloads from overwriting each other.
     */
    fun audioVariantOf(stream: StreamItem): String? {
        val texts = buildList {
            stream.badges.forEach { badge -> add(badge.name) }
            stream.name?.let { add(it) }
            stream.description?.let { add(it) }
            stream.behaviorHints.filename?.let { add(it) }
        }.filter { it.isNotBlank() }
        fun mentions(word: String): Boolean = texts.any { text ->
            Regex("\\b$word\\b", RegexOption.IGNORE_CASE).containsMatchIn(text)
        }
        val hasSub = mentions("sub")
        val hasDub = mentions("dub")
        return when {
            mentions("dual") || (hasSub && hasDub) -> "DUAL"
            hasDub -> "DUB"
            hasSub -> "SUB"
            else -> null
        }
    }

    // Each addon group is presented on its own with the same rules, so their regexes are
    // compiled once and reused until the rules change.
    private fun compiledFilters(rules: StreamBadgeRules): List<CompiledStreamBadgeFilter> =
        synchronized(filterCacheLock) {
            if (cachedRules != rules) {
                cachedFilters = StreamBadgeMatcher.compile(rules)
                cachedRules = rules
            }
            cachedFilters
        }

    private fun mergeBadges(existing: List<StreamBadge>, matched: List<StreamBadge>): List<StreamBadge> {
        if (existing.isEmpty()) return matched
        val seenKeys = existing.mapTo(mutableSetOf()) { it.dedupeKey() }
        return existing + matched.filter { badge -> seenKeys.add(badge.dedupeKey()) }
    }

    private fun StreamBadge.dedupeKey(): String =
        (imageURL.takeIf { it.isNotBlank() } ?: name).lowercase()
}
